"""
Christman Media Installer — detector.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

The detector takes an ExplorerReport and classifies what the project
ACTUALLY has — not what it might have, not what it claims to have.

It never says a component is present because a file exists.
It says it is present when the pathway has been confirmed.
"""

import importlib
import importlib.util
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .explorer import ExplorerReport

logger = logging.getLogger("christman.detector")


@dataclass
class DetectorResult:
    # Voice stack
    has_voice_sdk: bool = False
    voice_sdk_path: Optional[str] = None
    voice_sdk_importable: bool = False

    # Ear Canal
    has_ear_canal: bool = False
    ear_canal_importable: bool = False

    # MCP
    has_mcp_server: bool = False
    mcp_port_open: bool = False
    mcp_port_checked: Optional[int] = None

    # OCR
    has_ocr_module: bool = False
    ocr_importable: bool = False
    paddleocr_available: bool = False
    ocr_in_mock_mode: bool = False

    # ToneScore
    has_tonescore: bool = False
    tonescore_importable: bool = False

    # XTTS
    has_xtts_reference: bool = False
    xtts_model_present: bool = False
    xtts_importable: bool = False

    # Microphone
    has_microphone_code: bool = False
    pyaudio_available: bool = False
    sounddevice_available: bool = False

    # Speaker / TTS fallback
    macos_say_available: bool = False
    espeak_available: bool = False
    fallback_speech_available: bool = False

    # Phonemes / Visemes
    has_phoneme_code: bool = False
    phonemizer_available: bool = False

    # Security
    has_dotenv: bool = False
    env_file_present: bool = False
    secrets_in_source: bool = False  # True = problem

    # Warnings accumulated during detection
    warnings: list = field(default_factory=list)
    requires_human_approval: list = field(default_factory=list)


