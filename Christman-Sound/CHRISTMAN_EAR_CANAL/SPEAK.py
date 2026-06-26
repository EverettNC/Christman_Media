"""SPEAK.py — speech output adapter with honest fallback behavior."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from ._paths import ensure_family_paths, require_file
from .VOICES import map_ui_emotion, resolve_being_reference


def speak(
    text: str,
    emotion: str = "neutral",
    being: str = "derek",
    reference_audio: str | Path | None = None,
    allow_fallback: bool = True,
    play: bool = True,
) -> Dict[str, Any]:
    """Synthesize speech for a TCAP being. Set play=False for video pipeline renders."""
    ensure_family_paths()

    if not text or not text.strip():
        raise ValueError("text is required")

    ref_path = None
    if reference_audio:
        ref_path = require_file(reference_audio, "Reference voice WAV")
    else:
        ref_path = resolve_being_reference(being)
        if ref_path is None:
            try:
                from audio.config import get_config

                config = get_config()
                ref_path = require_file(
                    config.get("models.reference_audio", "models/default_voice.wav"),
                    "Reference voice WAV",
                )
            except Exception:
                ref_path = None

    if ref_path is None:
        return {
            "status": "failed",
            "engine": "none",
            "wav": None,
            "played": False,
            "being": being,
            "xtts_error": f"No reference WAV for being={being}. "
            "Drop models/voices/{being}.wav in Christman-Sound.",
        }

    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    os.environ.setdefault("NUMBA_CACHE_DIR", "/tmp/christman_numba_cache")

    christman_emotion = map_ui_emotion(emotion)
    xtts_error = "synthesis unavailable"

    try:
        from christman_voice_sdk import resolve_voice_params, synthesize_speech

        if play:
            from christman_voice_sdk import play_audio, wait_for_playback
        else:
            play_audio = None
            wait_for_playback = None

        params = resolve_voice_params(55.0, christman_emotion, 0.0)
        wav = synthesize_speech(text, params, str(ref_path))
        if wav:
            played = False
            if play and play_audio and wait_for_playback:
                played = bool(play_audio(wav))
                wait_for_playback()
            return {
                "status": "spoken",
                "engine": "christman_voice_sdk",
                "wav": str(wav),
                "played": played,
                "being": being,
                "emotion": christman_emotion,
            }
        xtts_error = "synthesis returned no WAV"
    except Exception as exc:
        xtts_error = f"{type(exc).__name__}: {exc}"

    if allow_fallback and shutil.which("say"):
        subprocess.run(["say", text], check=True, timeout=60)
        return {
            "status": "spoken",
            "engine": "macos_say_fallback",
            "wav": None,
            "played": play,
            "being": being,
            "xtts_error": xtts_error,
        }

    return {
        "status": "failed",
        "engine": "none",
        "wav": None,
        "played": False,
        "being": being,
        "xtts_error": xtts_error,
    }