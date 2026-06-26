#!/usr/bin/env python3
"""
TCAP Media — Everett's unified local launcher.

Starts ChristmanVideoEngine with ChristmanImageEngine mounted at /image.
One process. One port. Two public repos unchanged for pull/install.

Usage:
  python tcap_media.py

Override image engine location:
  CIE_ROOT=/path/to/ChristmanImageEngine python tcap_media.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CVE_ROOT = Path(__file__).resolve().parent

# Coqui XTTS (Christman voice cloning) requires Python 3.11 — not 3.12+.
_VENV311 = CVE_ROOT / ".venv311" / "bin" / "python"
if _VENV311.is_file() and sys.version_info >= (3, 12):
    os.execv(str(_VENV311), [str(_VENV311), str(Path(__file__).resolve()), *sys.argv[1:]])
CIE_ROOT = Path(os.environ.get("CIE_ROOT", CVE_ROOT.parent / "ChristmanImageEngine"))
SOUND_ROOT = Path(os.environ.get("CHRISTMAN_SOUND_ROOT", CVE_ROOT.parent / "Christman-Sound"))
VEGA_ROOT = Path(os.environ.get("VEGA_ROOT", Path("/Users/EverettN/vega")))

if not (CIE_ROOT / "server.py").is_file():
    print(f"CRITICAL: ChristmanImageEngine not found at {CIE_ROOT}")
    print("Clone it beside ChristmanVideoEngine or set CIE_ROOT.")
    sys.exit(1)

os.environ.setdefault("CVE_ROOT", str(CVE_ROOT))
os.environ.setdefault("CIE_ROOT", str(CIE_ROOT))
os.environ.setdefault("CIE_BASE", "http://127.0.0.1:8618/image")
os.environ.setdefault("TCAP_BASE", "http://127.0.0.1:8618")
os.environ.setdefault("CVE_BASE", "http://127.0.0.1:8618")
if (SOUND_ROOT / "core.py").is_file():
    os.environ.setdefault("CHRISTMAN_SOUND_ROOT", str(SOUND_ROOT))
if (VEGA_ROOT / "vega" / "CORE.py").is_file() or (VEGA_ROOT / "vega_output").is_dir():
    os.environ.setdefault("VEGA_ROOT", str(VEGA_ROOT))

os.chdir(CVE_ROOT)
sys.path.insert(0, str(CVE_ROOT))

import uvicorn  # noqa: E402
from server import app  # noqa: E402

if __name__ == "__main__":
    print(
        f"""
==================================================
  TCAP Media — Video + Image + Christman-Sound
  The Christman AI Project · Luma Cognify AI

  Portal:  http://127.0.0.1:8618/
  Video:   http://127.0.0.1:8618/video
  Image:   http://127.0.0.1:8618/image
  Sound:   {SOUND_ROOT}
  Vega:    {VEGA_ROOT}
==================================================
"""
    )
    uvicorn.run(app, host="127.0.0.1", port=8618, reload=False)