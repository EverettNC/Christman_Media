import asyncio
import json
import os
import uuid
import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from pathlib import Path

from core.jobs import create_job, get_job
from engine.production import run_production_job

ROOT = os.path.dirname(os.path.abspath(__file__))
CLIENT_HTML = os.path.join(ROOT, "client.html")
PORTAL_HTML = os.path.join(ROOT, "portal.html")
VEGA_CLIENT_HTML = os.path.join(ROOT, "vega_client.html")
CIE_ROOT = os.environ.get("CIE_ROOT", "")
OUTPUT_DIR = os.path.join(ROOT, "data", "output")
UPLOAD_DIR = os.path.join(ROOT, "data", "uploads")
ASSETS_IMAGES_DIR = os.path.join(ROOT, "assets", "images")

app = FastAPI(title="Christman Video Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VoiceConfig(BaseModel):
    being: str = "derek"
    emotion: str = "warm"
    engine: str = "XTTS"


class RenderRequest(BaseModel):
    kind: str = "prompt"
    prompt: str = ""
    theme: str = "steampunk"
    caption: str = "default"
    duration: int = Field(default=60, ge=15, le=300)
    resolution: str = "1080p"
    transition: str = "xfade"
    being: str = "derek"
    emotion: str = "warm"
    engine: str = "XTTS"
    voice: VoiceConfig | None = None
    method: str = "scene"
    clip: float = 15.0
    targetDur: float | None = None
    input_file_id: str | None = None
    input_file_ids: list[str] | None = None
    generate_broll: bool = False
    broll_image: str | None = None


def _upload_is_document(file_id: str | None) -> bool:
    if not file_id:
        return False
    from engine.document_ingest import is_document

    path = Path(UPLOAD_DIR) / file_id
    return path.is_file() and is_document(path)


def _job_payload(request: RenderRequest) -> dict:
    data = request.model_dump()
    if request.voice:
        data["being"] = request.voice.being
        data["emotion"] = request.voice.emotion
        data["engine"] = request.voice.engine
    if request.targetDur is not None:
        data["duration"] = request.targetDur
    return data


def _job_response(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    output_url = None
    if job.output_path and os.path.isfile(job.output_path):
        output_url = f"/api/output/{os.path.basename(job.output_path)}"

    return {
        "job_id": job.id,
        "jobId": job.id,
        "status": job.status,
        "progress": round(job.progress, 1),
        "lines": job.lines,
        "output_url": output_url,
        "outputUrl": output_url,
        "error": job.error,
    }


def _html_response(path: str) -> FileResponse:
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate"}
    if path.endswith("client.html"):
        # 2MB bundle — allow browser to reuse while developing
        headers["Cache-Control"] = "private, max-age=300"
    return FileResponse(path, media_type="text/html", headers=headers)


@app.get("/")
async def serve_portal():
    if os.path.isfile(PORTAL_HTML):
        return _html_response(PORTAL_HTML)
    return _html_response(CLIENT_HTML)


@app.get("/video")
async def serve_video_client():
    return _html_response(CLIENT_HTML)


@app.get("/vega")
async def serve_vega_client():
    if os.path.isfile(VEGA_CLIENT_HTML):
        return _html_response(VEGA_CLIENT_HTML)
    raise HTTPException(status_code=404, detail="vega_client.html missing.")


def _document_ingest_health() -> dict:
    checks = {"pypdf": False, "pymupdf": False, "multipart": False}
    try:
        import pypdf  # noqa: F401

        checks["pypdf"] = True
    except ImportError:
        pass
    try:
        import fitz  # noqa: F401

        checks["pymupdf"] = True
    except ImportError:
        pass
    try:
        import multipart  # noqa: F401

        checks["multipart"] = True
    except ImportError:
        pass
    from engine.document_ingest import DOCUMENT_SUFFIXES

    checks["ready"] = checks["multipart"] and (checks["pypdf"] or checks["pymupdf"])
    checks["formats"] = sorted(DOCUMENT_SUFFIXES)
    return checks


@app.get("/api/health")
async def health(deep: bool = False):
    from engine.sound_init import sound_health
    from engine.vega_init import vega_health

    image_engine = None
    if CIE_ROOT and os.path.isdir(CIE_ROOT):
        image_engine = {
            "name": "ChristmanImageEngine",
            "mounted": True,
            "path": CIE_ROOT,
            "url": "/image",
        }
    payload = {
        "status": "ok",
        "engine": "Christman Video Engine",
        "mode": "tcap_media" if image_engine else "video_only",
        "cie_bridge": True,
        "image_engine": image_engine,
        "sound_engine": sound_health(deep=deep),
        "document_ingest": _document_ingest_health(),
    }
    if deep:
        payload["vega_engine"] = vega_health()
    return payload


@app.get("/api/assets/images")
async def list_image_assets():
    from engine.vega_init import list_vega_images

    os.makedirs(ASSETS_IMAGES_DIR, exist_ok=True)
    images = []
    for name in sorted(os.listdir(ASSETS_IMAGES_DIR)):
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            path = os.path.join(ASSETS_IMAGES_DIR, name)
            if os.path.isfile(path):
                images.append({
                    "name": name,
                    "path": f"assets/images/{name}",
                    "url": f"/api/assets/images/{name}",
                    "source": "cve",
                    "size": os.path.getsize(path),
                })
    vega_images = list_vega_images()
    return {"images": images + vega_images, "count": len(images) + len(vega_images)}


@app.get("/api/assets/images/{filename}")
async def serve_image_asset(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    path = os.path.join(ASSETS_IMAGES_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Image not found.")
    media = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    return FileResponse(path, media_type=media, filename=filename)


@app.get("/api/vega/status")
async def vega_marketing_status():
    from engine.vega_marketing import marketing_status

    return marketing_status()


@app.get("/api/vega/queue")
async def vega_marketing_queue():
    from engine.vega_marketing import marketing_queue

    return marketing_queue()


@app.get("/api/vega/blueprint")
async def vega_blueprint_pdf():
    from engine.vega_init import bootstrap_vega

    path = bootstrap_vega() / "docs" / "social_media_agent_blueprint.pdf"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Blueprint PDF not found in VEGA_ROOT/docs/")
    return FileResponse(path, media_type="application/pdf", filename="social_media_agent_blueprint.pdf")


class VegaGenerateRequest(BaseModel):
    slot: int = 2
    platform: str = "instagram"
    topic: str | None = None


@app.post("/api/vega/generate")
async def vega_generate_post(request: VegaGenerateRequest):
    from engine.vega_marketing import proxy_vega_generate

    result = proxy_vega_generate({
        "slot": request.slot,
        "platform": request.platform,
        "topic": request.topic,
    })
    if result.get("status") == "error":
        raise HTTPException(status_code=503, detail=result.get("reason", "Vega generate failed"))
    return result


@app.get("/api/vega/images/{filename}")
async def serve_vega_image(filename: str):
    from engine.vega_init import vega_images_dir

    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    images_dir = vega_images_dir()
    if not images_dir:
        raise HTTPException(status_code=404, detail="Vega images not mounted.")
    path = images_dir / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found.")
    media = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    return FileResponse(path, media_type=media, filename=filename)


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required.")

    from engine.document_ingest import DOCUMENT_SUFFIXES, VIDEO_SUFFIXES

    suffix = Path(file.filename).suffix.lower()
    allowed = VIDEO_SUFFIXES | DOCUMENT_SUFFIXES
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Upload video (mp4, mov, …) or document (pdf, html, txt, png, jpg, …).",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_id = f"{uuid.uuid4().hex[:12]}{suffix}"
    dest = os.path.join(UPLOAD_DIR, file_id)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(content) > 4 * 1024 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 4 GB limit.")

    with open(dest, "wb") as handle:
        handle.write(content)

    return {"fileId": file_id, "name": file.filename, "size": len(content)}


@app.get("/api/documents/{file_id}/extract")
async def extract_uploaded_document(file_id: str):
    from engine.document_ingest import extract_text, is_document

    if ".." in file_id or "/" in file_id or "\\" in file_id:
        raise HTTPException(status_code=400, detail="Invalid file id.")

    path = Path(UPLOAD_DIR) / file_id
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Upload not found.")
    if not is_document(path):
        raise HTTPException(status_code=400, detail="File is not a supported document.")

    try:
        result = extract_text(path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "fileId": file_id,
        "filename": result["filename"],
        "text": result["text"],
        "method": result["method"],
        "chars": result["chars"],
        "truncated": result["truncated"],
        "editable": True,
    }


@app.post("/api/render")
async def start_render(request: RenderRequest, background_tasks: BackgroundTasks):
    payload = _job_payload(request)
    has_doc = bool(payload.get("input_file_id")) and _upload_is_document(payload.get("input_file_id"))
    if request.kind == "prompt" and not payload.get("prompt", "").strip() and not has_doc:
        raise HTTPException(status_code=400, detail="Prompt or document upload is required.")

    job_id = create_job(payload.get("prompt") or f"{request.kind}-render")
    background_tasks.add_task(run_production_job, job_id, payload)

    return {"jobId": job_id, "job_id": job_id, "status": "queued"}


@app.post("/api/generate")
async def start_render_legacy(request: RenderRequest, background_tasks: BackgroundTasks):
    return await start_render(request, background_tasks)


@app.get("/api/render/{job_id}/stream")
async def render_stream(job_id: str):
    async def events():
        seen = 0
        last_progress = -1.0
        for _ in range(900):
            job = get_job(job_id)
            if not job:
                yield f"event: fail\ndata: {json.dumps({'s': 'Job not found'})}\n\n"
                return

            while seen < len(job.lines):
                line = job.lines[seen]
                yield f"event: log\ndata: {json.dumps({'k': line['k'], 's': line['s']})}\n\n"
                seen += 1

            if job.progress != last_progress:
                yield f"event: progress\ndata: {json.dumps({'progress': job.progress})}\n\n"
                last_progress = job.progress

            if job.status == "done":
                output_url = None
                if job.output_path and os.path.isfile(job.output_path):
                    output_url = f"/api/output/{os.path.basename(job.output_path)}"
                yield f"event: done\ndata: {json.dumps({'outputUrl': output_url})}\n\n"
                return

            if job.status == "failed":
                yield f"event: fail\ndata: {json.dumps({'s': job.error or 'Render failed'})}\n\n"
                return

            await asyncio.sleep(0.4)

        yield f"event: fail\ndata: {json.dumps({'s': 'Stream timeout'})}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    return _job_response(job_id)


@app.get("/api/render/{job_id}")
async def render_status(job_id: str):
    return _job_response(job_id)


@app.get("/api/output/{filename}")
async def serve_output(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Output not found.")

    return FileResponse(path, media_type="video/mp4", filename=filename)


def mount_image_engine_if_configured() -> bool:
    """Mount ChristmanImageEngine at /image when CIE_ROOT is set (tcap_media.py)."""
    if not CIE_ROOT:
        return False
    from engine.cie_mount import mount_image_engine

    return mount_image_engine(app, CIE_ROOT)


mount_image_engine_if_configured()


if __name__ == "__main__":
    print("[System] Christman Video Engine API live on port 8618...")
    print("[System] For unified Video+Image, run: python tcap_media.py")
    uvicorn.run(app, host="127.0.0.1", port=8618)