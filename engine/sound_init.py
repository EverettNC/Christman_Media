"""
Mount Christman-Sound for CVE pipelines.

Christman-Sound (core.py + CHRISTMAN_EAR_CANAL + christman_voice_sdk) is the
third TCAP engine: ToneScore™, empathy modes, TTS, hearing, music, nonverbal.

Layout (canonical):
  Christman-Sound/
    core.py
    CHRISTMAN_EAR_CANAL/   → EAR, SPEAK, TONE, OCR, …
    christman_voice_sdk/   → audio, engines, synthesis, tone, utils, …

Resolution order:
  1. CHRISTMAN_SOUND_ROOT env
  2. Sibling ../Christman-Sound (Everett layout)
  3. Bundled ChristmanVideoEngine/Christman-Sound (public fallback)
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from typing import Any

CVE_ROOT = Path(__file__).resolve().parent.parent
_MOUNTED_ROOT: Path | None = None

_CORE_EXPORTS = (
    "synthesize_speech",
    "resolve_voice_params",
    "play_audio",
    "wait_for_playback",
    "capture_mic",
    "capture_mic_vad",
    "ToneScoreEngine",
    "CHRISTMAN_EMOTIONS",
)


def resolve_sound_root() -> Path:
    env = os.environ.get("CHRISTMAN_SOUND_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()

    candidates = [
        CVE_ROOT.parent / "Christman-Sound",
        Path("/Users/EverettN/Christman-Sound"),
        CVE_ROOT / "Christman-Sound",
    ]
    for path in candidates:
        if (path / "core.py").is_file():
            return path.resolve()
    return (CVE_ROOT / "Christman-Sound").resolve()


def resolve_sdk_dir(root: Path | None = None) -> Path | None:
    """
    Christman-Sound/christman_voice_sdk — engines, synthesis, utils, tone, etc.
    Accepts legacy folder name with trailing space.
    """
    root = root or resolve_sound_root()
    for name in ("christman_voice_sdk", "christman_voice_sdk "):
        candidate = root / name
        if (candidate / "engines" / "xtts_engine.py").is_file():
            return candidate.resolve()
    return None


def bootstrap_sound(*, required: bool = False) -> Path:
    """Add Christman-Sound to sys.path and register christman_voice_sdk. Idempotent."""
    global _MOUNTED_ROOT
    if _MOUNTED_ROOT is not None:
        return _MOUNTED_ROOT

    root = resolve_sound_root()
    if not (root / "core.py").is_file():
        if required:
            raise FileNotFoundError(
                f"Christman-Sound not found at {root}. "
                "Set CHRISTMAN_SOUND_ROOT to your install (e.g. ~/Christman-Sound)."
            )
        return root

    os.environ.setdefault("CHRISTMAN_SOUND_ROOT", str(root))
    os.environ.setdefault("CHRISTMAN_VOICE_SDK_ROOT", str(root))

    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    sdk_dir = resolve_sdk_dir(root)
    if sdk_dir is not None:
        sdk_str = str(sdk_dir)
        if sdk_str not in sys.path:
            sys.path.insert(0, sdk_str)

    try:
        from CHRISTMAN_EAR_CANAL._paths import ensure_family_paths

        ensure_family_paths()
    except ImportError:
        pass

    if sdk_dir is not None:
        _register_voice_sdk_package(root, sdk_dir)

    _MOUNTED_ROOT = root
    return root


def _register_voice_sdk_package(root: Path, sdk_dir: Path) -> None:
    """
    Expose Christman-Sound/core.py as christman_voice_sdk for EAR_CANAL + CVE.

    core.py imports subpackages relatively (.synthesis, .engines) — those live
    under christman_voice_sdk/. Submodules also use top-level imports (engines.*)
    when sdk_dir is on sys.path.
    """
    pkg = sys.modules.get("christman_voice_sdk")
    if pkg is not None and getattr(pkg, "synthesize_speech", None):
        return

    package = types.ModuleType("christman_voice_sdk")
    package.__path__ = [str(sdk_dir)]  # type: ignore[attr-defined]
    package.__package__ = "christman_voice_sdk"
    sys.modules["christman_voice_sdk"] = package

    spec = importlib.util.spec_from_file_location(
        "christman_voice_sdk.core",
        root / "core.py",
        submodule_search_locations=[str(sdk_dir)],
    )
    if spec is None or spec.loader is None:
        return

    core_mod = importlib.util.module_from_spec(spec)
    core_mod.__package__ = "christman_voice_sdk"
    sys.modules["christman_voice_sdk.core"] = core_mod
    try:
        spec.loader.exec_module(core_mod)
    except Exception:
        sys.modules.pop("christman_voice_sdk.core", None)
        return

    for name in _CORE_EXPORTS:
        if hasattr(core_mod, name):
            setattr(package, name, getattr(core_mod, name))


def sound_health(*, deep: bool = False) -> dict[str, Any]:
    """Fast path: filesystem checks only. deep=True imports speak (loads torch)."""
    root = resolve_sound_root()
    sdk_dir = resolve_sdk_dir(root)
    core_ok = (root / "core.py").is_file()
    dsp_ok = (root / "christman_dsp.so").is_file()
    ear_ok = (root / "CHRISTMAN_EAR_CANAL" / "SPEAK.py").is_file()

    speak_ok = False
    synthesis_ok = False
    probe_error = None
    if deep and core_ok:
        try:
            bootstrap_sound()
            from CHRISTMAN_EAR_CANAL import speak  # noqa: F401

            speak_ok = True
            core_mod = sys.modules.get("christman_voice_sdk.core")
            if core_mod is not None:
                synthesis_ok = bool(
                    getattr(core_mod, "_shorty_ok", False)
                    or getattr(core_mod, "_xtts_ok", False)
                )
        except Exception as exc:
            probe_error = str(exc)

    return {
        "name": "Christman-Sound",
        "path": str(root),
        "sdk_path": str(sdk_dir) if sdk_dir else None,
        "mounted": core_ok,
        "core_py": core_ok,
        "dsp_native": dsp_ok,
        "ear_canal": ear_ok,
        "speak_import": speak_ok,
        "synthesis_engines": synthesis_ok,
        "probe_error": probe_error,
        "ocr_module": (root / "christman_ocr_shared.py").is_file(),
        "capabilities": [
            "ToneScore",
            "Adaptive Response (Hold Space / Gentle Lift)",
            "Quantified Empathy",
            "Takotsubo Physics Layer",
            "11 Christman Emotion Labels",
            "XTTS / Shorty synthesis",
            "CHRISTMAN_EAR_CANAL (listen, speak, tone, OCR)",
            "Music engine",
            "Nonverbal / temporal engine",
            "Speech-to-speech pipeline",
        ],
    }