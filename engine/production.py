"""Real CVE production pipeline — wired to all CLI surfaces."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from core.agent_brain import AgentBrain
from core.jobs import append_line, update_job
from core.memory import MemoryModule
from core.system_init import initialize_environment
from modules.auto_edit import auto_edit_video
from modules.export import VideoExport
from modules.generator import VideoGenerator, render_timeline
from modules.text_overlay import make_caption_overlay
from modules.highlights import extract_highlights
from modules.montage import create_montage
from engine.cie_client import generate_broll
from engine.document_ingest import build_prompt_from_document, extract_text, is_document
from engine.sound_init import bootstrap_sound
from modules.timeline import (
    CINEMA_THEME,
    HIGH_CONTRAST_THEME,
    NEUTRAL_THEME,
    STEAMPUNK_THEME,
    ResolutionPreset,
    create_lesson_template,
)

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "data" / "uploads"
OUTPUT_DIR = ROOT / "data" / "output"

THEME_MAP = {
    "steampunk": STEAMPUNK_THEME,
    "cinema": CINEMA_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
    "neutral": NEUTRAL_THEME,
}

RESOLUTION_MAP = {
    "1080p": ResolutionPreset.FHD_1080,
    "720p": ResolutionPreset.HD_720,
    "4K": ResolutionPreset.UHD_4K,
}


def _setup() -> None:
    os.chdir(ROOT)
    bootstrap_sound()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _set_progress(job_id: str, progress: float, message: str, kind: str = "step") -> None:
    update_job(job_id, progress=progress)
    append_line(job_id, kind, message)


def _fail(job_id: str, message: str) -> bool:
    update_job(job_id, status="failed", error=message, progress=100)
    append_line(job_id, "err", message)
    return False


def _upload_path(file_id: str) -> Path:
    return UPLOAD_DIR / file_id


def _short_title_from_prompt(prompt: str) -> str:
    for line in (prompt or "").splitlines():
        s = line.strip()
        if s and len(s) > 6:
            return s[:80]
    return "Untitled"


def _finish(job_id: str, output_path: str, log_line: str, memory_prompt: str) -> bool:
    exporter = VideoExport(output_dir=str(OUTPUT_DIR))
    finalized = exporter.finalize(output_path)
    if not finalized:
        return _fail(job_id, "Export validation failed after render.")

    mem = MemoryModule()
    mem.store_event(memory_prompt, finalized)

    update_job(job_id, status="done", progress=100, output_path=finalized)
    append_line(job_id, "done", log_line)
    return True


def _run_prompt(job_id: str, request: dict) -> bool:
    prompt = (request.get("prompt") or "").strip()
    doc_id = request.get("input_file_id") or request.get("document_file_id")
    doc_display_title: str | None = None
    if doc_id:
        doc_path = _upload_path(doc_id)
        if not doc_path.is_file():
            return _fail(job_id, f"Document upload not found: {doc_id}")
        if is_document(doc_path):
            doc_display_title = doc_path.stem.replace("_", " ").replace("-", " ")
            try:
                if prompt.strip():
                    meta = extract_text(doc_path)
                    append_line(
                        job_id,
                        "ok",
                        f"document: {doc_path.name} attached · using your edited prompt "
                        f"({meta['method']}, {meta['chars']} chars available)",
                    )
                else:
                    prompt = build_prompt_from_document(doc_path, user_prompt=prompt)
                    append_line(job_id, "ok", f"document: extracted text from {doc_path.name}")
            except Exception as exc:
                return _fail(job_id, f"Document ingest failed: {exc}")
        elif not prompt:
            return _fail(job_id, "Upload is not a document and no prompt was provided.")

    if not prompt:
        return _fail(job_id, "Prompt is empty.")

    theme_id = request.get("theme", "steampunk")
    being = request.get("being", "derek")
    if isinstance(request.get("voice"), dict):
        being = request["voice"].get("being", being)
    resolution = request.get("resolution", "1080p")
    duration = int(request.get("duration") or 60)
    broll_image = request.get("broll_image")
    generate_broll_flag = bool(request.get("generate_broll"))

    append_line(job_id, "sys", f'$ cve render --prompt "{prompt[:72]}" --theme {theme_id} --being {being}')

    _set_progress(job_id, 8, "initialize: loading environment")
    initialize_environment()

    if generate_broll_flag and not broll_image:
        _set_progress(job_id, 12, "cie: generating B-roll still via ChristmanImageEngine")
        try:
            cie_result = generate_broll(
                prompt,
                style=theme_id if theme_id in THEME_MAP else "steampunk",
                being=being,
            )
            broll_image = cie_result["cve_asset_path"]
            append_line(job_id, "ok", f"cie: exported → {broll_image}")
        except Exception as exc:
            append_line(job_id, "warn", f"cie: B-roll skipped — {exc}")

    _set_progress(job_id, 15, "brain: decoding intent")
    brain = AgentBrain()
    final_prompt = brain.process_prompt(prompt)
    append_line(job_id, "ok", f"brain: {final_prompt[:120]}")

    target_destination = str(OUTPUT_DIR / f"job_{job_id}.mp4")
    theme = THEME_MAP.get(theme_id, STEAMPUNK_THEME)
    res_preset = RESOLUTION_MAP.get(resolution, ResolutionPreset.FHD_1080)

    for attempt in range(1, 4):
        _set_progress(job_id, 20 + attempt * 5, f"timeline: building lesson template (attempt {attempt})")
        overlay_path = None
        try:
            w, h = res_preset.dimensions
            overlay_path = make_caption_overlay(
                title=doc_display_title or _short_title_from_prompt(prompt),
                body=prompt[:420],
                width=w,
                height=h,
                out_path=ROOT / "data" / "temp" / f"overlay_{job_id}.png",
            )
        except Exception as exc:
            append_line(job_id, "warn", f"overlay: caption PNG skipped — {exc}")

        timeline = create_lesson_template(
            prompt,
            voice_being=being,
            theme=theme,
            broll_image=broll_image,
            target_duration=float(duration),
            display_title=doc_display_title,
            overlay_image=overlay_path,
        )
        timeline.resolution = res_preset
        if duration >= 15:
            for track in timeline.tracks:
                for clip in track.clips:
                    if clip.duration is not None:
                        clip.duration = min(clip.duration, float(duration))

        _set_progress(job_id, 35 + attempt * 10, "generator: ffmpeg render starting")
        result = render_timeline(
            timeline,
            target_destination,
            work_dir=str(ROOT / "data" / "temp"),
            burn_captions=True,
            caption_style="kids_large",
        )

        if result.success and os.path.getsize(result.output_path) > 1024:
            size_kb = os.path.getsize(result.output_path) / 1024
            _set_progress(job_id, 92, f"validate: {size_kb:.1f} KB · {result.duration:.1f}s", "ok")
            return _finish(
                job_id,
                result.output_path,
                f"done → {os.path.basename(result.output_path)} · {result.duration:.1f}s · {resolution}",
                prompt,
            )

        append_line(job_id, "warn", f"attempt {attempt} failed: {result.error or 'validation failed'}")
        time.sleep(0.5)

    return _fail(job_id, "Production failed after retries.")


def _run_autoedit(job_id: str, request: dict) -> bool:
    file_id = request.get("input_file_id")
    if not file_id:
        return _fail(job_id, "Upload a source video first.")

    src = _upload_path(file_id)
    if not src.is_file():
        return _fail(job_id, f"Upload not found: {file_id}")

    clip = float(request.get("clip") or 15)
    duration = float(request.get("duration") or request.get("targetDur") or 60)
    theme = request.get("theme", "steampunk")
    transition = request.get("transition", "fade")
    being = request.get("being", "derek")
    emotion = request.get("emotion", "warm")
    caption = request.get("caption", "kids_large")

    append_line(job_id, "sys", f"$ cve auto-edit {src.name} --clip-duration {clip} --target-duration {duration}")
    _set_progress(job_id, 10, "probe: analyzing source")
    initialize_environment()
    _set_progress(job_id, 30, "scene: detecting cuts")
    _set_progress(job_id, 55, "assemble: building timeline")

    result = auto_edit_video(
        str(src),
        output_dir=str(OUTPUT_DIR / "auto_edit"),
        clip_duration=clip,
        target_duration=duration,
        theme=theme,
        transition=transition,
        voice=being,
        emotion=emotion,
        caption_style=caption,
    )

    if not result.success:
        return _fail(job_id, result.error or "Auto-edit failed.")

    _set_progress(job_id, 90, f"encode: {result.clips_created} clips · {result.total_duration:.1f}s", "ok")
    final_path = str(OUTPUT_DIR / f"job_{job_id}.mp4")
    import shutil
    shutil.copy2(result.output_path, final_path)

    return _finish(job_id, final_path, f"done → {os.path.basename(final_path)} · {result.total_duration:.1f}s", src.name)


def _run_highlights(job_id: str, request: dict) -> bool:
    file_id = request.get("input_file_id")
    if not file_id:
        return _fail(job_id, "Upload a source video first.")

    src = _upload_path(file_id)
    if not src.is_file():
        return _fail(job_id, f"Upload not found: {file_id}")

    method = request.get("method", "scene")
    theme = request.get("theme", "steampunk")
    transition = request.get("transition", "xfade")
    caption = request.get("caption", "kids_large")

    append_line(job_id, "sys", f"$ cve highlights {src.name} --method {method}")
    _set_progress(job_id, 12, f"analyze: method={method}")
    initialize_environment()
    _set_progress(job_id, 40, "rank: scoring candidate moments")

    result = extract_highlights(
        str(src),
        output_dir=str(OUTPUT_DIR / "highlights"),
        method=method,
        theme=theme,
        transition=transition,
        caption_style=caption,
    )

    if not result.success:
        return _fail(job_id, result.error or "Highlights extraction failed.")

    _set_progress(job_id, 88, f"found: {result.highlights_found} highlights", "ok")
    final_path = str(OUTPUT_DIR / f"job_{job_id}.mp4")
    import shutil
    shutil.copy2(result.output_path, final_path)

    return _finish(
        job_id,
        final_path,
        f"done → {os.path.basename(final_path)} · {result.highlights_found} highlights",
        src.name,
    )


def _run_montage(job_id: str, request: dict) -> bool:
    file_ids = request.get("input_file_ids") or []
    if len(file_ids) < 2:
        return _fail(job_id, "Upload at least two clips for a montage.")

    paths = []
    for fid in file_ids:
        p = _upload_path(fid)
        if p.is_file():
            paths.append(str(p))
    if len(paths) < 2:
        return _fail(job_id, "Fewer than two valid uploaded clips.")

    duration = float(request.get("duration") or request.get("targetDur") or 60)
    theme = request.get("theme", "steampunk")
    transition = request.get("transition", "xfade")
    caption = request.get("caption", "kids_large")

    append_line(job_id, "sys", f"$ cve montage {' '.join(Path(p).name for p in paths)} --target-duration {duration}")
    _set_progress(job_id, 10, f"probe: {len(paths)} clips queued")
    initialize_environment()
    _set_progress(job_id, 45, "assemble: sequencing clips")

    target = str(OUTPUT_DIR / f"job_{job_id}.mp4")
    result = create_montage(
        paths,
        output_path=target,
        target_duration=duration,
        theme=theme,
        transition=transition,
        caption_style=caption,
    )

    if not result.success:
        return _fail(job_id, result.error or "Montage failed.")

    _set_progress(job_id, 90, f"encode: {result.clips_used} clips · {result.duration:.1f}s", "ok")
    return _finish(job_id, target, f"done → {os.path.basename(target)} · {result.duration:.1f}s", f"montage:{len(paths)}")


def run_production_job(job_id: str, request: dict) -> bool:
    kind = request.get("kind", "prompt")
    _setup()
    update_job(job_id, status="rendering", progress=2)

    try:
        if kind == "prompt":
            return _run_prompt(job_id, request)
        if kind == "autoedit":
            return _run_autoedit(job_id, request)
        if kind == "highlights":
            return _run_highlights(job_id, request)
        if kind == "montage":
            return _run_montage(job_id, request)
        if kind == "batch":
            return _fail(job_id, "Batch is not wired to the engine yet.")
        return _fail(job_id, f"Unknown render kind: {kind}")
    except Exception as exc:
        return _fail(job_id, str(exc))