"""Load ChristmanImageEngine in isolation so core/engine do not collide with CVE."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_COLLISION_ROOTS = ("core", "engine")


def _stash_collision_modules() -> dict[str, Any]:
    saved: dict[str, Any] = {}
    for name in list(sys.modules):
        if name in _COLLISION_ROOTS or any(
            name.startswith(f"{root}.") for root in _COLLISION_ROOTS
        ):
            saved[name] = sys.modules.pop(name)
    return saved


def _restore_modules(saved: dict[str, Any]) -> None:
    for name in list(sys.modules):
        if name in _COLLISION_ROOTS or any(
            name.startswith(f"{root}.") for root in _COLLISION_ROOTS
        ):
            sys.modules.pop(name, None)
    sys.modules.update(saved)


def load_cie_app(cie_root: Path):
    """
    Import CIE's FastAPI app without overwriting CVE's core/engine packages.
    Route handlers keep references to CIE modules captured at import time.
    """
    cie_root = cie_root.resolve()
    cie_server = cie_root / "server.py"
    if not cie_server.is_file():
        raise FileNotFoundError(f"ChristmanImageEngine server.py missing: {cie_server}")

    cie_path = str(cie_root)
    saved = _stash_collision_modules()

    if cie_path in sys.path:
        sys.path.remove(cie_path)
    sys.path.insert(0, cie_path)

    try:
        spec = importlib.util.spec_from_file_location(
            "christman_image_engine.server",
            cie_server,
            submodule_search_locations=[cie_path],
        )
        if spec is None or spec.loader is None:
            raise ImportError("Could not build module spec for ChristmanImageEngine")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        app = getattr(module, "app", None)
        if app is None:
            raise ImportError("ChristmanImageEngine server has no FastAPI app")

        return app
    finally:
        if cie_path in sys.path:
            sys.path.remove(cie_path)
        _restore_modules(saved)


def mount_image_engine(app, cie_root: str | Path) -> bool:
    """Mount CIE at /image when cie_root is valid. Returns True on success."""
    if not cie_root:
        return False

    root = Path(cie_root)
    try:
        cie_app = load_cie_app(root)
    except Exception as exc:
        print(f"[TCAP] ChristmanImageEngine mount failed: {exc}")
        return False

    app.mount("/image", cie_app)
    print(f"[TCAP] ChristmanImageEngine mounted at /image ← {root.resolve()}")
    return True