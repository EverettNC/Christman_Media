"""
Christman Media Installer — explorer.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

The explorer has one job: walk into a messy codebase and tell the truth.
It finds Python modules, broken imports, voice files, OCR modules, tone engines,
phoneme files, MCP servers, and media assets.

It does NOT install anything. It does NOT fix anything.
It only reports what is real.
"""

import os
import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

from .constants import (
    EAR_CANAL_SIGNATURES,
    VOICE_SDK_SIGNATURES,
    OCR_SIGNATURES,
    TONE_SIGNATURES,
    PHONEME_SIGNATURES,
    MCP_SIGNATURES,
    XTTS_SIGNATURES,
    MICROPHONE_SIGNATURES,
    SHIM_MAP,
)

logger = logging.getLogger("christman.explorer")

# File extensions the explorer cares about
PYTHON_EXTS = {".py"}
VOICE_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
MODEL_EXTS = {".pth", ".pt", ".onnx", ".bin", ".ckpt"}
CONFIG_EXTS = {".env", ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"}

# Directories to skip — never dig into these
SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "node_modules", ".mypy_cache", ".pytest_cache",
    "dist", "build", "*.egg-info",
}


@dataclass
class ImportIssue:
    file: str
    line: int
    import_name: str
    reason: str
    shim_available: bool = False
    shim_target: Optional[str] = None


@dataclass
class ExplorerReport:
    target_path: str
    python_modules: List[str] = field(default_factory=list)
    broken_imports: List[ImportIssue] = field(default_factory=list)
    voice_files: List[str] = field(default_factory=list)
    model_files: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    env_files: List[str] = field(default_factory=list)
    mcp_server_files: List[str] = field(default_factory=list)
    ear_canal_refs: List[str] = field(default_factory=list)
    voice_sdk_refs: List[str] = field(default_factory=list)
    ocr_refs: List[str] = field(default_factory=list)
    tone_refs: List[str] = field(default_factory=list)
    phoneme_refs: List[str] = field(default_factory=list)
    xtts_refs: List[str] = field(default_factory=list)
    microphone_refs: List[str] = field(default_factory=list)
    preflight_files: List[str] = field(default_factory=list)
    tracer_files: List[str] = field(default_factory=list)

    @property
    def module_count(self) -> int:
        return len(self.python_modules)

    @property
    def broken_count(self) -> int:
        return len(self.broken_imports)

    @property
    def shimmable_count(self) -> int:
        return sum(1 for i in self.broken_imports if i.shim_available)


