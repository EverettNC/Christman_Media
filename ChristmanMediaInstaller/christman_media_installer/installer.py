"""
Christman Media Installer — installer.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

Installs CHRISTMAN_EAR_CANAL, env defaults, MCP tools,
and core dependencies into the target being's project.

This module installs real things. Every install action is verified.
If something fails, it says so — loudly, with context.
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from .constants import ENV_DEFAULTS, DEREK_MCP_DEFAULT_PORT, INSTALLER_VERSION
from .targets import BeingProfile

logger = logging.getLogger("christman.installer")

# Packages to install for the core media stack
# Organized by function. License-gated packages are NOT in this list.
CORE_PACKAGES = [
    "python-dotenv",       # Secret loading
    "sounddevice",         # Microphone / speaker (preferred over pyaudio)
    "numpy",               # Required by sounddevice
]

VOICE_SDK_PACKAGES = [
    # The Christman Voice SDK is installed from the project, not PyPI.
    # We check for it, not install it blindly.
]

OCR_SAFE_PACKAGES = [
    "pymupdf",             # PDF OCR fallback — MIT license, safe
]

# MCP tool template for Derek
DEREK_MCP_TOOL_TEMPLATE = '''
@mcp.tool()
async def {tool_name}(target: str) -> dict:
    """Christman Media Installer — {tool_description}
    
    Installed by: Christman Media Installer v{version}
    Being: {being_name}
    """
    # TODO: Wire to installer.py public API
    return {{"status": "registered", "tool": "{tool_name}", "target": target}}
'''


class Installer:
    """Installs the Christman media stack into a target project.

    Respects the being's profile — only installs what the profile needs.
    Never installs license-gated packages without human approval recorded.
    """

    def __init__(
        self,
        target_path: str,
        being_profile: BeingProfile,
        dry_run: bool = False,
    ):
        self.target = Path(target_path).resolve()
        self.profile = being_profile
        self.dry_run = dry_run
        self.installed_packages: List[str] = []
        self.failed_packages: List[Tuple[str, str]] = []
        self.env_keys_written: List[str] = []
        self.mcp_tools_written: List[str] = []
        self.init_files_created: List[str] = []

    def install(self) -> bool:
        """Run the full install sequence for this being. Returns True if successful."""
        logger.info(f"🚀 Installing media stack for: {self.profile.name}")
        logger.info(f"   Target: {self.target}")

        success = True

        success &= self._ensure_directory_is_package()
        success &= self._install_core_packages()
        success &= self._write_env_defaults()

        if self.profile.needs_mcp_tools:
            self._write_mcp_tools()

        if self.profile.needs_ocr:
            self._install_ocr_safe()

        self._log_summary()
        return success

    # ──────────────────────────────────────────
    # ENSURE PACKAGE STRUCTURE
    # ──────────────────────────────────────────
    def _ensure_directory_is_package(self) -> bool:
        """Make sure the target directory has an __init__.py.
        Creates one if missing — never overwrites existing."""
        init_path = self.target / "__init__.py"
        if init_path.exists():
            return True

        logger.info("  📁 Creating missing __init__.py at project root...")
        if not self.dry_run:
            try:
                init_path.write_text(
                    '"""Christman AI Project — auto-generated package init."""\n',
                    encoding="utf-8",
                )
                self.init_files_created.append(str(init_path.relative_to(self.target)))
                return True
            except OSError as e:
                logger.error(f"  ❌ Could not create __init__.py: {e}")
                return False
        else:
            logger.info("  [DRY RUN] Would create __init__.py")
            return True

    # ──────────────────────────────────────────
    # CORE PACKAGES
    # ──────────────────────────────────────────
    def _install_core_packages(self) -> bool:
        all_ok = True
        for package in CORE_PACKAGES:
            ok = self._pip_install(package)
            if ok:
                self.installed_packages.append(package)
            else:
                self.failed_packages.append((package, "pip install failed"))
                all_ok = False
        return all_ok

    def _install_ocr_safe(self) -> None:
        for package in OCR_SAFE_PACKAGES:
            ok = self._pip_install(package)
            if ok:
                self.installed_packages.append(package)
            else:
                self.failed_packages.append((package, "pip install failed — OCR partial"))

    # ──────────────────────────────────────────
    # ENV DEFAULTS
    # ──────────────────────────────────────────
    def _write_env_defaults(self) -> bool:
        """Write missing env defaults to .env in the target directory.
        Never overwrites keys that are already set."""
        env_path = self.target / ".env"
        existing_keys: set = set()

        # Read existing .env if present
        if env_path.exists():
            try:
                content = env_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and "=" in stripped:
                        key = stripped.split("=")[0].strip()
                        existing_keys.add(key)
            except OSError as e:
                logger.warning(f"  ⚠ Could not read existing .env: {e}")

        # Determine which keys are missing
        missing = {
            k: v for k, v in ENV_DEFAULTS.items()
            if k not in existing_keys
        }

        if not missing:
            logger.info("  ✅ .env already has all required defaults.")
            return True

        if self.dry_run:
            logger.info(f"  [DRY RUN] Would add {len(missing)} env defaults to .env")
            return True

        try:
            with env_path.open("a", encoding="utf-8") as f:
                f.write(f"\n# Added by Christman Media Installer v{INSTALLER_VERSION}\n")
                for key, value in missing.items():
                    f.write(f"{key}={value}\n")
                    self.env_keys_written.append(key)
            logger.info(f"  ✅ Wrote {len(missing)} env defaults to {env_path.name}")
            return True
        except OSError as e:
            logger.error(f"  ❌ Could not write .env: {e}")
            return False

    # ──────────────────────────────────────────
    # MCP TOOLS
    # ──────────────────────────────────────────
    def _write_mcp_tools(self) -> None:
        """Append MCP tool stubs to the being's MCP server file if it exists.
        Only adds tools that aren't already present."""
        # Find the MCP server file
        mcp_file = self._find_mcp_server_file()
        if not mcp_file:
            logger.warning(
                f"  ⚠ No MCP server file found for {self.profile.name}. "
                f"Skipping MCP tool installation."
            )
            return

        try:
            existing = mcp_file.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning(f"  ⚠ Could not read MCP file {mcp_file}: {e}")
            return

        for tool_name in self.profile.mcp_tools:
            if tool_name in existing:
                logger.info(f"  ✅ MCP tool already present: {tool_name}")
                continue

            stub = DEREK_MCP_TOOL_TEMPLATE.format(
                tool_name=tool_name,
                tool_description=f"Christman Media Installer tool for {self.profile.name}",
                version=INSTALLER_VERSION,
                being_name=self.profile.name,
            )

            if not self.dry_run:
                try:
                    with mcp_file.open("a", encoding="utf-8") as f:
                        f.write(stub)
                    self.mcp_tools_written.append(tool_name)
                    logger.info(f"  ✅ MCP tool installed: {tool_name}")
                except OSError as e:
                    logger.warning(f"  ⚠ Could not write MCP tool {tool_name}: {e}")
            else:
                logger.info(f"  [DRY RUN] Would install MCP tool: {tool_name}")

    def _find_mcp_server_file(self) -> Optional[Path]:
        """Find the most likely MCP server Python file in the target."""
        candidates = list(self.target.rglob("*mcp*server*.py")) + \
                     list(self.target.rglob("*server*mcp*.py"))
        if candidates:
            return candidates[0]
        return None

    # ──────────────────────────────────────────
    # PIP HELPER
    # ──────────────────────────────────────────
    def _pip_install(self, package: str) -> bool:
        """Install a package with pip. Returns True if successful."""
        logger.info(f"  📦 Installing: {package}")
        if self.dry_run:
            logger.info(f"  [DRY RUN] Would install: {package}")
            return True

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--quiet"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                logger.info(f"  ✅ Installed: {package}")
                return True
            else:
                logger.error(
                    f"  ❌ Failed to install {package}:\n"
                    f"     {result.stderr.strip()}"
                )
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"  ❌ Timeout installing {package}")
            return False
        except Exception as e:
            logger.error(f"  ❌ Error installing {package}: {e}")
            return False

    # ──────────────────────────────────────────
    # SUMMARY
    # ──────────────────────────────────────────
    def _log_summary(self) -> None:
        logger.info("─" * 50)
        logger.info(f"  Install summary for {self.profile.name}:")
        logger.info(f"  Packages installed:    {len(self.installed_packages)}")
        logger.info(f"  Packages failed:       {len(self.failed_packages)}")
        logger.info(f"  Env defaults written:  {len(self.env_keys_written)}")
        logger.info(f"  MCP tools written:     {len(self.mcp_tools_written)}")
        logger.info(f"  __init__.py created:   {len(self.init_files_created)}")
        if self.failed_packages:
            for pkg, reason in self.failed_packages:
                logger.warning(f"  ⚠ Failed: {pkg} — {reason}")
