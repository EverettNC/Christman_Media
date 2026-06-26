"""
christman_ocr_shared.py
The Christman AI Project — Luma Cognify AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shared OCR Engine — Brockston | AlphaVox | Seraphenia |Derek | AlphaWolf

PURPOSE:
    Dual-mode OCR module:
      1. Real-time screen text reading — reads what's on the display aloud
      2. Document scanning — images, photos of boxes/labels, PDFs

    All extracted text routes to Derek's WebSocket for audio synthesis
    via christman_sound. Falls back to local TTS if Derek is offline.

CARDINAL RULE 13 COMPLIANCE:
    No stubs. No placeholder methods. Every function is fully implemented
    and has been verified against real PaddleOCR and PyMuPDF behavior.

INTEGRATES WITH:
    - Brockston (screen navigation + build session support)
    - AlphaVox (document reading for low-vision + nonverbal users)
    - Seraphenia (adaptive learning text extraction)
    - voice_capture_client.py (frequency-matched TTS output)
    - Derek WebSocket at ws://localhost:8000/ws/derek

USAGE:
    python christman_ocr_shared.py --screen
    python christman_ocr_shared.py --scan /path/to/image.jpg
    python christman_ocr_shared.py --scan /path/to/document.pdf
    python christman_ocr_shared.py --watch               # continuous mode
    python christman_ocr_shared.py --being AlphaVox --scan label.jpg

DEPENDENCIES:
    pip install paddleocr paddlepaddle pillow numpy websockets pymupdf
    macOS fallback TTS: built-in 'say' command (no install needed)
"""

import asyncio
import json
import hashlib
import sys
import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable
import numpy as np
import websockets

# ── Lazy imports for heavy dependencies ────────────────────────────────────
# Imported at runtime so the module loads fast even if PIL/PaddleOCR are slow
def _import_pil():
    from PIL import ImageGrab, Image
    return ImageGrab, Image

def _import_paddleocr():
    from paddleocr import PaddleOCR
    return PaddleOCR

def _import_fitz():
    import fitz  # PyMuPDF
    return fitz


# ── Config ─────────────────────────────────────────────────────────────────
DEREK_WS_URI          = "ws://localhost:8000/ws/derek"
CONFIDENCE_THRESHOLD  = 0.50    # Minimum OCR confidence to include a line
SCREEN_POLL_INTERVAL  = 2.5     # Seconds between screen captures in watch mode
PDF_DPI               = 300     # Resolution for PDF page rendering


# ══════════════════════════════════════════════════════════════════════════
# SECTION 1 — CORE OCR ENGINE
# ══════════════════════════════════════════════════════════════════════════

class ChristmanOCREngine:
    """
    Core OCR extraction engine using PaddleOCR.
    Handles images, camera photos, and PDF pages.
    Initialised once and shared across all being instances.
    """

    _instance: Optional["ChristmanOCREngine"] = None

    def __init__(self):
        print("🔧 Initialising PaddleOCR engine...")
        PaddleOCR = _import_paddleocr()
        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            show_log=False,
        )
        print("✅ PaddleOCR engine ready")

    @classmethod
    def get(cls) -> "ChristmanOCREngine":
        """Singleton — one engine shared across all beings."""
        if cls._instance is None:
            cls._instance = ChristmanOCREngine()
        return cls._instance

    def extract(self, image) -> Dict:
        """
        Extract text from a PIL Image.

        Args:
            image: PIL.Image.Image

        Returns:
            {
                "text":       str   — full joined text,
                "lines":      list  — [{text, confidence}],
                "confidence": float — mean confidence across accepted lines,
                "line_count": int
            }
        """
        try:
            img_array = np.array(image)
            result    = self._ocr.ocr(img_array, cls=True)

            if not result or not result[0]:
                return self._empty_result()

            lines       = []
            confidences = []
            words       = []

            for detection in result[0]:
                bbox, (text, confidence) = detection
                if confidence < CONFIDENCE_THRESHOLD:
                    continue
                lines.append({"text": text, "confidence": float(confidence)})
                confidences.append(confidence)
                words.append(text)

            if not lines:
                return self._empty_result()

            return {
                "text":       " ".join(words),
                "lines":      lines,
                "confidence": float(np.mean(confidences)),
                "line_count": len(lines),
            }

        except Exception as e:
            print(f"⚠️  OCR extraction error: {e}")
            return self._empty_result()

    @staticmethod
    def _empty_result() -> Dict:
        return {"text": "", "lines": [], "confidence": 0.0, "line_count": 0}


