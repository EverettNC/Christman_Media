"""
Christman Media Installer — cli.py
The Christman AI Project / Luma Cognify AI
Owner: Everett Nathaniel Christman

Command-line entry point.

Commands:
  explore   Walk a target project and inventory what's there
  install   Install the full media stack for a being
  repair    Apply shims and repair packets to a broken project
  verify    Run smoke tests, mic/speaker tests, preflight, tracer
  report    Generate the full truth report

Usage:
  christman-media install --target /path/to/being --being Derek
  christman-media explore --target /path/to/being
  christman-media repair  --target /path/to/being
  christman-media verify  --target /path/to/being
  christman-media report  --target /path/to/being [--being Derek]
"""

import argparse
import logging
import sys
from pathlib import Path

from .constants import INSTALLER_NAME, INSTALLER_VERSION
from .targets import get_profile, list_beings
from .explorer import Explorer
from .detector import Detector
from .shim_engine import ShimEngine
from .repair_packet import RepairPacketBuilder, save_packet
from .installer import Installer
from .verifier import Verifier
from .security import SecurityChecker
from .truth_report import TruthReport


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def _print_banner() -> None:
    print(f"\n{'═' * 60}")
    print(f"  {INSTALLER_NAME}  v{INSTALLER_VERSION}")
    print(f"  The Christman AI Project / Luma Cognify AI")
    print(f"  Truth is the product.")
    print(f"{'═' * 60}\n")


# ──────────────────────────────────────────────
# COMMAND: explore
# ──────────────────────────────────────────────
def cmd_explore(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose)
    _print_banner()
    print(f"🔍 EXPLORING: {args.target}\n")

    try:
        explorer = Explorer(args.target)
        report = explorer.explore()
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"❌ {e}")
        return 1

    print(f"\n📊 EXPLORE RESULTS")
    print(f"─" * 50)
    print(f"  Python modules found:  {report.module_count}")
    print(f"  Broken imports:        {report.broken_count}")
    print(f"  Shimmable:             {report.shimmable_count}")
    print(f"  Voice files:           {len(report.voice_files)}")
    print(f"  MCP server files:      {len(report.mcp_server_files)}")
    print(f"  OCR references:        {len(report.ocr_refs)}")
    print(f"  Tone references:       {len(report.tone_refs)}")
    print(f"  Microphone refs:       {len(report.microphone_refs)}")
    print(f"  Phoneme refs:          {len(report.phoneme_refs)}")
    print(f"  XTTS refs:             {len(report.xtts_refs)}")
    print(f"  .env files:            {len(report.env_files)}")

    if report.broken_imports:
        print(f"\n  Broken imports (sample):")
        for issue in report.broken_imports[:10]:
            shim_note = f" [shim available → {issue.shim_target}]" if issue.shim_available else ""
            print(f"    {issue.file}:{issue.line} — {issue.import_name}{shim_note}")
        if report.broken_count > 10:
            print(f"    ... and {report.broken_count - 10} more")

    return 0


# ──────────────────────────────────────────────
# COMMAND: install
# ──────────────────────────────────────────────
def cmd_install(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose)
    _print_banner()

    being_name = args.being or "Unknown"
    profile = get_profile(being_name)

    if not profile:
        print(f"⚠ No registered profile for being '{being_name}'.")
        print(f"  Known beings: {', '.join(list_beings())}")
        print(f"  Proceeding with default install (no being-specific wiring).")

    print(f"🚀 INSTALLING for: {being_name}")
    print(f"   Target: {args.target}\n")

    # Explore
    try:
        explorer = Explorer(args.target)
        explore_report = explorer.explore()
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"❌ {e}")
        return 1

    # Detect
    detector = Detector(args.target, explore_report)
    detect_result = detector.detect()

    # Install
    if profile:
        installer = Installer(args.target, profile, dry_run=args.dry_run)
        installer.install()

    # Shims
    shim_engine = ShimEngine(args.target, dry_run=args.dry_run)
    shim_results = shim_engine.install_shims(explore_report)

    # Repair packet
    packet_builder = RepairPacketBuilder(being_name, args.target, detect_result)
    packet_builder.add_shim_results(shim_results)
    if profile and hasattr(installer, 'env_keys_written'):
        if installer.env_keys_written:
            packet_builder.add_env_write(".env", installer.env_keys_written)
        for tool in installer.mcp_tools_written:
            packet_builder.add_mcp_tool(tool, "mcp_server.py")
    packet = packet_builder.build()

    # Security check
    security = SecurityChecker(args.target)
    sec_report = security.check()

    # Verify
    verifier = Verifier(args.target)
    verify_report = verifier.run_all()

    # Truth report
    truth = TruthReport(
        target_path=args.target,
        being_name=being_name,
        profile=profile,
        explorer=explore_report,
        detector=detect_result,
        verifier=verify_report,
        security=sec_report,
        repair_packet=packet,
    )
    truth.print()

    # Optionally save packet
    if args.save_packet:
        save_packet(packet, args.save_packet)

    return 0


