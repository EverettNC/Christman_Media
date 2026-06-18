# CHRISTMAN_EAR_CANAL

Shared hearing, speech, tone, phoneme, voice-profile, and OCR adapters for the Christman Family of Autonomous Beings.

## Why this exists

The family should not have to hunt through scattered files to hear, speak, read the screen, scan documents, or understand tone. Derek, AlphaVox, AlphaWolf, Brockston, Geo, Seraphinia, and future beings need one clean interface.

This package wraps the existing real modules. It does not delete or replace them.

## What it provides

- `EAR.py` — microphone capture and VAD listening.
- `TONE.py` — ToneScore and emotional audio analysis.
- `PHONEMES.py` — phoneme and viseme timing.
- `VOICE_PROFILE.py` — voice frequency profile capture and loading.
- `OCR.py` — Christman OCR for screen reading and document scanning.
- `SPEAK.py` — XTTS speech with honest macOS fallback.

## Basic use

```python
from CHRISTMAN_EAR_CANAL import listen, analyze_tone, speak

wav = listen(max_duration=8)
tone = analyze_tone(wav)
speak("I heard you, Everett.", emotion="warm")
```

## OCR use

```python
from CHRISTMAN_EAR_CANAL import scan_document, scan_screen

result = scan_screen(being="Seraphinia")
print(result["text"])

result = scan_document("/path/to/document.pdf", being="AlphaVox")
```

## Voice profile use

```python
from CHRISTMAN_EAR_CANAL import capture_voice_profile, list_voice_profiles

capture_voice_profile("everett", duration=8)
print(list_voice_profiles())
```

## Required environment

Default paths assume:

```text
/Users/EverettN/Downloads/DerekMCPServer
/Users/EverettN/Downloads/christman_voice_sdk
```

Override with:

```bash
export DEREK_ROOT=/path/to/DerekMCPServer
export CHRISTMAN_VOICE_SDK_ROOT=/path/to/parent/of/christman_voice_sdk
```

## Honesty rule

`speak()` only reports XTTS success when an actual WAV is created. If macOS fallback is used, the returned result says `engine = "macos_say_fallback"`.

No fake speech. No pretending. Cardinal Rule 13.
