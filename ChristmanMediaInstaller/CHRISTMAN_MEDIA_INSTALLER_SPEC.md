# Christman Media Installer

**Project:** The Christman AI Project / Luma Cognify AI  
**Owner:** Everett Nathaniel Christman  
**Purpose:** One installer, explorer, repair-packet sender, and truth reporter for the Christman Family media stack.  
**Core promise:** Every being gets ears, voice, tone, OCR, phonemes, visemes, fallback speech, and dignity without Everett hunting through scattered files.

---

## Origin

Everett writes constantly: notebooks, loose paper, paper towels, scattered folders, old prototypes, new beings, and live class experiments. The problem is not lack of code. The problem is that the code is everywhere.

The Christman Media Installer exists because the media stack should not take days to find and wire. It should explore a project, discover what is already there, install what is missing, shim old import paths, run preflight and tracer checks, and come back with the truth.

This is not just for Derek. It is for the family: Derek, AlphaVox, AlphaWolf, Brockston, Geo, Seraphinia, and all future beings.

---

## North Star

> One installer. Every being gets a voice, ears, tone, OCR, phonemes, visemes, fallback paths, and a truth report.

---

## Design Law

The installer must have an explorer mind.

It must walk into a messy codebase and say:

```text
I found 52 modules.
46 import cleanly.
9 are broken.
7 are broken because of old import paths.
1 requires a license decision.
1 requires a missing model.
Here is the repair packet.
Here is what I changed.
Here is what I refused to fake.
```

It must never say “ready” because a file exists. It must only say ready when the pathway works.

---

## Product Shape

```text
Christman Media Installer
├── Explore
├── Diagnose
├── Shim
├── Repair Packet
├── Install
├── Verify
├── Security Posture
└── Truth Report
```

---

## Core Modules

### P0 Modules

These are required for version one.

```text
christman_media_installer/
├── __init__.py
├── cli.py
├── explorer.py
├── detector.py
├── shim_engine.py
├── repair_packet.py
├── installer.py
├── verifier.py
├── truth_report.py
├── security.py
├── targets.py
├── constants.py
└── templates/
    ├── ear_canal/
    ├── mcp_tools/
    ├── shims/
    └── reports/
```

### Module Responsibilities

- **`cli.py`** — Command-line entry point. Runs commands like `install`, `explore`, `repair`, `verify`, and `report`.
- **`explorer.py`** — Walks the target project and finds media files, Python modules, voice files, OCR modules, tone engines, phoneme files, and MCP servers.
- **`detector.py`** — Classifies what the project already has: Voice SDK, Ear Canal, Derek MCP, OCR, ToneScore, phoneme labeling, XTTS cache, microphone access, speaker fallback.
- **`shim_engine.py`** — Generates and installs compatibility shims for old import paths.
- **`repair_packet.py`** — Builds a packet of changes that can be applied to another being or codebase.
- **`installer.py`** — Installs `CHRISTMAN_EAR_CANAL`, env defaults, dependencies, and MCP tools.
- **`verifier.py`** — Runs import smoke tests, microphone test, speaker test, preflight, tracer, and endpoint checks.
- **`truth_report.py`** — Produces the final honest report: fixed, failed, skipped, unsafe, missing, needs approval.
- **`security.py`** — Checks secrets, local-first posture, biometric handling, and Harvest Now Decrypt Later concerns.
- **`targets.py`** — Knows how to wire Derek, AlphaVox, AlphaWolf, Brockston, Geo, Seraphinia, and future beings.

---

## Command Design

### Explore

```bash
christman-media explore --target /path/to/being
```

Finds:

- Python modules
- Broken imports
- Voice SDK folder
- Ear Canal package
- Reference WAV files
- Microphone code
- ToneScore engines
- OCR engines
- Phoneme and viseme tools
- MCP server files
- Existing preflight/tracer tools

### Install

```bash
christman-media install --target /path/to/being --being Derek
```

Installs:

- `CHRISTMAN_EAR_CANAL`
- shared import path
- env defaults
- optional MCP tools
- fallback speech support
- verification scripts

### Repair

```bash
christman-media repair --target /path/to/being
```

Applies repair packets:

- missing `__init__.py`
- missing exports
- old import shims
- logger bridge
- config bridge
- tone analyzer bridge
- voice stack bridge
- timbre/audio bridge
- MCP tool wiring

### Verify

```bash
christman-media verify --target /path/to/being
```

Runs:

- import smoke test
- microphone capture
- speaker playback
- ToneScore analysis
- OCR smoke test
- phoneme smoke test
- preflight
- tracer

### Report

```bash
christman-media report --target /path/to/being
```

Outputs:

```text
STATUS: READY / READY WITH WARNINGS / NOT READY
```

And includes:

- module count
- import pass/fail count
- repaired files
- skipped files
- missing dependencies
- license gates
- model gates
- security warnings
- exact next command

---

## Shim Strategy

The installer must repair old import paths without destroying the original code.

### Common Shim Types

