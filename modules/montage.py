"""
Montage Module — Christman Video Engine
Create montage from multiple videos.
"""

from __future__ import annotations
import random
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from modules.timeline import (
    Timeline, Track, Clip, TrackType, TransitionType,
    ResolutionPreset, STEAMPUNK_THEME, CINEMA_THEME,
    HIGH_CONTRAST_THEME, NEUTRAL_THEME
)
from modules.generator import VideoGenerator

THEMES = {
    "steampunk": STEAMPUNK_THEME,
    "cinema": CINEMA_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
    "neutral": NEUTRAL_THEME,
}


@dataclass
class MontageResult:
    success: bool
    output_path: str = ""
    duration: float = 0.0
    clips_used: int = 0
    error: str = ""


def get_video_duration(path: str) -> float:
    """Get video duration using ffprobe."""
    import subprocess
    try:
        result = subprocess.run([
            "/usr/local/opt/ffmpeg-full/bin/ffprobe", "-v", "error",
            "-show_entries", "format=duration", "-of", "csv=p=0", path
        ], capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def create_montage(
    input_paths: list[str],
    output_path: str = "data/output/montage.mp4",
    target_duration: float = 60.0,
    clip_duration: float = 10.0,
    theme: str = "steampunk",
    transition: str = "xfade",
    music: Optional[str] = None,
    caption_style: str = "kids_large",
    shuffle: bool = False,
) -> MontageResult:
    """
    Create montage from multiple videos.
    
    Strategy:
    1. Analyze all input videos (duration, aspect)
    2. Calculate clips per video to reach target duration
    3. Extract clips from each video
    4. Build timeline with theme, transitions, optional music
    5. Render
    """
    
    # Validate inputs
    validated_paths = []
    for p in input_paths:
        path_obj = Path(p).resolve()
        if path_obj.exists():
            validated_paths.append(path_obj)
        else:
            print(f"[Montage] Warning: {p} not found, skipping")
    
    if not validated_paths:
        return MontageResult(success=False, error="No valid input videos")
    
    if shuffle:
        random.shuffle(validated_paths)
    
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # Get durations
    video_infos = []
    total_available = 0.0
    for p in validated_paths:
        dur = get_video_duration(str(p))
        if dur > 0:
            video_infos.append({"path": p, "duration": dur})
            total_available += dur
    
    print(f"[Montage] {len(video_infos)} videos, {total_available:.1f}s total, Target: {target_duration}s")
    
    if total_available < target_duration:
        print(f"[Montage] Warning: Total available ({total_available:.1f}s) < target ({target_duration}s)")
    
    # Calculate clips needed
    clips_needed = int(target_duration / clip_duration)
    if clips_needed <= 0:
        clips_needed = 1
    
    # Distribute clips across videos
    clips_per_video = max(1, clips_needed // len(video_infos))
    remainder = clips_needed % len(video_infos)
    
    # Build timeline
    theme_obj = THEMES.get(theme, THEMES["steampunk"])
    timeline = Timeline(
        fps=30,
        resolution=ResolutionPreset.FHD_1080,
        theme=theme_obj,
        background_color="0x1a1a2e",
    )
    
    video_track = Track(TrackType.VIDEO)
    audio_track = Track(TrackType.AUDIO)
    audio_track.volume = 0.6
    
    clip_count = 0
    
    for i, info in enumerate(video_infos):
        num_clips = clips_per_video + (1 if i < remainder else 0)
        dur = info["duration"]
        
        if num_clips > 0 and dur > 0:
            # Evenly space clips through the video
            for j in range(num_clips):
                if clip_count >= clips_needed:
                    break
                # Calculate start position
                interval = dur / (num_clips + 1)
                start = (j + 1) * interval - clip_duration / 2
                start = max(0, min(start, dur - clip_duration))
                
                clip = Clip(
                    source=str(info["path"]),
                    start=start,
                    duration=clip_duration,
                    transition=TransitionType[transition.upper()] if transition != "none" else TransitionType.NONE,
                    transition_duration=0.5,
                    scale_mode="fill",
                )
                video_track.add_clip(clip)
                
                audio_clip = Clip(
                    source=str(info["path"]),
                    start=start,
                    duration=clip_duration,
                )
                audio_track.add_clip(audio_clip)
                clip_count += 1
    
    timeline.add_track(video_track)
    timeline.add_track(audio_track)
    
    # Add music track if provided
    if music:
        music_path = Path(music).resolve()
        if music_path.exists():
            music_track = Track(TrackType.AUDIO)
            music_track.volume = 0.3
            
            # Loop music to cover duration
            music_dur = get_video_duration(str(music_path))
            if music_dur > 0:
                loops = int(target_duration / music_dur) + 1
                for i in range(loops):
                    music_clip = Clip(
                        source=str(music_path),
                        start=0,
                        duration=min(music_dur, target_duration - i * music_dur),
                    )
                    music_track.add_clip(music_clip)
            
            timeline.add_track(music_track)
    
    # Render
    print(f"[Montage] Rendering {clip_count} clips to {output_path}")
    
    generator = VideoGenerator(work_dir=str(output_path_obj.parent / "temp"))
    result = generator.create(timeline, str(output_path_obj))
    
    if result.success:
        return MontageResult(
            success=True,
            output_path=str(output_path_obj),
            duration=result.duration,
            clips_used=clip_count,
        )
    else:
        return MontageResult(success=False, error=result.error or "Render failed")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        r = create_montage(sys.argv[1:], target_duration=30, clip_duration=5)
        print(r)