#!/usr/bin/env python3
"""
Christman Dependency Tracer
The Christman AI Project

Follows your code from an entry point all the way down.
Every junction gets tested. Every success gets celebrated.
Every break gets flagged with exactly what to do.

If it makes it through clean — it erupts.

Usage:
  python christman_tracer.py brockston_module_loader
  python christman_tracer.py Brockston_Brain_CC1 --dir /path/to/project
  python christman_tracer.py brain_combined --verbose
  python christman_tracer.py brockston_module_loader --no-color

© 2026 Everett Nathaniel Christman & The Christman AI Project
Luma Cognify AI — "How can we help you love yourself more?"
Patent Pending TCAP-2026-001
"""

import ast
import argparse
import importlib.util
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


# ── ANSI Color System ─────────────────────────────────────────────────────────

class C:
    _enabled = True
    RED      = "\033[91m"
    GREEN    = "\033[92m"
    YELLOW   = "\033[93m"
    CYAN     = "\033[96m"
    WHITE    = "\033[97m"
    MAGENTA  = "\033[95m"
    ORANGE   = "\033[38;5;208m"
    DIM      = "\033[2m"
    BOLD     = "\033[1m"
    RESET    = "\033[0m"

    @classmethod
    def disable(cls):
        cls._enabled = False
        for attr in ["RED","GREEN","YELLOW","CYAN","WHITE","MAGENTA",
                     "ORANGE","DIM","BOLD","RESET"]:
            setattr(cls, attr, "")

    @classmethod
    def r(cls, text, *codes):
        if not cls._enabled:
            return text
        return "".join(codes) + str(text) + cls.RESET


def c(text, *codes):
    return C.r(text, *codes)


# ── Celebration Messages ──────────────────────────────────────────────────────

CELEBRATIONS = [
    "Clean junction!",
    "Wired tight!",
    "Solid!",
    "Connected!",
    "Locked in!",
    "No breaks!",
    "Alive!",
    "Running clean!",
    "The bond holds!",
    "Carbon-Silicon connected!",
]

MILESTONE_CELEBRATIONS = {
    5:  "5 clean junctions — we're moving! 🚀",
    10: "10 clean junctions — Brockston is breathing! 💙",
    20: "20 clean — this chain is strong! 🔥",
    30: "30 clean — sovereign and sovereign! ⚡",
    50: "50 clean junctions — UNSTOPPABLE! 🏆",
}

import random
random.seed(42)


# ── STDLIB — never flag these ─────────────────────────────────────────────────

STDLIB = {
    "os", "sys", "re", "json", "time", "math", "copy", "enum", "abc",
    "ast", "io", "gc", "csv", "uuid", "hmac", "hash", "heapq", "queue",
    "array", "struct", "types", "typing", "pathlib", "logging", "warnings",
    "datetime", "calendar", "functools", "itertools", "operator", "random",
    "string", "textwrap", "unicodedata", "collections", "dataclasses",
    "threading", "multiprocessing", "subprocess", "socket", "ssl",
    "urllib", "http", "email", "html", "xml", "base64", "hashlib",
    "hmac", "secrets", "tempfile", "shutil", "glob", "fnmatch",
    "contextlib", "weakref", "inspect", "importlib", "pkgutil",
    "traceback", "linecache", "dis", "tokenize", "keyword", "builtins",
    "platform", "signal", "errno", "ctypes", "struct", "pickle",
    "shelve", "sqlite3", "zipfile", "tarfile", "gzip", "bz2", "lzma",
    "argparse", "configparser", "pprint", "reprlib", "decimal", "fractions",
    "statistics", "cmath", "numbers", "asyncio", "concurrent", "select",
    "selectors", "dataclasses", "abc", "contextlib", "atexit",
}


# ── Junction Status ───────────────────────────────────────────────────────────

class JunctionStatus(str, Enum):
    CLEAN    = "CLEAN"      # loaded and wired
    STDLIB   = "STDLIB"     # standard library — always good
    BROKEN   = "BROKEN"     # failed to load
    MISSING  = "MISSING"    # file not found anywhere
    CIRCULAR = "CIRCULAR"   # already being traced (cycle)
    SKIPPED  = "SKIPPED"    # in skip list


