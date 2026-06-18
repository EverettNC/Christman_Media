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
  python christman_preflight.py --no-color

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


# ── ANSI Color System ─────────────────────────────────────────────────────────

class C:
    _enabled = True
    RED      = "\033[91m"
    GREEN    = "\033[92m"
    YELLOW   = "\033[93m"
    BLUE     = "\033[94m"
    MAGENTA  = "\033[95m"
    CYAN     = "\033[96m"
    WHITE    = "\033[97m"
    ORANGE   = "\033[38;5;208m"
    DIM      = "\033[2m"
    BOLD     = "\033[1m"
    RESET    = "\033[0m"

    @classmethod
    def disable(cls):
        cls._enabled = False
        for attr in ["RED","GREEN","YELLOW","BLUE","MAGENTA","CYAN",
                     "WHITE","ORANGE","DIM","BOLD","RESET"]:
            setattr(cls, attr, "")

    @classmethod
    def r(cls, text, *codes):
        if not cls._enabled:
            return text
        return "".join(codes) + str(text) + cls.RESET


def c(text, *codes):
    return C.r(text, *codes)


# ── ASCII Banner ──────────────────────────────────────────────────────────────

BANNER = r"""
   ██████╗██╗  ██╗██████╗ ██╗███████╗████████╗███╗   ███╗ █████╗ ███╗   ██╗
  ██╔════╝██║  ██║██╔══██╗██║██╔════╝╚══██╔══╝████╗ ████║██╔══██╗████╗  ██║
  ██║     ███████║██████╔╝██║███████╗   ██║   ██╔████╔██║███████║██╔██╗ ██║
  ██║     ██╔══██║██╔══██╗██║╚════██║   ██║   ██║╚██╔╝██║██╔══██║██║╚██╗██║
  ╚██████╗██║  ██║██║  ██║██║███████║   ██║   ██║ ╚═╝ ██║██║  ██║██║ ╚████║
   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
"""

SUBHEADER = "  U N I V E R S A L   P R E F L I G H T   D I A G N O S T I C S"
TAGLINE   = "  The Christman AI Project  ·  Luma Cognify AI  ·  Patent Pending TCAP-2026-001"
MISSION   = '  "How can we help you love yourself more?"'


def print_banner(project_dir: str):
    print()
    print(c(BANNER, C.CYAN, C.BOLD))
    print(c(SUBHEADER, C.WHITE, C.BOLD))
    print(c(TAGLINE, C.DIM))
    print(c(MISSION, C.GREEN))
    print()
    print(c("  ┌─────────────────────────────────────────────────────────────────────┐", C.DIM))
    print(c("  │  TARGET  ", C.DIM) + c(f"{project_dir:<60}", C.CYAN) + c("│", C.DIM))
    print(c("  └─────────────────────────────────────────────────────────────────────┘", C.DIM))
    print()


# ── Progress Bar ──────────────────────────────────────────────────────────────

def progress_bar(current: int, total: int, name: str, passed: int, failed: int, width: int = 40):
    pct    = current / total if total else 0
    filled = int(width * pct)
    bar    = c("█" * filled, C.GREEN) + c("░" * (width - filled), C.DIM)
    status = c(f"✅ {passed}", C.GREEN) + c(" │ ", C.DIM) + c(f"❌ {failed}", C.RED)
    label  = f"{name:<35}"[:35]
    print(f"  [{bar}] {c(f'{int(pct*100):3d}%', C.CYAN)}  {status}  {c(label, C.DIM)}", end="\r", flush=True)


def clear_progress():
    print(" " * 120, end="\r")


# ── Failure Categories ────────────────────────────────────────────────────────

class FailureType(str, Enum):
    SYNTAX_ERROR     = "SYNTAX_ERROR"
    MISSING_PIP      = "MISSING_PIP"
    MISSING_INTERNAL = "MISSING_INTERNAL"
    CIRCULAR_IMPORT  = "CIRCULAR_IMPORT"
    IMPORT_ERROR     = "IMPORT_ERROR"
    RUNTIME_ERROR    = "RUNTIME_ERROR"
    FILE_NOT_FOUND   = "FILE_NOT_FOUND"
    UNKNOWN          = "UNKNOWN"