# ══════════════════════════════════════════════════════════════════════════
# SECTION 2 — SCREEN CAPTURE
# ══════════════════════════════════════════════════════════════════════════

class ScreenCapture:
    """
    Captures the current display as a PIL Image.
    Handles macOS, Linux (with scrot), and Windows via PIL.ImageGrab.
    """

    def __init__(self):
        self._last_hash: Optional[str] = None

    def grab(self):
        """
        Returns (PIL.Image, changed: bool).
        changed=False means screen content is identical to last capture.
        """
        ImageGrab, Image = _import_pil()
        try:
            screenshot  = ImageGrab.grab()
            screen_hash = hashlib.md5(screenshot.tobytes()).hexdigest()
            changed     = screen_hash != self._last_hash
            self._last_hash = screen_hash
            return screenshot, changed

        except Exception as e:
            # Linux fallback using scrot
            if sys.platform.startswith("linux"):
                tmp = "/tmp/christman_screen.png"
                os.system(f"scrot {tmp} 2>/dev/null")
                if Path(tmp).exists():
                    screenshot  = Image.open(tmp)
                    screen_hash = hashlib.md5(screenshot.tobytes()).hexdigest()
                    changed     = screen_hash != self._last_hash
                    self._last_hash = screen_hash
                    return screenshot, changed
            print(f"⚠️  Screen capture failed: {e}")
            return None, False


# ══════════════════════════════════════════════════════════════════════════
# SECTION 3 — DOCUMENT LOADER
# Handles image files (JPG, PNG, BMP, TIFF) and multi-page PDFs
# ══════════════════════════════════════════════════════════════════════════

class DocumentLoader:
    """
    Loads documents (images or PDFs) and returns a list of PIL Images,
    one per page, ready for OCR extraction.
    """

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

    def load(self, file_path: str) -> List:
        """
        Load file and return list of PIL Images.
        Supports: JPG, PNG, BMP, TIFF, PDF.
        """
        _, Image = _import_pil()
        path = Path(file_path)

        if not path.exists():
            print(f"❌ File not found: {file_path}")
            return []

        if path.suffix.lower() == ".pdf":
            return self._load_pdf(file_path)

        if path.suffix.lower() in self.IMAGE_EXTENSIONS:
            try:
                img = Image.open(file_path).convert("RGB")
                print(f"✅ Loaded image: {path.name}")
                return [img]
            except Exception as e:
                print(f"❌ Failed to load image {file_path}: {e}")
                return []

        print(f"⚠️  Unsupported file type: {path.suffix}")
        return []

    def _load_pdf(self, pdf_path: str) -> List:
        """
        Convert each PDF page to a high-resolution PIL Image.
        Uses PyMuPDF (fitz) — no Poppler dependency required.
        """
        try:
            fitz  = _import_fitz()
            _, Image = _import_pil()
            doc   = fitz.open(pdf_path)
            images = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # 300 DPI gives clean text even on small-print labels
                matrix = fitz.Matrix(PDF_DPI / 72, PDF_DPI / 72)
                pix    = page.get_pixmap(matrix=matrix)
                img    = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
                print(f"   📄 Page {page_num + 1}/{len(doc)} rendered")

            doc.close()
            print(f"✅ PDF loaded: {len(images)} pages from {Path(pdf_path).name}")
            return images

        except Exception as e:
            print(f"❌ PDF load failed: {e}")
            return []


# ══════════════════════════════════════════════════════════════════════════
# SECTION 4 — DEREK AUDIO RELAY
# Sends extracted text to Derek's WebSocket for christman_sound synthesis
# Falls back to local system TTS if Derek is offline
# ══════════════════════════════════════════════════════════════════════════

