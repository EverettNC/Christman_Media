"""
© The Christman AI Project | Luma Cognify AI. All rights reserved. Patent pending.
No license — express or implied — is granted without prior written permission.

AlphaVox Voice Stack — Written-Tone Classifier.

Distinguishes *aggressive* from *incisive* writing in user-authored or
system-authored text, and offers a safe transformation that turns
aggressive text into incisive text without softening the message.

Why this matters for AlphaVox: AAC users frequently want their voice to
land *firmly*, not politely-by-default. The classifier exists so the
voice surface can ask: "Is this firm-and-clear, or is it venting at
someone?" and the user can decide.

NON-CLAIMS (Cardinal Rule #13: no fabricated engines):

  * This is a heuristic, lexicon-based classifier. It is NOT a clinical
    or forensic instrument and MUST NOT be used to evaluate someone's
    character, mental state, or intent.
  * The "tone breakdown" returns scores on a 0..1 scale. Those numbers
    are explainable feature counts, not calibrated probabilities.
  * `make_incisive` is a syntactic rewriter. It removes ad-hominem and
    inflammatory tokens; it does NOT understand context. Always show
    the user the rewrite before sending.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Tuple


class ToneCategory(Enum):
    INCISIVE = "incisive"        # firm, direct, on-target — keep as-is
    AGGRESSIVE = "aggressive"    # ad-hominem, inflammatory — offer rewrite
    NEUTRAL = "neutral"          # neither sharp nor hot
    PASSIVE = "passive"          # hedged / softened — flag if user wanted firm


# --- lexicons -------------------------------------------------------------

# Hot, ad-hominem, or character-attacking tokens. Substring-matched, so
# entries should be conservative.
_AGGRESSIVE_TOKENS: Tuple[str, ...] = (
    "idiot", "stupid", "moron", "dumb", "shut up", "shut the",
    "you people", "you always", "you never",
    "pathetic", "worthless", "loser", "garbage",
    "hate you", "hate them",
    "screw you", "screw this",
    "ridiculous", "disgusting",
)

# Profanity that we redact when rewriting, but treat as intensity rather
# than character-attack on its own.
_PROFANITY: Tuple[str, ...] = (
    "fuck", "shit", "damn", "asshole", "bitch", "bullshit",
)

# Markers of *incisive* writing: direct, evidence-anchored, takes a
# position. These ADD to the incisive score — they don't subtract from
# aggressive (e.g., a sentence can be both pointed and abusive).
_INCISIVE_TOKENS: Tuple[str, ...] = (
    "the issue is", "the point is", "the problem is",
    "specifically", "concretely", "to be clear",
    "i disagree", "i don't agree", "this is wrong",
    "this fails because", "the data shows", "the evidence shows",
    "no — ", "no, ",
)

# Hedges / softeners — too many of these mean the message is passive.
_HEDGES: Tuple[str, ...] = (
    "maybe", "perhaps", "kind of", "sort of", "i guess",
    "i was wondering", "if it's not too much",
    "i'm not sure but", "just a thought",
    "no worries if not", "no pressure",
)

_INTENSIFIER_PUNCT_RE = re.compile(r"!{2,}|\?{2,}")
_ALLCAPS_WORD_RE = re.compile(r"\b[A-Z]{4,}\b")


@dataclass
class ToneBreakdown:
    """Explainable per-feature scores."""

    aggressive_score: float
    incisive_score: float
    passive_score: float
    intensity_score: float
    category: ToneCategory
    aggressive_hits: List[str]
    incisive_hits: List[str]
    hedge_hits: List[str]
    profanity_hits: List[str]


def _hits(text_lower: str, lexicon: Iterable[str]) -> List[str]:
    return [token for token in lexicon if token in text_lower]


def _word_count(text: str) -> int:
    return max(1, len([w for w in text.split() if w.strip()]))


def analyze_tone_breakdown(text: str) -> ToneBreakdown:
    """Score the four tone axes plus overall category for a text."""
    if text is None:
        text = ""
    text_lower = text.lower()
    n_words = _word_count(text)

    aggressive_hits = _hits(text_lower, _AGGRESSIVE_TOKENS)
    incisive_hits = _hits(text_lower, _INCISIVE_TOKENS)
    hedge_hits = _hits(text_lower, _HEDGES)
    profanity_hits = _hits(text_lower, _PROFANITY)

    # Density-normalized scores so a long sober paragraph with one
    # heated word doesn't get flagged as aggressive.
    aggressive_score = min(1.0, len(aggressive_hits) * 4 / n_words)
    incisive_score = min(1.0, len(incisive_hits) * 5 / n_words)
    passive_score = min(1.0, len(hedge_hits) * 4 / n_words)

    # Intensity: punctuation shouting + ALL-CAPS shouting + profanity
    intensity_signals = (
        len(_INTENSIFIER_PUNCT_RE.findall(text))
        + len(_ALLCAPS_WORD_RE.findall(text))
        + len(profanity_hits)
    )
    intensity_score = min(1.0, intensity_signals * 3 / n_words)

    # Category: aggressive lexicon dominates everything else (it's the
    # ad-hominem signal). Then incisive vs passive vs neutral.
    if aggressive_score >= 0.05 or (intensity_score >= 0.15 and aggressive_hits):
        category = ToneCategory.AGGRESSIVE
    elif incisive_score >= 0.05 and incisive_score > passive_score:
        category = ToneCategory.INCISIVE
    elif passive_score >= 0.10 and passive_score > incisive_score:
        category = ToneCategory.PASSIVE
    else:
        category = ToneCategory.NEUTRAL

    return ToneBreakdown(
        aggressive_score=aggressive_score,
        incisive_score=incisive_score,
        passive_score=passive_score,
        intensity_score=intensity_score,
        category=category,
        aggressive_hits=aggressive_hits,
        incisive_hits=incisive_hits,
        hedge_hits=hedge_hits,
        profanity_hits=profanity_hits,
    )


def classify_written_tone(text: str) -> ToneCategory:
    """Convenience wrapper that returns just the category."""
    return analyze_tone_breakdown(text).category


def make_incisive(text: str) -> str:
    """
    Rewrite aggressive text into incisive text.

    The transformation keeps the firmness but strips:
      * ad-hominem / character-attack tokens
      * profanity
      * shouting punctuation (!! / ??)
      * ALL-CAPS shouting (lowercases words >= 4 letters all caps)

    It does NOT add hedges and does NOT change the underlying claim.
    Callers MUST surface the rewrite to the user for confirmation
    before sending — the classifier cannot tell whether the user
    wanted to send the heated original on purpose.
    """
    if not text:
        return text or ""

    out = text

    # Remove aggressive ad-hominem / character-attack tokens.
    for token in _AGGRESSIVE_TOKENS:
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        out = pattern.sub("", out)

    # Redact profanity.
    for token in _PROFANITY:
        pattern = re.compile(r"\b" + re.escape(token) + r"\w*\b", re.IGNORECASE)
        out = pattern.sub("[redacted]", out)

    # Collapse shouting punctuation.
    out = _INTENSIFIER_PUNCT_RE.sub(lambda m: m.group(0)[0], out)

    # Lowercase any remaining ALL-CAPS shouting.
    out = _ALLCAPS_WORD_RE.sub(lambda m: m.group(0).lower(), out)

    # Tidy whitespace and stranded punctuation left by removed tokens.
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.!?;:])", r"\1", out)
    out = re.sub(r"^[\s,;:.\-]+", "", out)
    return out.strip()
