"""
Christman Media Installer — constants.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

All shim mappings, status codes, known media stack signatures, and
immutable configuration live here. Nothing is guessed. Nothing is faked.
"""

# ──────────────────────────────────────────────
# STATUS CODES
# ──────────────────────────────────────────────
STATUS_READY = "READY"
STATUS_READY_WITH_WARNINGS = "READY WITH WARNINGS"
STATUS_NOT_READY = "NOT READY"

# ──────────────────────────────────────────────
# SHIM MAPPINGS
# Old import path → canonical christman_voice_sdk path
# Rule: never overwrite original logic. Bridge only.
# ──────────────────────────────────────────────
SHIM_MAP = {
    "logger": "christman_voice_sdk.utils.logger",
    "tone_analyzer": "christman_voice_sdk.tone.tone_analyzer",
    "audio_processor": "christman_voice_sdk.audio.audio_processor",
    "voicepack": "christman_voice_sdk.timbre.voicepack",
    "timbre_modeler": "christman_voice_sdk.timbre.timbre_modeler",
    "emotion_embedder": "christman_voice_sdk.tone.emotion_embedder",
    "gpt_sovits_engine": "christman_voice_sdk.engines.gpt_sovits_engine",
    "tone_engine": "christman_voice_sdk.tone.tonescore_engine",
    "config": "christman_voice_sdk.config",
    # voice_stack.* → SDK bridge
    "voice_stack": "christman_voice_sdk",
    # tiers.* → tier/config compatibility bridge
    "tiers": "christman_voice_sdk.config.tiers",
}

# ──────────────────────────────────────────────
# KNOWN MEDIA STACK COMPONENT SIGNATURES
# Used by detector.py to classify what already exists
# ──────────────────────────────────────────────
EAR_CANAL_SIGNATURES = [
    "CHRISTMAN_EAR_CANAL",
    "christman_ear_canal",
    "ear_canal",
    "EarCanal",
]

VOICE_SDK_SIGNATURES = [
    "christman_voice_sdk",
    "ChristmanVoiceSDK",
    "voice_sdk",
    "VoiceSDK",
]

OCR_SIGNATURES = [
    "christman_ocr_shared",
    "paddleocr",
    "PaddleOCR",
    "PyMuPDF",
    "fitz",
]

TONE_SIGNATURES = [
    "ToneScore",
    "tonescore",
    "tone_analyzer",
    "ToneAnalyzer",
]

PHONEME_SIGNATURES = [
    "phoneme",
    "viseme",
    "g2p",
    "phonemizer",
]

MCP_SIGNATURES = [
    "fastmcp",
    "FastMCP",
    "mcp_server",
    "MCPServer",
    "@mcp.tool",
]

XTTS_SIGNATURES = [
    "xtts",
    "XTTS",
    "coqui",
    "TTS",
]

MICROPHONE_SIGNATURES = [
    "pyaudio",
    "sounddevice",
    "microphone",
    "mic_capture",
    "voice_capture",
    "CHRISTMAN_EAR_CANAL",
]

BIOMETRIC_SIGNATURES = [
    "voiceprint",
    "biometric",
    "voice_profile",
    "speaker_id",
    "speaker_embedding",
]

# ──────────────────────────────────────────────
# LICENSE-GATED DEPENDENCIES
# These require human approval before install
# ──────────────────────────────────────────────
LICENSE_GATES = {
    "coqui-tts": "Coqui XTTS license terms require explicit approval.",
    "paddlepaddle": "PaddlePaddle license and GPU requirements — verify before install.",
}

# ──────────────────────────────────────────────
# MODEL-GATED DEPENDENCIES
# These require a model download before they work
# ──────────────────────────────────────────────
MODEL_GATES = {
    "xtts_v2": "XTTS v2 model (~1.8GB). Download required before voice verification.",
    "paddleocr_model": "PaddleOCR detection/recognition models. Auto-download on first run.",
}

# ──────────────────────────────────────────────
# ENV DEFAULTS
# Installed into target .env if not already present
# ──────────────────────────────────────────────
ENV_DEFAULTS = {
    "CHRISTMAN_EAR_CANAL_ENABLED": "true",
    "CHRISTMAN_VOICE_SDK_LOCAL_FIRST": "true",
    "CHRISTMAN_OCR_MOCK_FALLBACK": "true",
    "CHRISTMAN_MIC_CAPTURE_ENABLED": "true",
    "CHRISTMAN_SPEAKER_FALLBACK": "true",
    "CHRISTMAN_BIOMETRIC_EXPORT": "false",
    "CHRISTMAN_CHILD_VOICEPRINT_EXPORT": "false",
    "CHRISTMAN_HNDL_AWARE": "true",
    "CHRISTMAN_LOCAL_ONLY_VULNERABLE": "true",
}

# ──────────────────────────────────────────────
# MCP DEFAULT PORT
# Derek's canonical MCP backend
# ──────────────────────────────────────────────
DEREK_MCP_DEFAULT_PORT = 4880

# ──────────────────────────────────────────────
# INSTALLER VERSION
# ──────────────────────────────────────────────
INSTALLER_VERSION = "1.0.0"
INSTALLER_NAME = "Christman Media Installer"
INSTALLER_AUTHOR = "Everett Nathaniel Christman / The Christman AI Project"
