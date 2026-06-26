"""Extract text from PDF, HTML, images, and plain-text for editable prompt renders."""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

from engine.sound_init import bootstrap_sound, resolve_sound_root

DOCUMENT_SUFFIXES = {
    ".pdf", ".html", ".htm", ".txt", ".md",
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp",
}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
MIN_OCR_TEXT_CHARS = 40
_PRINT_ARTIFACT_MARKERS = (
    "claudeusercontent.com",
    "about:blank",
    "safari-extension",
    "chrome-extension",
)


def _clean_print_headers(text: str) -> str:
    """Drop browser print chrome; keep email body from OCR."""
    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        lower = s.lower()
        if "claudeusercontent.com" in lower:
            continue
        if re.fullmatch(r"\d+/\d+", s):
            continue
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}", s) and "acceptance reply email" in lower:
            continue
        if s.lower() in {"acceptance reply email"}:
            continue
        kept.append(s)
    return _trim_email_preamble(_normalize_text("\n".join(kept)))


def _trim_email_preamble(text: str) -> str:
    """Skip Claude UI / nav OCR noise; start at salutation or quoted body."""
    if not text:
        return text

    for marker in ("To the Anthropic Team", "Dear Anthropic", "Dear "):
        idx = text.find(marker)
        if idx != -1:
            trimmed = text[idx:].lstrip()
            if len(trimmed) >= MIN_OCR_TEXT_CHARS:
                return trimmed

    # Epigraph after Subject — only scan the header, not the full 6-page OCR blob.
    head = text[:2500]
    subject = re.search(r"Subject\s+(.+)", head, re.IGNORECASE)
    if subject:
        tail = head[subject.end() :].lstrip()
        if tail.startswith('"'):
            close = tail.find('"', 1)
            if close != -1 and close < 800:
                body = tail[close + 1 :].lstrip(" \n-—")
                if len(body) >= MIN_OCR_TEXT_CHARS:
                    return body

    return text


def document_display_title(text: str, *, fallback: str = "") -> str:
    """Human title for overlays — prefer Subject line over nav OCR / salutation."""
    subject = re.search(r"Subject\s+(.+)", text[:4000], re.IGNORECASE)
    if subject:
        title = subject.group(1).strip()
        if len(title) > 80:
            return title[:79].rsplit(" ", 1)[0] + "…"
        return title
    for line in text.splitlines():
        s = line.strip()
        if not s or len(s) < 10:
            continue
        if re.match(r"^(to|dear|from|hi)\b", s, re.IGNORECASE):
            continue
        if len(s) <= 80:
            return s
        return s[:79].rsplit(" ", 1)[0] + "…"
    fb = (fallback or "Untitled").replace("_", " ").replace("-", " ")
    return fb[:80]


def _is_browser_print_artifact(text: str) -> bool:
    """Detect print-to-PDF junk (headers/URLs only, no body)."""
    normalized = _normalize_text(text)
    if len(normalized) < MIN_OCR_TEXT_CHARS:
        return True
    lower = normalized.lower()
    if any(marker in lower for marker in _PRINT_ARTIFACT_MARKERS):
        return True
    if lower.count("http://") + lower.count("https://") >= 2:
        return True
    lines = [ln.strip() for ln in normalized.splitlines() if ln.strip()]
    if lines and sum(1 for ln in lines if re.search(r"\d+/\d+$", ln)) >= 2:
        words = re.findall(r"[a-zA-Z]{4,}", normalized)
        if len(words) < 80:
            return True
    return False


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        return "\n".join(self._chunks)


def is_document(path: Path) -> bool:
    return path.suffix.lower() in DOCUMENT_SUFFIXES


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_SUFFIXES


