"""Call ChristmanImageEngine to generate B-roll stills for CVE timelines."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

CIE_BASE = os.environ.get("CIE_BASE", "http://127.0.0.1:8618/image")


def generate_broll(
    prompt: str,
    *,
    style: str = "steampunk",
    being: str = "vega",
    platform: str = "instagram",
    negative: str = "",
    timeout_s: int = 600,
) -> dict:
    """
    Start a CIE render and block until done.
    Returns dict with cve_asset_path and output_url on success.
    Raises RuntimeError on failure.
    """
    payload = json.dumps({
        "prompt": prompt,
        "negative": negative,
        "style": style,
        "being": being,
        "platform": platform,
        "export_to_cve": True,
    }).encode()

    req = urllib.request.Request(
        f"{CIE_BASE}/api/render",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"ChristmanImageEngine unreachable at {CIE_BASE}. "
            "Start unified stack with: python tcap_media.py "
            "(or CIE standalone: python server.py in ChristmanImageEngine)"
        ) from exc

    job_id = data.get("jobId") or data.get("job_id")
    if not job_id:
        raise RuntimeError(f"CIE returned no job id: {data}")

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status_req = urllib.request.Request(f"{CIE_BASE}/api/jobs/{job_id}")
        with urllib.request.urlopen(status_req, timeout=15) as resp:
            job = json.loads(resp.read().decode())

        if job.get("status") == "done":
            if not job.get("cve_asset_path"):
                raise RuntimeError("CIE finished but did not export to CVE assets.")
            return {
                "job_id": job_id,
                "cve_asset_path": job["cve_asset_path"],
                "output_url": job.get("output_url") or job.get("outputUrl"),
            }

        if job.get("status") == "failed":
            raise RuntimeError(job.get("error") or "CIE generation failed")

        time.sleep(1.5)

    raise RuntimeError(f"CIE job {job_id} timed out after {timeout_s}s")