CATEGORY_COLORS = {
    FailureType.SYNTAX_ERROR:     C.RED,
    FailureType.CIRCULAR_IMPORT:  C.MAGENTA,
    FailureType.MISSING_PIP:      C.YELLOW,
    FailureType.MISSING_INTERNAL: C.ORANGE,
    FailureType.FILE_NOT_FOUND:   C.ORANGE,
    FailureType.IMPORT_ERROR:     C.CYAN,
    FailureType.RUNTIME_ERROR:    C.RED,
    FailureType.UNKNOWN:          C.DIM,
}

CATEGORY_ICONS = {
    FailureType.SYNTAX_ERROR:     "🔴",
    FailureType.CIRCULAR_IMPORT:  "🔁",
    FailureType.MISSING_PIP:      "📦",
    FailureType.MISSING_INTERNAL: "🔍",
    FailureType.FILE_NOT_FOUND:   "🗂",
    FailureType.IMPORT_ERROR:     "⚠️",
    FailureType.RUNTIME_ERROR:    "💥",
    FailureType.UNKNOWN:          "❓",
}

CATEGORY_LABELS = {
    FailureType.SYNTAX_ERROR:     "SYNTAX ERRORS       Fix the file first. Nothing else runs until this is clean.",
    FailureType.CIRCULAR_IMPORT:  "CIRCULAR IMPORTS    Two modules locked in a death grip. Break the cycle.",
    FailureType.MISSING_PIP:      "MISSING PIP PKGS    Not installed in this environment. One command fixes all.",
    FailureType.MISSING_INTERNAL: "MISSING INTERNAL    Module expected but the file does not exist on disk.",
    FailureType.FILE_NOT_FOUND:   "FILE NOT FOUND      Referenced file was deleted or moved.",
    FailureType.IMPORT_ERROR:     "IMPORT ERRORS       Symbol does not exist where expected.",
    FailureType.RUNTIME_ERROR:    "RUNTIME ERRORS      Crashes the moment Python loads it.",
    FailureType.UNKNOWN:          "UNKNOWN             Run --verbose to diagnose.",
}


@dataclass
class ModuleResult:
    name:          str
    passed:        bool
    filepath:      str   = ""
    load_time_ms:  float = 0.0
    failure_type:  Optional[FailureType] = None
    error_msg:     str   = ""
    root_cause:    str   = ""
    what_to_do:    str   = ""
    pip_package:   str   = ""
    traceback_str: str   = ""


# ── Known pip package name mappings ──────────────────────────────────────────

PIP_MAP = {
    "cv2":"opencv-python","sklearn":"scikit-learn","PIL":"Pillow",
    "dotenv":"python-dotenv","yaml":"PyYAML","bs4":"beautifulsoup4",
    "usb":"pyusb","serial":"pyserial","wx":"wxPython","gi":"PyGObject",
    "Crypto":"pycryptodome","OpenSSL":"pyOpenSSL","jwt":"PyJWT",
    "attr":"attrs","pkg_resources":"setuptools","google.cloud":"google-cloud",
    "azure":"azure-sdk","boto3":"boto3","botocore":"botocore",
    "faster_whisper":"faster-whisper","speech_recognition":"SpeechRecognition",
    "sounddevice":"sounddevice","soundfile":"soundfile","librosa":"librosa",
    "pyaudio":"PyAudio","playsound":"playsound","gtts":"gTTS","pygame":"pygame",
    "torch":"torch","tensorflow":"tensorflow","keras":"keras",
    "transformers":"transformers","diffusers":"diffusers",
    "sentence_transformers":"sentence-transformers","spacy":"spacy",
    "nltk":"nltk","textgrid":"textgrid","networkx":"networkx","sympy":"sympy",
    "qiskit":"qiskit","pandas":"pandas","numpy":"numpy","scipy":"scipy",
    "matplotlib":"matplotlib","seaborn":"seaborn","plotly":"plotly",
    "joblib":"joblib","aiohttp":"aiohttp","websockets":"websockets",
    "httpx":"httpx","anthropic":"anthropic","openai":"openai",
    "fastapi":"fastapi","uvicorn":"uvicorn","flask":"flask",
    "flask_cors":"flask-cors","flask_sqlalchemy":"flask-sqlalchemy",
    "fastmcp":"fastmcp","pydantic":"pydantic","sqlalchemy":"sqlalchemy",
    "alembic":"alembic","pymongo":"pymongo","redis":"redis","celery":"celery",
    "newspaper":"newspaper4k","autopep8":"autopep8","jsonschema":"jsonschema",
    "cryptography":"cryptography","paramiko":"paramiko","docker":"docker",
    "kubernetes":"kubernetes","aioschedule":"aioschedule","tiktoken":"tiktoken",
    "parselmouth":"praat-parselmouth","torchaudio":"torchaudio",
    "requests":"requests","pyttsx3":"pyttsx3","deepgram":"deepgram-sdk",
    "pyperclip":"pyperclip","rich":"rich","typer":"typer","click":"click",
}


