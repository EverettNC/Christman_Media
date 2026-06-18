"""EAR.py — microphone capture and listening adapter."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from .._paths import ensure_family_paths
from audio.config import get_config  # Bringing in the Sovereign Config

def capture(duration_seconds: float = 6.0, device: Optional[int] = None) -> Path:
    """Capture a fixed-duration sample using tier-specific settings."""
    ensure_family_paths()
    config = get_config()
    
    from christman_voice_sdk import capture_mic_vad

    return capture_mic_vad(
        max_duration=duration_seconds, 
        device=device,
        sample_rate=config.get("audio.sample_rate"),
        target_db=config.get("audio.target_db")
    )


def listen(max_duration: float = 10.0, device: Optional[int] = None) -> Path:
    """
    Listen using tier-gated VAD thresholds.
    """
    ensure_family_paths()
    config = get_config()
    
    from christman_voice_sdk import listen as sdk_listen

    return sdk_listen(
        max_duration=max_duration, 
        device=device,
        silence_threshold=config.get("audio.silence_threshold_db")
    )