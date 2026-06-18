"""
CHRISTMAN MCP TOOLS TEMPLATE — Media Installer Tools for Derek
The Christman AI Project / Luma Cognify AI

These MCP tools expose the Christman Media Installer
to Derek's orchestration layer via FastMCP.

Wire this into derek_mcp_server.py by importing and registering
these tools with the FastMCP instance.
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("christman.mcp_tools.media_installer")


def register_media_installer_tools(mcp) -> None:
    """Register all media installer MCP tools with the given FastMCP instance."""

    @mcp.tool()
    async def derek_ear_canal(target: str) -> dict:
        """Check the EarCanal installation status for a target being project."""
        from christman_media_installer import Explorer, Detector

        try:
            explorer = Explorer(target)
            report = explorer.explore()
            detector = Detector(target, report)
            result = detector.detect()
            return {
                "status": "ok",
                "ear_canal_importable": result.ear_canal_importable,
                "has_ear_canal": result.has_ear_canal,
                "microphone_available": result.pyaudio_available or result.sounddevice_available,
                "fallback_speech": result.fallback_speech_available,
                "warnings": result.warnings,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def derek_family_install_ear_canal(target: str, being: str) -> dict:
        """Install the Christman media stack (EarCanal + voice + MCP tools) for a family member."""
        from christman_media_installer import Explorer, Detector, Installer, get_profile

        profile = get_profile(being)
        if not profile:
            return {
                "status": "error",
                "message": f"Unknown being: {being}. Check christman_media_installer.targets.",
            }

        try:
            explorer = Explorer(target)
            report = explorer.explore()
            installer = Installer(target, profile, dry_run=False)
            success = installer.install()
            return {
                "status": "ok" if success else "partial",
                "being": being,
                "packages_installed": installer.installed_packages,
                "packages_failed": installer.failed_packages,
                "env_keys_written": installer.env_keys_written,
                "mcp_tools_written": installer.mcp_tools_written,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def derek_media_diagnose(target: str, being: Optional[str] = None) -> dict:
        """Run full explore + detect + security check on a target being project."""
        from christman_media_installer import Explorer, Detector, SecurityChecker

        try:
            explorer = Explorer(target)
            report = explorer.explore()
            detector = Detector(target, report)
            det = detector.detect()
            security = SecurityChecker(target)
            sec = security.check()
            return {
                "status": "ok",
                "module_count": report.module_count,
                "broken_imports": report.broken_count,
                "shimmable": report.shimmable_count,
                "ear_canal_importable": det.ear_canal_importable,
                "voice_sdk_importable": det.voice_sdk_importable,
                "ocr_mock_mode": det.ocr_in_mock_mode,
                "fallback_speech": det.fallback_speech_available,
                "mcp_port_open": det.mcp_port_open,
                "security_critical": sec.critical_count,
                "security_warnings": sec.warning_count,
                "detector_warnings": det.warnings,
                "requires_human_approval": det.requires_human_approval,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def derek_repair_packet(target: str, being: str, output_dir: str = "/tmp") -> dict:
        """Generate a repair packet for a target being and save it to disk."""
        from christman_media_installer import (
            Explorer, Detector, ShimEngine,
            RepairPacketBuilder, save_packet,
        )

        try:
            explorer = Explorer(target)
            report = explorer.explore()
            detector = Detector(target, report)
            det = detector.detect()
            shim_engine = ShimEngine(target, dry_run=False)
            shims = shim_engine.install_shims(report)
            builder = RepairPacketBuilder(being, target, det)
            builder.add_shim_results(shims)
            packet = builder.build()
            path = save_packet(packet, output_dir)
            return {
                "status": "ok",
                "packet_name": packet.packet_name,
                "packet_path": path,
                "changes": len(packet.changes),
                "requires_human_approval": packet.requires_human_approval,
                "ready": packet.truth_report.get("ready", False),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