# ── Known internal modules — not pip packages ─────────────────────────────────

KNOWN_INTERNAL = {
    # Brain / Core
    "brain", "brain_common_events", "brain_ferrari_v1", "derek_brain",
    "brockston_core", "Brockston_Brain_CC1", "brockston_module_loader",
    "brockston_boot", "brockston_reality_check", "brockston_education_system",
    "brain_combined", "cognitive_cortex",

    # Engines
    "local_reasoning_engine", "knowledge_engine", "memory_engine",
    "conversation_engine", "intent_engine", "crisis_detection",
    "provider_router", "perplexity_service", "tone_manager",
    "reasoning_reflective_planner", "reasoning_intent", "reasoning_reasoner",
    "reasoning_cortex_types",

    # Family
    "family_coordinator", "ultimateev", "alphavox_knowledge_engine",

    # Infrastructure
    "config", "utils", "events", "database", "app_init",
    "web_crawler", "nlp_module", "memory_mesh", "memory_mesh_bridge",
    "tts_bridge", "soul_forge_bridge", "bridge",

    # Voice
    "voice_analysis_service", "christman_tone_engine_v2",
    "emotion_service", "emotion",

    # RAG
    "store", "indexer", "memory_rag",

    # Embodiment
    "embodiment", "InfernoSoulForge",

    # Misc internal
    "backend", "speech", "src", "test_code",
    "routes", "loop", "answer", "executor",
}


# ── Core diagnostic logic ─────────────────────────────────────────────────────

def check_syntax(filepath: str) -> Optional[str]:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        ast.parse(source, filename=filepath)
        return None
    except SyntaxError as e:
        snippet = e.text.strip() if e.text else ""
        return f"Line {e.lineno}: {e.msg}  →  {snippet}"
    except Exception as e:
        return str(e)