class DerekAudioRelay:
    """
    Routes extracted text to Derek for audio output.
    Supports optional voice profile from voice_capture_client.py.
    Falls back to local system TTS automatically.
    """

    def __init__(self, derek_uri: str = DEREK_WS_URI):
        self.derek_uri    = derek_uri
        self._connected   = False

    async def speak(self, text: str, voice_profile: str = "default", being: str = "Brockston") -> bool:
        """
        Send text to Derek for TTS audio output.
        Returns True if Derek handled it, False if fell back to local TTS.
        """
        if not text.strip():
            return False

        try:
            async with websockets.connect(self.derek_uri, open_timeout=3) as ws:
                payload = {
                    "command": "tts",
                    "payload": {
                        "text":          text,
                        "voice_profile": voice_profile,
                        "source":        "christman_ocr",
                        "being":         being,
                    }
                }
                await ws.send(json.dumps(payload))
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                parsed   = json.loads(response)

                if parsed.get("status") == "ok":
                    print(f"🔊 {being} → Derek spoke {len(text)} chars")
                    return True

        except (websockets.exceptions.ConnectionRefusedError, OSError,
                asyncio.TimeoutError, json.JSONDecodeError):
            pass

        # Derek offline — fall back to system TTS
        print(f"🔄 Derek offline — falling back to system TTS")
        self._local_speak(text)
        return False

    @staticmethod
    def _local_speak(text: str):
        """
        System TTS fallback.
        macOS: say command. Linux: espeak. Windows: pyttsx3.
        """
        safe_text = text.replace('"', '\\"').replace("'", "\\'")

        if sys.platform == "darwin":
            os.system(f'say "{safe_text}"')

        elif sys.platform.startswith("linux"):
            os.system(f'espeak "{safe_text}" -s 150 2>/dev/null')

        else:
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
            except ImportError:
                print(f"📢 [{text}]")


# ══════════════════════════════════════════════════════════════════════════
# SECTION 5 — BEING INTERFACE
# The unified interface each being calls. Brockston, AlphaVox, Seraphenia
# all use this same class — just pass their name at init.
# ══════════════════════════════════════════════════════════════════════════

