"""SPEAK.py — speech output adapter with honest fallback behavior."""

from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from ._paths import ensure_family_paths, require_file
from audio.config import get_config # Bringing in Sovereign Config

def speak(
    text: str,
    emotion: str = "neutral",
    reference_audio: str | Path | None = None,
    allow_fallback: bool = True,
) -> Dict[str, Any]:
    """Speak text using Christman Voice SDK with tiered synthesis parameters."""
    ensure_family_paths()
    config = get_config()
    
    if not text or not text.strip():
        raise ValueError("text is required")

    # Resolve reference audio using the config's model directory
    # instead of hardcoding Derek's root.
    ref = require_file(
        reference_audio or config.get("models.reference_audio", "models/default_voice.wav"), 
        "Reference voice WAV"
    )
    
    # Environment variables set once
    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/christman_numba_cache")

    try:
        from christman_voice_sdk import play_audio, resolve_voice_params, synthesize_speech, wait_for_playback

        # Pull synthesis params from the Config tiers
        params = resolve_voice_params(
            temperature=config.get("synthesis.temperature", 0.7),
            emotion=emotion,
            top_p=config.get("synthesis.top_p", 0.9)
        )
        
        wav = synthesize_speech(text, params, str(ref))
        if wav:
            played = play_audio(wav)
            wait_for_playback()
            return {
                "status": "spoken",
                "engine": "christman_voice_sdk_xtts",
                "wav": str(wav),
                "played": bool(played),
            }
    except Exception as exc:
        xtts_error = f"{type(exc).__name__}: {exc}"
    else:
        xtts_error = "synthesis returned no WAV"

    # Fallback to macos 'say' if allowed
    if allow_fallback and shutil.which("say"):
        subprocess.run(["say", text], check=True, timeout=60)
        return {
            "status": "spoken",
            "engine": "macos_say_fallback",
            "wav": None,
            "played": True,
            "xtts_error": xtts_error,
        }

    return {"status": "failed", "engine": "none", "wav": None, "played": False, "xtts_error": xtts_error}