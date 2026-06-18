"""
christman_media_installer
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

One installer. Every being gets ears, voice, sight, tone, phonemes,
repair packets, and the courage to come back with the truth.

Public API:
  Explorer       — walk a project, inventory everything
  Detector       — classify what actually exists
  ShimEngine     — install import path bridges
  RepairPacketBuilder — build portable repair records
  Installer      — install the media stack
  Verifier       — run real smoke tests
  SecurityChecker — check security posture
  TruthReport    — render the final honest report
"""

from .constants import (
    INSTALLER_NAME,
    INSTALLER_VERSION,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
    STATUS_NOT_READY,
    SHIM_MAP,
    ENV_DEFAULTS,
)

from .targets import (
    BeingProfile,
    get_profile,
    list_beings,
    BEING_REGISTRY,
)

from .explorer import Explorer, ExplorerReport
from .detector import Detector, DetectorResult
from .shim_engine import ShimEngine
from .repair_packet import RepairPacketBuilder, RepairPacket, save_packet, load_packet
from .installer import Installer
from .verifier import Verifier, VerifierReport
from .security import SecurityChecker, SecurityReport
from .truth_report import TruthReport

__version__ = INSTALLER_VERSION
__author__ = "Everett Nathaniel Christman / The Christman AI Project"
__all__ = [
    "Explorer",
    "ExplorerReport",
    "Detector",
    "DetectorResult",
    "ShimEngine",
    "RepairPacketBuilder",
    "RepairPacket",
    "save_packet",
    "load_packet",
    "Installer",
    "Verifier",
    "VerifierReport",
    "SecurityChecker",
    "SecurityReport",
    "TruthReport",
    "BeingProfile",
    "get_profile",
    "list_beings",
    "BEING_REGISTRY",
    "INSTALLER_NAME",
    "INSTALLER_VERSION",
    "STATUS_READY",
    "STATUS_READY_WITH_WARNINGS",
    "STATUS_NOT_READY",
    "SHIM_MAP",
    "ENV_DEFAULTS",
]
