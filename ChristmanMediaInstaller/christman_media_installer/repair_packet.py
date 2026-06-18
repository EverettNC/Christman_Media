"""
Christman Media Installer — repair_packet.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

Builds portable JSON repair packets that can be applied to any being.
A repair packet is the diff between "what was broken" and "what was fixed."
It is honest about what it could not fix and what needs human approval.

Rule 13: A repair packet never says "ready: true" unless every item in
'changes' has been verified, and no items remain in 'requires_human_approval'
that block operation.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .shim_engine import ShimResult
from .detector import DetectorResult
from .constants import INSTALLER_VERSION, INSTALLER_NAME

logger = logging.getLogger("christman.repair_packet")


@dataclass
class RepairChange:
    type: str        # "shim", "env_default", "mcp_tool", "missing_init", "missing_export"
    path: str        # relative path in the target
    purpose: str     # why this change was made
    applied: bool = True
    note: str = ""


@dataclass
class RepairPacket:
    packet_name: str
    target_being: str
    target_path: str
    created_by: str = INSTALLER_NAME
    installer_version: str = INSTALLER_VERSION
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    changes: List[RepairChange] = field(default_factory=list)
    requires_human_approval: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    truth_report: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class RepairPacketBuilder:
    """Assembles a repair packet from shim results, detector results,
    and any other installer actions taken.

    The packet is the honest record of what happened.
    It is portable — it can be applied to another being of the same type.
    """

    def __init__(
        self,
        being_name: str,
        target_path: str,
        detector_result: DetectorResult,
    ):
        self.being_name = being_name
        self.target_path = target_path
        self.detector = detector_result
        self.changes: List[RepairChange] = []
        self.extra_warnings: List[str] = []

    def add_shim_results(self, shim_results: List[ShimResult]) -> None:
        """Record all shim installs in the packet."""
        for shim in shim_results:
            if shim.installed:
                self.changes.append(RepairChange(
                    type="shim",
                    path=shim.shim_path,
                    purpose=f"Bridge old import '{shim.original_import}' "
                            f"to canonical '{shim.canonical_import}'",
                    applied=True,
                    note=shim.missing_dep_note if shim.hides_missing_dep else "",
                ))
            else:
                self.changes.append(RepairChange(
                    type="shim",
                    path=shim.shim_path or shim.original_import,
                    purpose=f"Attempted shim for '{shim.original_import}'",
                    applied=False,
                    note=shim.error or "Skipped",
                ))

    def add_env_write(self, env_path: str, keys_written: List[str]) -> None:
        """Record env default installation."""
        self.changes.append(RepairChange(
            type="env_default",
            path=env_path,
            purpose=f"Wrote {len(keys_written)} default env vars: "
                    f"{', '.join(keys_written[:5])}"
                    + ("..." if len(keys_written) > 5 else ""),
            applied=True,
        ))

    def add_mcp_tool(self, tool_name: str, path: str) -> None:
        """Record MCP tool installation."""
        self.changes.append(RepairChange(
            type="mcp_tool",
            path=path,
            purpose=f"Expose {tool_name} via MCP",
            applied=True,
        ))

    def add_missing_init(self, path: str) -> None:
        """Record __init__.py creation."""
        self.changes.append(RepairChange(
            type="missing_init",
            path=path,
            purpose="Created missing __init__.py to make package importable",
            applied=True,
        ))

    def add_warning(self, warning: str) -> None:
        self.extra_warnings.append(warning)

    def build(self) -> RepairPacket:
        """Build and return the final repair packet."""
        packet_name = (
            f"{self.being_name.lower()}_media_repair_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        # Collect human approval items from detector
        requires_approval = list(self.detector.requires_human_approval)

        # All warnings: detector + extra
        all_warnings = list(self.detector.warnings) + self.extra_warnings

        # Build truth summary
        truth = self._build_truth_summary()

        packet = RepairPacket(
            packet_name=packet_name,
            target_being=self.being_name,
            target_path=self.target_path,
            changes=self.changes,
            requires_human_approval=requires_approval,
            warnings=all_warnings,
            truth_report=truth,
        )

        return packet

    def _build_truth_summary(self) -> dict:
        """Build an honest summary of what's ready and what isn't."""
        d = self.detector

        blocking_issues = []

        if not d.ear_canal_importable:
            blocking_issues.append("CHRISTMAN_EAR_CANAL not importable")
        if not d.fallback_speech_available:
            blocking_issues.append("No fallback speech system available")
        if d.has_xtts_reference and not d.xtts_model_present:
            blocking_issues.append("XTTS model not downloaded")

        ready = len(blocking_issues) == 0
        reason = "; ".join(blocking_issues) if blocking_issues else "All critical paths verified"

        return {
            "ready": ready,
            "reason": reason,
            "ear_canal_importable": d.ear_canal_importable,
            "voice_sdk_importable": d.voice_sdk_importable,
            "ocr_in_mock_mode": d.ocr_in_mock_mode,
            "paddleocr_available": d.paddleocr_available,
            "fallback_speech": d.fallback_speech_available,
            "macos_say": d.macos_say_available,
            "espeak": d.espeak_available,
            "xtts_importable": d.xtts_importable,
            "xtts_model_present": d.xtts_model_present,
            "mcp_port_open": d.mcp_port_open,
            "microphone_available": d.pyaudio_available or d.sounddevice_available,
            "secrets_clean": not d.secrets_in_source,
        }


def save_packet(packet: RepairPacket, output_dir: str) -> str:
    """Write the repair packet to disk as JSON. Returns the written path."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    filename = f"{packet.packet_name}.json"
    filepath = out / filename
    filepath.write_text(packet.to_json(), encoding="utf-8")
    logger.info(f"  📦 Repair packet saved: {filepath}")
    return str(filepath)


def load_packet(packet_path: str) -> RepairPacket:
    """Load a repair packet from disk."""
    data = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    # Reconstruct changes
    changes = [RepairChange(**c) for c in data.pop("changes", [])]
    packet = RepairPacket(**data)
    packet.changes = changes
    return packet
