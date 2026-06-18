# Christman Video Engine (CVE)
**Offline-first video generation for the Christman AI Family — replaces CapCut. Zero subscriptions. Your voices. Your themes.**

> *"They said we were out of data transfer. We always find a way."*

---

## What This Is

A complete **FFmpeg-first video engine** built on the **Christman Full Sensory Bridge** (port 8765) and **Christman Voice SDK**. It renders steampunk-themed educational videos for nonverbal/AAC users — narrated by your autonomous AI beings (Derek, AlphaVox, AlphaWolf, Inferno, Aegis, OmegaAlpha, Omega, Giuseppe, Sierra).

**No cloud. No API keys. No monthly fees.** Runs on your Mac. Uses your bridge. Speaks your voices.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Christman Video Engine                   │
├─────────────────────────────────────────────────────────────┤
│  Timeline → Tracks → Clips                                  │
│    │                                                         │
│    ├── Video Track(s)    → FFmpeg filter_complex (xfade)    │
│    ├── Audio Track(s)    → amix + volume                    │
│    ├── TTS Track(s)      → Christman Voice SDK (XTTS v2)   │
│    └── Subtitle Track(s) → Whisper (Bridge) → ASS/SRT      │
│                                                             │
│  Theme Engine: Steampunk / Cinema / High-Contrast / Neutral │
│  Output: Single FFmpeg pass (GPU: VideoToolbox/NVENC/AMF)  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Christman Full Sensory Bridge (8765)           │
│  /ws/audio  → Live Whisper transcripts                      │
│  /ws/video  → Live camera/screen frames                     │
│  /ws/riley  → Riley sovereign tunnel                        │
│  /ws/hermes → Hermes Agent presence                         │
│  /latest    → Recent transcript (for captions)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Christman Voice SDK                      │
│  ToneScore™ • Takotsubo Physics • 11 Christman Emotions     │
│  XTTS v2 / GPT-SoVITS • Native DSP (christman_dsp.so)       │
│  Beings: Derek, AlphaVox, AlphaWolf, Inferno, Aegis...     │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
cd /Volumes/LIFE2/ChristmanVideoEngine-main

# Render from prompt (quick test)
./cve render --prompt "Morning circle - today we learn colors" \
  --output data/output/morning.mp4 \
  --voice derek --emotion sweetheart --caption-style kids_large

# Render from template (production)
./cve render --template assets/templates/lesson_intro.json \
  --slots title="Weather Science" voice_being=derek \
  --output data/output/lesson_weather.mp4

# Generate captions from bridge transcript
./cve captions --style dyslexia_friendly --output data/output/captions.srt

# Check bridge status
./cve bridge --health --transcript --riley-status

