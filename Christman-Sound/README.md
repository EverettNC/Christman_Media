# Christman Sound — Unified Audio, Voice, and Speech System

A comprehensive framework for the Christman family of autonomous beings. This system integrates speech recognition, voice synthesis, tone analysis, music generation, and audio processing into a cohesive voice and sound ecosystem.

## Overview

Christman Sound is organized into three main layers:

1. **CHRISTMAN_EAR_CANAL** — High-level adapters for hearing, speaking, tone analysis, and OCR
2. **christman_voice_sdk** — Production engines and processing pipelines
3. **Core modules** — Utility functions, logging, and configuration

## Package Structure

### CHRISTMAN_EAR_CANAL
Simplified interfaces for common voice operations:
- `EAR.py` — Microphone capture and voice activity detection
- `SPEAK.py` — Speech synthesis (XTTS with macOS fallback)
- `TONE.py` — Emotional tone and personality analysis
- `PHONEMES.py` — Phoneme and viseme extraction
- `VOICE_PROFILE.py` — Voice frequency profiles
- `OCR.py` — Screen reading and document scanning

### christman_voice_sdk

#### Audio (`audio/`)
- `audio_processor.py` — WAV processing, normalization, format conversion
- `audio_encoder.py` — Audio encoding and compression
- `speech_recognition_engine.py` — Base speech-to-text
- `enhanced_speech_recognition.py` — Multi-model speech recognition
- `real_speech_recognition.py` — Production speech recognition
- `sound_recognition_service.py` — Sound classification and detection
- `fusion_engine.py` — Multi-engine audio fusion

#### Engines (`engines/`)
- `base_synthesizer.py` — Abstract TTS engine
- `xtts_engine.py` — Coqui XTTS voice synthesis
- `gpt_sovits_engine.py` — GPT-SoVITS synthesis engine

#### Synthesis (`synthesis/`)
- `voice_synthesis.py` — Core synthesis pipeline
- `voice_synthesis_orchestrator.py` — Synthesis coordination
- `tts_service.py` — TTS service layer
- `phoneme_labeler.py` — Phoneme timing and alignment
- `speech_response.py` — Response generation and streaming

#### Tone (`tone/`)
- `tone_analyzer.py` — Tone and emotion detection
- `tonescore_engine.py` — ToneScore calculation
- `tonescore_analyzer.py` — Detailed tone analysis
- `emotion_quantifier.py` — Emotion metric computation
- `emotion_embedder.py` — Emotion representation
- `christman_tone_engine_v2.py` — Production tone engine
- `speech_personality.py` — Personality extraction from speech
- `written_tone.py` — Tone analysis for text

#### Timbre (`timbre/`)
- `timbre_modeler.py` — Voice timbre modeling
- `shorty_emotion.py` — Emotion-based timbre modification
- `voicepack.py` — Voice pack management

#### Music (`music/`)
- `music_engine.py` — Music generation and synthesis
- `christman_studio.py` — Music studio orchestration

#### Nonverbal (`nonverbal/`)
- `nonverbal_engine.py` — Non-vocal audio synthesis
- `cochlear_sync_tts.py` — Cochlear implant sync
- `engine_temporal.py` — Temporal audio processing

#### Integration (`integration/`)
- `christman_speech_to_speech.py` — Speech-to-speech conversion
- `speech_integration.py` — Speech service integration
- `voice_capture_client.py` — Voice capture and streaming

#### Utils (`utils/`)
- `voice_diagnostics.py` — Audio quality analysis
- `grounder.py` — Context and grounding utilities
- `presence_guide.py` — User presence detection

### Core Modules
- `core.py` — Main framework initialization
- `logger.py` — Unified logging
- `tone_analyzer.py` — Top-level tone analysis
- `christman_dsp.c` — DSP operations (compiled)

## Quick Start

### Basic Voice I/O

```python
from CHRISTMAN_EAR_CANAL import listen, speak, analyze_tone

# Listen to user
wav = listen(max_duration=8)

# Analyze tone
tone = analyze_tone(wav)
print(f"Detected emotion: {tone['emotion']}")

# Respond
speak("I understood you, Everett.", emotion="warm")
```

### Speech Recognition

