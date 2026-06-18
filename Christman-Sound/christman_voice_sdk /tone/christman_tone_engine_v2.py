"""
CHRISTMAN EMOTION & TONESCORE ENGINE v2.0
"Nothing Vital Lives Below Root"
Architecture: Multi-layer tone detection (Raw Audio -> Quantified Emotion)

Sovereign implementation: Bypassing librosa/LLVM for bare-metal DSP.
"""

import torch
import numpy as np
import hashlib
from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification
from scipy.io import wavfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ChristmanToneEngine:
    def __init__(self, model_name="superb/wav2vec2-base-superb-er"):
        logger.info(f"[SYSTEM] Initializing Christman Tone Engine: {model_name}")
        self.processor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
        self.model = Wav2Vec2ForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

        # Hardware acceleration
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        self.model.to(self.device)

        # The Carbon Reality Labels
        self.EMOTION_LABELS = [
            "neutral", "happy", "proud", "teasing", "annoyed",
            "sarcastic", "sweetheart", "laugh", "tremble", "emphasis", "last_breath"
        ]

    def analyze_audio(self, wav_path: str) -> dict:
        """
        Extracts physiological state and paralinguistic emotion 
        from raw audio waveform using native processing.
        """
        try:
            # 1. Native Audio Load (Bypassing librosa)
            sr, y_raw = wavfile.read(wav_path)
            
            # Normalize to float32
            if y_raw.dtype == np.int16:
                y = y_raw.astype(np.float32) / 32768.0
            else:
                y = y_raw.astype(np.float32)

            # Mix stereo to mono if needed
            if y.ndim == 2:
                y = np.mean(y, axis=0)

            # Ensure 16kHz for Wav2Vec2 compatibility (Native Resample)
            if sr != 16000:
                duration = len(y) / sr
                new_len = int(duration * 16000)
                y = np.interp(np.linspace(0, len(y), new_len), np.arange(len(y)), y).astype(np.float32)
                sr = 16000

            # 2. Physiological T1 Layer (Native RMS)
            # Energy calculation using native numpy framing
            rms_energy = np.sqrt(np.mean(y**2))
            intensity_norm = np.clip(rms_energy * 400, 0, 1)

            # 3. Neural Paralinguistics T2 Layer
            # Wav2Vec2 expects mono-channel 16k
            input_values = self.processor(y, sampling_rate=sr, return_tensors="pt", padding=True).input_values
            input_values = input_values.to(self.device)

            with torch.no_grad():
                logits = self.model(input_values).logits
                probabilities = torch.softmax(logits, dim=-1)[0].cpu().numpy()

            # Map raw probabilities to Christman Labels
            emotion_scores = {
                self.EMOTION_LABELS[i] if i < len(self.EMOTION_LABELS) else f"unknown_{i}": round(float(p), 4)
                for i, p in enumerate(probabilities)
            }

            dominant_emotion = max(emotion_scores, key=emotion_scores.get)

            # 4. Generate Cadence Fingerprint (Hash)
            cadence_hash = hashlib.sha1(y.tobytes()).hexdigest()[:16]

            # 5. Actionable Routing Logic
            action_state = "NORMAL"
            if dominant_emotion in ["tremble", "last_breath"] or intensity_norm > 0.85:
                action_state = "HOLD_SPACE"

            return {
                "modality": "audio",
                "dominant_state": dominant_emotion,
                "action_state": action_state,
                "physical_intensity": float(intensity_norm),
                "cadence_fingerprint": cadence_hash,
                "raw_scores": emotion_scores
            }

        except FileNotFoundError:
            logger.error(f"[ERROR] Carbon input missing. Cannot find {wav_path}")
            return None
        except Exception as e:
            logger.error(f"[ERROR] ToneScore calculation failed: {e}")
            return None

if __name__ == "__main__":
    engine = ChristmanToneEngine()
    # Test wiring
    # print(engine.analyze_audio("data/raw/test_carbon_input.wav"))