def extract_root_cause(tb: str, error: Exception, project_dir: str) -> Tuple[str, str, str, FailureType]:
    import re
    err_str  = str(error)

    if any(s in err_str.lower() for s in ["circular import","partially initialized module","most likely due to a circular import"]):
        m   = re.search(r"module '([^']+)'", err_str)
        mod = m.group(1) if m else "unknown"
        return (
            f"Circular import involving '{mod}'",
            f"Find which module imports '{mod}' and vice versa. Move shared code to a third module or use lazy imports (import inside the function body).",
            "", FailureType.CIRCULAR_IMPORT,
        )

    if isinstance(error, ModuleNotFoundError):
        missing = getattr(error, "name", None) or ""
        if not missing:
            m       = re.search(r"No module named '([^']+)'", err_str)
            missing = m.group(1) if m else err_str
        root = missing.split(".")[0]
        if os.path.exists(os.path.join(project_dir, f"{root}.py")):
            return (
                f"'{root}' exists on disk but failed to load — it has its own broken import",
                f"Run preflight on {root}.py directly and fix its imports first.",
                "", FailureType.IMPORT_ERROR,
            )
        if root in KNOWN_INTERNAL:
            return (
                f"Internal module '{root}' is missing — not a pip package",
                f"Create or restore '{root}.py' in the project directory.",
                "", FailureType.MISSING_INTERNAL,
            )
        if root in PIP_MAP:
            pkg = PIP_MAP[root]
            return (f"pip package '{root}' not installed  (pip name: {pkg})", f"pip install {pkg}", pkg, FailureType.MISSING_PIP)
        return (f"Module '{root}' not found — likely a pip package", f"pip install {root}", root, FailureType.MISSING_PIP)

    if isinstance(error, ImportError):
        if "cannot import name" in err_str:
            m = re.search(r"cannot import name '([^']+)' from '([^']+)'", err_str)
            if m:
                sym, src = m.group(1), m.group(2)
                return (f"'{sym}' does not exist in '{src}'", f"grep -r '{sym}' --include='*.py'  — it may be renamed, moved, or never defined.", "", FailureType.IMPORT_ERROR)
            return (err_str, "Check the import — the symbol may have been renamed.", "", FailureType.IMPORT_ERROR)
        if "No such file or directory" in err_str:
            return (err_str, "A file referenced during import does not exist. Check hardcoded paths.", "", FailureType.FILE_NOT_FOUND)
        return (err_str, "Check the import statement at the top of this module.", "", FailureType.IMPORT_ERROR)

    if isinstance(error, FileNotFoundError):
        return (err_str, "A file this module opens at load time does not exist. Check hardcoded paths or missing config/data files.", "", FailureType.FILE_NOT_FOUND)

    if isinstance(error, AttributeError):
        return (f"Attribute error at module load: {err_str}", "A dependency is loading as None. Check module-level code that runs outside functions.", "", FailureType.RUNTIME_ERROR)

    return (f"{type(error).__name__}: {err_str}", "Module crashes on load. Run --verbose to see the full traceback.", "", FailureType.RUNTIME_ERROR)


def test_module(name: str, filepath: str, project_dir: str) -> ModuleResult:
    start      = time.perf_counter()
    syntax_err = check_syntax(filepath)
    if syntax_err:
        return ModuleResult(
            name=name, filepath=filepath, passed=False,
            load_time_ms=round((time.perf_counter()-start)*1000,1),
            failure_type=FailureType.SYNTAX_ERROR,
            error_msg=syntax_err, root_cause=f"Syntax error — {syntax_err}",
            what_to_do="Fix the syntax error at the indicated line. Common causes: missing colon, unclosed bracket, bad indentation, mismatched quotes.",
        )
    try:
        spec = importlib.util.spec_from_file_location(f"_cpf_{name}", filepath)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return ModuleResult(name=name, filepath=filepath, passed=True, load_time_ms=round((time.perf_counter()-start)*1000,1))
    except Exception as e:
        tb                             = traceback.format_exc()
        root_cause, what_to_do, pip_pkg, ftype = extract_root_cause(tb, e, project_dir)
        return ModuleResult(
            name=name, filepath=filepath, passed=False,
            load_time_ms=round((time.perf_counter()-start)*1000,1),
            failure_type=ftype, error_msg=str(e).split("\n")[0][:160],
            root_cause=root_cause, what_to_do=what_to_do,
            pip_package=pip_pkg, traceback_str=tb,
        )


def discover_modules(project_dir: str, skip: set, recursive: bool = False) -> List[Tuple[str, str]]:
    modules = []
    if recursive:
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in sorted(dirs) if not d.startswith((".", "__pycache__", "venv", "node_modules"))]
            for f in sorted(files):
                if f.endswith(".py") and f[:-3] not in skip:
                    modules.append((f[:-3], os.path.join(root, f)))
    else:
        for f in sorted(os.listdir(project_dir)):
            if f.endswith(".py") and f[:-3] not in skip:
                modules.append((f[:-3], os.path.join(project_dir, f)))
    return modules


# ── Report rendering ──────────────────────────────────────────────────────────

CATEGORY_ORDER = [
    FailureType.SYNTAX_ERROR, FailureType.CIRCULAR_IMPORT,
    FailureType.MISSING_PIP, FailureType.MISSING_INTERNAL,
    FailureType.FILE_NOT_FOUND, FailureType.IMPORT_ERROR,
    FailureType.RUNTIME_ERROR, FailureType.UNKNOWN,
]


