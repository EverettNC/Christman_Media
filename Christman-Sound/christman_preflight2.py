#!/usr/bin/env python3
"""
Christman Universal Preflight
The Christman AI Project

The most thorough automated module diagnostic ever built.
Drop into any Python project and run it.

Usage:
  python christman_preflight.py
  python christman_preflight.py --dir /path/to/project
  python christman_preflight.py --verbose
  python christman_preflight.py --json
  python christman_preflight.py --recursive
  python christman_preflight.py --skip module1,module2
  python christman_preflight.py --fix-deps

© 2026 Everett Nathaniel Christman & The Christman AI Project
Luma Cognify AI — "How can we help you love yourself more?"
Patent Pending TCAP-2026-001
"""

import ast
import argparse
import importlib.util
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ── Failure Categories ────────────────────────────────────────────────────────

class FailureType(str, Enum):
    SYNTAX_ERROR     = "SYNTAX_ERROR"       # Invalid Python syntax — file won't parse
    MISSING_PIP      = "MISSING_PIP"        # pip package not installed in environment
    MISSING_INTERNAL = "MISSING_INTERNAL"   # internal .py file referenced but not found
    CIRCULAR_IMPORT  = "CIRCULAR_IMPORT"    # two modules importing each other — deadlock
    IMPORT_ERROR     = "IMPORT_ERROR"       # wrong name/symbol from an existing module
    RUNTIME_ERROR    = "RUNTIME_ERROR"      # crashes during module-level execution
    FILE_NOT_FOUND   = "FILE_NOT_FOUND"     # references a file on disk that's gone
    UNKNOWN          = "UNKNOWN"            # couldn't classify — check verbose output


@dataclass
class ModuleResult:
    name:         str
    passed:       bool
    filepath:     str = ""
    load_time_ms: float = 0.0
    failure_type: Optional[FailureType] = None
    error_msg:    str = ""
    root_cause:   str = ""
    what_to_do:   str = ""           # human-readable fix instruction
    pip_package:  str = ""           # suggested pip install name
    traceback:    str = ""


# ── Known pip package name mappings ──────────────────────────────────────────

PIP_MAP = {
    "cv2":               "opencv-python",
    "sklearn":           "scikit-learn",
    "PIL":               "Pillow",
    "dotenv":            "python-dotenv",
    "yaml":              "PyYAML",
    "bs4":               "beautifulsoup4",
    "usb":               "pyusb",
    "serial":            "pyserial",
    "wx":                "wxPython",
    "gi":                "PyGObject",
    "Crypto":            "pycryptodome",
    "OpenSSL":           "pyOpenSSL",
    "jwt":               "PyJWT",
    "attr":              "attrs",
    "pkg_resources":     "setuptools",
    "google.cloud":      "google-cloud",
    "azure":             "azure-sdk",
    "boto3":             "boto3",
    "botocore":          "botocore",
    "faster_whisper":    "faster-whisper",
    "speech_recognition":"SpeechRecognition",
    "sounddevice":       "sounddevice",
    "soundfile":         "soundfile",
    "librosa":           "librosa",
    "pyaudio":           "PyAudio",
    "playsound":         "playsound",
    "gtts":              "gTTS",
    "pygame":            "pygame",
    "torch":             "torch",
    "tensorflow":        "tensorflow",
    "keras":             "keras",
    "transformers":      "transformers",
    "diffusers":         "diffusers",
    "sentence_transformers": "sentence-transformers",
    "spacy":             "spacy",
    "nltk":              "nltk",
    "textgrid":          "textgrid",
    "networkx":          "networkx",
    "sympy":             "sympy",
    "qiskit":            "qiskit",
    "pandas":            "pandas",
    "numpy":             "numpy",
    "scipy":             "scipy",
    "matplotlib":        "matplotlib",
    "seaborn":           "seaborn",
    "plotly":            "plotly",
    "joblib":            "joblib",
    "aiohttp":           "aiohttp",
    "websockets":        "websockets",
    "httpx":             "httpx",
    "anthropic":         "anthropic",
    "openai":            "openai",
    "fastapi":           "fastapi",
    "uvicorn":           "uvicorn",
    "flask":             "flask",
    "flask_cors":        "flask-cors",
    "flask_sqlalchemy":  "flask-sqlalchemy",
    "fastmcp":           "fastmcp",
    "pydantic":          "pydantic",
    "sqlalchemy":        "sqlalchemy",
    "alembic":           "alembic",
    "pymongo":           "pymongo",
    "redis":             "redis",
    "celery":            "celery",
    "newspaper":         "newspaper4k",
    "autopep8":          "autopep8",
    "jsonschema":        "jsonschema",
    "cryptography":      "cryptography",
    "paramiko":          "paramiko",
    "docker":            "docker",
    "kubernetes":        "kubernetes",
    "aioschedule":       "aioschedule",
    "tiktoken":          "tiktoken",
    "parselmouth":       "praat-parselmouth",
    "torchaudio":        "torchaudio",
    "requests":          "requests",
    "pyttsx3":           "pyttsx3",
    "elevenlabs":        "elevenlabs",
    "deepgram":          "deepgram-sdk",
}


