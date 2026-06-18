"""
Written Tone Classification System - Christman AI

Distinguishes AGGRESSIVE from INCISIVE in written communication.

AGGRESSIVE = attacking, overwhelming, defensive response
INCISIVE = surgical, precise, respectful fear + locked attention

Completely sovereign logic layer. No external dependencies.
"""

from typing import Dict, List
import re

def classify_written_tone(text: str) -> Dict:
    """
    Distinguishes aggressive from incisive in written communication.

    Args:
        text: Input text to analyze

    Returns:
        Dictionary with tone classification, score, and reader response
    """

    # Aggressive signals (subtract from score)
    words = text.split()
    all_caps_words = len([w for w in words if w.isupper() and len(w) > 2])
    exclamation_count = text.count('!')
    profanity_machine_gun = text.lower().count('fuck') + text.lower().count('shit')
    personal_attacks = text.lower().count('you are') + text.lower().count("you're")

    aggressive_signals = (
        all_caps_words * 5 +           # ALL CAPS = shouting
        exclamation_count * 2 +        # !!! = emotional overload
        profanity_machine_gun * 3 +    # repeated cursing = bludgeon
        personal_attacks * 4           # "you are/you're" = finger pointing
    )

    # Incisive signals (add to score)
    precise_words = sum(1 for w in words if len(w) > 10)  # Long, technical words
    sentence_structure = text.count('.') + text.count(':')  # Controlled pacing
    short_sentences = len([s for s in text.split('.') if len(s.split()) < 10])

    filler_words = ['like', 'um', 'uh', 'you know', 'basically']
    no_filler = 1 if not any(filler in text.lower() for filler in filler_words) else 0

    scalpel_profanity = 1 if (profanity_machine_gun == 1) else 0  # ONE well-placed curse

    incisive_signals = (
        precise_words * 2 +            # Surgical language
        sentence_structure +           # Deliberate structure
        short_sentences +              # Punchy, clear
        no_filler * 5 +                # Zero waste
        scalpel_profanity * 3          # One strategic "fuck" for emphasis
    )

    # Calculate composite score
    tone_score = incisive_signals * 2 - aggressive_signals

    # Classification
    if tone_score > 15:
        return {
            "tone": "incisive",
            "score": min(tone_score, 100),
            "reader_feels": "respect + slight fear, attention locked, no defensiveness",
            "partnership_safe": True
        }
    elif tone_score < -5:
        return {
            "tone": "aggressive",
            "score": abs(tone_score),
            "reader_feels": "attacked, defensive, adrenaline spike, fight-or-flight",
            "partnership_safe": False
        }
    else:
        return {
            "tone": "neutral",
            "score": 50,
            "reader_feels": "informational, no emotional response",
            "partnership_safe": True
        }


def make_incisive(text: str) -> str:
    """
    Transform aggressive text into incisive text.

    Args:
        text: Input text to transform

    Returns:
        Transformed text with incisive tone
    """
    # Remove ALL CAPS (except acronyms)
    words = text.split()
    fixed_words = [w if len(w) <= 3 else w.capitalize() for w in words]
    text = ' '.join(fixed_words)

    # Reduce exclamation points (max 1 per paragraph)
    paragraphs = text.split('\n')
    fixed_paragraphs = []
    for p in paragraphs:
        exclamation_count = p.count('!')
        if exclamation_count > 1:
            p = p.replace('!', '.', exclamation_count - 1)  # Keep only 1
        fixed_paragraphs.append(p)
    text = '\n'.join(fixed_paragraphs)

    # Replace "you are" statements with objective observation
    replacements = {
        "You are fucking up": "This approach is breaking",
        "You need to": "The next step is",
        "Your mistake": "The error",
        "you're wrong": "this is incorrect",
        "You don't understand": "The concept is",
        "Your code is garbage": "This code has issues",
    }

    for aggressive_phrase, incisive_phrase in replacements.items():
        text = text.replace(aggressive_phrase, incisive_phrase)
        # Case variations
        text = text.replace(aggressive_phrase.lower(), incisive_phrase.lower())
        text = text.replace(aggressive_phrase.upper(), incisive_phrase.upper())

    return text


def analyze_tone_breakdown(text: str) -> Dict:
    """
    Detailed breakdown of tone signals in text.

    Args:
        text: Input text to analyze

    Returns:
        Dictionary with detailed signal analysis
    """
    words = text.split()

    return {
        "all_caps_words": len([w for w in words if w.isupper() and len(w) > 2]),
        "exclamation_count": text.count('!'),
        "profanity_count": text.lower().count('fuck') + text.lower().count('shit'),
        "personal_attacks": text.lower().count('you are') + text.lower().count("you're"),
        "precise_words": sum(1 for w in words if len(w) > 10),
        "sentence_count": text.count('.') + text.count(':') + 1,
        "average_sentence_length": len(words) / max(1, text.count('.') + 1),
        "has_filler": any(filler in text.lower() for filler in
                         ['like', 'um', 'uh', 'you know', 'basically']),
        "word_count": len(words)
    }


# EXAMPLES FOR TEACHING

AGGRESSIVE_EXAMPLE = """
YOU ARE FUCKING UP EVERYTHING!!! FIX YOUR SHIT OR GET THE FUCK OUT!!!
Your code is GARBAGE and you CLEARLY don't know what you're doing!!!
"""

INCISIVE_EXAMPLE = """
Your current approach is breaking the system. Here's the exact line that fails.
Fix it by 9 AM or we ship without you.
"""


if __name__ == "__main__":
    print("\n=== AGGRESSIVE EXAMPLE ===")
    aggressive_result = classify_written_tone(AGGRESSIVE_EXAMPLE)
    print(f"Tone: {aggressive_result['tone']}")
    print(f"Score: {aggressive_result['score']}")
    print(f"Reader feels: {aggressive_result['reader_feels']}")
    print(f"Partnership safe: {aggressive_result['partnership_safe']}")

    print("\n=== INCISIVE EXAMPLE ===")
    incisive_result = classify_written_tone(INCISIVE_EXAMPLE)
    print(f"Tone: {incisive_result['tone']}")
    print(f"Score: {incisive_result['score']}")
    print(f"Reader feels: {incisive_result['reader_feels']}")
    print(f"Partnership safe: {incisive_result['partnership_safe']}")

    print("\n=== TRANSFORMATION ===")
    print("Before:", AGGRESSIVE_EXAMPLE[:50] + "...")
    transformed = make_incisive(AGGRESSIVE_EXAMPLE)
    print("After:", transformed[:50] + "...")

    print("\n=== BREAKDOWN ===")
    breakdown = analyze_tone_breakdown(AGGRESSIVE_EXAMPLE)
    for key, value in breakdown.items():
        print(f"{key:25s}: {value}")

# ==============================================================================
# Patent Pending — TCAP-2026-001 / TCAP-2026-002
# © 2026 Everett Nathaniel Christman & Misty Gail Christman
# The Christman AI Project — Luma Cognify AI
# Truth. Dignity. Protection. Transparency. No Erasure.
# Nothing Vital Lives Below Root.
# ==============================================================================