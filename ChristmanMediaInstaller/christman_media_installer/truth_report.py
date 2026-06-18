"""
Christman Media Installer — truth_report.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

Produces the final, honest truth report.
This report NEVER flatters.
It cannot say "ready" because a file exists.
It only says "ready" when the pathway works.

Required sections (from spec):
- Summary
- Module Inventory
- What Works
- What Failed
- What Was Repaired
- What Was Skipped
- Human Approval Needed
- Security Posture
- Next Command
- Final Status
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .constants import STATUS_READY, STATUS_READY_WITH_WARNINGS, STATUS_NOT_READY
from .explorer import ExplorerReport
from .detector import DetectorResult
from .verifier import VerifierReport
from .security import SecurityReport
from .repair_packet import RepairPacket
from .targets import BeingProfile

logger = logging.getLogger("christman.truth_report")


@dataclass
class TruthReport:
    target_path: str
    being_name: str
    profile: Optional[BeingProfile]
    explorer: ExplorerReport
    detector: DetectorResult
    verifier: VerifierReport
    security: SecurityReport
    repair_packet: Optional[RepairPacket] = None

    def _determine_status(self) -> str:
        """Determine the final status. Honest. No exceptions."""
        blockers: List[str] = []

        # Critical verifier failures
        for result in self.verifier.results:
            if result.critical and not result.passed:
                blockers.append(result.message.split("\n")[0])

        # Security critical findings
        for finding in self.security.findings:
            if finding.severity == "CRITICAL":
                blockers.append(f"Security: {finding.message}")

        if blockers:
            return STATUS_NOT_READY

        # Non-critical warnings → READY WITH WARNINGS
        has_warnings = (
            len(self.detector.warnings) > 0
            or any(not r.passed for r in self.verifier.results)
            or self.security.warning_count > 0
            or (self.detector.has_xtts_reference and not self.detector.xtts_model_present)
            or self.detector.ocr_in_mock_mode
        )

        if has_warnings:
            return STATUS_READY_WITH_WARNINGS

        return STATUS_READY

    def render(self) -> str:
        """Render the full truth report as human-readable text."""
        status = self._determine_status()
        lines: List[str] = []

        def line(s: str = "") -> None:
            lines.append(s)

        def hr() -> None:
            lines.append("─" * 60)

        # ──────────────────────────────────────
        # HEADER
        # ──────────────────────────────────────
        line()
        line("╔══════════════════════════════════════════════════════════╗")
        line(f"║     CHRISTMAN MEDIA INSTALLER — TRUTH REPORT            ║")
        line("╚══════════════════════════════════════════════════════════╝")
        line(f"  Target:  {self.target_path}")
        line(f"  Being:   {self.being_name}")
        hr()

        # ──────────────────────────────────────
        # MODULE INVENTORY
        # ──────────────────────────────────────
        line()
        line("📦 MODULE INVENTORY")
        line(f"  Modules found:          {self.explorer.module_count}")
        line(f"  Broken imports:         {self.explorer.broken_count}")
        line(f"  Shimmable imports:      {self.explorer.shimmable_count}")
        line(f"  Voice files:            {len(self.explorer.voice_files)}")
        line(f"  MCP server files:       {len(self.explorer.mcp_server_files)}")
        line(f"  Preflight scripts:      {len(self.explorer.preflight_files)}")
        line(f"  Tracer scripts:         {len(self.explorer.tracer_files)}")
        line(f"  .env files:             {len(self.explorer.env_files)}")

        # ──────────────────────────────────────
        # WHAT WORKS
        # ──────────────────────────────────────
        line()
        line("✅ WHAT WORKS")
        works: List[str] = []

        if self.detector.ear_canal_importable:
            works.append("CHRISTMAN_EAR_CANAL imports cleanly")
        if self.detector.pyaudio_available or self.detector.sounddevice_available:
            works.append("Microphone capture library available")
        if self.detector.tonescore_importable:
            works.append("ToneScore pathway importable")
        if self.detector.macos_say_available:
            works.append("macOS fallback speech (say) available")
        if self.detector.espeak_available:
            works.append("espeak fallback speech available")
        if self.detector.fallback_speech_available:
            works.append("Fallback speech: confirmed working")
        if self.detector.mcp_port_open:
            works.append(f"MCP backend responding on port {self.detector.mcp_port_checked}")
        if self.detector.has_dotenv:
            works.append("python-dotenv installed")
        if self.detector.ocr_importable and self.detector.paddleocr_available:
            works.append("OCR (PaddleOCR + christman_ocr_shared) fully available")
        if self.detector.xtts_importable and self.detector.xtts_model_present:
            works.append("XTTS voice library and model present")

        # Add passing verifier results
        for r in self.verifier.results:
            if r.passed and r.name not in [
                "microphone_capture", "speaker_playback", "tonescore", "ocr"
            ]:
                works.append(r.message.lstrip("✅ ").split("\n")[0])

        if works:
            for w in works:
                line(f"  ✅ {w}")
        else:
            line("  (nothing confirmed working yet)")

        # ──────────────────────────────────────
        # WHAT FAILED
        # ──────────────────────────────────────
        line()
        line("❌ WHAT FAILED")
        failures: List[str] = []

        if not self.detector.ear_canal_importable:
            failures.append("CHRISTMAN_EAR_CANAL not importable")
        if self.detector.has_xtts_reference and not self.detector.xtts_importable:
            failures.append("XTTS voice library not installed")
        if self.detector.has_xtts_reference and self.detector.xtts_importable and not self.detector.xtts_model_present:
            failures.append("XTTS voice personality not verified — model not downloaded")
        if not self.detector.fallback_speech_available:
            failures.append("No fallback speech system found")
        if not self.detector.has_dotenv:
            failures.append("python-dotenv not installed")

        for r in self.verifier.results:
            if not r.passed:
                failures.append(r.message.lstrip("❌ ⚠ ").split("\n")[0])

        if failures:
            for f in failures:
                line(f"  ❌ {f}")
        else:
            line("  (no failures recorded)")

        # ──────────────────────────────────────
        # WHAT WAS REPAIRED
        # ──────────────────────────────────────
        line()
        line("🔧 WHAT WAS REPAIRED")
        if self.repair_packet and self.repair_packet.changes:
            applied = [c for c in self.repair_packet.changes if c.applied]
            if applied:
                for c in applied:
                    line(f"  ✅ [{c.type}] {c.path}: {c.purpose}")
            else:
                line("  (no repairs applied)")
        else:
            line("  (no repair packet — run with install/repair command to apply)")

        # ──────────────────────────────────────
        # WHAT WAS SKIPPED
        # ──────────────────────────────────────
        line()
        line("⏭  WHAT WAS SKIPPED")
        if self.repair_packet and self.repair_packet.changes:
            skipped = [c for c in self.repair_packet.changes if not c.applied]
            if skipped:
                for c in skipped:
                    line(f"  ⏭ [{c.type}] {c.path}: {c.note or 'skipped'}")
            else:
                line("  (nothing skipped)")
        else:
            line("  (no repair packet)")

        # ──────────────────────────────────────
        # HUMAN APPROVAL NEEDED
        # ──────────────────────────────────────
        line()
        line("⚠  REQUIRES HUMAN APPROVAL")
        approvals = self.detector.requires_human_approval
        if self.repair_packet:
            approvals = list(set(approvals + self.repair_packet.requires_human_approval))
        if approvals:
            for a in approvals:
                line(f"  ⚠ {a}")
        else:
            line("  (none — all clear)")

        # ──────────────────────────────────────
        # SECURITY POSTURE
        # ──────────────────────────────────────
        line()
        line("🔒 SECURITY POSTURE")

        if self.security.gitignore_ok:
            line("  ✅ .gitignore covers .env files")
        else:
            line("  ❌ .gitignore does not cover .env — fix immediately")

        if self.security.local_first_confirmed:
            line("  ✅ Local-first posture confirmed")
        else:
            line("  ⚠ Local-first posture not confirmed in .env")

        if self.security.biometric_export_blocked:
            line("  ✅ Biometric export blocked")
        else:
            line("  ⚠ Biometric export not explicitly blocked")

        if self.security.child_voiceprint_export_blocked:
            line("  ✅ Child voiceprint export blocked")
        else:
            line("  ❌ Child voiceprint export not blocked — REQUIRED for child-safe systems")

        if self.security.hndl_warnings:
            for w in self.security.hndl_warnings:
                line(f"  {w}")

        if self.security.critical_count > 0:
            line()
            line("  CRITICAL SECURITY FINDINGS:")
            for f in self.security.findings:
                if f.severity == "CRITICAL":
                    line(f"  ❌ {f.file}:{f.line} — {f.message}")

        # ──────────────────────────────────────
        # NEXT COMMAND
        # ──────────────────────────────────────
        line()
        line("▶  NEXT COMMAND")
        next_cmd = self._suggest_next_command(status)
        line(f"  {next_cmd}")

        # ──────────────────────────────────────
        # FINAL STATUS
        # ──────────────────────────────────────
        line()
        hr()
        status_icon = {
            STATUS_READY: "✅",
            STATUS_READY_WITH_WARNINGS: "⚠",
            STATUS_NOT_READY: "❌",
        }[status]
        line(f"  STATUS: {status_icon} {status}")
        hr()
        line()

        return "\n".join(lines)

    def _suggest_next_command(self, status: str) -> str:
        """Suggest the single most useful next action."""
        if status == STATUS_NOT_READY:
            if not self.detector.ear_canal_importable:
                return (
                    f"christman-media install --target {self.target_path} "
                    f"--being {self.being_name}"
                )
            if not self.detector.fallback_speech_available:
                return "brew install espeak  # or: apt install espeak-ng"
            return (
                f"christman-media repair --target {self.target_path}"
            )
        elif status == STATUS_READY_WITH_WARNINGS:
            if self.detector.has_xtts_reference and not self.detector.xtts_model_present:
                return (
                    "python -c \"from TTS.api import TTS; TTS('tts_models/multilingual/multi-dataset/xtts_v2')\"  "
                    "# Download XTTS model (~1.8GB)"
                )
            if self.detector.ocr_in_mock_mode:
                return "pip install paddleocr  # then: christman-media verify --target <path>"
            return f"christman-media verify --target {self.target_path}"
        else:
            return (
                f"christman-media report --target {self.target_path}  "
                f"# System is READY — all pathways confirmed"
            )

    def print(self) -> None:
        """Print the truth report to stdout."""
        print(self.render())

    def save(self, output_path: str) -> str:
        """Save the truth report to a text file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.render(), encoding="utf-8")
        logger.info(f"  📄 Truth report saved: {path}")
        return str(path)
