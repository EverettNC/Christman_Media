"""
Christman Multi-Layer Tone Analyzer
=====================================

5-Layer audio tone analysis system for emotional intelligence in voice.

Layer 1: Physiological (pitch, jitter, shimmer, HNR)
Layer 2: VAD (valence, arousal, dominance)
Layer 3: Paralinguistics
Layer 4: Discrete Emotions
Layer 5: ToneScore (0-100 composite)

Completely sovereign architecture. Zero reliance on bloated external audio libraries like librosa.

Patent Pending TCAP-2026-001 / TCAP-2026-002
© 2026 Everett Nathaniel Christman & Misty Gail Christman
The Christman AI Project — Luma Cognify AI
"""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path
import ctypes

import numpy as np
from scipy.io import wavfile

warnings.filterwarnings("ignore")

try:
    import torch
    import torchaudio
    _torch_ok = True
except ImportError:
    _torch_ok = False

try:
    from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2Processor
    _transformers_ok = True
except ImportError:
    _transformers_ok = False

logger = logging.getLogger(__name__)


# =============================================================================
# Bare-Metal DSP Engine Hook
# =============================================================================
DSP_LIB_PATH = Path(__file__).parent.parent / "christman_dsp.so"

try:
    _dsp_engine = ctypes.CDLL(str(DSP_LIB_PATH))
    _dsp_engine.christman_yin.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_size_t, ctypes.c_int, ctypes.c_float, ctypes.POINTER(ctypes.c_float)
    ]
    _dsp_ok = True
    logger.info("Christman DSP Engine online in MultiLayerToneAnalyzer.")
except Exception as e:
    _dsp_ok = False
    logger.error(f"Christman DSP Engine failed to load: {e}")

def get_pitch_contour_native(audio_array: np.ndarray, sample_rate: int = 16000, threshold: float = 0.1) -> np.ndarray:
    if not _dsp_ok: return np.array([])
    frame_length = 2048
    hop_length = 512
    if len(audio_array) < frame_length: return np.array([])
    num_frames = 1 + (len(audio_array) - frame_length) // hop_length
    pitches = np.zeros(num_frames, dtype=np.float32)
    out_pitch = ctypes.c_float()
    for i in range(num_frames):
        start = i * hop_length
        frame = np.ascontiguousarray(audio_array[start:start + frame_length], dtype=np.float32)
        _dsp_engine.christman_yin(frame, len(frame), sample_rate, threshold, ctypes.byref(out_pitch))
        pitches[i] = out_pitch.value
    return pitches

def get_rms_contour(y: np.ndarray) -> np.ndarray:
    frame_length = 2048
    hop_length = 512
    pad_width = frame_length // 2
    y_padded = np.pad(y, pad_width, mode='reflect')
    num_frames = 1 + (len(y_padded) - frame_length) // hop_length
    if num_frames < 1: return np.array([0.0], dtype=np.float32)
    amplitude = np.zeros(num_frames, dtype=np.float32)
    for i in range(num_frames):
        start = i * hop_length
        frame = y_padded[start:start + frame_length]
        amplitude[i] = np.sqrt(np.mean(frame**2))
    return amplitude
# =============================================================================


@dataclass
class ToneAnalysisResult:
    arousal: float
    valence: float
    dominance: float
    emotions: Dict[str, float]
    emotion_intensity: float
    tone_score: float
    interpretation: str
    response_mode: Dict[str, Any]
    physiological: Dict[str, float]


class ToneScoreCalculator:

    @staticmethod
    def calculate(arousal: float, valence: float, emotion_intensity: float) -> float:
        return min(100.0, max(0.0, 0.40 * arousal + 0.35 * valence + 0.25 * emotion_intensity))

    @staticmethod
    def get_response_mode(tone_score: float) -> Dict[str, Any]:
        if tone_score > 75:
            return {
                "mode": "hold_space",
                "description": "High stress detected; create supportive space",
                "cadence": "slower", "pitch": "deeper", "pauses": "longer",
            }
        if tone_score < 35:
            return {
                "mode": "gentle_lift",
                "description": "Low energy detected; provide gentle support",
                "timbre": "warm", "affirmations": "micro", "energy": "gentle_boost",
            }
        return {"mode": "standard", "description": "Normal engagement range", "adaptive": True}


