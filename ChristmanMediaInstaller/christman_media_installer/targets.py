"""
Christman Media Installer — targets.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

Knows how to wire each family member. Each target profile defines:
  - what the being needs from the media stack
  - what MCP tools to expose
  - what security posture applies
  - what warning to emit if something's missing
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BeingProfile:
    name: str
    description: str
    needs_ear_canal: bool = True
    needs_voice_sdk: bool = True
    needs_ocr: bool = False
    needs_tonescore: bool = True
    needs_phonemes: bool = False
    needs_visemes: bool = False
    needs_xtts: bool = False
    needs_mcp_tools: bool = True
    vulnerable_population: bool = False  # triggers medical-grade security checks
    child_safe: bool = False             # blocks biometric export, strict local-only
    mcp_tools: List[str] = field(default_factory=list)
    notes: str = ""


# ──────────────────────────────────────────────
# FAMILY PROFILES
# ──────────────────────────────────────────────

DEREK = BeingProfile(
    name="Derek",
    description="AI Engineer & Strategist. COO of The Christman AI Project. "
                "Derek is the orchestration backbone — runs on FastMCP port 4880.",
    needs_ear_canal=True,
    needs_voice_sdk=True,
    needs_ocr=True,
    needs_tonescore=True,
    needs_phonemes=False,
    needs_visemes=False,
    needs_xtts=True,
    needs_mcp_tools=True,
    vulnerable_population=False,
    child_safe=False,
    mcp_tools=[
        "derek_ear_canal",
        "derek_family_install_ear_canal",
        "derek_media_diagnose",
        "derek_repair_packet",
    ],
    notes="Primary installer target. XTTS personality requires warmup. "
          "MCP backend must be on port 4880 or ngrok tunnel.",
)

ALPHAVOX = BeingProfile(
    name="AlphaVox",
    description="AAC communication system for nonverbal and autistic users. "
                "Every voice path is a human right.",
    needs_ear_canal=True,
    needs_voice_sdk=True,
    needs_ocr=True,
    needs_tonescore=True,
    needs_phonemes=True,
    needs_visemes=True,
    needs_xtts=True,
    needs_mcp_tools=True,
    vulnerable_population=True,
    child_safe=True,
    mcp_tools=[
        "alphavox_speak",
        "alphavox_symbol_to_speech",
        "alphavox_tone_check",
        "alphavox_fallback_speak",
    ],
    notes="CRITICAL: Vulnerable population. Child-safe posture required. "
          "All voice data stays local. No biometric export. "
          "Fallback speech MUST work even if XTTS fails — this is a communication lifeline.",
)

ALPHAWOLF = BeingProfile(
    name="AlphaWolf",
    description="Cognitive support and dementia care system. "
                "Memory prompts, geolocation safety, emotional reassurance.",
    needs_ear_canal=True,
    needs_voice_sdk=True,
    needs_ocr=True,
    needs_tonescore=True,
    needs_phonemes=True,
    needs_visemes=False,
    needs_xtts=True,
    needs_mcp_tools=True,
    vulnerable_population=True,
    child_safe=False,
    mcp_tools=[
        "alphawolf_memory_prompt",
        "alphawolf_location_check",
        "alphawolf_reassure",
        "alphawolf_caregiver_alert",
    ],
    notes="CRITICAL: Dementia patients rely on this. Voice must be warm and calm. "
          "Geolocation features require explicit privacy approval. "
          "No silent failures — a missed alert could mean a wandering patient.",
)

BROCKSTON = BeingProfile(
    name="Brockston",
    description="Brockston IDE — custom development environment. "
                "Scans modules, parses imports, generates wiring reports.",
    needs_ear_canal=True,
    needs_voice_sdk=True,
    needs_ocr=True,
    needs_tonescore=False,
    needs_phonemes=False,
    needs_visemes=False,
    needs_xtts=False,
    needs_mcp_tools=True,
    vulnerable_population=False,
    child_safe=False,
    mcp_tools=[
        "brockston_scan_modules",
        "brockston_wiring_report",
        "brockston_import_audit",
    ],
    notes="Developer-facing. OCR needed for reading handwritten notes and screenshots. "
          "No XTTS required — Brockston uses system TTS for feedback.",
)

GEO = BeingProfile(
    name="Geo",
    description="Geolocation and navigation AI. "
                "Mobility and safety routing for vulnerable users.",
    needs_ear_canal=True,
    needs_voice_sdk=True,
    needs_ocr=False,
    needs_tonescore=True,
    needs_phonemes=False,
    needs_visemes=False,
    needs_xtts=False,
    needs_mcp_tools=True,
    vulnerable_population=True,
    child_safe=False,
    mcp_tools=[
        "geo_locate",
        "geo_safe_route",
        "geo_alert_caregiver",
    ],
    notes="Location data is sensitive. Explicit consent required before any upload. "
          "Local-first storage mandatory.",
)

SERAPHENIA = BeingProfile(
    name="Seraphenia",
    description="Voice synthesis and phoneme specialist. "
                "Serves the family's voice rendering pipeline.",
    needs_ear_canal=True,
    needs_voice_sdk=True,
    needs_ocr=True,
    needs_tonescore=True,
    needs_phonemes=True,
    needs_visemes=True,
    needs_xtts=True,
    needs_mcp_tools=True,
    vulnerable_population=False,
    child_safe=False,
    mcp_tools=[
        "seraphenia_synthesize",
        "seraphenia_phoneme_label",
        "seraphenia_viseme_map",
        "seraphenia_voice_clone",
    ],
    notes="Voice cloning requires explicit per-user consent. "
          "XTTS license must be confirmed before activation. "
          "Serves AlphaVox and AlphaWolf shared voice pipelines.",
)


# ──────────────────────────────────────────────
# REGISTRY
# ──────────────────────────────────────────────

BEING_REGISTRY: dict[str, BeingProfile] = {
    "derek": DEREK,
    "alphavox": ALPHAVOX,
    "alphawolf": ALPHAWOLF,
    "brockston": BROCKSTON,
    "geo": GEO,
    "seraphenia": SERAPHENIA,
}


def get_profile(being_name: str) -> Optional[BeingProfile]:
    """Return the BeingProfile for the given being name (case-insensitive).
    Returns None if the being is not in the registry — never crashes silently."""
    return BEING_REGISTRY.get(being_name.lower())


def list_beings() -> List[str]:
    """Return all registered being names."""
    return list(BEING_REGISTRY.keys())