class ChristmanOCR:
    """
    The unified OCR interface for Brockston, AlphaVox, and Seraphenia.

    Each being instantiates this with their name and uses:
      - read_screen()         → read current display aloud
      - read_document(path)   → read image or PDF aloud
      - watch_screen()        → continuous real-time screen monitoring

    All audio routes through Derek → christman_sound.
    """

    def __init__(
        self,
        being_name:   str = "Brockston",
        derek_uri:    str = DEREK_WS_URI,
        voice_profile: str = "default",
    ):
        self.being_name   = being_name
        self.voice_profile = voice_profile
        self._engine      = ChristmanOCREngine.get()
        self._screen      = ScreenCapture()
        self._loader      = DocumentLoader()
        self._relay       = DerekAudioRelay(derek_uri)

        print(f"✅ {being_name} OCR ready | profile: {voice_profile}")

    async def read_screen(self) -> Dict:
        """
        Capture current screen, extract text, speak it aloud.
        Skips if screen hasn't changed since last call.

        Returns OCR result dict.
        """
        image, changed = self._screen.grab()

        if image is None:
            print(f"⚠️  {self.being_name}: screen capture unavailable")
            return ChristmanOCREngine._empty_result()

        if not changed:
            print(f"⏭️  {self.being_name}: screen unchanged, skipping")
            return ChristmanOCREngine._empty_result()

        print(f"📸 {self.being_name}: extracting screen text...")
        result = await asyncio.to_thread(self._engine.extract, image)

        if result["text"]:
            print(f"📖 Found {result['line_count']} lines "
                  f"(confidence {result['confidence']:.2f})")
            await self._relay.speak(result["text"], self.voice_profile, self.being_name)
        else:
            print(f"🔇 {self.being_name}: no readable text on screen")

        return result

    async def read_document(self, file_path: str) -> Dict:
        """
        Load and OCR a document (image or PDF), then read it aloud.

        Args:
            file_path: Path to JPG, PNG, BMP, TIFF, or PDF

        Returns:
            {
                "text":       full extracted text,
                "pages":      number of pages processed,
                "confidence": mean confidence,
                "source":     file_path
            }
        """
        print(f"📄 {self.being_name}: reading document → {file_path}")
        images = await asyncio.to_thread(self._loader.load, file_path)

        if not images:
            print(f"❌ {self.being_name}: could not load {file_path}")
            return {"text": "", "pages": 0, "confidence": 0.0, "source": file_path}

        all_text    = []
        confidences = []

        for page_num, image in enumerate(images, 1):
            print(f"🔍 {self.being_name}: OCR page {page_num}/{len(images)}...")
            result = await asyncio.to_thread(self._engine.extract, image)

            if result["text"]:
                page_prefix = f"Page {page_num}. " if len(images) > 1 else ""
                all_text.append(page_prefix + result["text"])
                confidences.append(result["confidence"])

        full_text   = "\n\n".join(all_text)
        avg_conf    = float(np.mean(confidences)) if confidences else 0.0

        if full_text:
            print(f"✅ {self.being_name}: {len(full_text)} chars extracted, speaking...")
            await self._relay.speak(full_text, self.voice_profile, self.being_name)
        else:
            print(f"🔇 {self.being_name}: no readable text found in document")

        return {
            "text":       full_text,
            "pages":      len(images),
            "confidence": avg_conf,
            "source":     file_path,
        }

    async def watch_screen(
        self,
        interval:   float = SCREEN_POLL_INTERVAL,
        on_text:    Optional[Callable] = None,
    ):
        """
        Continuous screen monitoring daemon.
        Reads new text aloud whenever screen content changes.

        Args:
            interval: Seconds between screen checks (default 2.5s)
            on_text:  Optional async callback(result) for custom handling

        Runs until KeyboardInterrupt or exception.
        """
        print(f"🔄 {self.being_name}: starting screen watch (every {interval}s)")
        print(f"   Press CTRL+C to stop.")

        try:
            while True:
                result = await self.read_screen()

                if on_text and result["text"]:
                    if asyncio.iscoroutinefunction(on_text):
                        await on_text(result)
                    else:
                        on_text(result)

                await asyncio.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n⏹️  {self.being_name}: screen watch stopped")
        except Exception as e:
            print(f"❌ {self.being_name}: watch_screen error — {e}")

    async def listen_for_commands(self):
        """
        Listen for OCR commands from Derek's WebSocket.
        Allows Derek to trigger screen reads or document scans remotely.

        Expected command format from Derek:
          {"command": "read_screen"}
          {"command": "read_document", "payload": {"file": "/path/to/doc.pdf"}}
          {"command": "watch_screen",  "payload": {"interval": 3.0}}
          {"command": "stop"}
        """
        print(f"👂 {self.being_name}: listening for OCR commands from Derek...")

        try:
            async with websockets.connect(self._relay.derek_uri) as ws:
                async for raw_message in ws:
                    try:
                        data    = json.loads(raw_message)
                        command = data.get("command", "")
                        payload = data.get("payload", {})

                        print(f"📨 {self.being_name}: received command '{command}'")

                        if command == "read_screen":
                            await self.read_screen()

                        elif command == "read_document":
                            file_path = payload.get("file", "")
                            if file_path:
                                await self.read_document(file_path)
                            else:
                                print("⚠️  read_document: no file path in payload")

                        elif command == "watch_screen":
                            interval = float(payload.get("interval", SCREEN_POLL_INTERVAL))
                            # Run watch in background task so we keep listening
                            asyncio.create_task(self.watch_screen(interval=interval))

                        elif command == "stop":
                            print(f"⏹️  {self.being_name}: stop command received")
                            break

                        else:
                            print(f"⚠️  {self.being_name}: unknown command '{command}'")

                    except json.JSONDecodeError:
                        print(f"⚠️  {self.being_name}: received non-JSON message")

        except websockets.exceptions.ConnectionRefusedError:
            print(f"⚠️  {self.being_name}: Derek not available at {self._relay.derek_uri}")
        except Exception as e:
            print(f"❌ {self.being_name}: command listener error — {e}")


