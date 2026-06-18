"""
Batch Module — Christman Video Engine
Batch process multiple videos with same template/settings.
"""

from __future__ import annotations
import subprocess
import concurrent.futures
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import glob

from modules.timeline import (
    Timeline, Track, Clip, TrackType, TransitionType,
    ResolutionPreset, STEAMPUNK_THEME, CINEMA_THEME,
    HIGH_CONTRAST_THEME, NEUTRAL_THEME
)
from modules.generator import VideoGenerator, RenderResult

THEMES = {
    "steampunk": STEAMPUNK_THEME,
    "cinema": CINEMA_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
    "neutral": NEUTRAL_THEME,
}


@dataclass
class BatchResult:
    success: bool
    total: int = 0
    successful: int = 0
    failed: int = 0
    results: list[BatchItemResult] = field(default_factory=list)
    error: str = ""


@dataclass
class BatchItemResult:
    input_name: str
    success: bool
    output_path: str = ""
    error: str = ""


def load_and_fill_template(
    template_path: str,
    slots: dict,
    input_video: str,
) -> Timeline:
    """Load JSON template and fill with slots + input video."""
    import json
    from modules.timeline import (
        Timeline, Track, Clip, TrackType, TransitionType,
        ResolutionPreset
    )
    
    with open(template_path, "r") as f:
        data = json.load(f)
    
    tl_data = data["timeline"]
    
    # Slot replacement
    json_str = json.dumps(tl_data)
    for key, value in slots.items():
        json_str = json_str.replace(f"{{{{{key}}}}}", str(value))
    # Also replace input video placeholder
    json_str = json_str.replace("{{input_video}}", input_video)
    json_str = json_str.replace("{{source_video}}", input_video)
    tl_data = json.loads(json_str)
    
    # Reconstruct Timeline
    tl = Timeline(
        fps=tl_data.get("fps", 30),
        resolution=ResolutionPreset[tl_data.get("resolution", "FHD_1080")],
        theme=THEMES.get(tl_data.get("theme", "steampunk"), THEMES["steampunk"]),
        background_color=tl_data.get("background_color", "0x1a1a2e"),
    )
    
    for track_data in tl_data.get("tracks", []):
        track = Track(TrackType(track_data["type"]))
        track.volume = track_data.get("volume", 1.0)
        track.enabled = track_data.get("enabled", True)
        
        for clip_data in track_data.get("clips", []):
            clip = Clip(
                source=clip_data["source"],
                start=clip_data.get("start", 0),
                duration=clip_data.get("duration"),
                trim_start=clip_data.get("trim_start", 0),
                trim_end=clip_data.get("trim_end"),
                scale_mode=clip_data.get("scale_mode", "fit"),
                position=tuple(clip_data.get("position", [0, 0])),
                opacity=clip_data.get("opacity", 1.0),
                transition=TransitionType(clip_data.get("transition", "none")),
                transition_duration=clip_data.get("transition_duration", 0.5),
                effects=clip_data.get("effects", []),
                tts_text=clip_data.get("tts_text"),
                tts_voice=clip_data.get("tts_voice", "derek"),
                tts_emotion=clip_data.get("tts_emotion", "neutral"),
                subtitle_text=clip_data.get("subtitle_text"),
                subtitle_style=clip_data.get("subtitle_style"),
            )
            track.add_clip(clip)
        
        tl.add_track(track)
    
    return tl


def process_single_video(
    input_path: str,
    template_path: str,
    output_dir: Path,
    slots: dict,
) -> BatchItemResult:
    """Process a single video through the template."""
    input_obj = Path(input_path)
    
    try:
        print(f"[Batch] Processing: {input_obj.name}")
        
        # Fill template with input video
        timeline = load_and_fill_template(template_path, slots, str(input_obj))
        
        # Output path
        output_path = output_dir / f"{input_obj.stem}_processed.mp4"
        
        # Render
        generator = VideoGenerator(work_dir=str(output_dir / "temp" / input_obj.stem))
        result = generator.create(timeline, str(output_path))
        
        if result.success:
            return BatchItemResult(
                input_name=input_obj.name,
                success=True,
                output_path=str(output_path),
            )
        else:
            return BatchItemResult(
                input_name=input_obj.name,
                success=False,
                error=result.error or "Render failed",
            )
    except Exception as e:
        return BatchItemResult(
            input_name=input_obj.name,
            success=False,
            error=str(e),
        )


def batch_process(
    input_dir: str,
    template_path: str,
    output_dir: str = "data/output/batch",
    slots: Optional[list] = None,
    pattern: str = "*.mp4",
    parallel: int = 2,
) -> BatchResult:
    """
    Batch process multiple videos with same template/settings.
    
    Args:
        input_dir: Directory containing input videos
        template_path: JSON template file
        output_dir: Output directory
        slots: Template slots as key=value strings
        pattern: File pattern to match (e.g., "*.mp4", "*.mov")
        parallel: Number of parallel jobs
    """
    
    input_dir_obj = Path(input_dir).resolve()
    if not input_dir_obj.exists():
        return BatchResult(success=False, error=f"Input directory not found: {input_dir}")
    
    template_obj = Path(template_path).resolve()
    if not template_obj.exists():
        return BatchResult(success=False, error=f"Template not found: {template_path}")
    
    output_dir_obj = Path(output_dir)
    output_dir_obj.mkdir(parents=True, exist_ok=True)
    
    # Parse slots
    slot_dict = {}
    if slots:
        for slot in slots:
            if "=" in slot:
                k, v = slot.split("=", 1)
                slot_dict[k] = v
    
    # Find matching files
    pattern_path = input_dir_obj / pattern
    input_files = glob.glob(str(pattern_path))
    
    if not input_files:
        return BatchResult(success=False, error=f"No files matching {pattern} in {input_dir}")
    
    print(f"[Batch] Found {len(input_files)} files to process")
    print(f"[Batch] Template: {template_obj.name}")
    print(f"[Batch] Slots: {slot_dict}")
    print(f"[Batch] Parallel jobs: {parallel}")
    
    # Process in parallel
    results = []
    
    if parallel > 1:
        with concurrent.futures.ProcessPoolExecutor(max_workers=parallel) as executor:
            futures = {
                executor.submit(
                    process_single_video,
                    f, str(template_obj), output_dir_obj, slot_dict
                ): f for f in input_files
            }
            
            for future in concurrent.futures.as_completed(futures):
                f = futures[future]
                try:
                    r = future.result()
                    results.append(r)
                    status = "✅" if r.success else "❌"
                    print(f"  {status} {r.input_name}")
                    if not r.success:
                        print(f"     Error: {r.error}")
                except Exception as e:
                    results.append(BatchItemResult(
                        input_name=Path(f).name,
                        success=False,
                        error=str(e),
                    ))
    else:
        # Sequential
        for f in input_files:
            r = process_single_video(f, str(template_obj), output_dir_obj, slot_dict)
            results.append(r)
            status = "✅" if r.success else "❌"
            print(f"  {status} {r.input_name}")
            if not r.success:
                print(f"     Error: {r.error}")
    
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    return BatchResult(
        success=successful > 0,
        total=len(results),
        successful=successful,
        failed=failed,
        results=results,
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        r = batch_process(sys.argv[1], sys.argv[2])
        print(f"Total: {r.total}, Success: {r.successful}, Failed: {r.failed}")