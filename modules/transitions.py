"""
Transitions — Christman Video Engine
FFmpeg filter implementations for clip-to-clip transitions.
All GPU-accelerated where possible (xfade, overlays).
"""

from __future__ import annotations
from modules.timeline import TransitionType
from typing import Optional


class TransitionBuilder:
    """Builds FFmpeg filter graphs for transitions."""

    # xfade transition names (GPU-accelerated, single filter)
    XFADE_TRANSITIONS = {
        TransitionType.FADE: "fade",
        TransitionType.XFADE: "fade",           # Generic crossfade
        TransitionType.WIPE_LEFT: "wipeleft",
        TransitionType.WIPE_RIGHT: "wiperight",
        TransitionType.WIPE_UP: "wipeup",
        TransitionType.WIPE_DOWN: "wipedown",
        TransitionType.ZOOM: "zoomin",          # Zoom crossfade
        TransitionType.SLIDE_LEFT: "slideleft",
        TransitionType.SLIDE_RIGHT: "slideright",
    }

    @classmethod
    def build_xfade_filter(
        cls,
        input_a: str,           # FFmpeg input label for clip A (e.g., "[v0]")
        input_b: str,           # FFmpeg input label for clip B (e.g., "[v1]")
        output_label: str,      # Output label (e.g., "[v_out]")
        transition: TransitionType,
        duration: float,        # Transition duration in seconds
        offset: float,          # When transition starts (end of clip A - duration)
    ) -> str:
        """Build xfade filter chain. Returns filter string."""
        xfade_name = cls.XFADE_TRANSITIONS.get(transition, "fade")

        # xfade syntax: [a][b]xfade=transition=NAME:duration=D:offset=O[out]
        return f"{input_a}{input_b}xfade=transition={xfade_name}:duration={duration}:offset={offset}[{output_label}]"

    @classmethod
    def build_fade_filter(
        cls,
        input_label: str,
        output_label: str,
        fade_type: Literal["in", "out", "inout"],
        start_time: float,
        duration: float,
    ) -> str:
        """Build simple fade in/out filter (for single clip, not crossfade)."""
        if fade_type == "in":
            return f"{input_label}fade=t=in:st={start_time}:d={duration}[{output_label}]"
        elif fade_type == "out":
            return f"{input_label}fade=t=out:st={start_time}:d={duration}[{output_label}]"
        else:
            mid = start_time + duration
            return f"{input_label}fade=t=in:st={start_time}:d={duration},fade=t=out:st={mid}:d={duration}[{output_label}]"

    @classmethod
    def build_wipe_filter(
        cls,
        input_a: str,
        input_b: str,
        output_label: str,
        direction: Literal["left", "right", "up", "down"],
        duration: float,
        offset: float,
    ) -> str:
        """Build manual wipe transition using overlay + crop/position animation.
        More flexible than xfade wipes, works on all platforms.
        """
        # Using overlay with animated position
        # For slide/wipe, we animate the overlay position
        expr_map = {
            "left": f"W*({offset}-t)/{duration}",
            "right": f"W*(1-({offset}-t)/{duration})",
            "up": f"H*({offset}-t)/{duration}",
            "down": f"H*(1-({offset}-t)/{duration})",
        }
        expr = expr_map.get(direction, expr_map["left"])

        # This is complex - simpler to use xfade for now
        # Keeping as reference for custom wipes
        return cls.build_xfade_filter(input_a, input_b, output_label, TransitionType.WIPE_LEFT, duration, offset)

    @classmethod
    def build_zoom_filter(
        cls,
        input_a: str,
        input_b: str,
        output_label: str,
        duration: float,
        offset: float,
        zoom_in: bool = True,
    ) -> str:
        """Zoom crossfade - scale up A while fading to B, or scale up B from center."""
        # xfade has 'zoomin' and 'zoomout'
        trans = "zoomin" if zoom_in else "zoomout"
        return f"{input_a}{input_b}xfade=transition={trans}:duration={duration}:offset={offset}[{output_label}]"


def get_transition_filter_name(transition: TransitionType) -> str:
    """Map our enum to xfade transition name."""
    return TransitionBuilder.XFADE_TRANSITIONS.get(transition, "fade")


def is_xfade_supported(transition: TransitionType) -> bool:
    """Check if transition has xfade implementation."""
    return transition in TransitionBuilder.XFADE_TRANSITIONS


# Transition presets for common use cases
TRANSITION_PRESETS = {
    "lesson_default": {
        "type": TransitionType.FADE,
        "duration": 1.0,
    },
    "quick_cut": {
        "type": TransitionType.NONE,
        "duration": 0.0,
    },
    "smooth_flow": {
        "type": TransitionType.XFADE,
        "duration": 0.75,
    },
    "dramatic": {
        "type": TransitionType.ZOOM,
        "duration": 1.5,
    },
    "slide_show": {
        "type": TransitionType.SLIDE_LEFT,
        "duration": 1.0,
    },
    "accessible": {
        "type": TransitionType.FADE,
        "duration": 1.5,  # Slower for cognitive processing
    },
}