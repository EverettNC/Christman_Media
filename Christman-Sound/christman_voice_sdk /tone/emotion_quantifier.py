"""
Shared-neutral emotional analysis service.

This module quantifies emotional tone, stress, coherence, grounding, crisis
signals, and gesture-derived emotional cues without pretending to "feel."
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EmotionalTone(str, Enum):
    CALM = "calm"
    ANXIOUS = "anxious"
    DISTRESSED = "distressed"
    AGITATED = "agitated"
    FLAT = "flat"
    CONFUSED = "confused"
    FEARFUL = "fearful"
    FRUSTRATED = "frustrated"
    CONFIDENT = "confident"
    NEUTRAL = "neutral"


class CoherenceLevel(str, Enum):
    COHERENT = "coherent"
    SLIGHTLY_SCATTERED = "slightly_scattered"
    CONFUSED = "confused"
    DISORGANIZED = "disorganized"
    INCOHERENT = "incoherent"


@dataclass
class EmotionalMetrics:
    stress_level: float = 0.0
    coherence_score: float = 1.0
    grounding_score: float = 1.0
    emotional_tone: EmotionalTone = EmotionalTone.CALM
    coherence_level: CoherenceLevel = CoherenceLevel.COHERENT
    crisis_detected: bool = False
    needs_grounding: bool = False
    needs_breathing: bool = False
    gesture_emotion: EmotionalTone = EmotionalTone.NEUTRAL
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["emotional_tone"] = self.emotional_tone.value
        data["coherence_level"] = self.coherence_level.value
        data["gesture_emotion"] = self.gesture_emotion.value
        data["timestamp"] = self.timestamp.isoformat()
        return data


class EmotionAnalysisService:
    """
    Shared-neutral emotion analysis service.

    Flat layout, deep behavior:
    - text stress analysis
    - coherence assessment
    - grounding estimation
    - crisis marker detection
    - gesture-derived emotional inference
    - baseline recalibration
    - visible contextual state
    """

    def __init__(self) -> None:
        self.baseline_stress = 0.03
        self.baseline_coherence = 0.90
        self.recent_assessments: List[EmotionalMetrics] = []

        self.stress_markers: Dict[str, float] = {
            "can't breathe": 0.15,
            "help me": 0.10,
            "scared": 0.08,
            "terrified": 0.12,
            "panicking": 0.15,
            "can't think": 0.10,
            "anxious": 0.05,
            "worried": 0.04,
            "nervous": 0.04,
            "uncomfortable": 0.04,
            "overwhelmed": 0.07,
            "shaking": 0.06,
            "spiraling": 0.08,
            "hurt myself": 0.25,
            "kill myself": 0.30,
            "end my life": 0.30,
            "end it all": 0.25,
            "can't do this": 0.15,
            "not safe": 0.20,
            "can't keep safe": 0.25,
        }

        self.calm_markers = {"calm", "okay", "fine", "good", "steady", "grounded"}
        self.fear_markers = {"scared", "terrified", "afraid", "fear", "panic"}
        self.confusion_markers = {
            "confused",
            "don't understand",
            "what's happening",
            "lost",
            "unclear",
        }
        self.flat_markers = {"nothing", "numb", "empty", "don't feel", "flat"}
        self.agitation_markers = {
            "can't sit",
            "restless",
            "pacing",
            "racing",
            "jittery",
        }
        self.frustration_markers = {
            "frustrated",
            "annoyed",
            "stuck",
            "why won't",
            "this isn't working",
        }

        self.crisis_phrases = {
            "hurt myself",
            "kill myself",
            "end my life",
            "hurt someone",
            "not safe",
            "can't keep safe",
            "better off dead",
            "end it all",
        }

    def analyze_text_input(self, text: str) -> EmotionalMetrics:
        """Analyze text and return quantified emotional metrics."""
        normalized_text = self._normalize_text(text)

        stress_level = self._calculate_stress_score(normalized_text, text)
        coherence_score, coherence_level = self._assess_coherence(text)
        grounding_score = self._calculate_grounding_score(
            stress_level,
            coherence_score,
        )
        emotional_tone = self._classify_emotional_tone(
            normalized_text,
            stress_level,
        )
        crisis_detected = self._detect_crisis_markers(normalized_text)

        metrics = EmotionalMetrics(
            stress_level=stress_level,
            coherence_score=coherence_score,
            grounding_score=grounding_score,
            emotional_tone=emotional_tone,
            coherence_level=coherence_level,
            crisis_detected=crisis_detected,
            needs_grounding=grounding_score < 0.5,
            needs_breathing=stress_level >= 0.07,
            gesture_emotion=EmotionalTone.NEUTRAL,
        )

        self._store_assessment(metrics)
        return metrics

    def analyze_gesture_input(self, user_data: Dict[str, Any]) -> EmotionalTone:
        """
        Infer emotional state from gesture repetition and error frequency.

        This preserves the useful heuristic from the smaller emotion files
        while treating it as one signal, not the whole emotional model.
        """
        score = 0
        gestures = user_data.get("gesture_score", {}) or {}
        errors = int(user_data.get("recent_errors", 0) or 0)

        if not gestures:
            return EmotionalTone.NEUTRAL

        high_repeats = [name for name, count in gestures.items() if count >= 5]
        moderate_repeats = [name for name, count in gestures.items() if count >= 3]

        if len(high_repeats) >= 3:
            score += 2
        elif len(moderate_repeats) >= 2:
            score += 1

        if errors >= 5:
            score -= 3
        elif errors >= 3:
            score -= 2
        elif errors >= 1:
            score -= 1

        if score <= -2:
            return EmotionalTone.FRUSTRATED
        if score >= 2:
            return EmotionalTone.CONFIDENT
        return EmotionalTone.NEUTRAL

    def analyze_combined_state(
        self,
        text: str,
        user_data: Optional[Dict[str, Any]] = None,
    ) -> EmotionalMetrics:
        """
        Combine text and gesture analysis into a single emotional reading.
        """
        metrics = self.analyze_text_input(text)
        gesture_emotion = self.analyze_gesture_input(user_data or {})
        metrics.gesture_emotion = gesture_emotion

        if gesture_emotion == EmotionalTone.FRUSTRATED and metrics.stress_level >= 0.05:
            metrics.emotional_tone = EmotionalTone.FRUSTRATED
            metrics.stress_level = min(1.0, metrics.stress_level + 0.05)
            metrics.grounding_score = max(0.0, metrics.grounding_score - 0.05)

        if gesture_emotion == EmotionalTone.CONFIDENT and metrics.coherence_score >= 0.8:
            if metrics.emotional_tone in {EmotionalTone.CALM, EmotionalTone.NEUTRAL}:
                metrics.emotional_tone = EmotionalTone.CONFIDENT
            metrics.grounding_score = min(1.0, metrics.grounding_score + 0.05)

        metrics.needs_grounding = metrics.grounding_score < 0.5
        metrics.needs_breathing = metrics.stress_level >= 0.07

        self._replace_latest_assessment(metrics)
        return metrics

    def get_comprehensive_assessment(
        self,
        text: str,
        user_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Return a visible, self-contained emotional assessment package.
        """
        metrics = self.analyze_combined_state(text, user_data)

        return {
            "metrics": {
                "stress_level": metrics.stress_level,
                "coherence_score": metrics.coherence_score,
                "grounding_score": metrics.grounding_score,
                "emotional_tone": metrics.emotional_tone.value,
                "coherence_level": metrics.coherence_level.value,
                "gesture_emotion": metrics.gesture_emotion.value,
            },
            "flags": {
                "crisis_detected": metrics.crisis_detected,
                "needs_breathing": metrics.needs_breathing,
                "needs_grounding": metrics.needs_grounding,
            },
            "baselines": {
                "stress": self.baseline_stress,
                "coherence": self.baseline_coherence,
            },
            "history_depth": len(self.recent_assessments),
            "timestamp": metrics.timestamp.isoformat(),
        }

    def update_baseline(
        self,
        stress: Optional[float] = None,
        coherence: Optional[float] = None,
    ) -> None:
        """Recalibrate baseline metrics after stable periods."""
        if stress is not None:
            self.baseline_stress = max(0.0, min(0.1, float(stress)))
        if coherence is not None:
            self.baseline_coherence = max(0.5, min(1.0, float(coherence)))

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return recent assessments as visible dictionaries."""
        if limit <= 0:
            return []
        return [item.to_dict() for item in self.recent_assessments[-limit:]]

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.lower().strip().split())

    def _calculate_stress_score(self, normalized_text: str, raw_text: str) -> float:
        score = self.baseline_stress

        for marker, weight in self.stress_markers.items():
            if marker in normalized_text:
                score += weight

        words = [word for word in normalized_text.split() if word]
        if words:
            counts: Dict[str, int] = {}
            for word in words:
                counts[word] = counts.get(word, 0) + 1

            repeated_words = sum(1 for count in counts.values() if count >= 3)
            score += min(0.15, repeated_words * 0.05)

        if raw_text.isupper() and len(raw_text.strip()) > 10:
            score += 0.05

        exclamation_count = raw_text.count("!")
        if exclamation_count > 2:
            score += min(0.10, exclamation_count * 0.02)

        question_count = raw_text.count("?")
        if question_count >= 3:
            score += min(0.06, question_count * 0.015)

        return min(1.0, round(score, 4))

    def _assess_coherence(self, text: str) -> Tuple[float, CoherenceLevel]:
        stripped = text.strip()
        if len(stripped) < 5:
            return 0.8, CoherenceLevel.COHERENT

        words = stripped.split()
        sentence_breaks = (
            stripped.count(".") + stripped.count("!") + stripped.count("?")
        )

        disorganization_score = 0.0

        short_alpha_words = [word for word in words if len(word) <= 2 and word.isalpha()]
        if words and len(short_alpha_words) > len(words) * 0.3:
            disorganization_score += 0.3

        if len(stripped) > 50 and sentence_breaks <= 1:
            disorganization_score += 0.2

        lowered = stripped.lower()
        if "wait" in lowered and "no" in lowered:
            disorganization_score += 0.1

        if "--" in stripped or "..." in stripped:
            disorganization_score += 0.05

        if len(set(words)) > 0 and len(words) > 30:
            lexical_ratio = len(set(words)) / len(words)
            if lexical_ratio < 0.35:
                disorganization_score += 0.1

        coherence_score = max(0.0, min(1.0, self.baseline_coherence - disorganization_score))

        if coherence_score >= 0.8:
            level = CoherenceLevel.COHERENT
        elif coherence_score >= 0.6:
            level = CoherenceLevel.SLIGHTLY_SCATTERED
        elif coherence_score >= 0.4:
            level = CoherenceLevel.CONFUSED
        elif coherence_score >= 0.2:
            level = CoherenceLevel.DISORGANIZED
        else:
            level = CoherenceLevel.INCOHERENT

        return round(coherence_score, 4), level

    def _calculate_grounding_score(
        self,
        stress_level: float,
        coherence_score: float,
    ) -> float:
        grounding = 1.0 - ((stress_level * 0.7) + ((1.0 - coherence_score) * 0.3))
        return max(0.0, min(1.0, round(grounding, 4)))

    def _classify_emotional_tone(
        self,
        normalized_text: str,
        stress_level: float,
    ) -> EmotionalTone:
        if any(marker in normalized_text for marker in self.frustration_markers):
            return EmotionalTone.FRUSTRATED

        if any(marker in normalized_text for marker in self.fear_markers):
            return EmotionalTone.FEARFUL

        if any(marker in normalized_text for marker in self.confusion_markers):
            return EmotionalTone.CONFUSED

        if any(marker in normalized_text for marker in self.flat_markers):
            return EmotionalTone.FLAT

        if any(marker in normalized_text for marker in self.agitation_markers):
            return EmotionalTone.AGITATED

        if any(marker in normalized_text for marker in self.calm_markers):
            return EmotionalTone.CALM

        if stress_level >= 0.10:
            return EmotionalTone.DISTRESSED
        if stress_level >= 0.05:
            return EmotionalTone.ANXIOUS
        return EmotionalTone.NEUTRAL

    def _detect_crisis_markers(self, normalized_text: str) -> bool:
        return any(phrase in normalized_text for phrase in self.crisis_phrases)

    def _store_assessment(self, metrics: EmotionalMetrics) -> None:
        self.recent_assessments.append(metrics)
        if len(self.recent_assessments) > 250:
            self.recent_assessments = self.recent_assessments[-250:]

    def _replace_latest_assessment(self, metrics: EmotionalMetrics) -> None:
        if self.recent_assessments:
            self.recent_assessments[-1] = metrics
        else:
            self._store_assessment(metrics)


emotion_analysis_service = EmotionAnalysisService()


# ==============================================================================
# Patent Pending
# Christman-AI Family
# Shared-neutral implementation for internal system use.
# ==============================================================================