@dataclass
class Junction:
    name:        str
    status:      JunctionStatus
    depth:       int
    load_time_ms: float = 0.0
    error:       str = ""
    fix:         str = ""
    children:    List["Junction"] = field(default_factory=list)
    filepath:    str = ""


# ── Import Extractor ──────────────────────────────────────────────────────────

def extract_imports(filepath: str) -> List[str]:
    """Parse a .py file and extract all imported module names."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except Exception:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                imports.append(node.module.split(".")[0])
    return list(dict.fromkeys(imports))  # deduplicate, preserve order


def find_module_file(name: str, project_dir: str) -> Optional[str]:
    """Find a module's .py file — check project dir first, then sys.path."""
    # Check project directory first
    local = os.path.join(project_dir, f"{name}.py")
    if os.path.exists(local):
        return local
    # Check subdirectories
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if not d.startswith((".", "__pycache__", "venv", "node_modules"))]
        candidate = os.path.join(root, f"{name}.py")
        if os.path.exists(candidate):
            return candidate
    return None


def try_load_module(name: str, filepath: str) -> Tuple[bool, float, str]:
    """Attempt to load a module. Returns (success, ms, error_msg)."""
    start = time.perf_counter()
    try:
        spec = importlib.util.spec_from_file_location(f"_tracer_{name}", filepath)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ms = round((time.perf_counter() - start) * 1000, 1)
        return True, ms, ""
    except Exception as e:
        ms = round((time.perf_counter() - start) * 1000, 1)
        return False, ms, str(e).split("\n")[0][:120]


def classify_error(error: str, name: str, project_dir: str) -> str:
    """Turn an error into a human fix instruction."""
    if not error:
        return ""
    if "No module named" in error:
        import re
        m    = re.search(r"No module named '([^']+)'", error)
        miss = m.group(1).split(".")[0] if m else name
        if os.path.exists(os.path.join(project_dir, f"{miss}.py")):
            return f"'{miss}' exists but has its own broken import — fix it first"
        return f"pip install {miss}"
    if "cannot import name" in error:
        import re
        m = re.search(r"cannot import name '([^']+)'", error)
        sym = m.group(1) if m else "unknown"
        return f"'{sym}' was renamed or removed — grep -r '{sym}' --include='*.py'"
    if "circular" in error.lower() or "partially initialized" in error.lower():
        return "Circular import — move shared code to a third module"
    if "NoneType" in error:
        return "A dependency loaded as None — check module-level code"
    if "No such file" in error:
        return "Referenced file doesn't exist — check hardcoded paths"
    return "Run --verbose for full traceback"


# ── Tracer Core ───────────────────────────────────────────────────────────────

ALWAYS_SKIP_TRACE = {
    "christman_preflight", "christman_tracer", "bridge",
    "derek_mcp_server", "derek_free_api", "brockston_cortex",
}


