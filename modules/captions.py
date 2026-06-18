"""
Captions / Subtitles — Christman Video Engine
Whisper → FFmpeg subtitles (burned-in or .srt export).
Accessibility-first: high contrast, dyslexia-friendly fonts, large text.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal
import json
import subprocess


@dataclass
class SubtitleSegment:
    """Single caption segment with timing."""
    start: float                    # Start time (seconds)
    end: float                      # End time (seconds)
    text: str                       # Caption text
    speaker: Optional[str] = None   # Speaker label (optional)

    def to_srt(self, index: int) -> str:
        """Convert to SRT format."""
        def fmt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t - int(t)) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        return f"{index}\n{fmt(self.start)} --> {fmt(self.end)}\n{self.text}\n"

    def to_ass(self) -> str:
        """Convert to ASS format (for advanced styling)."""
        def fmt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = t - h * 3600 - m * 60
            return f"{h:01d}:{m:02d}:{s:05.2f}"
        return f"Dialogue: 0,{fmt(self.start)},{fmt(self.end)},Default,,0,0,0,,{self.text}"


@dataclass
class CaptionStyle:
    """Visual style for burned-in subtitles."""
    font: str = "Arial"                    # Font family (must be installed)
    fontsize: int = 48                     # Base font size
    color: str = "white"                   # Primary color
    outline: int = 2                       # Outline width
    outline_color: str = "black"           # Outline color
    shadow: int = 1                        # Shadow offset
    shadow_color: str = "black@0.5"        # Shadow color with alpha
    alignment: int = 2                     # ASS alignment: 2=bottom center
    margin_v: int = 50                     # Vertical margin from bottom
    margin_l: int = 20                     # Left margin
    margin_r: int = 20                     # Right margin
    bold: bool = False
    italic: bool = False
    # Dyslexia-friendly options
    dyslexia_friendly: bool = False        # If True, uses OpenDyslexic if available
    letter_spacing: int = 0
    line_spacing: int = 5

    def to_ffmpeg_subtitles_filter(self) -> str:
        """Generate FFmpeg subtitles= filter force_style string."""
        style_parts = [
            f"FontName={self.font}",
            f"FontSize={self.fontsize}",
            f"PrimaryColour=&H{self._color_to_ass(self.color)}",
            f"Outline={self.outline}",
            f"OutlineColour=&H{self._color_to_ass(self.outline_color)}",
            f"Shadow={self.shadow}",
            f"ShadowColour=&H{self._color_to_ass(self.shadow_color)}",
            f"Alignment={self.alignment}",
            f"MarginV={self.margin_v}",
            f"MarginL={self.margin_l}",
            f"MarginR={self.margin_r}",
            f"Bold={1 if self.bold else 0}",
            f"Italic={1 if self.italic else 0}",
        ]
        if self.letter_spacing:
            style_parts.append(f"Spacing={self.letter_spacing}")
        return ",".join(style_parts)

    def _color_to_ass(self, color: str) -> str:
        """Convert CSS color to ASS BBGGRR format."""
        # Simple named color mapping
        named = {
            "white": "FFFFFF", "black": "000000", "red": "FF0000",
            "yellow": "FFFF00", "cyan": "00FFFF", "green": "00FF00",
            "blue": "0000FF", "magenta": "FF00FF",
        }
        if color.startswith("@"):
            # Alpha suffix like "black@0.5"
            base, alpha = color.split("@")
            hex_color = named.get(base, "000000")
            alpha_val = int(float(alpha) * 255)
            return f"{alpha_val:02X}{hex_color}"
        return named.get(color, "FFFFFF")


# Preset styles
CAPTION_STYLES = {
    "default": CaptionStyle(),
    "high_contrast": CaptionStyle(
        fontsize=56,
        color="yellow",
        outline=3,
        outline_color="black",
        shadow=2,
        margin_v=80,
    ),
    "dyslexia_friendly": CaptionStyle(
        fontsize=52,
        font="OpenDyslexic",  # Requires font installed
        color="white",
        outline=3,
        outline_color="black",
        margin_v=70,
        letter_spacing=2,
        line_spacing=8,
        dyslexia_friendly=True,
    ),
    "kids_large": CaptionStyle(
        fontsize=64,
        color="yellow",
        outline=4,
        outline_color="black",
        shadow=2,
        margin_v=100,
        bold=True,
    ),
    "minimal": CaptionStyle(
        fontsize=36,
        color="white",
        outline=1,
        margin_v=30,
    ),
    "cinema": CaptionStyle(
        fontsize=42,
        color="white",
        outline=2,
        outline_color="black@0.8",
        shadow=0,
        margin_v=60,
        alignment=2,
    ),
}


@dataclass
class CaptionGenerator:
    """Generates captions from various sources."""
    segments: list[SubtitleSegment] = field(default_factory=list)

    @classmethod
    def from_whisper_json(cls, json_path: str) -> "CaptionGenerator":
        """Load segments from Whisper JSON output."""
        with open(json_path, "r") as f:
            data = json.load(f)
        segments = []
        for seg in data.get("segments", []):
            segments.append(SubtitleSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"].strip(),
            ))
        return cls(segments=segments)

    @classmethod
    def from_bridge_transcript(cls, transcript: str) -> "CaptionGenerator":
        """Parse bridge transcript format: [start → end] text"""
        segments = []
        for line in transcript.strip().split("\n"):
            if line.startswith("[") and "→" in line:
                try:
                    time_part, text = line.split("]", 1)
                    time_part = time_part[1:]  # Remove [
                    start_str, end_str = time_part.split("→")
                    start = float(start_str.strip().replace("s", ""))
                    end = float(end_str.strip().replace("s", ""))
                    segments.append(SubtitleSegment(start=start, end=end, text=text.strip()))
                except Exception:
                    continue
        return cls(segments=segments)

    @classmethod
    def from_timeline_clips(cls, clips) -> "CaptionGenerator":
        """Extract subtitle_text from timeline clips."""
        segments = []
        for clip in clips:
            if clip.subtitle_text:
                segments.append(SubtitleSegment(
                    start=clip.start,
                    end=clip.end,
                    text=clip.subtitle_text,
                ))
        return cls(segments=segments)

    def add_segment(self, segment: SubtitleSegment) -> "CaptionGenerator":
        self.segments.append(segment)
        return self

    def merge_gaps(self, max_gap: float = 0.5) -> "CaptionGenerator":
        """Merge segments that are close together."""
        if not self.segments:
            return self
        self.segments.sort(key=lambda s: s.start)
        merged = [self.segments[0]]
        for seg in self.segments[1:]:
            last = merged[-1]
            if seg.start - last.end <= max_gap:
                last.end = seg.end
                last.text += " " + seg.text
            else:
                merged.append(seg)
        self.segments = merged
        return self

    def split_long(self, max_chars: int = 80, max_duration: float = 7.0) -> "CaptionGenerator":
        """Split long segments for readability."""
        new_segments = []
        for seg in self.segments:
            if len(seg.text) <= max_chars and seg.end - seg.start <= max_duration:
                new_segments.append(seg)
            else:
                # Split by words
                words = seg.text.split()
                mid = len(words) // 2
                mid_time = (seg.start + seg.end) / 2
                new_segments.append(SubtitleSegment(
                    start=seg.start, end=mid_time, text=" ".join(words[:mid])
                ))
                new_segments.append(SubtitleSegment(
                    start=mid_time, end=seg.end, text=" ".join(words[mid:])
                ))
        self.segments = new_segments
        return self

    def to_srt(self, path: str) -> str:
        """Write SRT file."""
        srt_content = "\n".join(seg.to_srt(i + 1) for i, seg in enumerate(self.segments))
        Path(path).write_text(srt_content)
        return path

    def to_ass(self, path: str, style: CaptionStyle = CAPTION_STYLES["default"]) -> str:
        """Write ASS file with styling."""
        header = f"""[Script Info]