def extract_text(path: Path, *, max_chars: int = 12000) -> dict:
    """
    Return extracted document text and metadata.
    Raises ValueError on empty or unsupported.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Document not found: {path}")

    suffix = path.suffix.lower()
    method = "text"

    if suffix == ".pdf":
        text = _extract_pdf(path)
        method = "pypdf"
        needs_ocr = (
            len(_normalize_text(text)) < MIN_OCR_TEXT_CHARS
            or _is_browser_print_artifact(text)
        )
        if needs_ocr:
            # System tesseract is fast and reliable on macOS; PaddleOCR is slow to load.
            tess_text, tess_ok = _extract_via_tesseract(path)
            if tess_ok:
                text = tess_text
                method = "tesseract"
            else:
                ocr_text, ocr_ok = _extract_via_ocr(path)
                if ocr_ok:
                    text = ocr_text
                    method = "ocr"
                elif _is_browser_print_artifact(text):
                    raise ValueError(
                        f"{path.name} is a browser print/screenshot PDF — OCR could not read it. "
                        "Paste the email text into the prompt box, or export as .html/.txt."
                    )
    elif suffix in {".html", ".htm"}:
        text = _extract_html(path)
        method = "html"
    elif suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        method = "text"
    elif suffix in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}:
        text, ocr_ok = _extract_via_ocr(path)
        if not ocr_ok:
            raise ValueError(f"OCR could not read text from {path.name}")
        method = "ocr"
    else:
        raise ValueError(f"Unsupported document type: {suffix}")

    if method in {"ocr", "tesseract"}:
        text = _clean_print_headers(text)
    else:
        text = _normalize_text(text)
        if _is_browser_print_artifact(text):
            tess_text, tess_ok = _extract_via_tesseract(path)
            if tess_ok:
                text = tess_text
                method = "tesseract"
            else:
                raise ValueError(
                    f"{path.name} looks like a browser print PDF with no extractable body. "
                    "Paste the text into the prompt box, or export as .html/.txt."
                )
    if not text:
        raise ValueError(f"No readable text in {path.name}")

    truncated = False
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
        truncated = True

    return {
        "text": text,
        "method": method,
        "filename": path.name,
        "chars": len(text),
        "truncated": truncated,
    }


def extract_text_plain(path: Path, *, max_chars: int = 12000) -> str:
    return extract_text(path, max_chars=max_chars)["text"]


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf(path: Path) -> str:
    errors: list[str] = []

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            chunk = (page.extract_text() or "").strip()
            if chunk:
                pages.append(chunk)
        if pages:
            return "\n\n".join(pages)
        errors.append("pypdf: no extractable text")
    except ImportError:
        errors.append("pypdf not installed")
    except Exception as exc:
        errors.append(f"pypdf: {exc}")

    try:
        import fitz  # pymupdf

        doc = fitz.open(str(path))
        pages = []
        for page in doc:
            chunk = (page.get_text() or "").strip()
            if chunk:
                pages.append(chunk)
        doc.close()
        if pages:
            return "\n\n".join(pages)
        errors.append("pymupdf: no extractable text")
    except ImportError:
        errors.append("pymupdf not installed")
    except Exception as exc:
        errors.append(f"pymupdf: {exc}")

    raise RuntimeError(
        "PDF text extraction failed. "
        + "; ".join(errors)
        + ". Install: uv pip install pypdf pymupdf"
    )


def _extract_html(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    text = parser.text()
    if text:
        return text
    return re.sub(r"<[^>]+>", " ", raw)


def _load_ocr_module():
    root = resolve_sound_root()
    ocr_path = root / "christman_ocr_shared.py"
    if not ocr_path.is_file():
        cve_copy = Path(__file__).resolve().parent.parent / "Christman-Sound" / "christman_ocr_shared.py"
        if cve_copy.is_file():
            ocr_path = cve_copy
        else:
            return None

    module_name = "christman_ocr_shared"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, ocr_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _extract_via_tesseract(path: Path) -> tuple[str, bool]:
    """macOS/Linux fallback using system tesseract + pymupdf page renders."""
    try:
        import fitz
    except ImportError:
        return "", False

    tesseract = _find_tesseract()
    if not tesseract:
        return "", False

    chunks: list[str] = []
    try:
        doc = fitz.open(str(path))
        with tempfile.TemporaryDirectory(prefix="cve_ocr_") as tmp:
            tmp_path = Path(tmp)
            for page_num, page in enumerate(doc, 1):
                pix = page.get_pixmap(dpi=200)
                img_path = tmp_path / f"page_{page_num}.png"
                pix.save(str(img_path))
                out_base = tmp_path / f"page_{page_num}"
                proc = subprocess.run(
                    [tesseract, str(img_path), str(out_base), "-l", "eng"],
                    capture_output=True,
                    timeout=120,
                )
                out_txt = Path(f"{out_base}.txt")
                if proc.returncode == 0 and out_txt.is_file():
                    page_text = out_txt.read_text(encoding="utf-8", errors="replace").strip()
                    if page_text:
                        chunks.append(page_text)
        doc.close()
    except Exception:
        return "", False

    text = _clean_print_headers("\n\n".join(chunks))
    return text, len(text) >= MIN_OCR_TEXT_CHARS


def _find_tesseract() -> str | None:
    for candidate in ("/usr/local/bin/tesseract", "/opt/homebrew/bin/tesseract"):
        if Path(candidate).is_file():
            return candidate
    try:
        proc = subprocess.run(["which", "tesseract"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return None


def _extract_via_ocr(path: Path) -> tuple[str, bool]:
    """OCR fallback for scanned PDFs and images. Returns (text, success)."""
    try:
        ocr = _load_ocr_module()
        if ocr is None:
            return "", False

        loader = ocr.DocumentLoader()
        engine = ocr.ChristmanOCREngine.get()
        images = loader.load(str(path))
        if not images:
            return "", False

        chunks: list[str] = []
        for page_num, image in enumerate(images, 1):
            result = engine.extract(image)
            if result.get("text"):
                prefix = f"Page {page_num}. " if len(images) > 1 else ""
                chunks.append(prefix + result["text"])

        text = _normalize_text("\n\n".join(chunks))
        return text, len(text) >= MIN_OCR_TEXT_CHARS
    except Exception:
        return "", False


def build_prompt_from_document(
    path: Path,
    *,
    user_prompt: str = "",
    title: str | None = None,
) -> str:
    """Merge optional user prompt with extracted document text."""
    body = extract_text_plain(path)
    name = title or path.stem.replace("_", " ").replace("-", " ")
    header = f"Source document: {name}"
    extra = user_prompt.strip()
    if extra:
        return f"{extra}\n\n{header}\n\n{body}"
    return f"Create a narrated video from this document.\n\n{header}\n\n{body}"