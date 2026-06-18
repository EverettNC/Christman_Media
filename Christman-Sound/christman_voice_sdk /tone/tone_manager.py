"""
Tone and Empathy Management Helpers - Christman AI

Applies communication adjustments after tone has been interpreted.
This layer manages delivery: pacing, warmth, structure, mirroring,
and response framing.

Completely sovereign logic layer. No external dependencies.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from logger import get_logger

logger = get_logger(__name__)

try:
    from emotion_service import emotion_service
except ImportError:
    emotion_service = None

try:
    from tone_engine import ResponseMode, ToneContext, ToneEngine, ToneProfile
except ImportError:
    ResponseMode = None
    ToneContext = None
    ToneEngine = None
    ToneProfile = None


class ToneManager:
    """
    Applies communication adjustments after tone has been interpreted.

    This layer does not replace ToneScore or ToneEngine.
    It manages delivery: pacing, warmth, structure, mirroring,
    and response framing.
    """

    def __init__(self) -> None:
        self.profile: Dict[str, Any] = {
            "speech_rate": 180,
            "volume": 1.0,
            "warmth": "balanced",
            "structure": "concise",
            "mirroring": True,
            "validation_level": "moderate",
            "response_mode": "standard",
        }
        self.emotion_state: str = "neutral"
        self.detected_cues: List[str] = []
        self.last_tone_profile: Optional[Any] = None

    def analyze_user_input(self, text: str, prior_misread: bool = False) -> str:
        """
        Analyze user input through the text-side tone engine when available,
        then map that understanding into response behavior.
        """
        if ToneEngine is not None and ToneContext is not None:
            engine = ToneEngine()
            context = ToneContext(
                user_said=text,
                prior_misread=prior_misread,
                explicit_state=None,
            )
            tone_profile = engine.analyze(context)
            response_mode = engine.choose_mode(tone_profile)
            self.last_tone_profile = tone_profile
            self._apply_tone_profile(tone_profile, response_mode)
            label = self.emotion_state
        else:
            updates, cues, label = analyse_user_text(text, self.profile)
            self.profile.update(updates)
            self.detected_cues = cues
            self.emotion_state = label

        if emotion_service is not None:
            try:
                emotion_service.update_from_gesture(self.emotion_state)
            except Exception:
                pass

        return self.emotion_state

    def _apply_tone_profile(self, tone_profile: Any, response_mode: Any) -> None:
        """
        Convert interpreted tone into communication settings.
        """
        cues: List[str] = []
        mode_name = getattr(response_mode, "name", str(response_mode)).lower()

        self.profile["response_mode"] = mode_name

        if getattr(tone_profile, "needs_validation", 0.0) >= 0.4:
            self.profile["validation_level"] = "high"
            self.profile["warmth"] = "reassuring"
            cues.append("validation_needed")
        else:
            self.profile["validation_level"] = "moderate"

        if getattr(tone_profile, "wants_action", 0.0) >= 0.5:
            self.profile["structure"] = "guided"
            cues.append("action_needed")

        if getattr(tone_profile, "emotional_intensity", 0.0) >= 0.5:
            self.profile["speech_rate"] = 160
            self.profile["warmth"] = "steady"
            cues.append("heightened_intensity")
        else:
            self.profile["speech_rate"] = 180

        if getattr(tone_profile, "humor_score", 0.0) >= 0.2:
            cues.append("humor_present")

        if getattr(tone_profile, "sarcasm_score", 0.0) >= 0.3:
            cues.append("sarcasm_present")

        if getattr(tone_profile, "distress_score", 0.0) >= 0.7:
            self.emotion_state = "serious_support"
            self.profile["warmth"] = "gentle"
            self.profile["speech_rate"] = 145
            self.profile["structure"] = "guided"
            cues.append("high_distress")
        elif mode_name == "playful_validating":
            self.emotion_state = "playful_support"
            self.profile["warmth"] = "light_warmth"
        elif mode_name == "warm_validating":
            self.emotion_state = "supportive"
            self.profile["warmth"] = "reassuring"
        elif mode_name == "direct_problem_solving":
            self.emotion_state = "focused"
            self.profile["structure"] = "guided"
            self.profile["warmth"] = "balanced"
        elif mode_name == "curious_reflection":
            self.emotion_state = "reflective"
            self.profile["warmth"] = "attuned"
        elif mode_name == "gentle_correction":
            self.emotion_state = "corrective"
            self.profile["warmth"] = "kind"
        else:
            self.emotion_state = "neutral"

        self.detected_cues = cues

    def get_emotional_context(self) -> str:
        """Get current emotional context for response generation."""
        return self.emotion_state

    def get_speech_controls(self) -> Dict[str, Any]:
        """Get current speech control parameters."""
        return extract_speech_controls(self.profile)

    def format_response(self, base_text: str) -> str:
        """Format a response using current cues and profile settings."""
        return format_response(base_text, self.detected_cues, self.profile)

    def reset(self) -> None:
        """Reset tone manager to default state."""
        self.__init__()


def _ensure_profile_defaults(profile: Dict[str, Any]) -> Dict[str, Any]:
    profile = dict(profile)
    profile.setdefault("speech_rate", 180)
    profile.setdefault("volume", 1.0)
    profile.setdefault("warmth", "balanced")
    profile.setdefault("structure", "concise")
    profile.setdefault("mirroring", True)
    profile.setdefault("validation_level", "moderate")
    profile.setdefault("response_mode", "standard")
    return profile


def analyse_user_text(text: str, profile: Dict[str, Any]) -> tuple[Dict[str, Any], List[str], str]:
    """
    Lightweight fallback when ToneEngine is unavailable.
    """
    profile = _ensure_profile_defaults(profile)
    text_lower = text.lower()

    updates: Dict[str, Any] = {}
    cues: List[str] = []
    label = "neutral"

    if any(
        phrase in text_lower
        for phrase in ["can't hear", "cannot hear", "hard to hear", "slow down"]
    ):
        updates["speech_rate"] = max(120, int(profile["speech_rate"] * 0.85))
        updates["warmth"] = "reassuring"
        cues.append("hearing_support")
        label = "supportive"

    if any(
        word in text_lower
        for word in ["confused", "don't understand", "lost", "not sure"]
    ):
        updates["structure"] = "guided"
        updates["warmth"] = "reassuring"
        cues.append("confusion")
        label = "supportive"

    if any(
        word in text_lower
        for word in ["good", "great", "awesome", "excited", "happy", "love"]
    ):
        updates.setdefault("warmth", "uplifting")
        cues.append("positive_affect")
        if label == "neutral":
            label = "positive"

    if any(
        word in text_lower
        for word in ["sad", "upset", "hurt", "pain", "difficult", "struggling"]
    ):
        updates["warmth"] = "gentle"
        cues.append("distress")
        label = "compassionate"

    return updates, cues, label


def format_response(base_text: str, cues: List[str], profile: Dict[str, Any]) -> str:
    """Apply empathy wrappers and structural adjustments to a reply."""
    profile = _ensure_profile_defaults(profile)
    intro_parts: List[str] = []

    if "hearing_support" in cues:
        intro_parts.append("Thanks for letting me know—I’ll keep things clear and steady.")

    if "confusion" in cues:
        intro_parts.append("Let me break that down so it feels simpler.")

    if "validation_needed" in cues:
        intro_parts.append("I hear you.")

    if "high_distress" in cues:
        intro_parts.append("I’m going to stay steady with you here.")

    if "positive_affect" in cues and profile.get("warmth") == "uplifting":
        intro_parts.append("I love the energy you're bringing.")

    body = base_text
    if profile.get("structure") == "guided":
        body = _structure_response(body)

    if intro_parts:
        return " ".join(intro_parts) + "\n\n" + body
    return body


def _structure_response(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [sentence for sentence in sentences if sentence]

    if len(sentences) <= 2:
        return text

    return "\n".join(f"• {sentence}" for sentence in sentences)


def extract_speech_controls(profile: Dict[str, Any]) -> Dict[str, Any]:
    profile = _ensure_profile_defaults(profile)
    return {
        "speech_rate": profile.get("speech_rate", 180),
        "volume": profile.get("volume", 1.0),
        "warmth": profile.get("warmth", "balanced"),
        "structure": profile.get("structure", "concise"),
        "mirroring": profile.get("mirroring", True),
        "validation_level": profile.get("validation_level", "moderate"),
        "response_mode": profile.get("response_mode", "standard"),
    }


tone_manager = ToneManager()


__all__ = [
    "ToneManager",
    "tone_manager",
    "analyse_user_text",
    "format_response",
    "extract_speech_controls",
]


# ==============================================================================
# Patent Pending — TCAP-2026-001 / TCAP-2026-002
# © 2026 Everett Nathaniel Christman & Misty Gail Christman
# The Christman AI Project — Luma Cognify AI
# Truth. Dignity. Protection. Transparency. No Erasure.
# Nothing Vital Lives Below Root.
# ==============================================================================