"""Path helpers for local Christman family projects.

The current family layout has Derek and the Christman Voice SDK as sibling
folders under Downloads. These helpers keep imports explicit and fail loudly
when the expected folders are absent.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


DEFAULT_DEREK_ROOT = Path(os.getenv(
    "DEREK_ROOT",
    "/Users/EverettN/Downloads/DerekMCPServer",
))
DEFAULT_SDK_ROOT = Path(os.getenv(
    "CHRISTMAN_VOICE_SDK_ROOT",
    "/Users/EverettN/Downloads",
))


def ensure_family_paths() -> None:
    """Add Derek and SDK parent directories to sys.path once."""
    for path in (DEFAULT_DEREK_ROOT, DEFAULT_SDK_ROOT):
        path_str = str(path)
        if path.exists() and path_str not in sys.path:
            sys.path.insert(0, path_str)


def require_file(path: str | Path, label: str) -> Path:
    """Return a path or raise a clear error if it is missing."""
    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"{label} not found: {resolved}")
    return resolved
