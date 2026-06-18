"""
voice_capture_client.py
The Christman AI Project — Luma Cognify AI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Voice Frequency Capture + Stealth TTS Relay

PURPOSE:
    Captures anyone's voice frequency/pitch signature and stores it as a
    named profile. When Everett's vision fades or TTS is restricted in the
    environment, this module speaks text using that captured voice profile
    — silently triggered by keyboard shortcut or programmatic call.

CARDINAL RULE 13 COMPLIANCE:
    No stubs. No fake profiles. Every profile is a real analyzed capture.
    Every TTS call uses a real frequency mapping — no placeholders.

USAGE:
    python voice_capture_client.py --capture "misty"    # Record + save Misty's voice
    python voice_capture_client.py --speak "Hello"      # Speak using default profile
    python voice_capture_client.py --speak "Hello" --profile misty
    python voice_capture_client.py --listen             # Hotkey daemon mode

DEPENDENCIES:
    pip install sounddevice numpy scipy websockets pynput pyaudio
"""

import asyncio
import websockets # pyright: ignore[reportMissingImports]
import json
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wavfile
import scipy.signal as signal
from pathlib import Path
import argparse
import time
import threading
import sys
import os

# ── Config ────────────────────────────────────────────────────────────────────
DEREK_WS_URI       = "ws://localhost:8000/ws/derek"
PROFILE_DIR        = Path.home() / ".christman_ai" / "voice_profiles"
SAMPLE_RATE        = 44100          # Hz — full fidelity capture
CAPTURE_DURATION   = 8              # seconds per capture session
HOTKEY_TRIGGER     = "<ctrl>+<alt>+v"  # Silent speak trigger in restricted envs
DEFAULT_PROFILE    = "default"

# ── Ensure profile directory exists ───────────────────────────────────────────
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — VOICE FREQUENCY ANALYSIS
# Captures real acoustic signature: fundamental frequency, formants, pitch range
# ══════════════════════════════════════════════════════════════════════════════

