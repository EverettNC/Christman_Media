"""Vega marketing PR — queue, blueprint, and TCAP stack bridge for CVE."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from engine.vega_init import bootstrap_vega, list_vega_images, vega_health


def _vega_posts_file() -> Path:
    root = bootstrap_vega()
    return root / "vega" / "data" / "posts.json"


def marketing_queue(*, limit: int = 50) -> dict[str, Any]:
    posts_file = _vega_posts_file()
    if not posts_file.is_file():
        return {"count": 0, "posts": [], "note": "No posts yet — run Vega daily engine or POST /api/vega/generate"}

    try:
        data = json.loads(posts_file.read_text())
    except json.JSONDecodeError as exc:
        return {"count": 0, "posts": [], "error": f"Corrupt posts.json: {exc}"}

    if not isinstance(data, list):
        return {"count": 0, "posts": []}

    ready = [p for p in data if p.get("status") in ("completed", "ready")]
    ready.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return {"count": len(ready[:limit]), "posts": ready[:limit]}


def marketing_status() -> dict[str, Any]:
    health = vega_health()
    blueprint = bootstrap_vega() / "docs" / "social_media_agent_blueprint.pdf"
    return {
        **health,
        "blueprint": str(blueprint) if blueprint.is_file() else None,
        "blueprint_url": "/api/vega/blueprint" if blueprint.is_file() else None,
        "queue_count": marketing_queue(limit=200)["count"],
        "recent_images": list_vega_images(limit=12),
        "frs_pillars": {
            "1_strategy": "STRATEGY.py — personas + platform matrix",
            "2_content": "HSO builder + daily_engine",
            "3_distribution": "scheduler + queue (manual post until API keys set)",
            "4_paid": "AD_FUNNEL_STAGES — triggers on real metrics only",
            "5_metrics": "analytics/tracker — rejects vanity metrics",
        },
        "gaps": _marketing_gaps(health),
    }


def _tcap_probe() -> dict[str, Any]:
    cie_root = os.environ.get("CIE_ROOT", "")
    return {
        "cie": bool(cie_root) and Path(cie_root).is_dir() and (Path(cie_root) / "server.py").is_file(),
        "cve": True,
    }


def _marketing_gaps(health: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    tcap = health.get("tcap_media") or _tcap_probe()
    if not health.get("mounted"):
        gaps.append("VEGA_ROOT not mounted — set VEGA_ROOT=~/vega")
    if not tcap.get("cie") and not os.environ.get("REPLICATE_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        gaps.append("Start TCAP Media (python tcap_media.py) for local image gen")
    if not tcap.get("cve"):
        gaps.append("CVE offline — short-form video slots will fail without tcap_media.py")
    if not Path("/Volumes/LIFE2").exists():
        gaps.append("LIFE2 not mounted — B-roll assembly unavailable")
    if not os.environ.get("INSTAGRAM_ACCESS_TOKEN"):
        gaps.append("No INSTAGRAM_ACCESS_TOKEN — auto-publish disabled; queue is review-only")
    return gaps


def proxy_vega_generate(payload: dict) -> dict[str, Any]:
    """Forward generate request to Vega Flask API on :5050 if running."""
    url = os.environ.get("VEGA_API", "http://127.0.0.1:5050/generate")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        return {
            "status": "error",
            "reason": (
                f"Vega API not running at {url}. "
                "Start: cd ~/vega && python3 -m vega.main"
            ),
            "detail": str(exc),
        }