def divider(label: str = "", color=None, width: int = 72):
    if label:
        pad  = width - len(label) - 6
        line = f"  ╠══ {label} {'═' * max(0,pad)}╣"
    else:
        line = "  " + "═" * width
    print(c(line, color or C.DIM))


def render_report(results: List[ModuleResult], verbose: bool, project_dir: str):
    passed  = [r for r in results if r.passed]
    failed  = [r for r in results if not r.passed]
    total   = len(results)
    elapsed = sum(r.load_time_ms for r in results)
    pct     = round(len(passed)/total*100) if total else 0

    if failed:
        by_category: dict = {}
        for r in failed:
            ft = r.failure_type or FailureType.UNKNOWN
            by_category.setdefault(ft, []).append(r)

        for ftype in CATEGORY_ORDER:
            group = by_category.get(ftype)
            if not group:
                continue
            col   = CATEGORY_COLORS.get(ftype, C.DIM)
            icon  = CATEGORY_ICONS.get(ftype, "❓")
            label = CATEGORY_LABELS.get(ftype, ftype.value)
            print()
            divider(f"{icon}  {label}  [{len(group)}]", color=col)
            for r in group:
                print()
                print(f"  {c('❌', C.RED)}  {c(r.name, C.WHITE, C.BOLD):<45} {c(f'{r.load_time_ms}ms', C.DIM)}")
                print(f"     {c('WHAT:', C.DIM)}  {c(r.root_cause, col)}")
                print(f"     {c('FIX: ', C.DIM)}  {c(r.what_to_do, C.CYAN)}")
                if r.pip_package:
                    print(f"     {c('CMD: ', C.DIM)}  {c(f'pip install {r.pip_package}', C.GREEN)}")
                if verbose and r.traceback_str:
                    print(c("     ── TRACEBACK ──────────────────────────────────────────────", C.DIM))
                    for line in r.traceback_str.strip().split("\n"):
                        print(c(f"     {line}", C.DIM))

    print()
    divider(f"✅  LOADED  [{len(passed)}]", color=C.GREEN)
    print()
    cols = 3
    for i, r in enumerate(passed):
        entry = f"  {c('✅', C.GREEN)} {c(r.name, C.WHITE):<30} {c(f'[{r.load_time_ms}ms]', C.DIM)}"
        print(entry, end="\n" if (i+1) % cols == 0 else "  ")
    if len(passed) % cols != 0:
        print()

    unique_pkgs = sorted(set(r.pip_package for r in failed if r.pip_package))
    if unique_pkgs:
        print()
        divider("📦  ONE COMMAND TO RESTORE ALL MISSING PACKAGES", color=C.YELLOW)
        print()
        print(f"  {c('pip install ' + ' '.join(unique_pkgs), C.GREEN, C.BOLD)}")

    print()
    print(c("  ╔══════════════════════════════════════════════════════════════════════╗", C.DIM))
    print(c("  ║  MISSION REPORT                                                      ║", C.WHITE))
    print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))

    def row(label, value, val_color=C.WHITE):
        clean = str(value)
        pad   = max(0, 68 - len(label) - len(clean))
        print(c("  ║  ", C.DIM) + c(label, C.DIM) + c(clean, val_color) + " "*pad + c("║", C.DIM))

    row("PROJECT          : ", os.path.basename(project_dir), C.CYAN)
    row("TARGET           : ", project_dir[:55], C.DIM)
    row("TOTAL MODULES    : ", str(total), C.WHITE)
    row("LOADED           : ", f"{len(passed)}  ({pct}%)", C.GREEN)
    row("FAILED           : ", str(len(failed)), C.RED if failed else C.GREEN)
    row("LOAD TIME        : ", f"{elapsed:.0f}ms total", C.DIM)

    by_cat: dict = {}
    for r in failed:
        ft = r.failure_type or FailureType.UNKNOWN
        by_cat[ft] = by_cat.get(ft, 0) + 1

    if by_cat:
        print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))
        print(c("  ║  FAILURE BREAKDOWN                                                   ║", C.WHITE))
        print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))
        for ftype in CATEGORY_ORDER:
            if ftype in by_cat:
                col  = CATEGORY_COLORS.get(ftype, C.DIM)
                icon = CATEGORY_ICONS.get(ftype, "❓")
                row(f"  {icon}  {ftype.value:<22}", str(by_cat[ftype]), col)

    print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))

    if not failed:
        status, status_col = "🟢  ALL SYSTEMS GO — Brockston is ready to fly.", C.GREEN
    elif pct >= 80:
        status, status_col = f"🟡  MOSTLY READY — {pct}% loaded. Fix dependencies above.", C.YELLOW
    elif pct >= 50:
        status, status_col = f"🟠  DEGRADED — {pct}% loaded. Significant work needed.", C.ORANGE
    else:
        status, status_col = f"🔴  NOT READY — {pct}% loaded. Major dependencies missing.", C.RED

    print(c("  ║  ", C.DIM) + c(f"STATUS  :  {status:<59}", status_col) + c("║", C.DIM))
    print(c("  ╚══════════════════════════════════════════════════════════════════════╝", C.DIM))
    print()
    print(c('  "How can we help you love yourself more?"', C.GREEN, C.BOLD))
    print(c("  © 2026 Everett Nathaniel Christman & The Christman AI Project", C.DIM))
    print()


