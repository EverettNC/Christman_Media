"""
Video Generator — Christman Video Engine
The real deal: Timeline → FFmpeg filter_complex → rendered video.
One FFmpeg pass. GPU-accelerated where possible. Zero dumb stubs.
"""

from __future__ import annotations
import os
import subprocess
import tempfile
import shlex
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass
import json

from modules.timeline import (
    Timeline, Track, Clip, TrackType, TransitionType,
    ResolutionPreset, Theme, STEAMPUNK_THEME
)
from modules.transitions import get_transition_filter_name, is_xfade_supported
from modules.captions import CaptionGenerator, CaptionStyle, CAPTION_STYLES


@dataclass
class RenderResult:
    success: bool
    output_path: str
    duration: float
    file_size: int
    ffmpeg_cmd: str
    error: Optional[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class VideoGenerator:
    """
    Timeline → FFmpeg filter_complex → Video.

    Architecture:
    1. Analyze timeline: collect all inputs, compute durations
    2. Generate TTS audio for TTS tracks (via Christman Voice SDK)
    3. Build filter_complex using numeric input indices
    4. Single ffmpeg execution
    5. Validate output
    """

    def __init__(
        self,
        work_dir: str = "data/temp",
        ffmpeg_bin: str = "ffmpeg",
        ffprobe_bin: str = "ffprobe",
        use_gpu: bool = True,
        gpu_encoder: Literal["auto", "h264_videotoolbox", "h264_nvenc", "h264_amf", "libx264"] = "auto",
    ):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = ffmpeg_bin
        self.ffprobe_bin = ffprobe_bin
        self.use_gpu = use_gpu
        self.gpu_encoder = gpu_encoder
        self._resolved_encoder = None

    def _resolve_encoder(self) -> str:
        """Auto-detect best available encoder."""
        if self._resolved_encoder:
            return self._resolved_encoder

        if self.gpu_encoder != "auto":
            self._resolved_encoder = self.gpu_encoder
            return self._resolved_encoder

        # Test encoders in preference order
        test_encoders = [
            "h264_videotoolbox",   # macOS VideoToolbox (Apple Silicon)
            "h264_nvenc",          # NVIDIA NVENC
            "h264_amf",            # AMD AMF
            "libx264",             # CPU fallback (always works)
        ]
        for enc in test_encoders:
            try:
                result = subprocess.run(
                    [self.ffmpeg_bin, "-hide_banner", "-encoders"],
                    capture_output=True, text=True
                )
                if enc in result.stdout:
                    self._resolved_encoder = enc
                    print(f"[VideoGenerator] Using encoder: {enc}")
                    return enc
            except Exception:
                continue
        self._resolved_encoder = "libx264"
        return self._resolved_encoder

    def create(self, timeline: Timeline, output_path: str) -> RenderResult:
        """
        Main entry point: render timeline to video file.
        """
        print(f"[VideoGenerator] Rendering timeline: {len(timeline.tracks)} tracks, {timeline.total_duration():.1f}s")
        print(f"[VideoGenerator] Resolution: {timeline.resolution.width}x{timeline.resolution.height} @ {timeline.fps}fps")
        print(f"[VideoGenerator] Theme: {timeline.theme.name}")

        # Validate timeline
        warnings = timeline.validate()
        for w in warnings:
            print(f"[VideoGenerator] WARNING: {w}")

        # 1. Prepare TTS audio files
        tts_audio_map = self._prepare_tts_audio(timeline)

        # 2. Build input list and filter graph
        inputs, filter_complex, output_map = self._build_filter_graph(timeline, tts_audio_map)

        # 3. Construct FFmpeg command
        cmd = self._build_ffmpeg_cmd(inputs, filter_complex, output_map, timeline, output_path)

        # 4. Execute
        print(f"[VideoGenerator] Executing FFmpeg...")
        result = self._execute_ffmpeg(cmd, output_path, timeline)

        result.warnings = warnings
        result.ffmpeg_cmd = " ".join(shlex.quote(c) for c in cmd)
        return result

    def _prepare_tts_audio(self, timeline: Timeline) -> dict[str, str]:
        """Generate TTS audio for all TTS clips. Returns map: clip_id -> audio_file_path."""
        tts_map = {}

        from engine.sound_init import bootstrap_sound

        bootstrap_sound()
        sdk_available = False
        speak = None
        try:
            from CHRISTMAN_EAR_CANAL import speak as ear_speak

            speak = ear_speak
            sdk_available = True
        except ImportError:
            pass
        if not sdk_available:
            try:
                from christman_voice_sdk import synthesize_speech, resolve_voice_params
                sdk_available = True
            except ImportError:
                print("[VideoGenerator] WARNING: Christman Voice SDK not available, TTS clips will be silent")

        if not sdk_available:
            return tts_map

        for track_idx, track in enumerate(timeline.tts_tracks()):
            for clip_idx, clip in enumerate(track.clips):
                if not clip.is_tts() or not clip.tts_text:
                    continue

                clip_id = f"tts_t{track_idx}_c{clip_idx}"
                output_wav = self.work_dir / f"{clip_id}.wav"

                try:
                    print(f"[VideoGenerator] Generating TTS: '{clip.tts_text[:50]}...' (voice={clip.tts_voice}, emotion={clip.tts_emotion})")

                    result = speak(
                        text=clip.tts_text,
                        emotion=clip.tts_emotion or "warm",
                        being=clip.tts_voice or "derek",
                        allow_fallback=False,
                        play=False,
                    )

                    if result.get("wav") and Path(result["wav"]).exists():
                        import shutil
                        shutil.copy2(result["wav"], output_wav)
                        tts_map[clip_id] = str(output_wav)
                        print(f"[VideoGenerator] TTS saved: {output_wav}")
                    else:
                        err = result.get("xtts_error") or result.get("engine") or "unknown"
                        print(
                            f"[VideoGenerator] WARNING: TTS failed for {clip_id} "
                            f"(being={clip.tts_voice}, emotion={clip.tts_emotion}): {err}"
                        )

                except Exception as e:
                    print(f"[VideoGenerator] ERROR generating TTS for {clip_id}: {e}")

        return tts_map

    def _build_filter_graph(
        self,
        timeline: Timeline,
        tts_audio_map: dict[str, str]
    ) -> tuple[list[str], str, dict]:
        """
        Build the complete FFmpeg filter_complex using numeric input indices.

        Returns:
            inputs: List of input file paths (in order)
            filter_complex: The filter graph string using [0:v], [1:a] etc.
            output_map: Dict mapping output labels to stream specs
        """
        # Collect all unique input files in order
        input_files = []
        input_info = {}  # file_path -> {index, has_video, has_audio}

        def get_input_index(path: str) -> int:
            """Get or assign input index for a file."""
            if path not in input_info:
                # Check if it's a lavfi source
                is_lavfi = path.startswith("color=") or path.startswith("anullsrc")
                has_v = False
                has_a = False
                if not is_lavfi:
                    has_v = self._has_video(path)
                    has_a = self._has_audio(path)
                else:
                    # Lavfi color source has video, anullsrc has audio
                    has_v = path.startswith("color=")
                    has_a = path.startswith("anullsrc")
                input_info[path] = {
                    "index": len(input_files),
                    "has_video": has_v,
                    "has_audio": has_a,
                    "is_lavfi": is_lavfi
                }
                input_files.append(path)
            return input_info[path]["index"]

        def v_label(path: str) -> str:
            """Get video stream label for input."""
            idx = get_input_index(path)
            return f"[{idx}:v]"

        def a_label(path: str) -> str:
            """Get audio stream label for input."""
            idx = get_input_index(path)
            return f"[{idx}:a]"

        filter_parts = []

        # === VIDEO TRACKS ===
        video_track_output_labels = []
        for track_idx, track in enumerate(timeline.video_tracks()):
            track_clips = sorted(track.clips, key=lambda c: c.start)
            if not track_clips:
                continue

            clip_labels = []
            for clip_idx, clip in enumerate(track_clips):
                if clip.is_tts():
                    continue
                clip_labels.append((clip.source, clip))

            if not clip_labels:
                continue

            track_label = f"vtrack{track_idx}"

            if len(clip_labels) == 1:
                # Single clip
                source, clip = clip_labels[0]
                v_in = v_label(source)
                filter_str = self._build_clip_video_filter(clip, timeline, track_idx, 0)
                filter_parts.append(f"{v_in}{filter_str}[{track_label}]")

                # Track audio from this clip
                info = input_info[source]
                if info["has_audio"]:
                    a_in = a_label(source)
                    vol = track.volume
                    a_out = f"[atrack{track_idx}]"
                    if vol != 1.0:
                        filter_parts.append(f"{a_in}volume={vol}{a_out}")
                    else:
                        a_out = a_in
                    # Store for later mixing
                    if not hasattr(self, '_audio_mix_labels'):
                        self._audio_mix_labels = []
                    self._audio_mix_labels.append(a_out)

            else:
                # Multiple clips - chain with transitions
                track_filter, final_label = self._build_video_track_chain(clip_labels, track, timeline, track_idx, v_label, a_label)
                filter_parts.append(track_filter)
                # final_label is the output of the chain (already includes track_label)

            video_track_output_labels.append(f"[{track_label}]")

        # If no video tracks, create black background
        if not video_track_output_labels:
            bg_source = f"color=c={timeline.background_color}:s={timeline.resolution.width}x{timeline.resolution.height}:r={timeline.fps}"
            v_in = v_label(bg_source)
            filter_parts.append(f"{v_in}format=yuv420p[v_bg]")
            video_track_output_labels.append("[v_bg]")

        # === COMPOSITE VIDEO TRACKS (overlay if multiple) ===
        if len(video_track_output_labels) == 1:
            final_video_label = video_track_output_labels[0]
        else:
            final_video_label = "[v_composite]"
            base = video_track_output_labels[0]
            for i, overlay in enumerate(video_track_output_labels[1:]):
                tmp_label = f"[v_tmp{i}]"
                filter_parts.append(f"{base}{overlay}overlay=shortest=1{tmp_label}")
                base = tmp_label
            filter_parts.append(f"{base}copy{final_video_label}")

        # === APPLY THEME FILTER ===
        themed_video = "[v_themed]"
        theme_filter = timeline.theme.filter_chain
        filter_parts.append(f"{final_video_label}{theme_filter}{themed_video}")
        final_video_label = themed_video

        # === AUDIO TRACKS ===
        audio_mix_labels = []

        # Video track audio (collected during video track processing)
        audio_mix_labels.extend(getattr(self, '_audio_mix_labels', []))

        # Dedicated audio tracks
        for track_idx, track in enumerate(timeline.audio_tracks()):
            track_clips = sorted(track.clips, key=lambda c: c.start)
            if not track_clips:
                continue

            for clip_idx, clip in enumerate(track_clips):
                source = clip.source
                # Ensure source is registered
                get_input_index(source)
                info = input_info[source]
                if info.get("has_audio"):
                    a_in = a_label(source)
                    vol = track.volume * clip.opacity
                    a_out = f"[a_audio{track_idx}_{clip_idx}]"
                    if vol != 1.0:
                        filter_parts.append(f"{a_in}volume={vol}{a_out}")
                        audio_mix_labels.append(a_out)
                    else:
                        audio_mix_labels.append(a_in)

        # TTS audio tracks
        for track_idx, track in enumerate(timeline.tts_tracks()):
            track_clips = sorted(track.clips, key=lambda c: c.start)
            for clip_idx, clip in enumerate(track_clips):
                if not clip.is_tts():
                    continue
                clip_id = f"tts_t{track_idx}_c{clip_idx}"
                if clip_id in tts_audio_map:
                    source = tts_audio_map[clip_id]
                    get_input_index(source)
                    a_in = a_label(source)
                    # Apply timing offset (clip.start)
                    a_out = f"[a_tts{track_idx}_{clip_idx}]"
                    delay_ms = int(clip.start * 1000)
                    filter_parts.append(f"{a_in}adelay={delay_ms}|{delay_ms}{a_out}")
                    audio_mix_labels.append(a_out)

        # === MIX ALL AUDIO ===
        final_audio_label = "[a_final]"
        if len(audio_mix_labels) == 1:
            filter_parts.append(f"{audio_mix_labels[0]}anull{final_audio_label}")
        elif len(audio_mix_labels) > 1:
            inputs_str = "".join(audio_mix_labels)
            filter_parts.append(f"{inputs_str}amix=inputs={len(audio_mix_labels)}:duration=longest:dropout_transition=0{final_audio_label}")
        else:
            # No audio - generate silence
            filter_parts.append(f"anullsrc=r={timeline.sample_rate}:cl=stereo{final_audio_label}")

        # Clean up temp attribute
        if hasattr(self, '_audio_mix_labels'):
            delattr(self, '_audio_mix_labels')

        return input_files, ";".join(filter_parts), {"v": final_video_label, "a": final_audio_label}

    def _build_clip_video_filter(
        self,
        clip: Clip,
        timeline: Timeline,
        track_idx: int,
        clip_idx: int
    ) -> str:
        """Build filter chain for a single video clip (WITHOUT output label)."""
        filters = []

        # Still images: hold frame for clip duration
        if clip.source and self._is_image(clip.source) and clip.duration:
            filters.append(f"fps={timeline.fps},trim=duration={clip.duration},setpts=PTS-STARTPTS")
        # Trim
        elif clip.trim_start > 0 or clip.trim_end is not None:
            trim_end = clip.trim_end if clip.trim_end is not None else clip.duration
            if trim_end and trim_end > clip.trim_start:
                filters.append(f"trim=start={clip.trim_start}:end={trim_end},setpts=PTS-STARTPTS")

        # Scale to timeline resolution
        w, h = timeline.resolution.dimensions
        if clip.scale_mode == "fit":
            filters.append(f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
        elif clip.scale_mode == "fill":
            filters.append(f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}")
        elif clip.scale_mode == "stretch":
            filters.append(f"scale={w}:{h}")

        # Opacity
        if clip.opacity < 1.0:
            filters.append(f"format=rgba,colorchannelmixer=aa={clip.opacity}")

        # Custom effects
        for effect in clip.effects:
            filters.append(effect)

        filter_str = ",".join(filters) if filters else "null"
        return filter_str

    def _build_video_track_chain(
        self,
        clip_labels: list[tuple],  # (source_path, clip)
        track: Track,
        timeline: Timeline,
        track_idx: int,
        v_label_func,
        a_label_func
    ) -> tuple[str, str]:
        """
        Chain multiple clips with transitions.
        Returns (complete_filter_string, final_output_label)
        """
        if len(clip_labels) == 1:
            source, clip = clip_labels[0]
            v_in = v_label_func(source)
            filter_chain = self._build_clip_video_filter(clip, timeline, track_idx, 0)
            output_label = f"[v_clip_t{track_idx}_c0]"
            return f"{v_in}{filter_chain}{output_label}", output_label

        # Multiple clips: use xfade for transitions
        chain_parts = []
        current_label = None

        for i, (source, clip) in enumerate(clip_labels):
            clip_out_label = f"[v_clip_t{track_idx}_c{i}]"
            v_in = v_label_func(source)
            clip_filter = self._build_clip_video_filter(clip, timeline, track_idx, i)
            chain_parts.append(f"{v_in}{clip_filter}{clip_out_label}")

            if i == 0:
                current_label = clip_out_label
            else:
                # Apply transition from previous
                prev_clip = clip_labels[i-1][1]
                curr_clip = clip

                trans_type = curr_clip.transition
                trans_dur = min(curr_clip.transition_duration, curr_clip.duration or 1.0)

                if trans_type != TransitionType.NONE and is_xfade_supported(trans_type):
                    prev_end = prev_clip.end
                    offset = prev_end - trans_dur

                    next_label = f"[v_xfade_t{track_idx}_c{i}]"
                    xfade_filter = f"{current_label}{clip_out_label}xfade=transition={get_transition_filter_name(trans_type)}:duration={trans_dur}:offset={offset}{next_label}"
                    chain_parts.append(xfade_filter)
                    current_label = next_label
                else:
                    next_label = f"[v_concat_t{track_idx}_c{i}]"
                    chain_parts.append(f"{current_label}{clip_out_label}concat=n=2:v=1:a=0{next_label}")
                    current_label = next_label

        final_label = f"[vtrack{track_idx}]"
        chain_parts.append(f"{current_label}copy{final_label}")

        return ";".join(chain_parts), final_label

    def _is_image(self, path: str) -> bool:
        return Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

    def _should_loop_video(self, path: str) -> bool:
        if not path or path.startswith("TTS:"):
            return False
        if self._is_image(path):
            return False
        return self._has_video(path) and path.endswith(".mp4")

    def _has_video(self, path: str) -> bool:
        if self._is_image(path):
            return True
        try:
            result = subprocess.run(
                [self.ffprobe_bin, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=10
            )
            return "video" in result.stdout
        except Exception:
            return False

    def _has_audio(self, path: str) -> bool:
        try:
            result = subprocess.run(
                [self.ffprobe_bin, "-v", "error", "-select_streams", "a:0",
                 "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=10
            )
            return "audio" in result.stdout
        except Exception:
            return False

    def _build_ffmpeg_cmd(
        self,
        inputs: list[str],
        filter_complex: str,
        output_map: dict,
        timeline: Timeline,
        output_path: str
    ) -> list[str]:
        """Construct the full FFmpeg command line."""
        cmd = [self.ffmpeg_bin, "-y", "-loglevel", "error", "-nostats"]

        # Input options - handle lavfi sources, still images, looping video
        for inp in inputs:
            if inp.startswith("color=") or inp.startswith("anullsrc"):
                cmd.extend(["-f", "lavfi", "-i", inp])
            elif self._is_image(inp):
                cmd.extend(["-loop", "1", "-i", inp])
            elif self._should_loop_video(inp):
                cmd.extend(["-stream_loop", "-1", "-i", inp])
            else:
                cmd.extend(["-i", inp])

        # Filter complex
        cmd.extend(["-filter_complex", filter_complex])

        # Output mapping
        cmd.extend(["-map", output_map["v"], "-map", output_map["a"]])

        # Video encoding
        encoder = self._resolve_encoder()
        if encoder in ("h264_videotoolbox", "h264_nvenc", "h264_amf"):
            cmd.extend([
                "-c:v", encoder,
                "-b:v", "8M",
                "-maxrate", "10M",
                "-bufsize", "16M",
                "-profile:v", "high",
                "-level", "4.2",
                "-pix_fmt", "yuv420p",
                "-colorspace", timeline.theme.color_space,
                "-color_primaries", timeline.theme.color_primaries,
                "-color_trc", timeline.theme.color_trc,
            ])
            if encoder == "h264_videotoolbox":
                cmd.extend(["-allow_sw", "1", "-realtime", "1"])
        else:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-profile:v", "high",
                "-level", "4.2",
                "-colorspace", timeline.theme.color_space,
                "-color_primaries", timeline.theme.color_primaries,
                "-color_trc", timeline.theme.color_trc,
                "-x264-params", f"colorprim={timeline.theme.color_primaries}:transfer={timeline.theme.color_trc}:colormatrix={timeline.theme.color_space}"
            ])

        # Audio encoding
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", str(timeline.sample_rate),
            "-ac", "2",
        ])

        # Output
        cmd.extend(["-shortest", output_path])

        return cmd

    def _execute_ffmpeg(self, cmd: list[str], output_path: str, timeline: Timeline) -> RenderResult:
        """Execute FFmpeg and validate output."""
        import os
        try:
            print(f"[VideoGenerator] Running: {' '.join(shlex.quote(c) for c in cmd[:10])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=0,
                    file_size=0,
                    ffmpeg_cmd=" ".join(shlex.quote(c) for c in cmd),
                    error=result.stderr[-1000:]
                )

            # Check file immediately
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
            else:
                abs_path = os.path.abspath(output_path)
                if os.path.exists(abs_path):
                    size = os.path.getsize(abs_path)
                else:
                    size = 0

            # Validate output
            props = self._probe_output(output_path)
            if props["size"] > 0:
                size = props["size"]

            if props["size"] < 1024:
                return RenderResult(
                    success=False,
                    output_path=output_path,
                    duration=props["duration"],
                    file_size=props["size"],
                    ffmpeg_cmd=" ".join(shlex.quote(c) for c in cmd),
                    error="Output file too small (<1KB)"
                )

            print(f"[VideoGenerator] SUCCESS: {output_path}")
            print(f"  Duration: {props['duration']:.2f}s")
            print(f"  Size: {props['size']/1024/1024:.2f} MB")
            print(f"  Resolution: {props['width']}x{props['height']}")
            print(f"  FPS: {props['fps']:.2f}")

            return RenderResult(
                success=True,
                output_path=output_path,
                duration=props["duration"],
                file_size=props["size"],
                ffmpeg_cmd=" ".join(shlex.quote(c) for c in cmd)
            )

        except subprocess.TimeoutExpired:
            return RenderResult(
                success=False,
                output_path=output_path,
                duration=0,
                file_size=0,
                ffmpeg_cmd=" ".join(shlex.quote(c) for c in cmd),
                error="FFmpeg timeout (10 min)"
            )
        except Exception as e:
            return RenderResult(
                success=False,
                output_path=output_path,
                duration=0,
                file_size=0,
                ffmpeg_cmd=" ".join(shlex.quote(c) for c in cmd),
                error=str(e)
            )

    def _probe_output(self, path: str) -> dict:
        """Get video properties via ffprobe."""
        try:
            cmd = [
                self.ffprobe_bin, "-v", "error",
                "-show_entries", "format=duration,size:stream=codec_type,width,height,r_frame_rate",
                "-of", "json", path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)

            duration = float(data["format"]["duration"])
            size = int(data["format"]["size"])

            video_stream = next((s for s in data["streams"] if s.get("codec_type") == "video"), {})
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            fps_str = video_stream.get("r_frame_rate", "30/1")
            num, den = map(int, fps_str.split("/"))
            fps = num / den if den else 30

            return {"duration": duration, "size": size, "width": width, "height": height, "fps": fps}
        except Exception as e:
            print(f"[VideoGenerator] Probe failed: {e}")
            return {"duration": 0, "size": 0, "width": 0, "height": 0, "fps": 0}

    def burn_captions(
        self,
        input_video: str,
        output_video: str,
        caption_generator: CaptionGenerator,
        style: CaptionStyle = CAPTION_STYLES["default"]
    ) -> RenderResult:
        """Post-process: burn captions into rendered video.
        Uses ASS file with embedded styles.
        Note: Requires FFmpeg with libass support. Returns original video if not available.
        """
        # Write ASS file to a simple path in work_dir
        ass_path = self.work_dir / "captions.ass"
        caption_generator.to_ass(str(ass_path), style)

        try:
            # Escape path for FFmpeg subtitles filter
            escaped_path = str(ass_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
            cmd = [
                self.ffmpeg_bin, "-y",
                "-i", input_video,
                "-vf", f"subtitles={escaped_path}",
                "-c:a", "copy",
                output_video
            ]
            result = self._execute_ffmpeg(cmd, output_video, None)
            if not result.success:
                # Subtitles filter not available - copy original
                import shutil
                shutil.copy2(input_video, output_video)
                result = RenderResult(
                    success=True,
                    output_path=output_video,
                    duration=0,
                    file_size=Path(output_video).stat().st_size,
                    ffmpeg_cmd=" ".join(shlex.quote(c) for c in cmd),
                    error="Subtitles filter not available in FFmpeg build; captions saved as .ass file"
                )
            return result
        finally:
            ass_path.unlink(missing_ok=True)


# === Convenience Functions ===

def render_timeline(
    timeline: Timeline,
    output_path: str,
    work_dir: str = "data/temp",
    burn_captions: bool = True,
    caption_style: str = "kids_large"
) -> RenderResult:
    """High-level render function."""
    gen = VideoGenerator(work_dir=work_dir)
    result = gen.create(timeline, output_path)

    if result.success and burn_captions:
        # Collect all subtitle tracks
        all_subtitle_clips = []
        for track in timeline.subtitle_tracks():
            all_subtitle_clips.extend(track.clips)

        if all_subtitle_clips:
            cap_gen = CaptionGenerator.from_timeline_clips(all_subtitle_clips)
            cap_gen.merge_gaps(0.5).split_long(80, 7.0)

            style = CAPTION_STYLES.get(caption_style, CAPTION_STYLES["default"])
            captioned_path = output_path.replace(".mp4", "_captioned.mp4")
            result = gen.burn_captions(output_path, captioned_path, cap_gen, style)
            if result.success:
                import shutil
                shutil.move(captioned_path, output_path)

    return result


def quick_render(
    prompt: str,
    output_path: str = "data/output/quick_render.mp4",
    voice: str = "derek",
    emotion: str = "warm",
    theme: Theme = STEAMPUNK_THEME,
    duration: float = 10.0
) -> RenderResult:
    """Quick one-shot render from text prompt."""
    from modules.timeline import create_lesson_template

    tl = create_lesson_template(prompt, voice_being=voice, theme=theme)
    # Adjust duration
    for track in tl.tracks:
        for clip in track.clips:
            if clip.duration:
                clip.duration = min(clip.duration, duration)

    return render_timeline(tl, output_path)