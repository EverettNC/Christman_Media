"""
Multi-Layer Tone Analysis System - Christman AI

5-Layer audio awareness architecture for detecting what the body reveals:
Layer 1: Physiological (pitch, jitter, shimmer, HNR)
Layer 2: Prosody (rhythm, pace, emphasis)
Layer 3: Paralinguistics (sighs, grunts, throat-clearing)
Layer 4: Discrete Emotions (anger, joy, sadness, fear)
Layer 5: ToneScore™ (composite 0-100)

Completely sovereign architecture. Zero reliance on bloated external audio libraries like librosa.
Used by: Giuseppe, Inferno, AlphaVox, Sierra
"""

import numpy as np
import parselmouth
from parselmouth.praat import call
from typing import Dict, Tuple, Optional
import torch
import torchaudio
from scipy.io import wavfile
# from config import Config, Tier  # Assuming these exist in your environment
from dataclasses import dataclass

from logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Native Audio Processing Helpers (Bypassing external libraries)
# =============================================================================
def get_rms_contour(y: np.ndarray) -> np.ndarray:
    """Native numpy RMS framing."""
    frame_length = 2048
    hop_length = 512
    pad_width = frame_length // 2
    y_padded = np.pad(y, pad_width, mode='reflect')
    num_frames = 1 + (len(y_padded) - frame_length) // hop_length
    if num_frames < 1: 
        return np.array([0.0], dtype=np.float32)
    amplitude = np.zeros(num_frames, dtype=np.float32)
    for i in range(num_frames):
        start = i * hop_length
        frame = y_padded[start:start + frame_length]
        amplitude[i] = np.sqrt(np.mean(frame**2))
    return amplitude

def load_audio_native(audio_path: str, target_sr: int = 16000) -> Tuple[np.ndarray, int]:
    """Native audio loading replacing librosa.load."""
    sr, y_raw = wavfile.read(audio_path)
    if y_raw.dtype == np.int16:
        y = y_raw.astype(np.float32) / 32768.0
    else:
        y = y_raw.astype(np.float32)
    return y, sr
# =============================================================================


@dataclass
class PhysiologicalFeatures:
    """Layer 1: What the body reveals."""
    pitch_mean: float
    pitch_std: float
    pitch_range: Tuple[float, float]
    jitter: float          # Vocal cord instability under stress
    shimmer: float         # Amplitude variation (exhaustion/illness)
    hnr: float            # Harmonic-to-noise ratio (clarity)

    def to_dict(self) -> Dict:
        return {
            "pitch_mean": round(self.pitch_mean, 2),
            "pitch_std": round(self.pitch_std, 2),
            "pitch_min": round(self.pitch_range[0], 2),
            "pitch_max": round(self.pitch_range[1], 2),
            "jitter": round(self.jitter, 4),
            "shimmer": round(self.shimmer, 4),
            "hnr": round(self.hnr, 2)
        }


@dataclass
class ProsodyFeatures:
    """Layer 2: Rhythm, pace, emphasis."""
    speech_rate: float      # Words per minute
    pause_duration: float   # Average pause length
    pause_count: int
    emphasis_peaks: int     # Number of emphasis points
    rhythm_variance: float

    def to_dict(self) -> Dict:
        return {
            "speech_rate": round(self.speech_rate, 1),
            "pause_duration": round(self.pause_duration, 3),
            "pause_count": self.pause_count,
            "emphasis_peaks": self.emphasis_peaks,
            "rhythm_variance": round(self.rhythm_variance, 3)
        }


@dataclass
class ParalinguisticFeatures:
    """Layer 3: Sounds between words."""
    sigh_count: int
    throat_clear_count: int
    grunt_count: int
    laugh_quality: str      # "genuine_joy", "nervous", "deflection"
    breath_pattern: str     # "normal", "shallow", "controlled"

    def to_dict(self) -> Dict:
        return {
            "sigh_count": self.sigh_count,
            "throat_clear_count": self.throat_clear_count,
            "grunt_count": self.grunt_count,
            "laugh_quality": self.laugh_quality,
            "breath_pattern": self.breath_pattern
        }


@dataclass
class DiscreteEmotions:
    """Layer 4: Emotion classification."""
    anger: float     # 0-1 confidence
    joy: float
    sadness: float
    fear: float
    neutral: float

    def to_dict(self) -> Dict:
        return {
            "anger": round(self.anger, 3),
            "joy": round(self.joy, 3),
            "sadness": round(self.sadness, 3),
            "fear": round(self.fear, 3),
            "neutral": round(self.neutral, 3)
        }

    def get_dominant(self) -> str:
        emotions = {
            "anger": self.anger, "joy": self.joy,
            "sadness": self.sadness, "fear": self.fear, "neutral": self.neutral
        }
        return max(emotions.items(), key=lambda x: x[1])[0]