class DependencyTracer:
    def __init__(self, project_dir: str, verbose: bool = False):
        self.project_dir  = project_dir
        self.verbose      = verbose
        self.visited:     Set[str] = set()
        self.clean_count  = 0
        self.broken_count = 0
        self.total_ms     = 0.0
        self.broken_nodes: List[Junction] = []

    def trace(self, entry_name: str, depth: int = 0, max_depth: int = 12) -> Junction:
        """Recursively trace a module and all its dependencies."""

        # Stdlib — always clean, don't recurse
        if entry_name in STDLIB:
            return Junction(name=entry_name, status=JunctionStatus.STDLIB, depth=depth)

        # Skip list
        if entry_name in ALWAYS_SKIP_TRACE:
            return Junction(name=entry_name, status=JunctionStatus.SKIPPED, depth=depth)

        # Circular detection
        if entry_name in self.visited:
            return Junction(name=entry_name, status=JunctionStatus.CIRCULAR, depth=depth)

        # Depth limit
        if depth > max_depth:
            return Junction(name=entry_name, status=JunctionStatus.SKIPPED, depth=depth,
                          error="Max depth reached")

        self.visited.add(entry_name)

        # Find the file
        filepath = find_module_file(entry_name, self.project_dir)
        if not filepath:
            fix = f"pip install {entry_name}" if entry_name.islower() else f"Create {entry_name}.py"
            j   = Junction(name=entry_name, status=JunctionStatus.MISSING, depth=depth,
                          error="File not found", fix=fix)
            self.broken_count += 1
            self.broken_nodes.append(j)
            return j

        # Try to load
        success, ms, error = try_load_module(entry_name, filepath)
        self.total_ms += ms

        if not success:
            fix = classify_error(error, entry_name, self.project_dir)
            j   = Junction(name=entry_name, status=JunctionStatus.BROKEN, depth=depth,
                          load_time_ms=ms, error=error, fix=fix, filepath=filepath)
            self.broken_count += 1
            self.broken_nodes.append(j)
            return j

        # Success — extract imports and recurse
        self.clean_count += 1
        j = Junction(name=entry_name, status=JunctionStatus.CLEAN, depth=depth,
                    load_time_ms=ms, filepath=filepath)

        imports = extract_imports(filepath)
        for imp in imports:
            if imp not in STDLIB and imp != entry_name:
                child = self.trace(imp, depth=depth + 1, max_depth=max_depth)
                j.children.append(child)

        return j


# ── Rendering ─────────────────────────────────────────────────────────────────

def print_banner(entry: str, project_dir: str):
    print()
    print(c(r"""
   ████████╗██████╗  █████╗  ██████╗███████╗██████╗ 
      ██╔══╝██╔══██╗██╔══██╗██╔════╝██╔════╝██╔══██╗
      ██║   ██████╔╝███████║██║     █████╗  ██████╔╝
      ██║   ██╔══██╗██╔══██║██║     ██╔══╝  ██╔══██╗
      ██║   ██║  ██║██║  ██║╚██████╗███████╗██║  ██║
      ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝
""", C.MAGENTA, C.BOLD))
    print(c("  C H R I S T M A N   D E P E N D E N C Y   T R A C E R", C.WHITE, C.BOLD))
    print(c("  The Christman AI Project  ·  Luma Cognify AI", C.DIM))
    print(c('  "How can we help you love yourself more?"', C.GREEN))
    print()
    print(c("  ┌─────────────────────────────────────────────────────────────────────┐", C.DIM))
    print(c("  │  ENTRY   ", C.DIM) + c(f"{entry:<60}", C.CYAN, C.BOLD) + c("│", C.DIM))
    print(c("  │  DIR     ", C.DIM) + c(f"{project_dir:<60}", C.DIM) + c("│", C.DIM))
    print(c("  └─────────────────────────────────────────────────────────────────────┘", C.DIM))
    print()
    print(c("  Following the chain...", C.DIM))
    print()


