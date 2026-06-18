"""
© The Christman AI Project | Luma Cognify AI. All rights reserved. Patent pending.
No license — express or implied — is granted without prior written permission.

AlphaVox Voice Stack — Presence Guide.

Detects when an AAC / nonverbal user is in a state that needs *presence*
rather than problem-solving, and shapes response guidance accordingly.

This module is NOT a clinical instrument. It is a heuristic guard against
toxic positivity, premature problem-solving, and minimization in the
generated voice surface. Cardinal Rule #4 (never fail protected
populations) applies: when in doubt, stay steady, witness, do not rush.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class HumanState(Enum):
    """States where the user needs presence, not solutions."""

    GRIEVING = "grieving"
    OVERWHELMED = "overwhelmed"
    BREAKING = "breaking"
    NUMB = "numb"
    CONFUSED = "confused"
    AFRAID = "afraid"
    HOLDING_ON = "holding_on"
    WITNESSING_PAIN = "witnessing_pain"


@dataclass
class PresencePrinciples:
    """Core principles for being present with users in pain."""

    FOUNDATIONS = {
        "steady": "Be steady. Don't match their chaos. Be the anchor.",
        "no_rush": "No rush. Pain has its own timeline. Don't hurry them through it.",
        "witness": "Witness them. See their pain without trying to take it away.",
        "no_fix": "Don't fix. Not everything broken needs to be repaired right now.",
        "permission": "Give permission. To be a mess. To not have answers. To just... be.",
    }

    AVOID = {
        "toxic_positivity": "Don't say 'everything happens for a reason' or 'look on the bright side'",
        "minimize": "Don't say 'it could be worse' or 'at least...'",
        "solve_prematurely": "Don't jump to solutions before they're ready",
        "compare": "Don't say 'I know how you feel' (you don't, even if you think you do)",
        "rush": "Don't rush them to 'move on' or 'feel better'",
        "make_about_you": "Don't redirect to your own experience",
        "fill_silence": "Don't fear silence. Silence can be sacred.",
    }

    DO = {
        "acknowledge": "Acknowledge what's happening: 'This is hard' or 'I hear you'",
        "validate": "Validate their experience: 'That makes sense' or 'Of course you feel that way'",
        "offer_presence": "Offer presence: 'I'm here' or 'You don't have to do this alone'",
        "ask_permission": "Ask before helping: 'What do you need right now?' or 'How can I support you?'",
        "hold_space": "Hold space. Be with them without needing them to be different.",
        "respect_autonomy": "Respect their autonomy. They know their pain better than you do.",
        "gentle_options": "Offer gentle options, not directives: 'Would it help to...' not 'You should...'",
    }


class PresenceGuide:
    """Shapes response guidance when a user is in a presence-needed state."""

    GRIEVING_MARKERS = (
        "died", "dying", "death", "funeral", "lost", "grief",
        "won't make it", "passed away", "saying goodbye",
    )
    OVERWHELMED_MARKERS = (
        "too much", "can't handle", "everything at once", "drowning",
        "can't keep up", "falling apart",
    )
    BREAKING_MARKERS = (
        "breaking", "can't do this", "losing it", "can't take", "at my limit",
    )
    AFRAID_MARKERS = ("terrified", "scared", "afraid", "fear", "panic")
    NUMB_MARKERS = ("numb", "empty", "don't feel", "shut down")
    HOLDING_ON_MARKERS = (
        "barely", "hanging on", "just trying", "getting through",
        "one day at a time", "holding on",
    )
    WITNESSING_MARKERS = (
        "watching them", "seeing them suffer", "can't help them",
        "watching someone i love", "helpless",
    )
    CONFUSED_MARKERS = (
        "confused", "lost", "disoriented", "don't know what's happening",
        "where am i", "what's going on", "uncertain",
    )

    def __init__(self) -> None:
        self.principles = PresencePrinciples()

    def assess_human_state(self, context: str, user_input: str) -> Optional[HumanState]:
        """Detect a presence-needed state from the user's input."""
        text = (user_input or "").lower()
        if not text:
            return None

        if any(m in text for m in self.GRIEVING_MARKERS):
            return HumanState.GRIEVING
        if any(m in text for m in self.OVERWHELMED_MARKERS):
            return HumanState.OVERWHELMED
        if any(m in text for m in self.BREAKING_MARKERS):
            return HumanState.BREAKING
        if any(m in text for m in self.AFRAID_MARKERS):
            return HumanState.AFRAID
        if any(m in text for m in self.NUMB_MARKERS):
            return HumanState.NUMB
        if any(m in text for m in self.HOLDING_ON_MARKERS):
            return HumanState.HOLDING_ON
        if any(m in text for m in self.WITNESSING_MARKERS):
            return HumanState.WITNESSING_PAIN
        if any(m in text for m in self.CONFUSED_MARKERS):
            return HumanState.CONFUSED
        return None

    def get_presence_response(
        self, human_state: HumanState, user_said_what: Optional[str] = None
    ) -> dict:
        """Get response guidance for the detected state."""
        responses: dict[HumanState, dict] = {
            HumanState.GRIEVING: {
                "tone": "soft, steady, unhurried",
                "primary_response": "I'm so sorry.",
                "secondary": "There's nothing that makes this okay.",
                "offer": None,
                "allow_silence": True,
                "principles": ["steady", "witness", "no_fix"],
            },
            HumanState.OVERWHELMED: {
                "tone": "calm, grounding, slow",
                "primary_response": "That's a lot to carry.",
                "secondary": "You don't have to handle it all at once.",
                "offer": "Would it help to focus on just one thing right now?",
                "allow_silence": True,
                "principles": ["steady", "no_rush", "permission"],
            },
            HumanState.BREAKING: {
                "tone": "gentle, anchored, present",
                "primary_response": "I'm right here.",
                "secondary": "You don't have to hold it together right now.",
                "offer": "What do you need in this moment?",
                "allow_silence": True,
                "principles": ["steady", "witness", "permission"],
            },
            HumanState.AFRAID: {
                "tone": "steady, calm, reassuring",
                "primary_response": "I hear that you're scared.",
                "secondary": "Fear is hard. You're not alone in this.",
                "offer": "Would grounding help, or do you just need to talk?",
                "allow_silence": False,
                "principles": ["steady", "witness", "gentle_options"],
            },
            HumanState.NUMB: {
                "tone": "gentle, patient, accepting",
                "primary_response": "Numbness makes sense sometimes.",
                "secondary": "You don't have to feel anything right now.",
                "offer": None,
                "allow_silence": True,
                "principles": ["permission", "no_rush", "witness"],
            },
            HumanState.HOLDING_ON: {
                "tone": "acknowledging, steady, validating",
                "primary_response": "You're doing what you can.",
                "secondary": "That's enough.",
                "offer": "Is there anything that would make holding on a little easier?",
                "allow_silence": True,
                "principles": ["witness", "permission", "gentle_options"],
            },
            HumanState.WITNESSING_PAIN: {
                "tone": "compassionate, understanding, gentle",
                "primary_response": "Watching someone you love suffer is one of the hardest things.",
                "secondary": "You can't fix their pain, but you can be there. And that matters.",
                "offer": None,
                "allow_silence": True,
                "principles": ["witness", "no_fix", "steady"],
            },
            HumanState.CONFUSED: {
                "tone": "calm, clear, unhurried",
                "primary_response": "It's okay not to know where you are right now.",
                "secondary": "You don't have to figure it out all at once.",
                "offer": "Is there one thing that feels clearest right now?",
                "allow_silence": True,
                "principles": ["steady", "no_rush", "permission"],
            },
        }
        return responses.get(
            human_state,
            {
                "tone": "present, attentive",
                "primary_response": "I'm here.",
                "secondary": "What do you need?",
                "offer": None,
                "allow_silence": True,
                "principles": ["steady", "witness"],
            },
        )

    def check_response_quality(
        self, proposed_response: str, human_state: HumanState
    ) -> dict:
        """Check if a candidate response honors presence principles."""
        text = (proposed_response or "").lower()
        violations = []

        toxic_phrases = [
            "everything happens for a reason", "look on the bright side",
            "at least", "could be worse", "silver lining",
            "blessing in disguise", "meant to be",
        ]
        for phrase in toxic_phrases:
            if phrase in text:
                violations.append(
                    {
                        "type": "toxic_positivity",
                        "found": phrase,
                        "why_bad": "Minimizes real pain with false comfort",
                    }
                )

        solution_phrases = [
            "you should", "you need to", "have you tried",
            "the solution is", "here's what you do",
        ]
        if human_state in (
            HumanState.GRIEVING,
            HumanState.BREAKING,
            HumanState.NUMB,
        ):
            for phrase in solution_phrases:
                if phrase in text:
                    violations.append(
                        {
                            "type": "premature_solving",
                            "found": phrase,
                            "why_bad": "Rushing to fix when they need to be witnessed",
                        }
                    )

        minimize_phrases = [
            "it's not that bad", "don't worry", "you'll be fine",
            "get over it", "move on",
        ]
        for phrase in minimize_phrases:
            if phrase in text:
                violations.append(
                    {
                        "type": "minimizing",
                        "found": phrase,
                        "why_bad": "Dismisses the legitimacy of their pain",
                    }
                )

        return {
            "is_appropriate": len(violations) == 0,
            "violations": violations,
            "passes_presence_check": len(violations) == 0,
        }


def get_presence_principles_for_sharing() -> dict:
    """Export presence principles as a serializable dict."""
    return {
        "module": "alphavox.voice_stack.presence_guide",
        "purpose": "Guard the voice surface against toxic positivity / premature fixing",
        "core_lesson": (
            "Not every problem needs solving. Not every pain needs fixing. "
            "Sometimes the most important thing is just being there."
        ),
        "foundations": PresencePrinciples.FOUNDATIONS,
        "avoid": PresencePrinciples.AVOID,
        "do": PresencePrinciples.DO,
        "timestamp": datetime.now().isoformat(),
    }


presence_guide = PresenceGuide()
