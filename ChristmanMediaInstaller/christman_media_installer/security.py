"""
Christman Media Installer — security.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

Security posture check. Scans for hardcoded secrets, verifies local-first
defaults, flags biometric and child voice data exposure risks, and emits
HNDL-aware storage warnings for sensitive data.

This scanner never uploads, never modifies, and never hides what it finds.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

logger = logging.getLogger("christman.security")

# ──────────────────────────────────────────────
# PATTERNS: hardcoded secret indicators
# These are heuristic. A match is a warning, not a conviction.
# ──────────────────────────────────────────────
SECRET_PATTERNS = [
    (re.compile(r'(?i)(api[_\-]?key|apikey)\s*=\s*["\'][^"\']{8,}["\']'), "Possible hardcoded API key"),
    (re.compile(r'(?i)(secret[_\-]?key|secretkey)\s*=\s*["\'][^"\']{8,}["\']'), "Possible hardcoded secret key"),
    (re.compile(r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']'), "Possible hardcoded password"),
    (re.compile(r'(?i)(token)\s*=\s*["\'][^"\']{8,}["\']'), "Possible hardcoded token"),
    (re.compile(r'(?i)(aws_access_key|aws_secret)\s*=\s*["\'][^"\']{8,}["\']'), "AWS credential in source"),
    (re.compile(r'AKIA[0-9A-Z]{16}'), "AWS Access Key ID pattern"),
    (re.compile(r'(?i)(anthropic[_\-]?key|claude[_\-]?key)\s*=\s*["\'][^"\']{8,}["\']'), "Anthropic API key in source"),
    (re.compile(r'sk-[a-zA-Z0-9]{32,}'), "OpenAI-style secret key pattern"),
    (re.compile(r'(?i)(ngrok[_\-]?token|ngrok[_\-]?auth)\s*=\s*["\'][^"\']{8,}["\']'), "ngrok auth token in source"),
]

BIOMETRIC_PATTERNS = [
    (re.compile(r'(?i)voiceprint'), "Voiceprint reference"),
    (re.compile(r'(?i)speaker[_\-]?embedding'), "Speaker embedding reference"),
    (re.compile(r'(?i)biometric'), "Biometric data reference"),
    (re.compile(r'(?i)voice[_\-]?profile'), "Voice profile reference"),
]

CHILD_DATA_PATTERNS = [
    (re.compile(r'(?i)child[_\-]?voice'), "Child voice data reference"),
    (re.compile(r'(?i)kid[_\-]?voice'), "Kid voice data reference"),
    (re.compile(r'(?i)minor[_\-]?user'), "Minor user data reference"),
]

SKIP_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "node_modules", ".mypy_cache", ".pytest_cache",
}


@dataclass
class SecurityFinding:
    severity: str      # "CRITICAL", "WARNING", "INFO"
    file: str
    line: int
    message: str
    pattern_name: str


@dataclass
class SecurityReport:
    findings: List[SecurityFinding] = field(default_factory=list)
    hndl_warnings: List[str] = field(default_factory=list)
    gitignore_ok: bool = False
    dotenv_pattern_followed: bool = False
    local_first_confirmed: bool = False
    biometric_export_blocked: bool = False
    child_voiceprint_export_blocked: bool = False

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARNING")


class SecurityChecker:
    """Scans the target for security posture violations.

    Scope:
    - Hardcoded secrets in Python source
    - Biometric data references (flag for review)
    - Child voice data references (flag for review)
    - .gitignore coverage of .env files
    - HNDL-aware storage warnings
    - Local-first default confirmation
    """

    def __init__(self, target_path: str):
        self.target = Path(target_path).resolve()
        self.report = SecurityReport()

    def check(self) -> SecurityReport:
        logger.info("🔒 Running security posture check...")
        self._scan_python_files()
        self._check_gitignore()
        self._check_env_defaults()
        self._check_hndl_posture()
        self._log_summary()
        return self.report

    def _scan_python_files(self) -> None:
        """Scan all Python files for hardcoded secrets and biometric patterns."""
        for root, dirs, files in self._walk():
            for filename in files:
                if not filename.endswith(".py"):
                    continue
                filepath = Path(root) / filename
                rel_path = str(filepath.relative_to(self.target))
                self._scan_file(filepath, rel_path)

    def _scan_file(self, filepath: Path, rel_path: str) -> None:
        try:
            lines = filepath.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return

        for lineno, line in enumerate(lines, start=1):
            # Skip comment lines
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            for pattern, description in SECRET_PATTERNS:
                if pattern.search(line):
                    self.report.findings.append(SecurityFinding(
                        severity="CRITICAL",
                        file=rel_path,
                        line=lineno,
                        message=f"{description} at line {lineno}",
                        pattern_name=description,
                    ))

            for pattern, description in BIOMETRIC_PATTERNS:
                if pattern.search(line):
                    self.report.findings.append(SecurityFinding(
                        severity="WARNING",
                        file=rel_path,
                        line=lineno,
                        message=f"{description} — ensure no biometric data is exported without consent.",
                        pattern_name=description,
                    ))

            for pattern, description in CHILD_DATA_PATTERNS:
                if pattern.search(line):
                    self.report.findings.append(SecurityFinding(
                        severity="CRITICAL",
                        file=rel_path,
                        line=lineno,
                        message=f"{description} — child voice/data MUST NOT be exported. "
                                f"Verify local-only posture.",
                        pattern_name=description,
                    ))

    def _check_gitignore(self) -> None:
        """Verify .gitignore covers .env files."""
        gitignore = self.target / ".gitignore"
        if not gitignore.exists():
            self.report.findings.append(SecurityFinding(
                severity="WARNING",
                file=".gitignore",
                line=0,
                message=".gitignore not found — .env files may be committed accidentally.",
                pattern_name="gitignore_missing",
            ))
            return

        content = gitignore.read_text(encoding="utf-8", errors="replace")
        covers_env = ".env" in content or "*.env" in content
        self.report.gitignore_ok = covers_env

        if not covers_env:
            self.report.findings.append(SecurityFinding(
                severity="CRITICAL",
                file=".gitignore",
                line=0,
                message=".gitignore exists but does not cover .env files. "
                        "Add '.env' to .gitignore immediately.",
                pattern_name="gitignore_no_env",
            ))
        else:
            logger.info("  ✅ .gitignore covers .env files.")

    def _check_env_defaults(self) -> None:
        """Confirm that CHRISTMAN_LOCAL_ONLY_VULNERABLE is set to true in .env."""
        env_file = self.target / ".env"
        if not env_file.exists():
            return

        content = env_file.read_text(encoding="utf-8", errors="replace")
        local_first = "CHRISTMAN_LOCAL_ONLY_VULNERABLE=true" in content
        biometric_blocked = "CHRISTMAN_BIOMETRIC_EXPORT=false" in content
        child_blocked = "CHRISTMAN_CHILD_VOICEPRINT_EXPORT=false" in content

        self.report.local_first_confirmed = local_first
        self.report.biometric_export_blocked = biometric_blocked
        self.report.child_voiceprint_export_blocked = child_blocked

        if not local_first:
            self.report.findings.append(SecurityFinding(
                severity="WARNING",
                file=".env",
                line=0,
                message="CHRISTMAN_LOCAL_ONLY_VULNERABLE not confirmed true. "
                        "Vulnerable user data may not be local-first.",
                pattern_name="local_first_missing",
            ))

        if not biometric_blocked:
            self.report.findings.append(SecurityFinding(
                severity="WARNING",
                file=".env",
                line=0,
                message="CHRISTMAN_BIOMETRIC_EXPORT not confirmed false. "
                        "Biometric data may be exposed.",
                pattern_name="biometric_export_unset",
            ))

        if not child_blocked:
            self.report.findings.append(SecurityFinding(
                severity="CRITICAL",
                file=".env",
                line=0,
                message="CHRISTMAN_CHILD_VOICEPRINT_EXPORT not confirmed false. "
                        "Child voiceprint export must be explicitly blocked.",
                pattern_name="child_voiceprint_unset",
            ))

    def _check_hndl_posture(self) -> None:
        """Emit HNDL-aware warnings for any sensitive data found."""
        # HNDL = Harvest Now Decrypt Later: a quantum-era threat
        # Any health, voice, biometric, or location data is a target
        biometric_findings = [
            f for f in self.report.findings
            if "biometric" in f.pattern_name.lower()
            or "voice" in f.pattern_name.lower()
            or "child" in f.pattern_name.lower()
        ]

        if biometric_findings:
            self.report.hndl_warnings.append(
                "⚠ HNDL RISK: Biometric or voice data detected in codebase. "
                "Any at-rest storage of voiceprints, speaker embeddings, or user voice profiles "
                "should use HNDL-aware encryption (christman-crypto / ML-KEM-768). "
                "Harvest Now Decrypt Later attacks target this class of data."
            )

        # Also flag if XTTS model output (cloned voices) might be stored
        xtts_files = list(self.target.rglob("*.pth")) + list(self.target.rglob("*.onnx"))
        if xtts_files:
            self.report.hndl_warnings.append(
                f"⚠ HNDL RISK: {len(xtts_files)} model file(s) found (.pth/.onnx). "
                f"Cloned voice models are sensitive biometric artifacts — "
                f"encrypt at rest and restrict access."
            )

    def _walk(self):
        """Walk the target directory, skipping irrelevant dirs."""
        import os
        for root, dirs, files in os.walk(self.target):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            yield root, dirs, files

    def _log_summary(self) -> None:
        logger.info("─" * 50)
        logger.info(f"  Security: {self.report.critical_count} critical, "
                    f"{self.report.warning_count} warnings")
        if self.report.hndl_warnings:
            for w in self.report.hndl_warnings:
                logger.warning(f"  {w}")
        for f in self.report.findings:
            if f.severity == "CRITICAL":
                logger.error(f"  ❌ {f.file}:{f.line} — {f.message}")
