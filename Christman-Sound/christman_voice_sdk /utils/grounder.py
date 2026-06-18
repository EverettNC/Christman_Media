"""
© The Christman AI Project | Luma Cognify AI. All rights reserved. Patent pending.
No license — express or implied — is granted without prior written permission.

AlphaVox Voice Stack — Grounder.

Short, repeatable, safe grounding techniques the voice surface can offer
when emotional metrics indicate the user is escalating or dissociating.

Techniques included:
  * Breath-first protocol (the 0.07+ stress trigger)
  * Box / 4-7-8 / steady breath pacing
  * 5-4-3-2-1 sensory grounding
  * Object-orientation
  * Companion-externalization mode (optional, configurable companion name)
  * Memory-anchored grounding (scaffold; integrates with memory_mesh_bridge)
  * Body-based grounding (feet, temperature)

This module is *content-only*. It returns scripted prompts; it does NOT
auto-deliver them and does NOT constitute clinical care. AAC clients
deserve dignity, not robotic coaching, so callers must respect the
`allow_silence` and `no_rush` flags returned in each script.
"""

from enum import Enum
from typing import Any, Dict, Optional


class CompanionState(Enum):
    """Externalization states for an optional companion (e.g. a service dog)."""

    CALM = "calm"
    WORRIED = "worried"
    PACING = "pacing"
    FRIGHTENED = "frightened"
    ALERT = "alert"
    TIRED = "tired"


# Stress threshold above which breathing is triggered first, before any
# additional cognitive load. Mirrors the Cardinal-Rule-#4-aligned 0.07+
# safety protocol.
BREATHING_FIRST_THRESHOLD = 0.07