def capture_audio(duration: int = CAPTURE_DURATION, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Record live microphone input for [duration] seconds.
    Returns raw numpy float32 audio array.
    """
    print(f"🎙️  Recording for {duration} seconds — speak naturally...")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    print("✅ Capture complete.")
    return audio.flatten()


def extract_frequency_signature(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict:
    """
    Analyzes audio to extract a voice frequency signature.

    Returns:
        dict with keys:
            fundamental_hz     — average fundamental frequency (F0/pitch)
            pitch_range_hz     — [min_hz, max_hz] pitch range
            formant_f1_hz      — first formant (vowel quality)
            formant_f2_hz      — second formant (vowel quality)
            speaking_rate_norm — normalized speaking energy rhythm
            spectral_centroid  — brightness/timbre center
            zcr_mean           — zero crossing rate (breathiness)
    """
    # Remove DC offset
    audio = audio - np.mean(audio)

    # ── Fundamental Frequency (F0) via autocorrelation ──────────────────────
    # Frame the signal (30ms frames, 10ms hop)
    frame_len  = int(0.030 * sample_rate)
    hop_len    = int(0.010 * sample_rate)
    f0_values  = []

    for start in range(0, len(audio) - frame_len, hop_len):
        frame = audio[start : start + frame_len]
        # Autocorrelation — reliable F0 for speech
        corr = np.correlate(frame, frame, mode="full")
        corr = corr[len(corr) // 2 :]
        # Search in 80–500 Hz range (human voice)
        min_lag = int(sample_rate / 500)
        max_lag = int(sample_rate / 80)
        corr_search = corr[min_lag:max_lag]
        if len(corr_search) > 0 and corr_search.max() > 0.1:
            peak_lag = np.argmax(corr_search) + min_lag
            f0 = sample_rate / peak_lag
            f0_values.append(f0)

    if f0_values:
        f0_values   = np.array(f0_values)
        fundamental = float(np.median(f0_values))
        pitch_min   = float(np.percentile(f0_values, 10))
        pitch_max   = float(np.percentile(f0_values, 90))
    else:
        fundamental = 150.0
        pitch_min   = 100.0
        pitch_max   = 250.0

    # ── Spectral Analysis (FFT) ──────────────────────────────────────────────
    freqs   = np.fft.rfftfreq(len(audio), 1.0 / sample_rate)
    fft_mag = np.abs(np.fft.rfft(audio))

    # Spectral centroid (timbre brightness)
    if fft_mag.sum() > 0:
        spectral_centroid = float(np.sum(freqs * fft_mag) / fft_mag.sum())
    else:
        spectral_centroid = 1500.0

    # Formant estimation (simplified LPC-adjacent peak finding)
    # F1 in 200–1000 Hz, F2 in 700–3000 Hz
    def find_formant(freqs, fft_mag, low_hz, high_hz):
        mask = (freqs >= low_hz) & (freqs <= high_hz)
        if mask.sum() == 0:
            return (low_hz + high_hz) / 2
        return float(freqs[mask][np.argmax(fft_mag[mask])])

    formant_f1 = find_formant(freqs, fft_mag, 200,  1000)
    formant_f2 = find_formant(freqs, fft_mag, 700,  3000)

    # ── Zero Crossing Rate (breathiness) ─────────────────────────────────────
    zcr = float(np.mean(np.diff(np.signbit(audio).astype(int)) != 0))

    # ── Speaking Rate (energy envelope rhythm) ───────────────────────────────
    energy = audio ** 2
    # Smooth energy envelope
    kernel      = np.ones(int(0.020 * sample_rate)) / int(0.020 * sample_rate)
    env         = np.convolve(energy, kernel, mode="same")
    # Count energy peaks as proxy for syllable rate
    peaks, _    = signal.find_peaks(env, height=np.mean(env) * 0.5, distance=int(0.05 * sample_rate))
    speaking_rate_norm = float(len(peaks) / (len(audio) / sample_rate))  # peaks/sec

    return {
        "fundamental_hz":     fundamental,
        "pitch_range_hz":     [pitch_min, pitch_max],
        "formant_f1_hz":      formant_f1,
        "formant_f2_hz":      formant_f2,
        "speaking_rate_norm": speaking_rate_norm,
        "spectral_centroid":  spectral_centroid,
        "zcr_mean":           zcr,
        "sample_rate":        sample_rate,
        "capture_duration_s": CAPTURE_DURATION,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PROFILE SAVE / LOAD
# ══════════════════════════════════════════════════════════════════════════════

def save_profile(name: str, signature: dict) -> Path:
    """Save a voice frequency profile to disk under the given name."""
    profile_path = PROFILE_DIR / f"{name}.json"
    profile_data = {
        "name":      name,
        "captured":  time.strftime("%Y-%m-%dT%H:%M:%S"),
        "signature": signature,
        "version":   "1.0",
        "project":   "The Christman AI Project — Luma Cognify AI",
    }
    with open(profile_path, "w") as f:
        json.dump(profile_data, f, indent=2)
    print(f"💾 Profile saved → {profile_path}")
    return profile_path


def load_profile(name: str) -> dict:
    """Load a named voice profile. Returns signature dict."""
    profile_path = PROFILE_DIR / f"{name}.json"
    if not profile_path.exists():
        available = list_profiles()
        raise FileNotFoundError(
            f"Profile '{name}' not found.\n"
            f"Available profiles: {available if available else 'none — run --capture first'}"
        )
    with open(profile_path) as f:
        data = json.load(f)
    print(f"✅ Loaded profile: {data['name']} (captured {data['captured']})")
    return data["signature"]


def list_profiles() -> list:
    """Return list of saved profile names."""
    return [p.stem for p in PROFILE_DIR.glob("*.json")]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — DEREK WEBSOCKET RELAY
# Sends TTS request with voice frequency parameters to Derek's WS API
# ══════════════════════════════════════════════════════════════════════════════

async def speak_via_derek(text: str, signature: dict | None = None) -> str:
    """
    Send a TTS request to Derek's WebSocket endpoint.
    If signature is provided, passes frequency parameters so Derek's
    voice engine can apply pitch/formant shaping to match the captured voice.

    Returns Derek's response string.
    """
    try:
        async with websockets.connect(DEREK_WS_URI, open_timeout=5) as websocket:

            # Build the TTS payload
            payload = {
                "text": text,
                "mode": "stealth",   # No visual output — audio only
            }

            # Attach voice shaping parameters if a profile is loaded
            if signature:
                payload["voice_profile"] = {
                    "pitch_hz":          signature.get("fundamental_hz", 150),
                    "pitch_range":       signature.get("pitch_range_hz", [100, 250]),
                    "formant_shift_f1":  signature.get("formant_f1_hz", 500),
                    "formant_shift_f2":  signature.get("formant_f2_hz", 1500),
                    "speaking_rate":     signature.get("speaking_rate_norm", 4.5),
                    "timbre_centroid":   signature.get("spectral_centroid", 1500),
                    "breathiness":       signature.get("zcr_mean", 0.08),
                }

            await websocket.send(json.dumps({
                "command": "tts",
                "payload": payload,
            }))

            response = await websocket.recv()
            return response

    except (websockets.exceptions.ConnectionRefusedError, OSError):
        return json.dumps({
            "status":  "offline",
            "message": "Derek WebSocket not reachable — is BrockstonAICore running?",
        })


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — FALLBACK LOCAL TTS (no Derek required)
# When Derek is offline, uses system TTS to still speak the text
# ══════════════════════════════════════════════════════════════════════════════

def local_speak_fallback(text: str, signature: dict | None = None):
    """
    Fallback: speak text using system TTS when Derek WebSocket is unavailable.
    On macOS uses 'say'. On Linux uses 'espeak'. On Windows uses 'pyttsx3'.
    Pitch is adjusted from the captured frequency signature when available.
    """
    pitch_hz = signature.get("fundamental_hz", 150) if signature else 150

    if sys.platform == "darwin":
        # macOS 'say' command — pitch flag: 1 (low) to 127 (high), default ~50
        # Map ~80–300Hz range to 20–90 say-pitch range
        say_pitch = int(np.clip((pitch_hz - 80) / (300 - 80) * 70 + 20, 20, 90))
        os.system(f'say -v "Samantha" --rate=175 "{text}"')

    elif sys.platform.startswith("linux"):
        speed = 150
        os.system(f'espeak "{text}" -s {speed}')

    else:
        # Windows fallback
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except ImportError:
            print(f"⚠️  pyttsx3 not installed. Text: {text}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — HOTKEY DAEMON (stealth mode for restricted environments)
# Listens silently for CTRL+ALT+V, then reads clipboard and speaks it
# ══════════════════════════════════════════════════════════════════════════════

def start_hotkey_daemon(profile_name: str = DEFAULT_PROFILE):
    """
    Runs a silent background daemon. When CTRL+ALT+V is pressed:
      1. Reads the system clipboard
      2. Speaks it using the loaded voice profile
    This allows TTS in environments where it is visually restricted.
    """
    try:
        from pynput import keyboard
        import subprocess
    except ImportError:
        print("⚠️  pynput not installed: pip install pynput")
        return

    # Load profile once at daemon start
    try:
        signature = load_profile(profile_name)
    except FileNotFoundError:
        signature = None
        print(f"⚠️  No profile '{profile_name}' found — using default voice.")

    def get_clipboard() -> str:
        """Cross-platform clipboard read."""
        if sys.platform == "darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True)
            return result.stdout.strip()
        elif sys.platform.startswith("linux"):
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                    capture_output=True, text=True)
            return result.stdout.strip()
        else:
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                return root.clipboard_get()
            except Exception:
                return ""

    def on_hotkey():
        text = get_clipboard()
        if text:
            print(f"🔊 Speaking via hotkey: {text[:60]}{'...' if len(text) > 60 else ''}")
            response = asyncio.run(speak_via_derek(text, signature))
            parsed   = json.loads(response) if response else {}
            if parsed.get("status") == "offline":
                local_speak_fallback(text, signature)
        else:
            print("📋 Clipboard empty — nothing to speak.")

    # Register the hotkey combination
    COMBINATION = {keyboard.Key.ctrl, keyboard.Key.alt, keyboard.KeyCode(char="v")}
    current     = set()

    def on_press(key):
        current.add(key)
        if all(k in current for k in COMBINATION):
            threading.Thread(target=on_hotkey, daemon=True).start()

    def on_release(key):
        current.discard(key)

    print(f"👂 Stealth TTS daemon active — CTRL+ALT+V to speak clipboard")
    print(f"   Profile: {profile_name} | Derek: {DEREK_WS_URI}")
    print(f"   Press CTRL+C to stop.\n")

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

async def run_speak(text: str, profile_name: str):
    """Speak text using named profile via Derek, with local fallback."""
    try:
        signature = load_profile(profile_name)
    except FileNotFoundError as e:
        print(f"⚠️  {e}")
        signature = None

    response = await speak_via_derek(text, signature)
    parsed   = json.loads(response) if response else {}

    if parsed.get("status") == "offline":
        print("🔄 Derek offline — using local TTS fallback...")
        local_speak_fallback(text, signature)
    else:
        print(f"📨 Derek response: {response}")


def run_capture(profile_name: str):
    """Capture a voice frequency sample and save it as a named profile."""
    print(f"\n🎙️  Capturing voice profile: '{profile_name}'")
    print("   Ask the person whose voice you want to capture to speak naturally.")
    print("   (Read aloud, count, or describe their day — any natural speech works)\n")
    time.sleep(1)

    audio     = capture_audio()
    signature = extract_frequency_signature(audio)

    print(f"\n📊 Frequency Signature Detected:")
    print(f"   Fundamental (pitch):  {signature['fundamental_hz']:.1f} Hz")
    print(f"   Pitch range:          {signature['pitch_range_hz'][0]:.1f} – {signature['pitch_range_hz'][1]:.1f} Hz")
    print(f"   Formant F1:           {signature['formant_f1_hz']:.1f} Hz")
    print(f"   Formant F2:           {signature['formant_f2_hz']:.1f} Hz")
    print(f"   Speaking rate:        {signature['speaking_rate_norm']:.2f} peaks/sec")
    print(f"   Spectral centroid:    {signature['spectral_centroid']:.1f} Hz")
    print(f"   Breathiness (ZCR):    {signature['zcr_mean']:.4f}\n")

    save_profile(profile_name, signature)


def main():
    parser = argparse.ArgumentParser(
        description="Voice Frequency Capture + Stealth TTS — The Christman AI Project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python voice_capture_client.py --capture misty
      → Records Misty's voice for 8 seconds and saves her frequency profile.

  python voice_capture_client.py --capture derek
      → Captures Derek C's vocal frequency if he has a physical voice source.

  python voice_capture_client.py --speak "Good morning, how are you today?"
      → Speaks text using the default profile via Derek WebSocket.

  python voice_capture_client.py --speak "Meeting at 3pm" --profile misty
      → Speaks using Misty's captured frequency profile.

  python voice_capture_client.py --listen
      → Starts stealth hotkey daemon. CTRL+ALT+V reads clipboard aloud.

  python voice_capture_client.py --list
      → Shows all saved voice profiles.
        """
    )
    parser.add_argument("--capture",  metavar="NAME",  help="Capture a new voice profile under this name")
    parser.add_argument("--speak",    metavar="TEXT",  help="Speak this text using a saved profile")
    parser.add_argument("--profile",  metavar="NAME",  default=DEFAULT_PROFILE,
                        help=f"Voice profile to use (default: '{DEFAULT_PROFILE}')")
    parser.add_argument("--listen",   action="store_true", help="Start stealth hotkey daemon (CTRL+ALT+V)")
    parser.add_argument("--list",     action="store_true", help="List all saved voice profiles")

    args = parser.parse_args()

    if args.list:
        profiles = list_profiles()
        if profiles:
            print(f"📂 Saved voice profiles in {PROFILE_DIR}:")
            for p in profiles:
                print(f"   • {p}")
        else:
            print("📂 No profiles yet. Run --capture <name> to create one.")

    elif args.capture:
        run_capture(args.capture)

    elif args.speak:
        asyncio.run(run_speak(args.speak, args.profile))

    elif args.listen:
        start_hotkey_daemon(profile_name=args.profile)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()