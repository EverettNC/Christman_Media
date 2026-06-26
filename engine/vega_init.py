"""
Mount Vega for CVE / TCAP Media pipelines.

Vega is the marketing being — content orchestration, B-roll output, and (when
trained) reference voice for XTTS via Christman-Sound.

Resolution order:
  1. VEGA_ROOT env
  2. ~/vega (Everett layout)
  3. Sibling ../vega beside ChristmanVideoEngine
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

CVE_ROOT = Path(__file__).resolve().parent.parent
_MOUNTED_ROOT: Path | None = None

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def resolve_vega_root() -> Path:
    env = os.environ.get("VEGA_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()

    candidates = [
        Path("/Users/EverettN/vega"),
        CVE_ROOT.parent / "vega",
    ]
    for path in candidates:
        if (path / "vega" / "CORE.py").is_file() or (path / "vega_output").is_dir():
            return path.resolve()
    return Path("/Users/EverettN/vega").resolve()


def resolve_vega_voice_training_root() -> Path | None:
    """NextGen TTS training cwd (Vega voice fine-tune checkpoints)."""
    env = os.environ.get("VEGA_VOICE_TRAINING_ROOT", "").strip()
    if env:
        root = Path(env).expanduser().resolve()
        return root if root.is_dir() else None

    candidates = [
        Path("/Users/EverettN/Neural-Audio-Codec"),
        CVE_ROOT.parent / "Neural-Audio-Codec",
    ]
    for path in candidates:
        if (path / "checkpoints").is_dir() or (path / "training_data").is_dir():
            return path.resolve()
    return None


def bootstrap_vega(*, required: bool = False) -> Path:
    """Set VEGA_ROOT in the environment. Idempotent."""
    global _MOUNTED_ROOT
    if _MOUNTED_ROOT is not None:
        return _MOUNTED_ROOT

    root = resolve_vega_root()
    pkg = root / "vega"
    if not pkg.is_dir() and not (root / "vega_output").is_dir():
        if required:
            raise FileNotFoundError(
                f"Vega not found at {root}. Set VEGA_ROOT (e.g. ~/vega)."
            )
        return root

    os.environ.setdefault("VEGA_ROOT", str(root))
    training = resolve_vega_voice_training_root()
    if training:
        os.environ.setdefault("VEGA_VOICE_TRAINING_ROOT", str(training))

    _MOUNTED_ROOT = root
    return root


def vega_images_dir() -> Path | None:
    root = bootstrap_vega()
    images = root / "vega_output" / "images"
    return images if images.is_dir() else None


def list_vega_images(*, limit: int = 200) -> list[dict[str, Any]]:
    images_dir = vega_images_dir()
    if not images_dir:
        return []

    entries: list[tuple[float, dict[str, Any]]] = []
    for path in images_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in _IMAGE_SUFFIXES:
            continue
        entries.append((
            path.stat().st_mtime,
            {
                "name": path.name,
                "path": f"vega_output/images/{path.name}",
                "url": f"/api/vega/images/{path.name}",
                "source": "vega",
                "size": path.stat().st_size,
            },
        ))

    entries.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in entries[:limit]]


def _latest_checkpoint(training_root: Path | None) -> Path | None:
    if not training_root:
        return None
    search_dirs = [training_root / "checkpoints", training_root]
    found: list[Path] = []
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        found.extend(directory.glob("nextgen_tts_epoch_*.pt"))
    if not found:
        return None
    return max(found, key=lambda p: p.stat().st_mtime)


def vega_health() -> dict[str, Any]:
    root = bootstrap_vega()
    pkg = root / "vega"
    output = root / "vega_output"
    images_dir = output / "images"
    audio_dir = output / "audio"
    training = resolve_vega_voice_training_root()
    latest_ckpt = _latest_checkpoint(training)

    image_count = 0
    if images_dir.is_dir():
        image_count = sum(
            1 for p in images_dir.iterdir()
            if p.is_file() and p.suffix.lower() in _IMAGE_SUFFIXES
        )

    blueprint = root / "docs" / "social_media_agent_blueprint.pdf"
    cie_root = os.environ.get("CIE_ROOT", "")
    tcap = {
        "tcap_base": os.environ.get("TCAP_BASE", "http://127.0.0.1:8618"),
        "cie": bool(cie_root) and Path(cie_root).is_dir() and (Path(cie_root) / "server.py").is_file(),
        "cve": True,
    }

    return {
        "name": "Vega",
        "path": str(root),
        "package": str(pkg) if pkg.is_dir() else None,
        "mounted": pkg.is_dir() or output.is_dir(),
        "core_py": (pkg / "CORE.py").is_file(),
        "vega_output": output.is_dir(),
        "image_count": image_count,
        "audio_dir": audio_dir.is_dir(),
        "frs_blueprint": str(blueprint) if blueprint.is_file() else None,
        "tcap_media": tcap,
        "voice_training": {
            "path": str(training) if training else None,
            "latest_checkpoint": str(latest_ckpt) if latest_ckpt else None,
            "epoch": _checkpoint_epoch(latest_ckpt),
            "note": "Independent of being voice — marketing uses CVE/CIE stack",
        },
        "capabilities": [
            "Social content orchestration (CORE.py)",
            "B-roll / title cards (vega_output/)",
            "Caption & hashtag engine (VOICE.py)",
            "Narrator (edge-tts / pyttsx3 fallback)",
            "XTTS reference via Christman-Sound when vega.wav is present",
        ],
    }


def _checkpoint_epoch(path: Path | None) -> int | None:
    if not path:
        return None
    stem = path.stem  # nextgen_tts_epoch_80
    if "_epoch_" in stem:
        try:
            return int(stem.rsplit("_epoch_", 1)[-1])
        except ValueError:
            return None
    return None