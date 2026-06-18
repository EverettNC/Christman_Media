"""
Highlights Module — Christman Video Engine
Extract highlights from video using transcript/audio/scene analysis.
"""

from __future__ import annotations
import subprocess
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from modules.timeline import (
    Timeline, Track, Clip, TrackType, TransitionType,
    ResolutionPreset, STEAMPUNK_THEME, CINEMA_THEME,
    HIGH_CONTRAST_THEME, NEUTRAL_THEME
)
from modules.generator import VideoGenerator
from modules.captions import CAPTION_STYLES

THEMES = {
    "steampunk": STEAMPUNK_THEME,
    "cinema": CINEMA_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
    "neutral": NEUTRAL_THEME,
}


@dataclass
class Highlight:
    start: float
    end: float
    reason: str
    score: float = 0.0


@dataclass
class HighlightsResult:
    success: bool
    highlights_found: int = 0
    highlights: list[Highlight] = field(default_factory=list)
    output_path: str = ""
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


def get_audio_energy_segments(path: str) -> list[tuple[float, float, float]]:
    """Get audio energy segments using ffmpeg."""
    try:
        # Use volumedetect for quick energy analysis
        result = subprocess.run([
            "/usr/local/opt/ffmpeg-full/bin/ffmpeg", "-i", path,
            "-af", "volumedetect", "-f", "null", "-"
        ], capture_output=True, text=True, timeout=30)
        
        # Parse mean_volume and max_volume
        mean_vol = -60.0
        max_vol = -60.0
        for line in result.stderr.split('\n'):
            if 'mean_volume' in line:
                mean_vol = float(line.split(':')[-1].strip().replace('dB', ''))
            elif 'max_volume' in line:
                max_vol = float(line.split(':')[-1].strip().replace('dB', ''))
        
        # Return a simple high-energy indicator
        return [(0, 1, mean_vol)]
    except Exception:
        return []


def extract_highlights(
    input_path: str,
    output_dir: str = "data/output/highlights",
    method: str = "auto",
    max_highlights: int = 10,
    min_duration: float = 3.0,
    max_duration: float = 30.0,
    theme: str = "steampunk",
    transition: str = "xfade",
    caption_style: str = "kids_large",
) -> HighlightsResult:
    """
    Extract highlights from video using multiple detection methods.
    
    Methods:
    - auto: Combine all methods
    - transcript: Use bridge transcript for speech-based highlights
    - audio: Use audio energy peaks
    - scene: Use scene change detection
    - motion: Use motion detection (placeholder)
    """
    
    input_path_obj = Path(input_path).resolve()
    if not input_path_obj.exists():
        return HighlightsResult(success=False, error=f"Input not found: {input_path_obj}")
    
    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)
    
    duration = get_video_duration(str(input_path_obj))
    if duration <= 0:
        return HighlightsResult(success=False, error="Could not determine video duration")
    
    print(f"[Highlights] Source: {duration:.1f}s, Method: {method}")
    
    highlights = []
    
    # Method: Scene changes
    if method in ("auto", "scene"):
        scene_times = detect_scene_changes(str(input_path_obj))
        print(f"[Highlights] Scene changes: {len(scene_times)}")
        
        if scene_times:
            for i, s in enumerate(scene_times):
                if i >= max_highlights:
                    break
                # Create highlight around scene change
                start = max(0, s - min_duration / 2)
                end = min(duration, s + min_duration / 2)
                if end - start >= min_duration:
                    highlights.append(Highlight(
                        start=start,
                        end=end,
                        reason=f"Scene change at {s:.1f}s",
                        score=0.8
                    ))
        else:
            # Fallback: evenly spaced segments
            segment_duration = min(min_duration * 2, duration / max(1, max_highlights))
            for i in range(max_highlights):
                start = i * segment_duration
                if start >= duration:
                    break
                end = min(start + segment_duration, duration)
                if end - start >= min_duration:
                    highlights.append(Highlight(
                        start=start,
                        end=end,
                        reason=f"Time-based segment {i+1}",
                        score=0.5
                    ))
    
    # Method: Audio energy (simplified)
    if method in ("auto", "audio"):
        # For now, use scene changes as proxy
        # Could be enhanced with actual audio peak detection
        pass
    
    # Method: Transcript-based
    if method in ("auto", "transcript"):
        try:
            from modules.captions import fetch_latest_transcript_from_bridge
            transcript = fetch_latest_transcript_from_bridge()
            if transcript:
                lines = transcript.strip().split('\n')
                for i, line in enumerate(lines):
                    if len(highlights) >= max_highlights:
                        break
                    if line.strip():
                        # Rough time estimation from transcript
                        est_time = min(i * 5, duration - min_duration)
                        highlights.append(Highlight(
                            start=est_time,
                            end=min(est_time + min_duration, duration),
                            reason=f"Transcript: {line[:50]}...",
                            score=0.7
                        ))
        except Exception:
            pass
    
    # Deduplicate and sort
    highlights = sorted(highlights, key=lambda h: h.start)
    # Simple dedup - merge overlapping
    deduped = []
    for h in highlights:
        if not deduped or h.start > deduped[-1].end:
            deduped.append(h)
        else:
            # Extend previous
            deduped[-1].end = max(deduped[-1].end, h.end)
            deduped[-1].score = max(deduped[-1].score, h.score)
    
    highlights = deduped[:max_highlights]
    
    if not highlights:
        return HighlightsResult(success=False, error="No highlights detected")
    
    print(f"[Highlights] Found {len(highlights)} highlights")
    
    # Build timeline with highlights
    theme_obj = THEMES.get(theme, THEMES["steampunk"])
    timeline = Timeline(
        fps=30,
        resolution=ResolutionPreset.FHD_1080,
        theme=theme_obj,
        background_color="0x1a1a2e",
    )
    
    video_track = Track(TrackType.VIDEO)
    audio_track = Track(TrackType.AUDIO)
    audio_track.volume = 0.8
    
    for i, h in enumerate(highlights):
        clip = Clip(
            source=str(input_path_obj),
            start=h.start,
            duration=h.end - h.start,
            transition=TransitionType[transition.upper()] if transition != "none" else TransitionType.NONE,
            transition_duration=0.5,
            scale_mode="fill",
        )
        video_track.add_clip(clip)
        
        audio_clip = Clip(
            source=str(input_path_obj),
            start=h.start,
            duration=h.end - h.start,
        )
        audio_track.add_clip(audio_clip)
    
    timeline.add_track(video_track)
    timeline.add_track(audio_track)
    
    # Render
    output_path = output_dir_obj / f"highlights_{input_path_obj.stem}.mp4"
    
    print(f"[Highlights] Rendering to {output_path}")
    
    generator = VideoGenerator(work_dir=str(output_dir_obj / "temp"))
    result = generator.create(timeline, str(output_path))
    
    if result.success:
        return HighlightsResult(
            success=True,
            highlights_found=len(highlights),
            highlights=highlights,
            output_path=str(output_path),
        )
    else:
        return HighlightsResult(success=False, error=result.error or "Render failed")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        r = extract_highlights(sys.argv[1], method="auto")
        print(r)