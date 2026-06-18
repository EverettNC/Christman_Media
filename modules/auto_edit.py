"""
Auto-Edit Module — Christman Video Engine
Drop a video in, specify clip length, get themed output automatically.
"""

from __future__ import annotations
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from modules.timeline import (
    Timeline, Track, Clip, TrackType, TransitionType,
    ResolutionPreset, Theme, STEAMPUNK_THEME, CINEMA_THEME,
    HIGH_CONTRAST_THEME, NEUTRAL_THEME
)
from modules.generator import VideoGenerator, RenderResult
from modules.captions import CaptionGenerator, CaptionStyle, CAPTION_STYLES, fetch_latest_transcript_from_bridge

# Theme registry (mirror from CLI)
THEMES = {
    "steampunk": STEAMPUNK_THEME,
    "cinema": CINEMA_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
    "neutral": NEUTRAL_THEME,
}


@dataclass
class AutoEditResult:
    success: bool
    output_path: str = ""
    clips_created: int = 0
    total_duration: float = 0.0
    error: str = ""


def get_video_duration(path: str) -> float:
    """Get video duration using ffprobe."""
    try:
        result = subprocess.run([
            "/usr/local/opt/ffmpeg-full/bin/ffprobe", "-v", "error",
            "-show_entries", "format=duration", "-of", "csv=p=0", path
        ], capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def detect_scene_changes(path: str, threshold: float = 0.3) -> list[float]:
    """Detect scene changes using ffmpeg's select filter with scene detection."""
    try:
        # Use ffmpeg scene detection
        result = subprocess.run([
            "/usr/local/opt/ffmpeg-full/bin/ffmpeg", "-i", path,
            "-filter:v", f"select='gt(scene,{threshold})',metadata=print:file=/dev/stdout",
            "-f", "null", "-"
        ], capture_output=True, text=True, timeout=60)
        
        scene_times = []
        for line in result.stderr.split('\n'):
            if 'pts_time:' in line:
                try:
                    t = float(line.split('pts_time:')[1].split()[0])
                    scene_times.append(t)
                except Exception:
                    pass
        return scene_times
    except Exception:
        return []


def get_audio_energy_peaks(path: str, window: float = 1.0) -> list[float]:
    """Find high-energy audio segments."""
    try:
        # Use ffmpeg astats to find loud segments
        result = subprocess.run([
            "/usr/local/opt/ffmpeg-full/bin/ffmpeg", "-i", path,
            "-filter:a", f"astats=metadata=1:reset=1,ametadata=print:file=/dev/stdout",
            "-f", "null", "-"
        ], capture_output=True, text=True, timeout=60)
        
        # Parse RMS values - simplified approach
        return []
    except Exception:
        return []


def auto_edit_video(
    input_path: str,
    output_dir: str = "data/output/auto_edit",
    clip_duration: float = 15.0,
    target_duration: float = 60.0,
    theme: str = "steampunk",
    transition: str = "fade",
    voice: str = "derek",
    emotion: str = "warm",
    caption_style: str = "kids_large",
    add_intro: bool = False,
    add_outro: bool = False,
    bridge_transcript: bool = False,
) -> AutoEditResult:
    """
    Auto-edit a source video into themed clips.
    
    Strategy:
    1. Analyze source video (duration, scene changes, audio energy)
    2. Create clips of specified duration
    3. Build timeline with theme, transitions, TTS, captions
    4. Render single output video
    """
    
    input_path_obj = Path(input_path).resolve()
    if not input_path_obj.exists():
        return AutoEditResult(success=False, error=f"Input not found: {input_path_obj}")
    
    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)
    
    # Get source duration
    source_duration = get_video_duration(str(input_path))
    if source_duration <= 0:
        return AutoEditResult(success=False, error="Could not determine video duration")
    
    print(f"[AutoEdit] Source: {source_duration:.1f}s, Target: {target_duration}s, Clip: {clip_duration}s")
    
    # Detect scene changes for smart cuts
    scene_times = detect_scene_changes(str(input_path_obj))
    print(f"[AutoEdit] Scene changes detected: {len(scene_times)}")
    
    # Calculate clips
    max_clips = int(target_duration / clip_duration)
    num_clips = min(max_clips, int(source_duration / clip_duration))
    
    if num_clips <= 0:
        num_clips = 1
        clip_duration = min(clip_duration, source_duration)
    
    # Smart clip start times - align with scene changes when possible
    clip_starts = []
    for i in range(num_clips):
        ideal_start = i * clip_duration
        # Find nearest scene change
        best_start = ideal_start
        for scene_t in scene_times:
            if abs(scene_t - ideal_start) < clip_duration * 0.3:
                best_start = scene_t
                break
        clip_starts.append(best_start)
    
    # Build timeline
    theme_obj = THEMES.get(theme, THEMES["steampunk"])
    timeline = Timeline(
        fps=30,
        resolution=ResolutionPreset.FHD_1080,
        theme=theme_obj,
        background_color="0x1a1a2e",
    )
    
    # Video track
    video_track = Track(TrackType.VIDEO)
    
    # Add intro if requested
    if add_intro:
        intro_clip = Clip(
            source=str(input_path_obj),
            start=0,
            duration=3.0,
            transition=TransitionType.FADE,
            transition_duration=1.0,
            effects=[theme_obj.filter_chain],
        )
        video_track.add_clip(intro_clip)
    
    # Main clips
    for i, start in enumerate(clip_starts):
        clip = Clip(
            source=str(input_path_obj),
            start=start,
            duration=clip_duration,
            transition=TransitionType[transition.upper()] if transition != "none" else TransitionType.NONE,
            transition_duration=0.5,
            scale_mode="fill",
        )
        video_track.add_clip(clip)
    
    # Add outro if requested
    outro_start = 0
    if add_outro:
        outro_start = max(0, source_duration - 3.0)
        outro_clip = Clip(
            source=str(input_path_obj),
            start=outro_start,
            duration=3.0,
            transition=TransitionType.FADE,
            transition_duration=1.0,
        )
        video_track.add_clip(outro_clip)
    
    timeline.add_track(video_track)
    
    # Audio track (source audio)
    audio_track = Track(TrackType.AUDIO)
    audio_track.volume = 0.3  # Lower source audio for TTS mix
    
    for i, start in enumerate(clip_starts):
        clip = Clip(
            source=str(input_path_obj),
            start=start,
            duration=clip_duration,
        )
        audio_track.add_clip(clip)
    
    if add_intro:
        intro_audio = Clip(source=str(input_path_obj), start=0, duration=3.0)
        audio_track.clips.insert(0, intro_audio)
    if add_outro:
        outro_audio = Clip(source=str(input_path_obj), start=outro_start, duration=3.0)
        audio_track.add_clip(outro_audio)
    
    timeline.add_track(audio_track)
    
    # TTS track - generate narrative
    tts_track = Track(TrackType.TTS)
    
    if add_intro:
        tts_track.add_clip(Clip(
            source="",
            start=0,
            duration=3.0,
            tts_text="Welcome to the Christman Video Engine. Auto-edit mode engaged.",
            tts_voice=voice,
            tts_emotion=emotion,
        ))
    
    for i, start in enumerate(clip_starts):
        tts_track.add_clip(Clip(
            source="",
            start=start + (0.5 if add_intro else 0),
            duration=clip_duration,
            tts_text=f"Clip {i+1}. Extracted from source at {start:.1f} seconds. Duration {clip_duration} seconds.",
            tts_voice=voice,
            tts_emotion=emotion,
        ))
    
    if add_outro:
        tts_end_time = sum(c.duration for c in tts_track.clips if c.duration) + 0.5
        tts_track.add_clip(Clip(
            source="",
            start=tts_end_time,
            duration=3.0,
            tts_text="Auto-edit complete. Thank you for using the Christman Video Engine.",
            tts_voice=voice,
            tts_emotion=emotion,
        ))
    
    timeline.add_track(tts_track)
    
    # Caption track
    subtitle_track = Track(TrackType.SUBTITLE)
    
    if bridge_transcript:
        print("[AutoEdit] Fetching transcript from bridge...")
        transcript = fetch_latest_transcript_from_bridge()
        if transcript:
            # Parse transcript into segments (simplified)
            lines = transcript.strip().split('\n')
            for i, line in enumerate(lines[:num_clips]):
                if line.strip():
                    subtitle_track.add_clip(Clip(
                        source="",
                        start=clip_starts[i] + (0.5 if add_intro else 0),
                        duration=clip_duration,
                        subtitle_text=line[:100],
                        subtitle_style=caption_style,
                    ))
    
    if subtitle_track.clips:
        timeline.add_track(subtitle_track)
    
    # Render
    output_path = output_dir_obj / f"auto_edit_{input_path_obj.stem}_{int(clip_duration)}s.mp4"
    
    print(f"[AutoEdit] Rendering {num_clips} clips to {output_path}")
    
    generator = VideoGenerator(work_dir=str(output_dir_obj / "temp"))
    result = generator.create(timeline, str(output_path))
    
    if result.success:
        return AutoEditResult(
            success=True,
            output_path=str(output_path),
            clips_created=num_clips,
            total_duration=result.duration,
        )
    else:
        return AutoEditResult(success=False, error=result.error or "Render failed")


# Quick test
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        r = auto_edit_video(sys.argv[1], clip_duration=10, target_duration=30)
        print(r)