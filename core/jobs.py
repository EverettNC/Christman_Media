"""In-memory render job state for the CVE API."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class JobState:
    id: str
    prompt: str
    status: str = "queued"  # queued | rendering | done | failed
    progress: float = 0.0
    lines: list[dict[str, Any]] = field(default_factory=list)
    output_path: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)


_jobs: dict[str, JobState] = {}
_lock = threading.Lock()


def create_job(prompt: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = JobState(id=job_id, prompt=prompt)
    return job_id


def get_job(job_id: str) -> Optional[JobState]:
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        for key, value in fields.items():
            setattr(job, key, value)


def append_line(job_id: str, kind: str, message: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job.lines.append({
            "t": int((time.time() - job.created_at) * 1000),
            "k": kind,
            "s": message,
        })