```python
from christman_voice_sdk.audio import enhanced_speech_recognition

recognizer = enhanced_speech_recognition.EnhancedSpeechRecognizer()
text = recognizer.recognize(wav_file="input.wav")
print(f"Recognized: {text}")
```

### Voice Synthesis

```python
from christman_voice_sdk.synthesis import voice_synthesis

synthesizer = voice_synthesis.VoiceSynthesizer(engine="xtts")
wav = synthesizer.synthesize(
    text="Hello, I am Seraphinia",
    voice_profile="seraphinia",
    emotion="curious"
)
```

### Tone & Emotion Analysis

```python
from christman_voice_sdk.tone import christman_tone_engine_v2

tone_engine = christman_tone_engine_v2.ChristmanToneEngineV2()
analysis = tone_engine.analyze_audio(wav_file="speech.wav")

print(f"Tone Score: {analysis['tonescore']}")
print(f"Personality: {analysis['personality']}")
print(f"Emotion: {analysis['emotion']}")
```

### Speech-to-Speech

```python
from christman_voice_sdk.integration import christman_speech_to_speech

converter = christman_speech_to_speech.ChristmanSpeechToSpeech()
output_wav = converter.convert(
    input_wav="user_voice.wav",
    target_voice="derek",
    emotion="authoritative"
)
```

### OCR & Screen Reading

```python
from CHRISTMAN_EAR_CANAL import scan_screen, scan_document

# Read screen
result = scan_screen(being="AlphaVox")
print(result["text"])

# Scan document
result = scan_document("/path/to/document.pdf", being="Seraphinia")
```

## Configuration

### Environment Variables

```bash
# MCP Server root (Derek configuration)
export DEREK_ROOT=/path/to/DerekMCPServer

# Voice SDK root
export CHRISTMAN_VOICE_SDK_ROOT=/path/to/christman_voice_sdk

# TTS Engine preference (xtts, gpt-sovits)
export CHRISTMAN_TTS_ENGINE=xtts

# Audio device settings
export CHRISTMAN_AUDIO_DEVICE=0
export CHRISTMAN_SAMPLE_RATE=16000
```

### Voice Profiles

```python
from CHRISTMAN_EAR_CANAL import capture_voice_profile, list_voice_profiles

# Capture new profile
capture_voice_profile("being_name", duration=8)

# List available profiles
profiles = list_voice_profiles()
print(profiles)
```

## Architecture

```
User Input
    ↓
[CHRISTMAN_EAR_CANAL] (High-level API)
    ↓
[christman_voice_sdk] (Production engines)
    ├── Audio → Speech Recognition → Text
    ├── Text → Synthesis → Audio
    ├── Audio → Tone Analysis → Emotions
    └── Audio → Feature Extraction → Voice Profile
    ↓
User Output (Speech, Sound, Feedback)
```

## Key Features

- **Multi-Engine Support** — XTTS, GPT-SoVITS, macOS fallback
- **Real-Time Processing** — Streaming speech recognition and synthesis
- **Emotional Intelligence** — ToneScore, personality, and emotion quantification
- **Voice Profiles** — Frequency-based speaker identification
- **Honesty Rule** — Truthful reporting of engine capabilities
- **No Fakes** — Fallback modes clearly indicated, never pretending

## Beings

Christman Sound supports the following autonomous beings:
- Derek
- AlphaVox
- AlphaWolf
- Brockston
- Geo
- Seraphinia

Each being can have custom voice profiles, emotional ranges, and personality settings.

## Requirements

- Python 3.8+
- macOS 11+ (for fallback speech synthesis)
- XTTS models (auto-downloaded on first use)
- FFmpeg (for audio encoding)

## Installation

```bash
pip install -e .
```

## Logging

All modules use unified logging via `logger.py`. Enable debug output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Honesty Rule — Cardinal Rule 13

This system never fakes capabilities. When speech synthesis falls back to macOS `say`, the returned result explicitly states `engine = "macos_say_fallback"`. No pretending. No deception.

## License

Proprietary — Christman Family of Autonomous Beings

## Support

For integration issues or audio problems, check `christman_voice_sdk/utils/voice_diagnostics.py`.