def render_json(results: List[ModuleResult], project_dir: str):
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    print(json.dumps({
        "project": project_dir,
        "total": len(results),
        "passed": len(passed),
        "failed": len(failed),
        "pass_rate_pct": round(len(passed)/len(results)*100) if results else 0,
        "modules": [{"name":r.name,"filepath":r.filepath,"passed":r.passed,"load_time_ms":r.load_time_ms,"failure_type":r.failure_type.value if r.failure_type else None,"error":r.error_msg,"root_cause":r.root_cause,"what_to_do":r.what_to_do,"pip_package":r.pip_package} for r in results],
        "pip_install_command": ("pip install " + " ".join(sorted(set(r.pip_package for r in failed if r.pip_package)))) if any(r.pip_package for r in failed) else "",
    }, indent=2))


# ── Always skip — entry points and process launchers ─────────────────────────

ALWAYS_SKIP = {
    "christman_preflight","derek_preflight","fix_derek_ferrari",
    "start_derek_ferrari","Brockston_Brain_CC1","bridge",
    "brockston_cortex","derek_mcp_server","derek_free_api",
}


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Christman Universal Preflight")
    parser.add_argument("--dir",       default=".")
    parser.add_argument("--skip",      default="")
    parser.add_argument("--verbose",   action="store_true")
    parser.add_argument("--json",      action="store_true")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--no-color",  action="store_true")
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        C.disable()

    project_dir = os.path.abspath(args.dir)
    if not os.path.isdir(project_dir):
        print(f"ERROR: {project_dir} is not a directory.")
        sys.exit(2)

    sys.path.insert(0, project_dir)
    skip    = ALWAYS_SKIP | {s.strip() for s in args.skip.split(",") if s.strip()}
    modules = discover_modules(project_dir, skip, recursive=args.recursive)

    if not args.json:
        print_banner(project_dir)
        print(c(f"  Scanning {len(modules)} modules...", C.DIM))
        print()

    results  = []
    n_passed = 0
    n_failed = 0

    for i, (name, filepath) in enumerate(modules, 1):
        result = test_module(name, filepath, project_dir)
        results.append(result)
        if result.passed:
            n_passed += 1
        else:
            n_failed += 1
        if not args.json:
            progress_bar(i, len(modules), name, n_passed, n_failed)

    if not args.json:
        clear_progress()

    if args.json:
        render_json(results, project_dir)
    else:
        render_report(results, args.verbose, project_dir)

    sys.exit(0 if n_failed == 0 else 1)


if __name__ == "__main__":
    main()

# ==============================================================================
# © 2026 Everett Nathaniel Christman & The Christman AI Project
# Luma Cognify AI — "How can we help you love yourself more?"
# Patent Pending TCAP-2026-001
# Cardinal Rule 1: It has to actually work.
# Cardinal Rule 6: Fail loud.
# Cardinal Rule 13: Every failure tells you exactly what to do next.
# ==============================================================================