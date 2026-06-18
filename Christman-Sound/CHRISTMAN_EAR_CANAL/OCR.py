"""OCR.py — Christman shared OCR and screen-reading adapter."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional
import asyncio
from .._paths import ensure_family_paths, require_file
from audio.config import get_config

def _get_ocr_engine(being: str):
    """Factory to get OCR engine with config-based resource limits."""
    from christman_ocr_shared import ChristmanOCR
    config = get_config()
    # Inject config settings: num_workers, device acceleration, etc.
    return ChristmanOCR(
        being_name=being,
        device=config.get("system.device"),
        workers=config.get("system.num_workers")
    )

def scan_document(path: str | Path, being: str = "Derek") -> Dict[str, Any]:
    ensure_family_paths()
    source = require_file(path, "Document/image")
    return asyncio.run(_get_ocr_engine(being).read_document(str(source)))

def scan_screen(being: str = "Derek") -> Dict[str, Any]:
    ensure_family_paths()
    return asyncio.run(_get_ocr_engine(being).read_screen())