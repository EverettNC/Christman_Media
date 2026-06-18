"""TONE.py — audio tone and emotion analysis adapter."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
from .._paths import ensure_family_paths, require_file
from audio.config import get_config  # Bringing in the Sovereign Config

def analyze_tone(audio_path: str | Path) -> Dict[str, Any]:
    """Analyze audio using tier-gated tone analysis parameters."""
    ensure_family_paths()
    wav = require_file(audio_path, "Audio file")
    config = get_config()

    # We extract settings from the config tier
    # This prevents the system from "flattening" the analysis parameters
    try:
        from christman_voice_sdk.tone.tone_analyzer import get_tone_analyzer
        
        # Inject the model path directly from your config
        model_path = config.get("models.tone_engine", "default")
        analyzer = get_tone_analyzer(engine=model_path)
        
        return analyzer.analyze(str(wav))
    
    except Exception:
        # Fallback to the sovereign engine with specific emotional calibration
        from christman_voice_sdk.core import ToneScoreEngine
        
        # Inject the emotional range from your config tier
        # This keeps the "human fingerprint" (intensity/cadence) intact
        return ToneScoreEngine(
            emotional_range=config.get("synthesis.emotional_range", 7)
        ).analyze(str(wav))