Title: Christman Video Engine Captions
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font},{style.fontsize},&H{style._color_to_ass(style.color)},&H{style._color_to_ass(style.outline_color)},&H{style._color_to_ass(style.outline_color)},&H{style._color_to_ass(style.shadow_color)},{1 if style.bold else 0},{1 if style.italic else 0},0,0,100,100,{style.letter_spacing},0,1,{style.outline},{style.shadow},{style.alignment},{style.margin_l},{style.margin_r},{style.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = "\n".join(seg.to_ass() for seg in self.segments)
        Path(path).write_text(header + events)
        return path

    def burn_into_video(
        self,
        input_video: str,
        output_video: str,
        style: CaptionStyle = CAPTION_STYLES["default"],
        preset: str = "default",
    ) -> bool:
        """Burn subtitles directly into video using FFmpeg.
        Returns True on success.
        """
        # Write temporary ASS file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False, mode="w") as f:
            ass_path = f.name
            self.to_ass(ass_path, style)

        try:
            # Build FFmpeg command
            force_style = style.to_ffmpeg_subtitles_filter()
            cmd = [
                "ffmpeg", "-y",
                "-i", input_video,
                "-vf", f"subtitles={ass_path}:force_style='{force_style}'",
                "-c:a", "copy",
                output_video
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                return False
            return True
        finally:
            Path(ass_path).unlink(missing_ok=True)

    def get_ffmpeg_filter(self, style: CaptionStyle = CAPTION_STYLES["default"]) -> str:
        """Get FFmpeg filter string for subtitles (without burning).
        Use with -vf in a larger filter graph.
        """
        # Requires ASS file written first
        return f"subtitles=captions.ass:force_style='{style.to_ffmpeg_subtitles_filter()}'"


def fetch_latest_transcript_from_bridge() -> Optional[str]:
    """Fetch latest transcript from Christman Full Sensory Bridge (port 8765)."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen("http://localhost:8765/latest", timeout=3) as r:
            return r.read().decode("utf-8")
    except Exception:
        return None


def generate_captions_from_bridge(
    output_srt: str = "data/output/captions.srt",
    style: str = "kids_large",
) -> Optional[CaptionGenerator]:
    """One-shot: fetch bridge transcript → generate caption file."""
    transcript = fetch_latest_transcript_from_bridge()
    if not transcript:
        print("No transcript available from bridge")
        return None

    gen = CaptionGenerator.from_bridge_transcript(transcript)
    gen.merge_gaps(0.5).split_long(80, 7.0)

    caption_style = CAPTION_STYLES.get(style, CAPTION_STYLES["default"])
    gen.to_srt(output_srt)
    print(f"Captions written to {output_srt} ({len(gen.segments)} segments)")
    return gen