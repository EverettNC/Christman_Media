"""Resolve per-being reference audio for XTTS synthesis."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from ._paths import ensure_family_paths

# CVE UI emotions → Christman acoustic labels (core.py CHRISTMAN_VOICE_PARAMS)
UI_EMOTION_MAP = {
    "warm": "happy",
    "calm": "neutral",
    "bright": "happy",
    "tender": "sweetheart",
    "resolute": "emphasis",
    "playful": "teasing",
    "neutral": "neutral",
    "happy": "happy",
    "proud": "proud",
}


def sound_root() -> Path:
    ensure_family_paths()
    env = os.environ.get("CHRISTMAN_SOUND_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def vega_root() -> Path | None:
    env = os.environ.get("VEGA_ROOT", "").strip()
    if env:
        root = Path(env).expanduser().resolve()
        return root if root.is_dir() else None
    default = Path("/Users/EverettN/vega")
    return default if default.is_dir() else None


def resolve_being_reference(being: str | None) -> Optional[Path]:
    """Find reference WAV for a TCAP being id (derek, vega, …)."""
    being = (being or "derek").strip().lower()
    root = sound_root()

    candidates: list[Path] = [
        root / "models" / "voices" / f"{being}.wav",
        root / "models" / "reference_audio" / f"{being}.wav",
        root / "voices" / f"{being}.wav",
    ]

    if being == "vega":
        vega = vega_root()
        if vega:
            candidates.extend([
                vega / "models" / "voices" / "vega.wav",
                vega / "voice" / "reference.wav",
                vega / "vega_output" / "audio" / "vega_reference.wav",
                vega / "vega_output" / "audio" / "vega.wav",
            ])
            audio_dir = vega / "vega_output" / "audio"
            if audio_dir.is_dir():
                wavs = sorted(
                    (p for p in audio_dir.glob("*.wav") if p.stat().st_size > 1024),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if wavs:
                    candidates.append(wavs[0])

    candidates.append(root / "models" / "default_voice.wav")

    profile_dir = Path.home() / ".christman_ai" / "voice_profiles"
    candidates.extend([
        profile_dir / being / "reference.wav",
        profile_dir / f"{being}.wav",
    ])

    for path in candidates:
        if path.is_file() and path.stat().st_size > 1024:
            return path
    return None


def map_ui_emotion(emotion: str) -> str:
    key = (emotion or "neutral").strip().lower()
    return UI_EMOTION_MAP.get(key, key)