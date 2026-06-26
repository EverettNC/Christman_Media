#!/usr/bin/env python3
"""Verify client.html bundle is wired to the real CVE API."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CLIENT = Path(__file__).resolve().parent.parent / "client.html"
UI_UUID = "85b84a65-4906-4bda-a0c8-de7adb46dc41"
DATA_UUID = "6f94d0ef-c13a-4348-bf41-977dd4f15bff"
CREATE_UUID = "5d753dcf-3c18-4810-8ca7-aae75502f5c3"


def decode_entry(entry: dict) -> str:
    import base64
    import gzip

    data = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        data = gzip.decompress(data)
    return data.decode("utf-8")


def main() -> int:
    text = CLIENT.read_text(encoding="utf-8")
    manifest = json.loads(
        re.search(r'<script type="__bundler/manifest">\n(.+?)\n  </script>', text, re.DOTALL).group(1)
    )

    errors: list[str] = []
    data = decode_entry(manifest[DATA_UUID])
    ui = decode_entry(manifest[UI_UUID])
    create = decode_entry(manifest[CREATE_UUID])

    if data.count("const API_BASE") != 1:
        errors.append(f"expected 1 API_BASE declaration, found {data.count('const API_BASE')}")
    if "uploadFile" not in data:
        errors.append("uploadFile missing from data bundle")
    if "useRenderEngine" not in ui or "/api/render" not in ui:
        errors.append("useRenderEngine not wired to /api/render")
    if "EventSource" not in ui:
        errors.append("SSE EventSource missing from UI bundle")
    if "uploadFiles" not in create and "onUploaded" not in create:
        errors.append("DropZone upload wiring missing from create bundle")
    if "ingestDocument" not in create or "Source document" not in create:
        errors.append("PromptSurface document ingest missing from create bundle")
    if ".pdf" not in create or "/api/documents/" not in create:
        errors.append("Document extract API wiring missing from create bundle")
    if "<video" not in ui and "outputUrl" not in ui:
        errors.append("video preview / outputUrl missing")

    if errors:
        print("client.html verification FAILED:")
        for err in errors:
            print(f"  - {err}")
        print("Run: python tools/patch_client.py")
        return 1

    print(f"OK: {CLIENT} is wired (API, upload, SSE, preview)")
    return 0


if __name__ == "__main__":
    sys.exit(main())