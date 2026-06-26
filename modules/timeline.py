"""
Timeline Data Models — Christman Video Engine
The structural backbone: Timeline → Tracks → Clips.
FFmpeg filter_complex IS the timeline. One command = full render.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional
from enum import Enum


class TrackType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    TTS = "tts"  # Text-to-speech track (uses Christman Voice SDK)


class TransitionType(Enum):
    NONE = "none"
    FADE = "fade"           # Simple crossfade
    XFADE = "xfade"         # GPU-accelerated xfade (requires filter_complex)
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    ZOOM = "zoom"           # Zoom crossfade
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"


class ResolutionPreset(Enum):
    HD_720 = (1280, 720)
    FHD_1080 = (1920, 1080)
    UHD_4K = (3840, 2160)

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.value

    @property
    def width(self) -> int:
        return self.value[0]

    @property
    def height(self) -> int:
        return self.value[1]


@dataclass
class Clip:
    """A single media segment on a track."""
    source: str                                    # File path or "TTS:" prefix for generated speech
    start: float = 0.0                             # Start time on timeline (seconds)
    duration: Optional[float] = None               # None = full source duration
    trim_start: float = 0.0                        # Trim from source start
    trim_end: Optional[float] = None               # Trim from source end (None = no trim)

    # Video properties
    scale_mode: Literal["fit", "fill", "stretch", "original"] = "fit"
    position: tuple[int, int] = (0, 0)             # For picture-in-picture / overlays
    opacity: float = 1.0

    # Transition into this clip (from previous clip on same track)
    transition: TransitionType = TransitionType.NONE
    transition_duration: float = 0.5

    # Effects
    effects: list[str] = field(default_factory=list)  # FFmpeg filter names: "eq=contrast=1.2", "gblur=sigma=2"

    # TTS-specific (when source starts with "TTS:")
    tts_text: Optional[str] = None
    tts_voice: str = "derek"                       # Voice profile ID
    tts_emotion: str = "neutral"

    # Subtitle-specific (when track type = subtitle)
    subtitle_text: Optional[str] = None
    subtitle_style: Optional[dict] = None

    def __post_init__(self):
        if self.source.startswith("TTS:") and self.tts_text is None:
            self.tts_text = self.source[4:]  # Strip "TTS:" prefix

    @property
    def end(self) -> float:
        return self.start + (self.duration or 0)

    def is_tts(self) -> bool:
        return self.source.startswith("TTS:") or self.tts_text is not None

    def is_subtitle(self) -> bool:
        return self.subtitle_text is not None


@dataclass
class Track:
    """A timeline track — video, audio, subtitle, or TTS."""
    type: TrackType
    clips: list[Clip] = field(default_factory=list)
    volume: float = 1.0                            # Audio tracks only
    enabled: bool = True

    def total_duration(self) -> float:
        if not self.clips:
            return 0.0
        return max(c.end for c in self.clips)

    def add_clip(self, clip: Clip) -> "Track":
        self.clips.append(clip)
        return self

    def sort_clips(self):
        self.clips.sort(key=lambda c: c.start)


@dataclass
class Theme:
    """Visual theme — LUT + filter chain."""
    name: str = "steampunk"
    lut_path: Optional[str] = None                 # Path to .cube LUT file
    filter_chain: str = (
        "colorchannelmixer=rr=1.2:rg=0.1:rb=0.1,"
        "eq=contrast=1.2:saturation=1.3,"
        "curves=preset=medium_contrast"
    )
    color_primaries: str = "bt709"
    color_trc: str = "bt709"
    color_space: str = "bt709"


# Built-in themes
STEAMPUNK_THEME = Theme(
    name="steampunk",
    filter_chain=(
        "colorchannelmixer=rr=1.2:rg=0.1:rb=0.1,"
        "eq=contrast=1.15:brightness=0.14:saturation=1.25,"
        "curves=preset=medium_contrast"
    )
)

CINEMA_THEME = Theme(
    name="cinema",
    filter_chain=(
        "eq=contrast=1.15:saturation=1.1,"
        "colorlevels=rimin=0.02:gimin=0.02:bimin=0.02"
    )
)

HIGH_CONTRAST_THEME = Theme(
    name="high_contrast",
    filter_chain=(
        "eq=contrast=1.5:brightness=0.05:saturation=0.8,"
        "curves=preset=strong_contrast"
    )
)  # For accessibility / kids' content

NEUTRAL_THEME = Theme(
    name="neutral",
    filter_chain="format=yuv420p"
)


@dataclass
class Timeline:
    """The complete timeline — multiple tracks rendered to one video."""
    tracks: list[Track] = field(default_factory=list)
    fps: int = 30
    resolution: ResolutionPreset = ResolutionPreset.FHD_1080
    theme: Theme = field(default_factory=lambda: STEAMPUNK_THEME)
    background_color: str = "0x1a1a2e"            # Dark steampunk backdrop
    sample_rate: int = 48000                       # Audio sample rate

    def add_track(self, track: Track) -> "Timeline":
        self.tracks.append(track)
        return self

    def get_tracks_by_type(self, track_type: TrackType) -> list[Track]:
        return [t for t in self.tracks if t.type == track_type and t.enabled]

    def video_tracks(self) -> list[Track]:
        return self.get_tracks_by_type(TrackType.VIDEO)

    def audio_tracks(self) -> list[Track]:
        return self.get_tracks_by_type(TrackType.AUDIO)

    def subtitle_tracks(self) -> list[Track]:
        return self.get_tracks_by_type(TrackType.SUBTITLE)

    def tts_tracks(self) -> list[Track]:
        return self.get_tracks_by_type(TrackType.TTS)

    def total_duration(self) -> float:
        """Longest track determines timeline duration."""
        return max((t.total_duration() for t in self.tracks), default=0.0)

    def validate(self) -> list[str]:
        """Check for common issues. Returns list of warnings."""
        warnings = []
        if not self.tracks:
            warnings.append("Timeline has no tracks")
        if not self.video_tracks():
            warnings.append("No video tracks — output will be black with audio only")
        for track in self.tracks:
            if track.clips:
                for i, clip in enumerate(track.clips):
                    if clip.duration is not None and clip.duration <= 0:
                        warnings.append(f"Track {track.type.value}, clip {i}: duration <= 0")
                    if clip.transition != TransitionType.NONE and clip.transition_duration > (clip.duration or 0):
                        warnings.append(f"Track {track.type.value}, clip {i}: transition longer than clip")
        return warnings


def _short_title(text: str, max_len: int = 80, *, fallback: str = "") -> str:
    """First meaningful line for on-screen title — not the full document."""
    try:
        from engine.document_ingest import document_display_title

        return document_display_title(text, fallback=fallback)
    except Exception:
        pass
    for line in text.splitlines():
        s = line.strip()
        if s and len(s) > 3:
            if len(s) <= max_len:
                return s
            return s[: max_len - 1].rsplit(" ", 1)[0] + "…"
    return "Untitled"


def _narration_excerpt(text: str, *, max_chars: int = 500) -> str:
    body = (text or "").strip()
    if not body:
        return "Welcome to today's lesson."
    if len(body) <= max_chars:
        return body
    return body[: max_chars - 1].rsplit(" ", 1)[0] + "…"


# Example: Building a lesson timeline programmatically
def create_lesson_template(
    title: str,
    voice_being: str = "derek",
    theme: Theme = STEAMPUNK_THEME,
    broll_image: Optional[str] = None,
    *,
    target_duration: float = 60.0,
    display_title: Optional[str] = None,
    overlay_image: Optional[str] = None,
) -> Timeline:
    """Create a standard lesson video template."""
    tl = Timeline(theme=theme)
    display_title = (display_title or _short_title(title)).strip() or "Untitled"
    # ~14 spoken chars/sec; cap narration to fit requested render length
    narr_budget = max(500, min(4000, int(target_duration * 14)))
    narration = _narration_excerpt(title, max_chars=narr_budget)
    narr_secs = min(target_duration * 0.85, max(4.0, len(narration) / 14.0))

    # Video track: background + optional CIE still + title overlay
    video = Track(TrackType.VIDEO)
    video.add_clip(Clip(
        source="assets/backgrounds/steampunk_classroom.mp4",
        start=0,
        duration=None,  # Full loop - handled by stream_loop on input
        scale_mode="fill"
    ))
    if broll_image:
        video.add_clip(Clip(
            source=broll_image,
            start=0.5,
            duration=6.0,
            scale_mode="fill",
            transition=TransitionType.FADE,
            transition_duration=0.8,
        ))
    if overlay_image:
        video.add_clip(Clip(
            source=overlay_image,
            start=0,
            duration=None,
            scale_mode="fill",
            opacity=1.0,
        ))
    video.add_clip(Clip(
        source="TTS:" + display_title,
        start=1.0,
        duration=4.0,
        scale_mode="fit",
        tts_text=display_title,
        tts_voice=voice_being,
        tts_emotion="sweetheart",
        transition=TransitionType.FADE,
        transition_duration=1.0
    ))
    tl.add_track(video)

    # TTS track: narrate document / prompt (not a hardcoded placeholder)
    tts = Track(TrackType.TTS)
    tts.add_clip(Clip(
        source="TTS:" + narration,
        start=2.0,
        duration=narr_secs,
        tts_text=narration,
        tts_voice=voice_being,
        tts_emotion="warm",
    ))
    tl.add_track(tts)

    sub = Track(TrackType.SUBTITLE)
    sub.add_clip(Clip(
        source="",
        start=2.0,
        duration=narr_secs,
        subtitle_text=narration[:120],
        subtitle_style={"fontsize": 48, "color": "white", "outline": 2},
    ))
    tl.add_track(sub)

    # Audio track: ambient music
    audio = Track(TrackType.AUDIO)
    audio.volume = 0.15
    audio.add_clip(Clip(
        source="assets/music/ambient_steampunk_loop.wav",
        start=0,
        duration=None
    ))
    tl.add_track(audio)

    return tl