class MultiLayerToneAnalyzer:

    EMOTION_LABELS: List[str] = [
        "anger", "disgust", "fear", "joy", "neutral", "sadness", "surprise",
    ]

    def __init__(self, emotion_model: str = "superb/wav2vec2-base-superb-er", device: str = "auto") -> None:
        logger.info("Initializing MultiLayerToneAnalyzer...")
        self.device = self._resolve_device(device)
        self.wav2vec = None
        self.processor = None
        if _torch_ok and _transformers_ok:
            self._load_emotion_model(emotion_model)

    def analyze_complete(self, audio_path: str) -> Dict[str, Any]:
        logger.info("Analyzing tone natively for: %s", audio_path)
        
        try:
            sample_rate, audio_raw = wavfile.read(audio_path)
            if audio_raw.dtype == np.int16:
                audio = audio_raw.astype(np.float32) / 32768.0
            else:
                audio = audio_raw.astype(np.float32)
        except Exception as e:
            return {"error": f"Failed to load audio: {e}"}

        pitch = self._extract_pitch(audio, sample_rate)
        jitter = self._compute_jitter(audio, sample_rate, pitch)
        shimmer = self._compute_shimmer(audio)
        hnr = self._harmonic_noise_ratio(audio)
        arousal = self._compute_arousal(audio, sample_rate, jitter, pitch)
        valence = self._compute_valence(audio, sample_rate, hnr)
        dominance = self._compute_dominance(audio, sample_rate, pitch)
        emotions = self._detect_emotions(audio_path)
        emotion_intensity = max(emotions.values()) * 100 if emotions else 0.0
        tone_score = ToneScoreCalculator.calculate(arousal=arousal, valence=valence, emotion_intensity=emotion_intensity)
        interpretation = self._interpret_score(tone_score, emotions)
        response_mode = ToneScoreCalculator.get_response_mode(tone_score)
        pitch_values = pitch[pitch > 0] if len(pitch) > 0 else np.array([])
        return {
            "layer_1_physiological": {
                "pitch_mean": float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0.0,
                "pitch_std": float(np.std(pitch_values)) if len(pitch_values) > 0 else 0.0,
                "jitter": float(jitter), "shimmer": float(shimmer), "hnr": float(hnr),
            },
            "layer_2_vad": {"arousal": float(arousal), "valence": float(valence), "dominance": float(dominance)},
            "layer_3_emotions": emotions,
            "layer_4_interpretation": {"interpretation": interpretation},
            "layer_5_tonescore": {
                "score": float(tone_score), "arousal": float(arousal), "valence": float(valence),
                "dominance": float(dominance), "intensity": float(emotion_intensity), "response_mode": response_mode,
            },
        }

    def analyze_tone(self, audio_path: str) -> Dict[str, Any]:
        result = self.analyze_complete(audio_path)
        if "error" in result:
            return result
        return {
            "arousal": result["layer_2_vad"]["arousal"],
            "valence": result["layer_2_vad"]["valence"],
            "dominance": result["layer_2_vad"]["dominance"],
            "emotions": result["layer_3_emotions"],
            "emotion_intensity": result["layer_5_tonescore"]["intensity"],
            "tone_score": result["layer_5_tonescore"]["score"],
            "interpretation": result["layer_4_interpretation"]["interpretation"],
            "response_mode": result["layer_5_tonescore"]["response_mode"],
            "physiological": result["layer_1_physiological"],
        }

    def adaptive_response_mode(self, tone_score: float) -> Dict[str, Any]:
        return ToneScoreCalculator.get_response_mode(tone_score)

    def _resolve_device(self, device: str):
        if not _torch_ok:
            return None
        if device != "auto":
            return torch.device(device)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")

    def _load_emotion_model(self, emotion_model: str) -> None:
        try:
            self.wav2vec = Wav2Vec2ForSequenceClassification.from_pretrained(emotion_model)
            self.processor = Wav2Vec2Processor.from_pretrained(emotion_model)
            if self.device is not None:
                self.wav2vec.to(self.device)
            self.wav2vec.eval()
        except Exception as exc:
            logger.warning("Failed to load emotion model: %s", exc)
            self.wav2vec = None
            self.processor = None

    def _extract_pitch(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        try:
            return get_pitch_contour_native(audio, sample_rate)
        except Exception as exc:
            logger.warning("Pitch extraction failed: %s", exc)
            return np.zeros(len(audio), dtype=float)

    def _compute_jitter(self, audio: np.ndarray, sample_rate: int, pitch: Optional[np.ndarray] = None) -> float:
        try:
            pitch_values = pitch if pitch is not None else self._extract_pitch(audio, sample_rate)
            pitch_values = pitch_values[pitch_values > 0]
            if len(pitch_values) < 2:
                return 0.0
            periods = 1.0 / pitch_values
            return min(1.0, float(np.mean(np.abs(np.diff(periods))) / np.mean(periods)) * 10.0)
        except Exception as exc:
            logger.warning("Jitter computation failed: %s", exc)
            return 0.0

    def _compute_shimmer(self, audio: np.ndarray) -> float:
        try:
            amplitude = get_rms_contour(audio)
            if len(amplitude) < 2:
                return 0.0
            amplitude_mean = float(np.mean(amplitude))
            if amplitude_mean == 0:
                return 0.0
            return min(1.0, float(np.mean(np.abs(np.diff(amplitude))) / amplitude_mean) * 5.0)
        except Exception as exc:
            logger.warning("Shimmer computation failed: %s", exc)
            return 0.0

    def _harmonic_noise_ratio(self, audio: np.ndarray) -> float:
        try:
            S = np.abs(np.fft.rfft(audio))
            median_S = np.median(S)
            peaks = S[S > median_S * 2]
            harmonic_power = float(np.sum(peaks ** 2)) + 1e-9
            total_power = float(np.sum(S ** 2)) + 1e-9
            noise_power = total_power - harmonic_power
            if noise_power <= 0: return 30.0
            if harmonic_power <= 0: return 0.0
            return float(max(0.0, min(30.0, 10.0 * np.log10(harmonic_power / noise_power))))
        except Exception as exc:
            logger.warning("HNR computation failed: %s", exc)
            return 15.0

    def _compute_arousal(self, audio: np.ndarray, sample_rate: int, jitter: float, pitch: np.ndarray) -> float:
        try:
            rms = get_rms_contour(audio)
            energy = min(100.0, float(np.mean(rms) * 1000.0))
            if len(rms) > 2:
                peaks = np.where((rms[1:-1] > rms[:-2]) & (rms[1:-1] > rms[2:]))[0]
                fps = sample_rate / 512.0
                tempo = float((fps / np.mean(np.diff(peaks))) * 60.0 if len(peaks) > 1 else 120.0)
            else:
                tempo = 120.0
            tempo_score = min(100.0, (tempo / 180.0) * 100.0)
            pitch_values = pitch[pitch > 0]
            pitch_score = (min(100.0, (float(np.mean(pitch_values)) / 250.0) * 100.0) if len(pitch_values) > 0 else 50.0)
            return min(100.0, max(0.0, 0.30 * energy + 0.30 * tempo_score + 0.25 * pitch_score + 0.15 * (jitter * 100.0)))
        except Exception as exc:
            logger.warning("Arousal computation failed: %s", exc)
            return 50.0

    def _compute_valence(self, audio: np.ndarray, sample_rate: int, hnr: float) -> float:
        try:
            S = np.abs(np.fft.rfft(audio))
            freqs = np.fft.rfftfreq(len(audio), 1/sample_rate)
            sum_S = np.sum(S)
            brightness = float(np.sum(freqs * S) / sum_S if sum_S > 0 else 0.0)
            brightness_score = min(100.0, (brightness / 3000.0) * 100.0)
            hnr_score = min(100.0, max(0.0, (hnr + 10.0) * 3.33))
            zcr_mean = np.mean(np.abs(np.diff(np.signbit(audio))))
            smoothness = max(0.0, 100.0 - (float(zcr_mean) * 200.0))
            return min(100.0, max(0.0, 0.40 * brightness_score + 0.40 * hnr_score + 0.20 * smoothness))
        except Exception as exc:
            logger.warning("Valence computation failed: %s", exc)
            return 50.0

    def _compute_dominance(self, audio: np.ndarray, sample_rate: int, pitch: Optional[np.ndarray] = None) -> float:
        try:
            rms = get_rms_contour(audio)
            energy = min(100.0, float(np.mean(rms) * 1000.0))
            pitch_values = pitch if pitch is not None else self._extract_pitch(audio, sample_rate)
            pitch_values = pitch_values[pitch_values > 0]
            pitch_range = (float(np.max(pitch_values) - np.min(pitch_values)) if len(pitch_values) > 0 else 0.0)
            range_score = min(100.0, (pitch_range / 150.0) * 100.0)
            
            S = np.abs(np.fft.rfft(audio))
            cumsum = np.cumsum(S)
            if cumsum[-1] > 0:
                rolloff = np.fft.rfftfreq(len(audio), 1/sample_rate)[np.searchsorted(cumsum, 0.85 * cumsum[-1])]
            else:
                rolloff = 0.0
            rolloff_score = min(100.0, (float(rolloff) / 4000.0) * 100.0)
            return min(100.0, max(0.0, 0.40 * energy + 0.30 * range_score + 0.30 * rolloff_score))
        except Exception as exc:
            logger.warning("Dominance computation failed: %s", exc)
            return 50.0

    def _detect_emotions(self, audio_path: str) -> Dict[str, float]:
        if self.wav2vec is None or self.processor is None or not _torch_ok:
            fallback = round(1.0 / len(self.EMOTION_LABELS), 4)
            return {label: fallback for label in self.EMOTION_LABELS}
        try:
            speech, sample_rate = torchaudio.load(audio_path)
            if sample_rate != 16000:
                speech = torchaudio.transforms.Resample(sample_rate, 16000)(speech)
            if speech.shape[0] > 1:
                speech = speech.mean(dim=0, keepdim=True)
            inputs = self.processor(speech.squeeze().numpy(), sampling_rate=16000, return_tensors="pt", padding=True)
            with torch.no_grad():
                if self.device is not None:
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                logits = self.wav2vec(**inputs).logits
                probabilities = torch.nn.functional.softmax(logits, dim=-1).cpu().numpy()[0]
            return {label: float(probabilities[i]) if i < len(probabilities) else 0.0 for i, label in enumerate(self.EMOTION_LABELS)}
        except Exception as exc:
            logger.error("Emotion detection failed: %s", exc)
            fallback = round(1.0 / len(self.EMOTION_LABELS), 4)
            return {label: fallback for label in self.EMOTION_LABELS}

    def _interpret_score(self, tone_score: float, emotions: Dict[str, float]) -> str:
        if emotions:
            dominant_name, dominant_confidence = max(emotions.items(), key=lambda item: item[1])
        else:
            dominant_name, dominant_confidence = "neutral", 0.5
        if tone_score > 80:
            state = "highly activated"
        elif tone_score > 60:
            state = "energized"
        elif tone_score > 40:
            state = "balanced"
        elif tone_score > 20:
            state = "subdued"
        else:
            state = "depleted"
        return f"{state}, showing {dominant_name} ({dominant_confidence:.2%} confidence)"


_tone_analyzer: Optional[MultiLayerToneAnalyzer] = None


def get_tone_analyzer() -> MultiLayerToneAnalyzer:
    global _tone_analyzer
    if _tone_analyzer is None:
        _tone_analyzer = MultiLayerToneAnalyzer()
    return _tone_analyzer


__all__ = ["ToneAnalysisResult", "ToneScoreCalculator", "MultiLayerToneAnalyzer", "get_tone_analyzer"]

# ==============================================================================
# Patent Pending TCAP-2026-001 / TCAP-2026-002
# The Christman AI Project — Luma Cognify AI
# "How can we help you love yourself more?"
# Nothing Vital Lives Below Root.
# ==============================================================================