# ──────────────────────────────────────────────
# COMMAND: repair
# ──────────────────────────────────────────────
def cmd_repair(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose)
    _print_banner()

    being_name = args.being or "Unknown"
    print(f"🔧 REPAIRING: {args.target}\n")

    try:
        explorer = Explorer(args.target)
        explore_report = explorer.explore()
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"❌ {e}")
        return 1

    detector = Detector(args.target, explore_report)
    detect_result = detector.detect()

    shim_engine = ShimEngine(args.target, dry_run=args.dry_run)
    shim_results = shim_engine.install_shims(explore_report)

    packet_builder = RepairPacketBuilder(being_name, args.target, detect_result)
    packet_builder.add_shim_results(shim_results)
    packet = packet_builder.build()

    print(f"\n📦 Repair complete.")
    print(f"   Shims installed: {shim_engine.shim_count}")
    print(f"   Shims skipped:   {shim_engine.skip_count}")

    if args.save_packet:
        save_packet(packet, args.save_packet)

    hidden = shim_engine.hidden_dep_warnings()
    if hidden:
        print("\n⚠  SHIMS HIDING MISSING DEPENDENCIES:")
        for w in hidden:
            print(f"   {w}")

    return 0


# ──────────────────────────────────────────────
# COMMAND: verify
# ──────────────────────────────────────────────
def cmd_verify(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose)
    _print_banner()

    print(f"🧪 VERIFYING: {args.target}\n")

    verifier = Verifier(args.target)
    report = verifier.run_all()

    print(f"\n📊 VERIFICATION RESULTS")
    print(f"─" * 50)
    for result in report.results:
        icon = "✅" if result.passed else ("❌" if result.critical else "⚠")
        print(f"  {icon} [{result.name}] {result.message.split(chr(10))[0]}")

    print()
    print(f"  Passed: {report.pass_count}  Failed: {report.fail_count}")

    if report.blockers:
        print("\n  ❌ BLOCKERS (must be resolved before READY):")
        for b in report.blockers:
            print(f"    {b}")

    return 0 if report.all_critical_pass else 1


# ──────────────────────────────────────────────
# COMMAND: report
# ──────────────────────────────────────────────
def cmd_report(args: argparse.Namespace) -> int:
    _configure_logging(args.verbose)
    _print_banner()

    being_name = args.being or "Unknown"
    profile = get_profile(being_name)

    try:
        explorer = Explorer(args.target)
        explore_report = explorer.explore()
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"❌ {e}")
        return 1

    detector = Detector(args.target, explore_report)
    detect_result = detector.detect()

    security = SecurityChecker(args.target)
    sec_report = security.check()

    verifier = Verifier(args.target)
    verify_report = verifier.run_all()

    truth = TruthReport(
        target_path=args.target,
        being_name=being_name,
        profile=profile,
        explorer=explore_report,
        detector=detect_result,
        verifier=verify_report,
        security=sec_report,
    )
    truth.print()

    if args.save:
        truth.save(args.save)

    return 0


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        prog="christman-media",
        description=f"{INSTALLER_NAME} — Truth is the product.",
    )
    parser.add_argument("--version", action="version", version=INSTALLER_VERSION)

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shared arguments
    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--target", required=True, help="Path to target being project directory")
        p.add_argument("--being", default=None, help=f"Being name. Known: {', '.join(list_beings())}")
        p.add_argument("--verbose", action="store_true", help="Enable verbose logging")
        p.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")

    # explore
    p_explore = subparsers.add_parser("explore", help="Walk target and inventory what's there")
    add_common(p_explore)
    p_explore.set_defaults(func=cmd_explore)

    # install
    p_install = subparsers.add_parser("install", help="Install full media stack for a being")
    add_common(p_install)
    p_install.add_argument("--save-packet", default=None, help="Path to save repair packet JSON")
    p_install.set_defaults(func=cmd_install)

    # repair
    p_repair = subparsers.add_parser("repair", help="Apply shims and repair broken imports")
    add_common(p_repair)
    p_repair.add_argument("--save-packet", default=None, help="Path to save repair packet JSON")
    p_repair.set_defaults(func=cmd_repair)

    # verify
    p_verify = subparsers.add_parser("verify", help="Run smoke tests and verifications")
    add_common(p_verify)
    p_verify.set_defaults(func=cmd_verify)

    # report
    p_report = subparsers.add_parser("report", help="Generate full truth report")
    add_common(p_report)
    p_report.add_argument("--save", default=None, help="Path to save truth report text file")
    p_report.set_defaults(func=cmd_report)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