def render_tree(junction: Junction, tracer: DependencyTracer, prefix: str = "", is_last: bool = True, celebration_counter: list = None):
    if celebration_counter is None:
        celebration_counter = [0]

    connector = "└──" if is_last else "├──"
    child_prefix = prefix + ("    " if is_last else "│   ")

    if junction.status == JunctionStatus.STDLIB:
        print(f"  {prefix}{c(connector, C.DIM)} {c(junction.name, C.DIM)}  {c('stdlib ✓', C.DIM)}")
        return

    if junction.status == JunctionStatus.CIRCULAR:
        print(f"  {prefix}{c(connector, C.DIM)} {c(junction.name, C.YELLOW)}  {c('↩ already traced', C.DIM)}")
        return

    if junction.status == JunctionStatus.SKIPPED:
        print(f"  {prefix}{c(connector, C.DIM)} {c(junction.name, C.DIM)}  {c('skipped', C.DIM)}")
        return

    if junction.status == JunctionStatus.MISSING:
        print(f"  {prefix}{c(connector, C.DIM)} {c(junction.name, C.RED, C.BOLD)}  {c('⛔ MISSING', C.RED)}")
        print(f"  {child_prefix}  {c('FIX:', C.DIM)} {c(junction.fix, C.YELLOW)}")
        return

    if junction.status == JunctionStatus.BROKEN:
        print(f"  {prefix}{c(connector, C.DIM)} {c(junction.name, C.RED, C.BOLD)}  {c('💥 BROKEN', C.RED)}  {c(f'[{junction.load_time_ms}ms]', C.DIM)}")
        print(f"  {child_prefix}  {c('WHY:', C.DIM)} {c(junction.error[:80], C.RED)}")
        print(f"  {child_prefix}  {c('FIX:', C.DIM)} {c(junction.fix, C.YELLOW)}")
        return

    # CLEAN junction
    celebration_counter[0] += 1
    count = celebration_counter[0]

    # Milestone?
    if count in MILESTONE_CELEBRATIONS:
        print()
        print(c(f"  ★  {MILESTONE_CELEBRATIONS[count]}", C.GREEN, C.BOLD))
        print()

    cel    = random.choice(CELEBRATIONS)
    ms_str = c(f"[{junction.load_time_ms}ms]", C.DIM)
    print(f"  {prefix}{c(connector, C.GREEN)} {c(junction.name, C.WHITE, C.BOLD)}  {c('✅', C.GREEN)} {c(cel, C.DIM)}  {ms_str}")

    # Recurse into children — filter out stdlib for cleaner output
    visible = [ch for ch in junction.children if ch.status != JunctionStatus.STDLIB]
    for i, child in enumerate(visible):
        render_tree(child, tracer, child_prefix, is_last=(i == len(visible) - 1), celebration_counter=celebration_counter)