class Detector:
    """Classifies what a target project actually has.

    Works in two passes:
    1. Static pass: reads the ExplorerReport (file-based evidence).
    2. Runtime pass: attempts actual imports and subprocess checks.

    Rule 13 enforcement: every positive result must be confirmed.
    A file existing is not a confirmation. An import succeeding is.
    """

    def __init__(self, target_path: str, explorer_report: ExplorerReport):
        self.target = Path(target_path).resolve()
        self.report = explorer_report
        self.result = DetectorResult()

    def detect(self) -> DetectorResult:
        logger.info("🔬 Running detection pass...")
        self._detect_voice_sdk()
        self._detect_ear_canal()
        self._detect_mcp()
        self._detect_ocr()
        self._detect_tonescore()
        self._detect_xtts()
        self._detect_microphone()
        self._detect_speaker_fallback()
        self._detect_phonemes()
        self._detect_security()
        return self.result

    # ──────────────────────────────────────────
    # VOICE SDK
    # ──────────────────────────────────────────
    def _detect_voice_sdk(self) -> None:
        has_refs = len(self.report.voice_sdk_refs) > 0
        importable = self._try_import("christman_voice_sdk")
        self.result.has_voice_sdk = has_refs
        self.result.voice_sdk_importable = importable
        if has_refs and not importable:
            self.result.warnings.append(
                "christman_voice_sdk referenced but not importable — "
                "install or add to PYTHONPATH."
            )

    # ──────────────────────────────────────────
    # EAR CANAL
    # ──────────────────────────────────────────
    def _detect_ear_canal(self) -> None:
        has_refs = len(self.report.ear_canal_refs) > 0
        importable = self._try_import("christman_ear_canal")
        self.result.has_ear_canal = has_refs
        self.result.ear_canal_importable = importable
        if has_refs and not importable:
            self.result.warnings.append(
                "CHRISTMAN_EAR_CANAL referenced but not importable — "
                "run: christman-media install --target <path>"
            )

    # ──────────────────────────────────────────
    # MCP SERVER
    # ──────────────────────────────────────────
    def _detect_mcp(self) -> None:
        self.result.has_mcp_server = len(self.report.mcp_server_files) > 0
        # Check if port 4880 is actually responding
        port_open = self._check_port(4880)
        self.result.mcp_port_open = port_open
        self.result.mcp_port_checked = 4880
        if self.result.has_mcp_server and not port_open:
            self.result.warnings.append(
                "MCP server file found but port 4880 is not responding. "
                "Start the MCP server before verifying."
            )

    # ──────────────────────────────────────────
    # OCR
    # ──────────────────────────────────────────
    def _detect_ocr(self) -> None:
        has_refs = len(self.report.ocr_refs) > 0
        ocr_importable = self._try_import("christman_ocr_shared")
        paddle_available = self._try_import("paddleocr")

        self.result.has_ocr_module = has_refs
        self.result.ocr_importable = ocr_importable
        self.result.paddleocr_available = paddle_available
        self.result.ocr_in_mock_mode = has_refs and not paddle_available

        if has_refs and not paddle_available:
            self.result.warnings.append(
                "PaddleOCR missing — OCR module will run in mock mode only. "
                "Install: pip install paddleocr"
            )
            self.result.requires_human_approval.append(
                "paddlepaddle: PaddlePaddle license and GPU requirements — verify before install."
            )

    # ──────────────────────────────────────────
    # TONESCORE
    # ──────────────────────────────────────────
    def _detect_tonescore(self) -> None:
        has_refs = len(self.report.tone_refs) > 0
        importable = self._try_import("christman_voice_sdk.tone.tonescore_engine")
        self.result.has_tonescore = has_refs
        self.result.tonescore_importable = importable
        if has_refs and not importable:
            self.result.warnings.append(
                "ToneScore referenced but not importable via SDK. "
                "Check christman_voice_sdk installation."
            )

    # ──────────────────────────────────────────
    # XTTS
    # ──────────────────────────────────────────
    def _detect_xtts(self) -> None:
        has_refs = len(self.report.xtts_refs) > 0
        importable = self._try_import("TTS")

        # Look for model cache
        model_dirs = [
            Path.home() / ".local/share/tts",
            Path.home() / "tts_models",
            self.target / "models" / "xtts",
            self.target / "xtts_model",
        ]
        model_present = any(d.exists() for d in model_dirs)

        self.result.has_xtts_reference = has_refs
        self.result.xtts_importable = importable
        self.result.xtts_model_present = model_present

        if has_refs:
            self.result.requires_human_approval.append(
                "coqui-tts: Coqui XTTS license terms require explicit approval."
            )
        if has_refs and not importable:
            self.result.warnings.append(
                "XTTS referenced but TTS library not importable. "
                "Install: pip install TTS  (after approving Coqui license)"
            )
        if importable and not model_present:
            self.result.warnings.append(
                "XTTS library installed but no model cache found (~1.8GB download needed). "
                "Voice personality will not work until model is downloaded."
            )

    # ──────────────────────────────────────────
    # MICROPHONE
    # ──────────────────────────────────────────
    def _detect_microphone(self) -> None:
        has_refs = len(self.report.microphone_refs) > 0
        pyaudio = self._try_import("pyaudio")
        sounddevice = self._try_import("sounddevice")

        self.result.has_microphone_code = has_refs
        self.result.pyaudio_available = pyaudio
        self.result.sounddevice_available = sounddevice

        if has_refs and not pyaudio and not sounddevice:
            self.result.warnings.append(
                "Microphone code found but neither pyaudio nor sounddevice is installed. "
                "Install: pip install sounddevice  (preferred) or pip install pyaudio"
            )

    # ──────────────────────────────────────────
    # SPEAKER FALLBACK
    # ──────────────────────────────────────────
    def _detect_speaker_fallback(self) -> None:
        say_available = self._command_exists("say")   # macOS
        espeak_available = self._command_exists("espeak")
        espeak_ng_available = self._command_exists("espeak-ng")

        self.result.macos_say_available = say_available
        self.result.espeak_available = espeak_available or espeak_ng_available
        self.result.fallback_speech_available = (
            say_available or espeak_available or espeak_ng_available
        )

        if not self.result.fallback_speech_available:
            self.result.warnings.append(
                "No fallback speech system found (no 'say', no 'espeak'). "
                "At least one fallback TTS must be available."
            )

    # ──────────────────────────────────────────
    # PHONEMES / VISEMES
    # ──────────────────────────────────────────
    def _detect_phonemes(self) -> None:
        has_refs = len(self.report.phoneme_refs) > 0
        importable = self._try_import("phonemizer")
        self.result.has_phoneme_code = has_refs
        self.result.phonemizer_available = importable
        if has_refs and not importable:
            self.result.warnings.append(
                "Phoneme/viseme code found but 'phonemizer' not installed. "
                "Install: pip install phonemizer"
            )

    # ──────────────────────────────────────────
    # SECURITY
    # ──────────────────────────────────────────
    def _detect_security(self) -> None:
        self.result.has_dotenv = self._try_import("dotenv")
        self.result.env_file_present = len(self.report.env_files) > 0

        if not self.result.has_dotenv:
            self.result.warnings.append(
                "python-dotenv not installed — secrets must be loaded another way. "
                "Install: pip install python-dotenv"
            )
        if not self.result.env_file_present:
            self.result.warnings.append(
                "No .env file found. Installer will create env defaults on install."
            )

    # ──────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────
    def _try_import(self, module_name: str) -> bool:
        """Attempt to import a module. Returns True only if it actually imports."""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError:
            return False
        except Exception:
            # Anything else (e.g. config error on import) = not safely importable
            return False

    def _command_exists(self, cmd: str) -> bool:
        """Check if a shell command exists on this system."""
        try:
            result = subprocess.run(
                ["which", cmd],
                capture_output=True,
                timeout=3,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_port(self, port: int) -> bool:
        """Check if a local port is accepting connections."""
        import socket
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except (ConnectionRefusedError, OSError, TimeoutError):
            return False