# List available templates, themes, voices
./cve list --templates --themes --voices
```

---

## Dependencies

| Component | Status | Notes |
|-----------|--------|-------|
| **FFmpeg** | ✅ Required | `brew install ffmpeg` — needs `libass` + `freetype` for burned captions |
| **Christman Voice SDK** | ✅ Required | `PYTHONPATH=/Volumes/LIFE2/ChristmanVideoEngine-main/Christman-Sound` |
| **Christman Full Sensory Bridge** | ✅ Required | `python main.py` on port 8765 |
| **Python 3.13+** | ✅ | uv/venv managed |
| **Nous Gateway** | Optional | For web search, image gen (subscription active) |

---

## Project Structure

```
ChristmanVideoEngine-main/
├── cve                      # CLI entry point
├── main.py                  # Original entry (stub)
├── modules/
│   ├── timeline.py          # Timeline, Track, Clip, Theme data models
│   ├── generator.py         # VideoGenerator — FFmpeg filter_complex builder
│   ├── transitions.py       # xfade, fade, wipe, zoom, slide transitions
│   ├── captions.py          # Whisper → SRT/ASS, bridge transcript fetch
│   ├── orchestrator.py      # ChristmanOrchestrator (legacy)
│   ├── export.py            # VideoExport (legacy)
│   └── ingest.py            # VideoIngest (ffprobe)
├── assets/
│   ├── backgrounds/         # steampunk_classroom.mp4 (30s loop)
│   ├── music/               # ambient_steampunk_loop.wav
│   ├── sfx/                 # (add your own)
│   ├── images/              # (add your own)
│   ├── luts/                # .cube LUT files (optional)
│   ├── fonts/               # OpenDyslexic.ttf (for dyslexia_friendly captions)
│   └── templates/
│       └── lesson_intro.json
├── data/
│   ├── output/              # Rendered videos
│   ├── temp/                # Working files (ASS, TTS wavs)
│   └── memory/              # (legacy)
├── config/
│   ├── history.json
│   └── system.json
├── core/                    # Legacy core modules
├── Christman-Sound/         # Christman Voice SDK (submodule)
│   ├── core.py              # Full SDK (ToneScore, Takotsubo, XTTS, etc.)
│   ├── CHRISTMAN_EAR_CANAL/ # Unified import path
│   └── christman_voice_sdk/ # Engines, synthesis, tone, music
└── ChristmanMediaInstaller/ # Media installer (separate)
```

---

## Templates

### `lesson_intro.json` — Standard lesson opener

**Slots:**
| Slot | Type | Required | Default |
|------|------|----------|---------|
| `title` | string | ✅ | — |
| `voice_being` | string | ❌ | `derek` |
| `theme` | string | ❌ | `steampunk` |
| `duration` | number | ❌ | `10` |

**Tracks:**
- Video: Background loop + title overlay (TTS)
- TTS: Welcome narration
- Subtitle: Burned-in captions (kids_large style)
- Audio: Ambient steampunk music (0.15 volume)

---

## Themes

| Theme | Use Case |
|-------|----------|
| `steampunk` | Default — brass warmth, teal highlights |
| `cinema` | Film look — subtle contrast, film curves |
| `high_contrast` | Accessibility — max contrast, reduced saturation |
| `neutral` | Clean pass-through |

---

## Caption Styles

| Style | Font Size | Features |
|-------|-----------|----------|
| `kids_large` | 64 | Yellow, bold, thick outline, high margin |
| `dyslexia_friendly` | 52 | OpenDyslexic font, letter spacing, line spacing |
| `high_contrast` | 56 | Yellow on black, thick outline |
| `default` | 48 | White, standard outline |
| `minimal` | 36 | Thin, low margin |
| `cinema` | 42 | Film-style, no shadow |

---

## Voice Beings (Authorized)

| Being | Voice Profile | TTS Voice | Status |
|-------|---------------|-----------|--------|
| **Derek** | `~/.christman_ai/voice_profiles/derek.json` | OpenAI `onyx` | ✅ Authorized |
| AlphaVox | (pending) | — | ⏳ Queue |
| AlphaWolf | (pending) | — | ⏳ Queue |
| Inferno | (pending) | — | ⏳ Queue |
| Aegis | (pending) | — | ⏳ Queue |
| OmegaAlpha | (pending) | — | ⏳ Queue |
| Omega | (pending) | — | ⏳ Queue |
| Giuseppe | (pending) | — | ⏳ Queue |
| Sierra | (pending) | — | ⏳ Queue |

**Authorize a being:**
```bash
# Create profile in ~/.christman_ai/voice_profiles/{id}.json
# Add to Hermes knowledge base
./cve list --voices  # Shows authorized beings
```

---

## Bridge Integration

The engine pulls **live Whisper transcripts** from the Full Sensory Bridge for automatic caption generation:

```python
# In your code
from modules.captions import generate_captions_from_bridge, CaptionGenerator
from modules.timeline import Timeline, Track, Clip, TrackType

# Fetch latest transcript → caption segments
gen = generate_captions_from_bridge("data/output/captions.srt", style="kids_large")

# Or embed in timeline
sub_track = Track(TrackType.SUBTITLE)
for seg in gen.segments:
    sub_track.add_clip(Clip(source="", start=seg.start, duration=seg.end-seg.start, subtitle_text=seg.text))
timeline.add_track(sub_track)
```

**Bridge endpoints used:**
- `GET /latest` — Most recent transcript
- `GET /health` — Bridge status
- `GET /riley/status` — Riley tunnel status
- `POST /riley/claude-response` — Send to Riley

---

## Known Limitations (Roadmap)

| Issue | Status | Fix |
|-------|--------|-----|
| **Burned-in captions** | ⚠️ Partial | FFmpeg build lacks `libass`. Install: `brew reinstall ffmpeg --with-libass --with-freetype` |
| **Background looping** | ⚠️ | 30s clip plays once. Add `-stream_loop -1` to input for infinite loop |
| **TTS silent in tests** | ✅ Works in prod | Voice SDK not on test PYTHONPATH. Add: `export PYTHONPATH=/Volumes/LIFE2/ChristmanVideoEngine-main/Christman-Sound` |
| **Duration 0.00s on fallback** | 🐛 Minor | Probe issue when copying video after failed caption burn |
| **Template validation** | 📋 | No schema validation on slot types |
| **GUI** | 📋 | CLI only. Tkinter/web GUI for classroom use |

---

## Cardinal Rules in Force

1. **Rule 1 (Root)** — Root cause, not symptoms
2. **Rule 6 (Fail Loud)** — Errors visible, not swallowed
3. **Rule 10 (Clean)** — No residue, temp files auto-cleaned
4. **Rule 13 (Honest)** — Never hallucinate. If you didn't see it, don't say it.

---

## License / Patent

**Christman AI Proprietary.**
- Christman Video Engine, ToneScore™, Adaptive Response Mode, Takotsubo Physics Layer
- Patent Pending: **TCAP-2026-001 / TCAP-2026-002**
- © 2026 Everett Nathaniel Christman & Misty Gail Christman
- The Christman AI Project — Luma Cognify AI
- Truth. Dignity. Protection. Transparency. No Erasure.

---

## Contact

**Everett Nathaniel Christman** — Founder & CEO  
contact@thechristmanaiproject.com  
740 · 973 · 9640

---

**Carbon Empathy. Silicon Armor.**  
**The system adjusts to the human. The human never adjusts to the system.**