class Explorer:
    """Walks a target project directory and inventories everything it finds.

    Rules:
    - Never modify any file.
    - Never assume an import works because the file exists.
    - Report everything found. Hide nothing.
    """

    def __init__(self, target_path: str):
        self.target = Path(target_path).resolve()
        if not self.target.exists():
            raise FileNotFoundError(
                f"Target path does not exist: {self.target}\n"
                f"Cannot explore what isn't there."
            )
        if not self.target.is_dir():
            raise NotADirectoryError(
                f"Target must be a directory: {self.target}"
            )

    def explore(self) -> ExplorerReport:
        """Walk the entire target directory and return a full inventory report."""
        report = ExplorerReport(target_path=str(self.target))
        logger.info(f"🔍 Exploring: {self.target}")

        for root, dirs, files in os.walk(self.target):
            # Prune directories we should skip
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS and not d.endswith(".egg-info")
            ]

            for filename in files:
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(self.target))
                ext = filepath.suffix.lower()

                if ext in PYTHON_EXTS:
                    self._process_python_file(filepath, rel_path, report)

                elif ext in VOICE_EXTS:
                    report.voice_files.append(rel_path)

                elif ext in MODEL_EXTS:
                    report.model_files.append(rel_path)

                elif filename == ".env" or filename.startswith(".env."):
                    report.env_files.append(rel_path)

                elif ext in CONFIG_EXTS:
                    report.config_files.append(rel_path)

        self._log_summary(report)
        return report

    def _process_python_file(
        self,
        filepath: Path,
        rel_path: str,
        report: ExplorerReport,
    ) -> None:
        """Parse one Python file and extract module info and import issues."""
        report.python_modules.append(rel_path)

        try:
            source = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.warning(f"  ⚠ Could not read {rel_path}: {e}")
            return

        # Tag well-known file types by content signature
        self._tag_by_content(source, rel_path, report)

        # Parse AST for import analysis
        try:
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError as e:
            report.broken_imports.append(ImportIssue(
                file=rel_path,
                line=e.lineno or 0,
                import_name="(syntax error)",
                reason=f"SyntaxError: {e.msg}",
                shim_available=False,
            ))
            return

        self._audit_imports(tree, rel_path, report)

    def _tag_by_content(
        self,
        source: str,
        rel_path: str,
        report: ExplorerReport,
    ) -> None:
        """Tag the file against known media stack signatures."""
        lower = source.lower()
        filename = rel_path.lower()

        if any(sig.lower() in lower for sig in EAR_CANAL_SIGNATURES):
            report.ear_canal_refs.append(rel_path)

        if any(sig.lower() in lower for sig in VOICE_SDK_SIGNATURES):
            report.voice_sdk_refs.append(rel_path)

        if any(sig.lower() in lower for sig in OCR_SIGNATURES):
            report.ocr_refs.append(rel_path)

        if any(sig.lower() in lower for sig in TONE_SIGNATURES):
            report.tone_refs.append(rel_path)

        if any(sig.lower() in lower for sig in PHONEME_SIGNATURES):
            report.phoneme_refs.append(rel_path)

        if any(sig.lower() in lower for sig in XTTS_SIGNATURES):
            report.xtts_refs.append(rel_path)

        if any(sig.lower() in lower for sig in MICROPHONE_SIGNATURES):
            report.microphone_refs.append(rel_path)

        if any(sig.lower() in lower for sig in MCP_SIGNATURES):
            report.mcp_server_files.append(rel_path)

        if "preflight" in filename or "pre_flight" in filename:
            report.preflight_files.append(rel_path)

        if "tracer" in filename:
            report.tracer_files.append(rel_path)

    def _audit_imports(
        self,
        tree: ast.AST,
        rel_path: str,
        report: ExplorerReport,
    ) -> None:
        """Walk the AST and flag imports that use old/unmapped paths."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                self._check_import_node(node, rel_path, report)

    def _check_import_node(
        self,
        node: ast.Import | ast.ImportFrom,
        rel_path: str,
        report: ExplorerReport,
    ) -> None:
        """Check one import node for known broken patterns."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self._flag_if_old_path(alias.name, node.lineno, rel_path, report)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            self._flag_if_old_path(module, node.lineno, rel_path, report)

    def _flag_if_old_path(
        self,
        import_name: str,
        lineno: int,
        rel_path: str,
        report: ExplorerReport,
    ) -> None:
        """If the import matches a known old path, record a broken import issue."""
        # Check if the bare module name matches any shim key
        base = import_name.split(".")[0]
        if base in SHIM_MAP:
            canonical = SHIM_MAP[base]
            # Only flag if it's NOT already using the canonical path
            if not import_name.startswith("christman_voice_sdk"):
                report.broken_imports.append(ImportIssue(
                    file=rel_path,
                    line=lineno,
                    import_name=import_name,
                    reason=f"Old import path — canonical path is '{canonical}'",
                    shim_available=True,
                    shim_target=canonical,
                ))

    def _log_summary(self, report: ExplorerReport) -> None:
        logger.info(f"  📦 Python modules found: {report.module_count}")
        logger.info(f"  ❌ Broken imports: {report.broken_count}")
        logger.info(f"  🔧 Shimmable: {report.shimmable_count}")
        logger.info(f"  🎤 Microphone refs: {len(report.microphone_refs)}")
        logger.info(f"  👁  OCR refs: {len(report.ocr_refs)}")
        logger.info(f"  🎵 Tone refs: {len(report.tone_refs)}")
        logger.info(f"  🔌 MCP server files: {len(report.mcp_server_files)}")
        logger.info(f"  🔊 Voice files: {len(report.voice_files)}")
