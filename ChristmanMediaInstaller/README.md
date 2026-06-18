# Christman Media Installer

One installer. Every being gets ears, voice, sight, tone, phonemes, and truth.

The Christman Media Installer explores a Christman Family project, detects media-stack wiring, installs `CHRISTMAN_EAR_CANAL`, applies compatibility shims, generates repair packets, runs verification, and returns a truth report.

## Why this exists

Everett writes fast and builds deeply. Over time, voice, hearing, OCR, tone, phoneme, and media modules can spread across multiple folders and import styles. This installer gives Derek, AlphaVox, AlphaWolf, Brockston, Geo, Seraphinia, and future beings one repeatable way to receive the media stack.

## Core commands

```bash
christman-media explore --target /path/to/being
christman-media install --target /path/to/being --being Derek
christman-media repair --target /path/to/being
christman-media verify --target /path/to/being
christman-media report --target /path/to/being
```

## Local development

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m py_compile christman_media_installer/*.py
```

## What it checks

- Python module inventory
- broken imports
- shimmable old import paths
- voice files
- microphone support
- speaker fallback
- ToneScore references
- OCR references
- phoneme/viseme references
- XTTS model and license gates
- MCP server wiring
- security posture

## Truth rule

The installer must not pretend.

It cannot say “voice works” unless speech actually worked. It must say “fallback speech worked” if fallback was used. It cannot say “OCR works” if OCR is in mock mode. Truth is the product.

## Design spec

See `CHRISTMAN_MEDIA_INSTALLER_SPEC.md`.