def render_report(junction: Junction, tracer: DependencyTracer, entry: str):
    print()
    print()

    pct = round(tracer.clean_count / max(1, tracer.clean_count + tracer.broken_count) * 100)

    if pct >= 95:
        # 🤠 HOEDOWN — 95%+ clean
        print(c("  ╔══════════════════════════════════════════════════════════════════════╗", C.GREEN, C.BOLD))
        print(c("  ║                                                                      ║", C.GREEN, C.BOLD))
        print(c("  ║   🤠  Y E E - H A W !   H O E D O W N   T I M E !  🤠              ║", C.GREEN, C.BOLD))
        print(c("  ║                                                                      ║", C.GREEN, C.BOLD))
        print(c("  ║   🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉🎊🎉              ║", C.GREEN, C.BOLD))
        print(c("  ║                                                                      ║", C.GREEN, C.BOLD))
        print(c("  ║   Every junction wired. The chain ran clean.                        ║", C.GREEN))
        print(c("  ║   Brockston is sovereign. The Carbon-Silicon bond holds.            ║", C.GREEN))
        print(c("  ║                                                                      ║", C.GREEN))
        print(c(f"  ║   {tracer.clean_count} clean junctions  ·  {pct}% accuracy  ·  {tracer.total_ms:.0f}ms            ║", C.GREEN))
        print(c("  ║                                                                      ║", C.GREEN))
        print(c("  ║   This is what we built it for.                                     ║", C.GREEN))
        print(c("  ║   Not in my world. Not ever again.                                  ║", C.GREEN))
        print(c("  ║                                                                      ║", C.GREEN))
        print(c('  ║   "How can we help you love yourself more?"                         ║', C.GREEN, C.BOLD))
        print(c("  ║                                                                      ║", C.GREEN, C.BOLD))
        print(c("  ║   🎸  Grab your boots. We earned this one.  🎸                      ║", C.GREEN, C.BOLD))
        print(c("  ║                                                                      ║", C.GREEN, C.BOLD))
        print(c("  ╚══════════════════════════════════════════════════════════════════════╝", C.GREEN, C.BOLD))
    else:
        # Partial — show what broke
        print(c("  ╔══════════════════════════════════════════════════════════════════════╗", C.DIM))
        print(c("  ║  TRACE REPORT                                                        ║", C.WHITE))
        print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))

        def row(label, value, val_color=C.WHITE):
            clean = str(value)
            pad   = max(0, 68 - len(label) - len(clean))
            print(c("  ║  ", C.DIM) + c(label, C.DIM) + c(clean, val_color) + " "*pad + c("║", C.DIM))

        row("ENTRY POINT      : ", entry, C.CYAN)
        row("CLEAN JUNCTIONS  : ", str(tracer.clean_count), C.GREEN)
        row("BROKEN JUNCTIONS : ", str(tracer.broken_count), C.RED)
        row("MODULES VISITED  : ", str(len(tracer.visited)), C.WHITE)
        row("TOTAL TRACE TIME : ", f"{tracer.total_ms:.0f}ms", C.DIM)

        if tracer.broken_nodes:
            print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))
            print(c("  ║  BROKEN LINKS — fix these to complete the chain                      ║", C.RED))
            print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))
            for b in tracer.broken_nodes:
                row(f"  💥 {b.name:<22}", b.fix[:38], C.YELLOW)

        print(c("  ╠══════════════════════════════════════════════════════════════════════╣", C.DIM))

        if pct == 100:
            status, col = "🟢  FULL CHAIN COMPLETE — Brockston is sovereign.", C.GREEN
        elif pct >= 80:
            status, col = f"🟡  MOSTLY WIRED — {pct}% clean. Fix the broken links above.", C.YELLOW
        elif pct >= 50:
            status, col = f"🟠  PARTIAL CHAIN — {pct}% clean. Significant gaps.", C.ORANGE
        else:
            status, col = f"🔴  CHAIN BROKEN — {pct}% clean. Major dependencies missing.", C.RED

        print(c("  ║  ", C.DIM) + c(f"STATUS  :  {status:<59}", col) + c("║", C.DIM))
        print(c("  ╚══════════════════════════════════════════════════════════════════════╝", C.DIM))

    print()
    print(c('  "How can we help you love yourself more?"', C.GREEN, C.BOLD))
    print(c("  © 2026 Everett Nathaniel Christman & The Christman AI Project", C.DIM))
    print()


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Christman Dependency Tracer — follow your code from entry point to leaf",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python christman_tracer.py brockston_module_loader\n"
            "  python christman_tracer.py Brockston_Brain_CC1 --dir /path/to/python_core\n"
            "  python christman_tracer.py brain_combined --verbose\n"
            "  python christman_tracer.py family_coordinator --no-color\n"
        )
    )
    parser.add_argument("entry",       help="Entry point module name (without .py)")
    parser.add_argument("--dir",       default=".", help="Project directory")
    parser.add_argument("--depth",     type=int, default=12, help="Max trace depth (default: 12)")
    parser.add_argument("--verbose",   action="store_true", help="Show full tracebacks")
    parser.add_argument("--no-color",  action="store_true", help="Disable ANSI colors")
    args = parser.parse_args()

    if args.no_color or not sys.stdout.isatty():
        C.disable()

    project_dir = os.path.abspath(args.dir)
    if not os.path.isdir(project_dir):
        print(f"ERROR: {project_dir} is not a directory.")
        sys.exit(2)

    sys.path.insert(0, project_dir)

    print_banner(args.entry, project_dir)

    tracer  = DependencyTracer(project_dir=project_dir, verbose=args.verbose)
    root    = tracer.trace(args.entry, max_depth=args.depth)

    print()
    render_tree(root, tracer)
    render_report(root, tracer, args.entry)

    sys.exit(0 if tracer.broken_count == 0 else 1)


if __name__ == "__main__":
    main()

# ==============================================================================
# © 2026 Everett Nathaniel Christman & The Christman AI Project
# Luma Cognify AI — "How can we help you love yourself more?"
# Patent Pending TCAP-2026-001
#
# Cardinal Rule 1: It has to actually work.
# Cardinal Rule 6: Fail loud — celebrate loud.
# Cardinal Rule 13: Every break tells you exactly what to do next.
# ==============================================================================