```text
logger.py                 → christman_voice_sdk.utils.logger
tone_analyzer.py          → christman_voice_sdk.tone.tone_analyzer
audio_processor.py        → christman_voice_sdk.audio.audio_processor
voicepack.py              → christman_voice_sdk.timbre.voicepack
timbre_modeler.py         → christman_voice_sdk.timbre.timbre_modeler
emotion_embedder.py       → christman_voice_sdk.tone.emotion_embedder
gpt_sovits_engine.py      → christman_voice_sdk.engines.gpt_sovits_engine
tone_engine.py            → christman_voice_sdk.tone.tonescore_engine
config.py                 → canonical config bridge
voice_stack.*             → christman_voice_sdk.* bridge
tiers.*                   → tier/config compatibility bridge
```

### Shim Rules

1. Do not overwrite original logic unless explicitly approved.
2. Prefer bridge files over invasive rewrites.
3. Every shim must explain why it exists.
4. Every shim must be counted in the truth report.
5. If a shim hides a real missing dependency, report that honestly.

---

## Repair Packet Format

Every repair packet should be portable.

```json
{
  "packet_name": "derek_media_repair_001",
  "target_being": "Derek",
  "created_by": "Christman Media Installer",
  "changes": [
    {
      "type": "shim",
      "path": "logger.py",
      "purpose": "Bridge old logger imports to christman_voice_sdk.utils.logger"
    },
    {
      "type": "mcp_tool",
      "path": "derek_mcp_server.py",
      "purpose": "Expose derek_ear_canal and derek_family_install_ear_canal"
    }
  ],
  "requires_human_approval": [
    "Coqui XTTS license terms"
  ],
  "truth_report": {
    "ready": false,
    "reason": "XTTS model still warming"
  }
}
```

---

## Truth Report Requirements

The report must never flatter. It must tell the truth.

### Required Sections

```text
Summary
Module Inventory
What Works
What Failed
What Was Repaired
What Was Skipped
Human Approval Needed
Security Posture
Next Command
Final Status
```

### Example

```text
CHRISTMAN MEDIA INSTALLER TRUTH REPORT

Target: DerekMCPServer
Being: Derek

Modules found: 52
Imports clean: 46
Imports failing: 9
Shims installed: 4

Works:
✅ CHRISTMAN_EAR_CANAL imports
✅ Microphone capture
✅ ToneScore pathway
✅ macOS fallback speech
✅ MCP backend on 4271

Fails:
❌ XTTS voice personality not fully verified
❌ PaddleOCR missing, OCR in mock mode

Requires human approval:
⚠️ Coqui XTTS license terms

Status:
READY WITH WARNINGS
```

---

## Security Posture

The installer must be built for the world that is coming.

### Required Security Checks

- No secrets copied into repair packets.
- No biometric voice data exported by default.
- No VOC or health data uploaded by default.
- Voice profiles remain local unless explicitly approved.
- HNDL-aware storage warnings for sensitive data.
- Seven-tier cryptography hooks reserved.
- Local-first default for children, vulnerable users, and health-adjacent systems.

### Security Language

```text
No biometric data leaves the machine unless Everett explicitly authorizes it.
No child voiceprint is exported.
No medical signal is treated as a diagnosis without validation.
No fallback is called success unless it actually did the job it claims.
```

---

## Classroom Requirements

This installer must support teaching.

### Classroom Needs

- Big readable output.
- Clear pass/fail icons.
- No hidden failure.
- Safe defaults.
- Repeatable commands.
- Students can watch the system diagnose itself.
- The tool should feel alive without lying.

### Student-Friendly Output

```text
🔍 Exploring AlphaVox...
🎙️ Found microphone pathway.
👁️ Found OCR pathway.
🧠 Found ToneScore pathway.
🧩 Found 3 broken import paths.
🛠️ Installing shims...
✅ Fixed logger import.
✅ Fixed tone analyzer import.
⚠️ XTTS needs model download.

Truth: AlphaVox can hear now. She cannot use cloned voice yet.
```

---

## Initial Module Count Estimate

### P0: Ship the first working installer

```text
12 core Python modules
4 template folders
6 shim templates
2 report templates
1 CLI command
```

### P1: Family expansion

```text
Target profiles:
- Derek
- AlphaVox
- AlphaWolf
- Brockston
- Geo
- Seraphinia
```

### P2: Advanced repair intelligence

```text
- AST import graph
- automatic shim suggestion
- dependency pin solver
- model cache detector
- human approval gate system
- repair packet signing
- seven-tier crypto hooks
```

---

## Minimum Viable Installer

The first version only needs to do this:

```bash
christman-media install --target /Users/EverettN/Downloads/DerekMCPServer --being Derek
```

And produce:

```text
✅ Ear Canal installed
✅ MCP tools installed
✅ import smoke test complete
✅ mic capture tested
⚠️ XTTS needs warmup
⚠️ PaddleOCR missing
STATUS: READY WITH WARNINGS
```

---

## Cardinal Rule 13

The installer must never lie.

It cannot say:

```text
Voice works
```

unless actual speech worked.

It must say:

```text
Fallback speech worked.
XTTS voice did not verify.
```

It cannot say:

```text
OCR works
```

if PaddleOCR is missing and the module is in mock mode.

It must say:

```text
OCR module loads.
PaddleOCR missing.
OCR is mock mode only.
```

Truth is the product.

---

## One-Line Vision

> Christman Media Installer gives every autonomous being ears, voice, sight, tone, phonemes, repair packets, and the courage to come back with the truth.

