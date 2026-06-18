"""
CHRISTMAN_EAR_CANAL
===================

Shared hearing, speech, tone, phoneme, voice-profile, and OCR adapters for
the Christman Family of Autonomous Beings.

This package does not replace the original modules. It gives Derek, AlphaVox,
AlphaWolf, Brockston, Geo, Seraphinia, and future beings one clean import path.
"""

from .EAR import capture, listen
from .OCR import scan_document, scan_screen
from .PHONEMES import label_phonemes, phonemes_to_visemes
from .SPEAK import speak
from .TONE import analyze_tone
from .VOICE_PROFILE import capture_voice_profile, list_voice_profiles, load_voice_profile

__all__ = [
    "analyze_tone",
    "capture",
    "capture_voice_profile",
    "label_phonemes",
    "list_voice_profiles",
    "listen",
    "load_voice_profile",
    "phonemes_to_visemes",
    "scan_document",
    "scan_screen",
    "speak",
]