# ── Module names that are internal — not pip packages ─────────────────────────

KNOWN_INTERNAL = {
    "brain", "brain_common_events", "brain_ferrari_v1", "derek_brain",
    "config", "utils", "events", "database", "app_init",
    "brockston_module_loader", "nlp_module", "memory_mesh",
    "web_crawler", "alphavox_knowledge_engine", "brockston_core",
    "family_coordinator", "ultimateev", "emotion_service",
    "crisis_detection", "provider_router", "perplexity_service",
    "tone_manager", "intent_engine", "memory_engine", "conversation_engine",
    "local_reasoning_engine", "knowledge_engine", "soul_forge_bridge",
    "christman_tone_engine_v2", "voice_analysis_service",
}


# ── Core logic ────────────────────────────────────────────────────────────────

def check_syntax(filepath: str) -> Optional[str]:
    """Return syntax error string or None if clean."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        ast.parse(source, filename=filepath)
        return None
    except SyntaxError as e:
        return f"Line {e.lineno}: {e.msg} — {e.text.strip() if e.text else ''}"
    except Exception as e:
        return str(e)


def extract_root_cause(
    tb: str,
    error: Exception,
    project_dir: str,
) -> Tuple[str, str, str, FailureType]:
    """
    Parse traceback + error to find root cause, a fix instruction,
    pip package, and failure type.
    Returns (root_cause, what_to_do, pip_package, failure_type)
    """
    import re
    err_str = str(error)
    err_type = type(error).__name__

    # ── Circular import ───────────────────────────────────────────────────────
    if (
        "circular import" in err_str.lower()
        or "partially initialized module" in err_str.lower()
        or "most likely due to a circular import" in err_str.lower()
    ):
        m = re.search(r"module '([^']+)'", err_str)
        mod = m.group(1) if m else "unknown"
        return (
            f"Circular import detected involving '{mod}'",
            f"Trace the import chain: which module imports '{mod}' and vice versa. "
            f"Break the cycle by moving shared code to a third module, "
            f"or use a lazy import (import inside the function that needs it).",
            "",
            FailureType.CIRCULAR_IMPORT,
        )

    # ── Missing module ────────────────────────────────────────────────────────
    if isinstance(error, ModuleNotFoundError):
        missing = getattr(error, "name", None) or ""
        if not missing:
            m = re.search(r"No module named '([^']+)'", err_str)
            missing = m.group(1) if m else err_str

        root = missing.split(".")[0]

        # Is it an internal file that exists but failed?
        local_path = os.path.join(project_dir, f"{root}.py")
        if os.path.exists(local_path):
            return (
                f"Internal module '{root}' exists on disk but failed to load — "
                f"it has its own import error. Run preflight on it directly.",
                f"Open {root}.py and check its own imports at the top of the file.",
                "",
                FailureType.IMPORT_ERROR,
            )

        # Is it a known internal module that's simply missing?
        if root in KNOWN_INTERNAL:
            return (
                f"Internal module '{root}' is missing — not a pip package, "
                f"it needs to be created or restored.",
                f"Create or restore '{root}.py' in the project directory.",
                "",
                FailureType.MISSING_INTERNAL,
            )

        # Known pip package
        if root in PIP_MAP:
            pkg = PIP_MAP[root]
            return (
                f"pip package '{root}' is not installed (install as: {pkg})",
                f"Run: pip install {pkg}",
                pkg,
                FailureType.MISSING_PIP,
            )

        # Unknown — assume pip
        return (
            f"Module '{root}' not found — likely a pip package not installed",
            f"Run: pip install {root}  (or check the correct package name on PyPI)",
            root,
            FailureType.MISSING_PIP,
        )

    # ── Import name error ─────────────────────────────────────────────────────
    if isinstance(error, ImportError):
        if "cannot import name" in err_str:
            m = re.search(r"cannot import name '([^']+)' from '([^']+)'", err_str)
            if m:
                symbol, source_mod = m.group(1), m.group(2)
                return (
                    f"'{symbol}' does not exist in module '{source_mod}'",
                    f"Check if '{symbol}' was renamed, moved, or never defined in '{source_mod}'. "
                    f"Search the codebase: grep -r '{symbol}' --include='*.py'",
                    "",
                    FailureType.IMPORT_ERROR,
                )
            return (
                err_str,
                "The symbol being imported doesn't exist. Check spelling and module version.",
                "",
                FailureType.IMPORT_ERROR,
            )
        if "No such file or directory" in err_str:
            return (
                err_str,
                "A file referenced during import doesn't exist on disk. "
                "Check paths in __init__.py or config files.",
                "",
                FailureType.FILE_NOT_FOUND,
            )
        return (
            err_str,
            "Check the import statement at the top of this module.",
            "",
            FailureType.IMPORT_ERROR,
        )

    # ── File not found ────────────────────────────────────────────────────────
    if isinstance(error, FileNotFoundError):
        return (
            err_str,
            "A file this module tries to open at load time doesn't exist. "
            "Check for hardcoded paths or missing config/data files.",
            "",
            FailureType.FILE_NOT_FOUND,
        )

    # ── Attribute error at module level ───────────────────────────────────────
    if isinstance(error, AttributeError):
        return (
            f"Attribute error at module load: {err_str}",
            "Something is None or missing when this module initializes. "
            "Check module-level code that runs outside of functions — "
            "a dependency is loading as None.",
            "",
            FailureType.RUNTIME_ERROR,
        )

    # ── Everything else ───────────────────────────────────────────────────────
    return (
        f"{err_type}: {err_str}",
        f"This module crashes when Python tries to load it. "
        f"Run with --verbose to see the full traceback.",
        "",
        FailureType.RUNTIME_ERROR,
    )


def test_module(name: str, filepath: str, project_dir: str) -> ModuleResult:
    """Run a full diagnostic on a single module file."""
    start = time.perf_counter()

    # Step 1: Syntax check first — fast, no execution risk
    syntax_err = check_syntax(filepath)
    if syntax_err:
        return ModuleResult(
            name=name,
            filepath=filepath,
            passed=False,
            load_time_ms=round((time.perf_counter() - start) * 1000, 1),
            failure_type=FailureType.SYNTAX_ERROR,
            error_msg=syntax_err,
            root_cause=f"Syntax error — {syntax_err}",
            what_to_do=(
                "Fix the syntax error at the line indicated. "
                "Common causes: missing colon, unclosed bracket, "
                "bad indentation, mismatched quotes."
            ),
        )

    # Step 2: Attempt import
    try:
        spec = importlib.util.spec_from_file_location(f"_cpf_{name}", filepath)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        return ModuleResult(name=name, filepath=filepath, passed=True, load_time_ms=elapsed)

    except Exception as e:
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        tb = traceback.format_exc()
        root_cause, what_to_do, pip_pkg, ftype = extract_root_cause(tb, e, project_dir)
        return ModuleResult(
            name=name,
            filepath=filepath,
            passed=False,
            load_time_ms=elapsed,
            failure_type=ftype,
            error_msg=str(e).split("\n")[0][:160],
            root_cause=root_cause,
            what_to_do=what_to_do,
            pip_package=pip_pkg,
            traceback=tb,
        )


def discover_modules(
    project_dir: str,
    skip: set,
    recursive: bool = False,
) -> List[Tuple[str, str]]:
    """Find all .py files in project_dir."""
    modules = []
    if recursive:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in sorted(dirs) if not d.startswith((".", "__pycache__", "venv", "node_modules"))]
            for f in sorted(files):
                if f.endswith(".py"):
                    name = f[:-3]
                    if name not in skip:
                        modules.append((name, os.path.join(root, f)))
    else:
        for f in sorted(os.listdir(project_dir)):
            if f.endswith(".py"):
                name = f[:-3]
                if name not in skip:
                    modules.append((name, os.path.join(project_dir, f)))
    return modules


# ── Report rendering ──────────────────────────────────────────────────────────

CATEGORY_ORDER = [
    FailureType.SYNTAX_ERROR,
    FailureType.CIRCULAR_IMPORT,
    FailureType.MISSING_PIP,
    FailureType.MISSING_INTERNAL,
    FailureType.FILE_NOT_FOUND,
    FailureType.IMPORT_ERROR,
    FailureType.RUNTIME_ERROR,
    FailureType.UNKNOWN,
]

CATEGORY_LABELS = {
    FailureType.SYNTAX_ERROR:     "SYNTAX ERRORS      — Fix the file first, nothing else matters",
    FailureType.CIRCULAR_IMPORT:  "CIRCULAR IMPORTS   — Two modules locked in a death grip",
    FailureType.MISSING_PIP:      "MISSING PIP PKGS   — Not installed in this environment",
    FailureType.MISSING_INTERNAL: "MISSING INTERNAL   — Module expected but file doesn't exist",
    FailureType.FILE_NOT_FOUND:   "FILE NOT FOUND     — Referenced file deleted or moved",
    FailureType.IMPORT_ERROR:     "IMPORT ERRORS      — Symbol doesn't exist where expected",
    FailureType.RUNTIME_ERROR:    "RUNTIME ERRORS     — Crashes the moment Python loads it",
    FailureType.UNKNOWN:          "UNKNOWN            — Run --verbose to diagnose",
}


def render_report(
    results: List[ModuleResult],
    verbose: bool,
    project_dir: str,
):
    passed  = [r for r in results if r.passed]
    failed  = [r for r in results if not r.passed]
    total   = len(results)
    elapsed = sum(r.load_time_ms for r in results)
    pct     = round((len(passed) / total) * 100) if total else 0

    W = 72
    print()
    print("═" * W)
    print("  CHRISTMAN UNIVERSAL PREFLIGHT")
    print(f"  {project_dir}")
    print("═" * W)

    # ── Failures grouped by category ──────────────────────────────────────────
    if failed:
        by_category: dict = {}
        for r in failed:
            ft = r.failure_type or FailureType.UNKNOWN
            by_category.setdefault(ft, []).append(r)

        for ftype in CATEGORY_ORDER:
            group = by_category.get(ftype)
            if not group:
                continue

            print(f"\n  ── {CATEGORY_LABELS[ftype]} ({len(group)}) ──")

            for r in group:
                print(f"\n  ❌  {r.name:<40} [{r.load_time_ms}ms]")
                print(f"      WHAT:  {r.root_cause}")
                print(f"      FIX:   {r.what_to_do}")
                if r.pip_package:
                    print(f"      CMD:   pip install {r.pip_package}")
                if verbose and r.traceback:
                    print(f"      ── TRACEBACK ──")
                    for line in r.traceback.strip().split("\n"):
                        print(f"      {line}")

    # ── Passed ────────────────────────────────────────────────────────────────
    if passed:
        print(f"\n  ── LOADED ({len(passed)}) ──\n")
        for r in passed:
            print(f"  ✅  {r.name:<40} [{r.load_time_ms}ms]")

    # ── pip install command ───────────────────────────────────────────────────
    pip_failures = [r for r in failed if r.pip_package]
    unique_pkgs  = sorted(set(r.pip_package for r in pip_failures if r.pip_package))
    if unique_pkgs:
        print(f"\n  ── ONE COMMAND TO FIX ALL MISSING PACKAGES ──\n")
        print(f"  pip install {' '.join(unique_pkgs)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("═" * W)
    print(f"  PROJECT          : {os.path.basename(project_dir)}")
    print(f"  TOTAL MODULES    : {total}")
    print(f"  LOADED           : {len(passed)}  ({pct}%)")
    print(f"  FAILED           : {len(failed)}")
    print(f"  TOTAL LOAD TIME  : {elapsed:.0f}ms")
    print()

    # Failure breakdown
    by_cat: dict = {}
    for r in failed:
        ft = r.failure_type or FailureType.UNKNOWN
        by_cat[ft] = by_cat.get(ft, 0) + 1
    if by_cat:
        print("  FAILURE BREAKDOWN:")
        for ftype in CATEGORY_ORDER:
            if ftype in by_cat:
                print(f"    {ftype.value:<22} {by_cat[ftype]}")
        print()

    if len(failed) == 0:
        status = "🟢  ALL SYSTEMS GO — Brockston is ready to fly."
    elif pct >= 80:
        status = f"🟡  MOSTLY READY — {pct}% loaded. Fix the dependencies above."
    elif pct >= 50:
        status = f"🟠  DEGRADED — {pct}% loaded. Significant work needed before deployment."
    else:
        status = f"🔴  NOT READY — {pct}% loaded. Major dependencies missing."

    print(f"  STATUS           : {status}")
    print("═" * W)
    print()


def render_json(results: List[ModuleResult], project_dir: str):
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    out = {
        "project": project_dir,
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "pass_rate_pct": round(len(passed) / len(results) * 100) if results else 0,
        "modules": [
            {
                "name": r.name,
                "filepath": r.filepath,
                "passed": r.passed,
                "load_time_ms": r.load_time_ms,
                "failure_type": r.failure_type.value if r.failure_type else None,
                "error": r.error_msg,
                "root_cause": r.root_cause,
                "what_to_do": r.what_to_do,
                "pip_package": r.pip_package,
            }
            for r in results
        ],
        "pip_install_command": (
            "pip install " + " ".join(sorted(set(
                r.pip_package for r in failed if r.pip_package
            )))
        ) if any(r.pip_package for r in failed) else "",
    }
    print(json.dumps(out, indent=2))


# ── Modules that fire side effects on import — always skip ───────────────────

ALWAYS_SKIP = {
    "christman_preflight",
    "derek_preflight",
    "fix_derek_ferrari",
    "start_derek_ferrari",
}


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Christman Universal Preflight — drop into any Python project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python christman_preflight.py\n"
            "  python christman_preflight.py --dir /workspaces/BROCKSTON/src/ai/python_core\n"
            "  python christman_preflight.py --verbose\n"
            "  python christman_preflight.py --json\n"
            "  python christman_preflight.py --recursive\n"
            "  python christman_preflight.py --skip brain,soul\n"
        )
    )
    parser.add_argument("--dir",       default=".",   help="Project directory to scan")
    parser.add_argument("--skip",      default="",    help="Comma-separated module names to skip")
    parser.add_argument("--verbose",   action="store_true", help="Show full tracebacks on failures")
    parser.add_argument("--json",      action="store_true", help="Output results as JSON")
    parser.add_argument("--recursive", action="store_true", help="Scan subdirectories too")
    args = parser.parse_args()

    project_dir = os.path.abspath(args.dir)
    if not os.path.isdir(project_dir):
        print(f"ERROR: {project_dir} is not a directory.")
        sys.exit(2)

    sys.path.insert(0, project_dir)

    skip = ALWAYS_SKIP | {s.strip() for s in args.skip.split(",") if s.strip()}
    modules = discover_modules(project_dir, skip, recursive=args.recursive)

    if not args.json:
        print(f"\n  Scanning {len(modules)} modules in {project_dir} ...")

    results = []
    for name, filepath in modules:
        result = test_module(name, filepath, project_dir)
        results.append(result)
        if not args.json:
            icon = "✅" if result.passed else "❌"
            # Pad to 50 chars so shorter names don't leave ghost text
            print(f"  {icon}  {name:<50}", end="\r", flush=True)

    # Clear the progress line
    if not args.json:
        print(" " * 60, end="\r")

    if args.json:
        render_json(results, project_dir)
    else:
        render_report(results, args.verbose, project_dir)

    failed_count = sum(1 for r in results if not r.passed)
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()

# ==============================================================================
# © 2026 Everett Nathaniel Christman & The Christman AI Project
# Luma Cognify AI — "How can we help you love yourself more?"
# Patent Pending TCAP-2026-001
#
# Cardinal Rule 1: It has to actually work.
# Cardinal Rule 6: Fail loud — no silent failures.
# Cardinal Rule 13: Every failure tells you exactly what to do next.
# ==============================================================================