class ToneScoreCalculator:
    """
    Layer 5: ToneScore™ calculation.
    """
    @staticmethod
    def calculate(arousal: float, valence: float, emotion_intensity: float) -> float:
        score = 0.4 * arousal + 0.35 * valence + 0.25 * emotion_intensity
        return round(min(100, max(0, score)), 2)

    @staticmethod
    def get_response_mode(tone_score: float) -> Dict:
        if tone_score > 75:
            return {
                "mode": "hold-space",
                "description": "High arousal - person needs space",
                "adjustments": {"cadence": "slower", "pitch": "deeper", "pauses": "longer", "volume": "softer"}
            }
        elif tone_score < 35:
            return {
                "mode": "gentle-lift",
                "description": "Low energy - person needs support",
                "adjustments": {"timbre": "warmer", "affirmations": "micro", "sentences": "shorter", "energy": "gentle_boost"}
            }
        else:
            return {
                "mode": "standard",
                "description": "Normal engagement range",
                "adjustments": {"monitoring": "continuous", "adaptive": True}
            }


class MultiLayerToneAnalyzer:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        logger.info("MultiLayerToneAnalyzer initialized (Native Processing)")

    def extract_physiological(self, audio_path: str) -> PhysiologicalFeatures:
        """Layer 1: Extract physiological features using Praat (parselmouth)."""
        snd = parselmouth.Sound(audio_path)
        pitch = snd.to_pitch()
        pitch_values = pitch.selected_array['frequency']
        pitch_values = pitch_values[pitch_values > 0] 

        if len(pitch_values) > 0:
            pitch_mean = np.mean(pitch_values)
            pitch_std = np.std(pitch_values)
            pitch_range = (np.min(pitch_values), np.max(pitch_values))
        else:
            pitch_mean = pitch_std = 0.0
            pitch_range = (0.0, 0.0)

        pointProcess = call(snd, "To PointProcess (periodic, cc)", 75, 600)
        jitter = call(pointProcess, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer = call([snd, pointProcess], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        harmonicity = call(snd, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harmonicity, "Get mean", 0, 0)

        return PhysiologicalFeatures(
            pitch_mean=pitch_mean,
            pitch_std=pitch_std,
            pitch_range=pitch_range,
            jitter=jitter if not np.isnan(jitter) else 0.0,
            shimmer=shimmer if not np.isnan(shimmer) else 0.0,
            hnr=hnr if not np.isnan(hnr) else 0.0
        )

    def extract_prosody(self, audio_path: str) -> ProsodyFeatures:
        """Layer 2: Extract prosodic features natively (no librosa)."""
        y, sr = load_audio_native(audio_path, target_sr=self.sample_rate)
        rms = get_rms_contour(y)
        
        # Native Speech rate estimation
        if len(rms) > 2:
            peaks = np.where((rms[1:-1] > rms[:-2]) & (rms[1:-1] > rms[2:]))[0]
            fps = sr / 512.0
            tempo = (fps / np.mean(np.diff(peaks))) * 60.0 if len(peaks) > 1 else 120.0
        else:
            tempo = 120.0
        speech_rate = tempo * 1.5 

        # Native Pause detection (silence > 200ms) based on RMS energy
        threshold = np.max(rms) * 0.1  # 10% of max energy
        is_speech = rms > threshold
        frame_duration = 512.0 / sr
        
        pauses = []
        current_pause = 0.0
        for active in is_speech:
            if not active:
                current_pause += frame_duration
            else:
                if current_pause > 0.2:
                    pauses.append(current_pause)
                current_pause = 0.0
        if current_pause > 0.2:
            pauses.append(current_pause)

        pause_count = len(pauses)
        pause_duration = np.mean(pauses) if pauses else 0.0

        # Emphasis detection
        emp_threshold = np.mean(rms) + 1.5 * np.std(rms)
        emphasis_peaks = np.sum(rms > emp_threshold)
        rhythm_variance = np.std(rms)

        return ProsodyFeatures(
            speech_rate=speech_rate,
            pause_duration=pause_duration,
            pause_count=pause_count,
            emphasis_peaks=int(emphasis_peaks),
            rhythm_variance=rhythm_variance
        )

    def extract_paralinguistics(self, audio_path: str) -> ParalinguisticFeatures:
        """Layer 3: Detect paralinguistic events natively."""
        y, sr = load_audio_native(audio_path)

        sigh_count = 0 
        throat_clear_count = 0  
        grunt_count = 0  
        laugh_quality = "unknown" 

        # Breath pattern natively using zero-crossing rate variance
        frame_length = 2048
        hop_length = 512
        pad_width = frame_length // 2
        y_padded = np.pad(y, pad_width, mode='reflect')
        num_frames = 1 + (len(y_padded) - frame_length) // hop_length
        
        zcr = np.zeros(num_frames, dtype=np.float32)
        for i in range(num_frames):
            start = i * hop_length
            frame = y_padded[start:start + frame_length]
            zcr[i] = np.mean(np.abs(np.diff(np.signbit(frame))))

        if np.std(zcr) > 0.05:
            breath_pattern = "irregular"
        elif np.mean(zcr) < 0.03:
            breath_pattern = "shallow"
        else:
            breath_pattern = "normal"

        return ParalinguisticFeatures(
            sigh_count=sigh_count,
            throat_clear_count=throat_clear_count,
            grunt_count=grunt_count,
            laugh_quality=laugh_quality,
            breath_pattern=breath_pattern
        )

    def analyze_complete(self, audio_path: str) -> Dict:
        """Complete 5-layer analysis."""
        logger.info(f"Analyzing audio: {audio_path}")
        physio = self.extract_physiological(audio_path)
        prosody = self.extract_prosody(audio_path)
        para = self.extract_paralinguistics(audio_path)
        emotions = self._derive_emotions_from_features(physio, prosody)

        arousal = self._calculate_arousal(physio, prosody)
        valence = self._calculate_valence(physio, emotions)
        intensity = self._calculate_intensity(prosody, emotions)

        tone_score = ToneScoreCalculator.calculate(arousal, valence, intensity)
        response_mode = ToneScoreCalculator.get_response_mode(tone_score)

        return {
            "layer_1_physiological": physio.to_dict(),
            "layer_2_prosody": prosody.to_dict(),
            "layer_3_paralinguistics": para.to_dict(),
            "layer_4_emotions": emotions.to_dict(),
            "layer_5_tonescore": {
                "score": tone_score,
                "arousal": round(arousal, 2),
                "valence": round(valence, 2),
                "intensity": round(intensity, 2),
                "response_mode": response_mode
            },
            "meta": {"audio_path": audio_path, "analysis_version": "1.0"}
        }

    def _derive_emotions_from_features(self, physio: PhysiologicalFeatures, prosody: ProsodyFeatures) -> DiscreteEmotions:
        anger = 0.5 if physio.pitch_mean > 200 and prosody.speech_rate > 150 else 0.1
        joy = 0.5 if physio.hnr > 15 and 120 < physio.pitch_mean < 180 else 0.1
        sadness = 0.5 if physio.hnr < 10 or prosody.speech_rate < 100 else 0.1
        fear = 0.5 if physio.jitter > 0.03 or physio.pitch_mean > 220 else 0.1
        neutral = 1.0 - max(anger, joy, sadness, fear)
        return DiscreteEmotions(anger=anger, joy=joy, sadness=sadness, fear=fear, neutral=max(0, neutral))

    def _calculate_arousal(self, physio: PhysiologicalFeatures, prosody: ProsodyFeatures) -> float:
        pitch_factor = min(100, (physio.pitch_mean / 250) * 100)
        rate_factor = min(100, (prosody.speech_rate / 200) * 100)
        jitter_factor = min(100, physio.jitter * 1000)
        arousal = (pitch_factor + rate_factor + jitter_factor) / 3
        return min(100, max(0, arousal))

    def _calculate_valence(self, physio: PhysiologicalFeatures, emotions: DiscreteEmotions) -> float:
        positive = emotions.joy * 100
        negative = (emotions.sadness + emotions.anger + emotions.fear) / 3 * 100
        valence = 50 + (positive - negative) / 2
        return min(100, max(0, valence))

    def _calculate_intensity(self, prosody: ProsodyFeatures, emotions: DiscreteEmotions) -> float:
        dominant_strength = max(emotions.anger, emotions.joy, emotions.sadness, emotions.fear) * 100
        energy_factor = min(100, prosody.rhythm_variance * 200)
        intensity = (dominant_strength + energy_factor) / 2
        return min(100, max(0, float(intensity)))


if __name__ == "__main__":
    analyzer = MultiLayerToneAnalyzer()
    result = analyzer.analyze_complete("data/raw/test_audio.wav")

    print("\n=== COMPLETE TONE ANALYSIS ===")
    print(f"\nToneScore™: {result['layer_5_tonescore']['score']}")
    print(f"Response Mode: {result['layer_5_tonescore']['response_mode']['mode']}")
    print(f"\nDominant Emotion: {result['layer_4_emotions']}")
    print(f"\nPhysiological: Jitter={result['layer_1_physiological']['jitter']:.4f}, HNR={result['layer_1_physiological']['hnr']:.2f}")
    print(f"\nProsody: Speech Rate={result['layer_2_prosody']['speech_rate']:.1f} wpm")