class Grounder:
    """Grounding techniques for the AlphaVox voice surface."""

    def __init__(self, companion_name: Optional[str] = None) -> None:
        # If set, the companion-externalization technique becomes available.
        # Caller is responsible for supplying a name that the user has
        # already consented to (e.g. their own service animal or stuffed
        # companion). Cardinal Rule #14: ambiguity is not consent.
        self.companion_name = companion_name

    def breathing_first(self) -> Dict[str, Any]:
        """The 0.07+ protocol — breathing comes FIRST."""
        return {
            "type": "breathing",
            "priority": "critical",
            "script": [
                "Let's slow things down together.",
                "",
                "In through your nose… hold… out through your mouth.",
                "",
                "We'll do this together. No rush.",
            ],
            "guidance": {
                "pace": "slow",
                "repetitions": "until_stable",
                "no_additional_questions": True,
            },
        }

    def breath_pacing_guide(self, pace: str = "slow") -> Dict[str, Any]:
        """Guided breath pacing at slow / medium / quick speeds."""
        patterns = {
            "slow": {"in": 4, "hold": 7, "out": 8, "name": "calming breath"},
            "medium": {"in": 4, "hold": 4, "out": 4, "name": "box breathing"},
            "quick": {"in": 4, "hold": 2, "out": 4, "name": "steady breath"},
        }
        pattern = patterns.get(pace, patterns["slow"])
        return {
            "type": "breathing",
            "pattern": pattern,
            "script": [
                f"Let's try {pattern['name']}.",
                "",
                f"Breathe in for {pattern['in']}…",
                f"Hold for {pattern['hold']}…",
                f"Breathe out for {pattern['out']}…",
                "",
                "Again, in your own time.",
            ],
        }

    def five_four_three_two_one(self) -> Dict[str, Any]:
        """5-4-3-2-1 sensory grounding."""
        return {
            "type": "sensory",
            "script": [
                "Let's ground together. We'll use your senses.",
                "",
                "Name 5 things you can see around you.",
                "Take your time.",
            ],
            "steps": [
                {"sense": "sight", "count": 5, "prompt": "5 things you can see"},
                {"sense": "touch", "count": 4, "prompt": "4 things you can touch"},
                {"sense": "hearing", "count": 3, "prompt": "3 things you can hear"},
                {"sense": "smell", "count": 2, "prompt": "2 things you can smell"},
                {"sense": "taste", "count": 1, "prompt": "1 thing you can taste"},
            ],
            "guidance": {"pace": "slow", "validate_each": True, "no_rush": True},
        }

    def object_orientation(self, target_feature: Optional[str] = None) -> Dict[str, Any]:
        """Focus on a single concrete detail in the environment."""
        target = target_feature or "the closest object"
        return {
            "type": "sensory",
            "script": [
                "Look around where you are.",
                "",
                f"Find {target}.",
                "",
                "Take a moment with it. What do you notice?",
            ],
            "guidance": {"pace": "gentle", "allow_silence": True},
        }

    def companion_check_in(self) -> Optional[Dict[str, Any]]:
        """
        Optional externalization technique. Returns None if no companion is
        configured — the caller MUST NOT invent a companion the user has
        not consented to.
        """
        if not self.companion_name:
            return None
        name = self.companion_name
        return {
            "type": "companion_externalization",
            "script": [
                f"If your mind was {name} right now,",
                f"is {name} calm, worried, pacing, or frightened?",
            ],
            "options": [s.value for s in CompanionState],
            "guidance": {"no_pressure": True, "validate_choice": True},
        }

    def companion_grounding_response(self, state: CompanionState) -> Optional[Dict[str, Any]]:
        """Grounding response continuing the companion externalization."""
        if not self.companion_name:
            return None
        name = self.companion_name
        responses = {
            CompanionState.CALM: {
                "script": [
                    f"{name} sounds steady right now.",
                    "Let's keep that calm going.",
                ],
                "next_action": "maintain",
            },
            CompanionState.WORRIED: {
                "script": [
                    f"Okay. {name} is worried.",
                    "Let's help settle.",
                    "",
                    f"If {name} could find one safe thing right now,",
                    "what would it be?",
                ],
                "next_action": "gentle_grounding",
            },
            CompanionState.PACING: {
                "script": [
                    f"Okay. If {name} is pacing, let's slow things down together.",
                    "",
                    f"Can you name one thing you can see that {name} would notice first?",
                ],
                "next_action": "sensory_grounding",
            },
            CompanionState.FRIGHTENED: {
                "script": [
                    f"{name} sounds really scared right now.",
                    "Let's help find something solid.",
                    "",
                    f"What would {name} want to be close to right now to feel safe?",
                ],
                "next_action": "comfort_object",
            },
            CompanionState.ALERT: {
                "script": [
                    f"{name} is on alert.",
                    "Let's check what's being picked up on.",
                    "",
                    f"What does {name} hear or sense right now?",
                ],
                "next_action": "environment_scan",
            },
            CompanionState.TIRED: {
                "script": [
                    f"{name} sounds tired.",
                    "Maybe it's time to rest.",
                    "",
                    "Is there a comfortable spot nearby?",
                ],
                "next_action": "rest_guidance",
            },
        }
        return responses.get(state, responses[CompanionState.WORRIED])

    def memory_anchor(self, memory_type: str = "calm") -> Dict[str, Any]:
        """
        Use memories as grounding anchors (scaffold).

        Production: connect to backend.memory_mesh_bridge for stored
        positive anchors. Until that wiring exists, this returns a generic
        recall prompt — it does NOT fabricate or invent memories.
        """
        prompts = {
            "calm": "Think of a time when you felt calm. Where were you?",
            "safe": "Remember a place where you felt safe. What was around you?",
            "happy": "Picture a moment that made you smile. What do you remember?",
            "connected": "Think of someone who makes you feel less alone. Picture them.",
        }
        return {
            "type": "memory_anchored",
            "script": [
                "Let's find a good memory to hold onto.",
                "",
                prompts.get(memory_type, prompts["calm"]),
                "",
                "Take your time. Just notice what comes up.",
            ],
            "guidance": {
                "allow_silence": True,
                "gentle_validation": True,
                "no_forced_detail": True,
            },
        }

    def feet_on_ground(self) -> Dict[str, Any]:
        """Simple physical grounding — feel your feet."""
        return {
            "type": "physical",
            "script": [
                "Let's feel where your feet are.",
                "",
                "Press them into the floor.",
                "Notice what that feels like.",
                "",
                "You're here. You're solid.",
            ],
            "guidance": {"pace": "slow", "repetition_ok": True},
        }

    def temperature_awareness(self) -> Dict[str, Any]:
        """Temperature-based grounding."""
        return {
            "type": "physical",
            "script": [
                "Notice the temperature around you.",
                "",
                "Is the air cool or warm on your skin?",
                "Can you feel any breeze?",
                "",
                "Just notice. No need to change anything.",
            ],
        }

    def get_grounding_for_state(
        self,
        stress_level: float,
        grounding_level: float,
        companion_mode: bool = False,
    ) -> Dict[str, Any]:
        """Pick a grounding technique based on the user's current metrics."""
        if stress_level >= BREATHING_FIRST_THRESHOLD:
            return self.breathing_first()
        if companion_mode and grounding_level < 0.5:
            check_in = self.companion_check_in()
            if check_in is not None:
                return check_in
        if grounding_level < 0.3:
            return self.feet_on_ground()
        if stress_level >= 0.04:
            return self.five_four_three_two_one()
        return self.breath_pacing_guide("medium")

    @staticmethod
    def format_script_for_voice(script_dict: Dict[str, Any]) -> str:
        """Flatten a script dict to the text the voice surface should speak."""
        lines = script_dict.get("script", [])
        return "\n".join(lines)
