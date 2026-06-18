"""
Voice diagnostics module.

Provides diagnostic utilities for validating speech synthesis output,
comparing regional voice variants, and generating a structured report.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from gtts import gTTS


VOICE_REGION_PROFILES: List[Dict[str, str]] = [
    {"code": "com", "name": "US English"},
    {"code": "co.uk", "name": "UK English"},
    {"code": "com.au", "name": "Australian English"},
    {"code": "ca", "name": "Canadian English"},
    {"code": "co.in", "name": "Indian English"},
    {"code": "co.za", "name": "South African English"},
    {"code": "ie", "name": "Irish English"},
]

SPEECH_RATE_PROFILES: List[Dict[str, object]] = [
    {"name": "Slow", "slow": True},
    {"name": "Normal", "slow": False},
]


def calculate_file_hash(file_path: str) -> str:
    """Return the MD5 hash for a file."""
    md5_hasher = hashlib.md5()

    with open(file_path, "rb") as file_handle:
        while chunk := file_handle.read(8192):
            md5_hasher.update(chunk)

    return md5_hasher.hexdigest()


def generate_voice_diagnostic_report(
    text: str = "This is a test of the voice system",
    language: str = "en",
    output_directory: str | None = None,
) -> List[Dict[str, object]]:
    """Generate diagnostic audio samples and a comparison report."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    diagnostic_directory = Path(output_directory or f"voice_test_{timestamp}")
    diagnostic_directory.mkdir(parents=True, exist_ok=True)

    report_path = diagnostic_directory / "voice_report.txt"
    diagnostic_results: List[Dict[str, object]] = []

    with report_path.open("w", encoding="utf-8") as report_file:
        report_file.write("Voice System Diagnostic Report\n")
        report_file.write("================================\n\n")
        report_file.write(
            f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        report_file.write(f"Test Text: '{text}'\n")
        report_file.write(f"Language: {language}\n\n")

        for region_profile in VOICE_REGION_PROFILES:
            for speed_profile in SPEECH_RATE_PROFILES:
                region_code = region_profile["code"]
                region_name = region_profile["name"]
                speed_name = str(speed_profile["name"])
                slow_mode = bool(speed_profile["slow"])

                safe_region_code = region_code.replace(".", "_")
                safe_speed_name = speed_name.lower()
                file_name = f"{safe_region_code}_{safe_speed_name}.mp3"
                file_path = diagnostic_directory / file_name

                tts = gTTS(
                    text=text,
                    lang=language,
                    slow=slow_mode,
                    tld=region_code,
                )
                tts.save(str(file_path))

                file_size = file_path.stat().st_size
                file_hash = calculate_file_hash(str(file_path))

                result = {
                    "tld": region_code,
                    "region": region_name,
                    "speed": speed_name,
                    "filename": file_name,
                    "file_size": file_size,
                    "md5": file_hash,
                }
                diagnostic_results.append(result)

                report_file.write(
                    f"Configuration: {region_name} ({region_code}), "
                    f"Speed: {speed_name}\n"
                )
                report_file.write(f"  Filename: {file_name}\n")
                report_file.write(f"  File Size: {file_size} bytes\n")
                report_file.write(f"  MD5 Hash: {file_hash}\n\n")

        unique_hashes = {result["md5"] for result in diagnostic_results}
        report_file.write("Uniqueness Analysis\n")
        report_file.write("-------------------\n")
        report_file.write(f"Total Configurations: {len(diagnostic_results)}\n")
        report_file.write(f"Unique Outputs: {len(unique_hashes)}\n\n")

        if len(unique_hashes) < len(diagnostic_results):
            report_file.write("Identical Output Groups\n")
            report_file.write("-----------------------\n")

            grouped_results: Dict[str, List[str]] = {}
            for result in diagnostic_results:
                grouped_results.setdefault(result["md5"], []).append(
                    f"{result['region']} ({result['tld']}), Speed: {result['speed']}"
                )

            group_number = 1
            for matching_hash, configurations in grouped_results.items():
                if len(configurations) > 1:
                    report_file.write(f"Group {group_number}:\n")
                    report_file.write(f"  Hash: {matching_hash}\n")
                    for configuration in configurations:
                        report_file.write(f"  - {configuration}\n")
                    report_file.write("\n")
                    group_number += 1

    print(f"Voice diagnostic complete. Report saved to {report_path}")
    return diagnostic_results


if __name__ == "__main__":
    generate_voice_diagnostic_report()


# ==============================================================================
# Patent Pending
# Christman-AI Family
# Shared-neutral implementation for internal system use.
# ==============================================================================