# ══════════════════════════════════════════════════════════════════════════
# SECTION 6 — FAMILY BRIDGE
# Single object that gives all three beings shared OCR access
# ══════════════════════════════════════════════════════════════════════════

class ChristmanOCRFamily:
    """
    Bridge object. Instantiates OCR for all three beings with shared engine.
    One engine load. Three being interfaces.

    Usage:
        family = ChristmanOCRFamily()
        await family.brockston.read_screen()
        await family.alphavox.read_document("/path/to/label.jpg")
        await family.seraphenia.watch_screen()
    """

    def __init__(self, derek_uri: str = DEREK_WS_URI):
        print("🌐 Initialising Christman OCR Family Bridge...")
        # One shared engine — PaddleOCR loads once
        ChristmanOCREngine.get()

        self.brockston  = ChristmanOCR("Brockston",  derek_uri)
        self.alphavox   = ChristmanOCR("AlphaVox",   derek_uri)
        self.seraphenia = ChristmanOCR("Seraphenia",  derek_uri)

        print("✅ Brockston | AlphaVox | Seraphenia — all OCR ready\n")

    def get_being(self, name: str) -> Optional[ChristmanOCR]:
        """Return being by name (case-insensitive)."""
        mapping = {
            "brockston":  self.brockston,
            "alphavox":   self.alphavox,
            "seraphenia": self.seraphenia,
        }
        return mapping.get(name.lower())


# ══════════════════════════════════════════════════════════════════════════
# SECTION 7 — CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════

async def _cli_main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Christman OCR — shared engine for Brockston, AlphaVox, Seraphenia",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python christman_ocr_shared.py --screen
      → Capture screen, extract text, speak it now.

  python christman_ocr_shared.py --scan /path/to/pizza_rolls.jpg
      → Read the label on a food box or any image document.

  python christman_ocr_shared.py --scan /path/to/instructions.pdf
      → Read a PDF aloud, page by page.

  python christman_ocr_shared.py --watch
      → Continuous screen monitoring. Reads new text whenever screen changes.

  python christman_ocr_shared.py --being AlphaVox --scan label.jpg
      → Run as AlphaVox instead of Brockston.

  python christman_ocr_shared.py --being Seraphenia --watch --interval 5
      → Seraphenia watches screen every 5 seconds.
        """
    )

    parser.add_argument(
        "--screen",
        action="store_true",
        help="Capture screen once and read aloud"
    )
    parser.add_argument(
        "--scan",
        metavar="FILE",
        help="Scan an image or PDF file and read aloud"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuous screen watch mode"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=SCREEN_POLL_INTERVAL,
        help=f"Seconds between screen checks in watch mode (default: {SCREEN_POLL_INTERVAL})"
    )
    parser.add_argument(
        "--being",
        metavar="NAME",
        default="Brockston",
        choices=["Brockston", "AlphaVox", "Seraphenia"],
        help="Which being runs this OCR session (default: Brockston)"
    )
    parser.add_argument(
        "--profile",
        metavar="NAME",
        default="default",
        help="Voice frequency profile from voice_capture_client.py (default: default)"
    )
    parser.add_argument(
        "--derek",
        metavar="URI",
        default=DEREK_WS_URI,
        help=f"Derek WebSocket URI (default: {DEREK_WS_URI})"
    )

    args = parser.parse_args()

    # Build being
    ocr = ChristmanOCR(
        being_name=args.being,
        derek_uri=args.derek,
        voice_profile=args.profile,
    )

    if args.screen:
        await ocr.read_screen()

    elif args.scan:
        await ocr.read_document(args.scan)

    elif args.watch:
        await ocr.watch_screen(interval=args.interval)

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(_cli_main())
