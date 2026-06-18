"""VOICE_PROFILE.py — voice frequency profile capture adapter."""

from __future__ import annotations
from typing import Dict, List
from .._paths import ensure_family_paths
from audio.config import get_config  # Bringing in the Sovereign Config

def capture_voice_profile(name: str = "default", duration: int = 8) -> Dict:
    """Capture and save a real acoustic voice-frequency profile using tier-gated settings."""
    ensure_family_paths()
    config = get_config()
    
    from christman_voice_sdk.integration.voice_capture_client import (
        capture_audio,
        extract_frequency_signature,
        save_profile,
    )

    # Use config settings for capture (e.g., sample rate) to ensure 
    # the frequency signature is captured at the intended resolution.
    audio = capture_audio(
        duration=duration, 
        sample_rate=config.get("audio.sample_rate")
    )
    
    signature = extract_frequency_signature(audio)
    profile_path = save_profile(name, signature)
    
    return {
        "name": name,
        "profile_path": str(profile_path),
        "signature": signature,
    }

def load_voice_profile(name: str = "default") -> Dict:
    """Load a saved voice-frequency signature."""
    ensure_family_paths()
    from christman_voice_sdk.integration.voice_capture_client import load_profile
    return load_profile(name)

def list_voice_profiles() -> List[str]:
    """List saved voice-frequency profile names."""
    ensure_family_paths()
    from christman_voice_sdk.integration.voice_capture_client import list_profiles
    return list_profiles()