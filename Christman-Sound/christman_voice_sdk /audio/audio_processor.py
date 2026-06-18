"""
Audio Processor Module - Stage 1: Raw Audio Intake

Handles noise reduction, audio segmentation, and quality analysis.
Sovereign implementation: Zero reliance on bloated external audio libraries (librosa).
"""

import numpy as np # pyright: ignore[reportMissingImports]
import soundfile as sf # pyright: ignore[reportMissingImports]
from scipy import signal # pyright: ignore[reportMissingImports]
try:
    import noisereduce as nr # pyright: ignore[reportMissingImports]
except ImportError:
    nr = None
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

from .config import Config, Tier, get_config
from timbre.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AudioSegment:
    audio: np.ndarray
    sample_rate: int
    start_time: float
    end_time: float
    duration: float
    quality_score: float
    snr_db: float
    
    def save(self, path: Path):
        sf.write(str(path), self.audio, self.sample_rate)
    
    def to_dict(self) -> Dict:
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "quality_score": self.quality_score,
            "snr_db": self.snr_db,
            "sample_rate": self.sample_rate
        }


class AudioProcessor:
    def __init__(self, config: Optional[Config] = None, tier: Tier = Tier.BASIC):
        self.config = config or get_config()
        self.tier = tier
        self.tier_features = self.config.get_tier_features(tier)
        
        self.target_sr = self.config.get('audio.sample_rate', 16000)
        self.target_db = self.config.get('audio.target_db', -20.0)
        self.silence_threshold = self.config.get('audio.silence_threshold_db', -40.0)
        self.segment_length = self.config.get('audio.segment_length_seconds', 10.0)
        self.overlap = self.config.get('audio.overlap_seconds', 2.0)
        
        logger.info(f"AudioProcessor initialized for tier: {tier.value}")
    
    def process_file(self, input_path: str, output_dir: Optional[str] = None) -> List[AudioSegment]:
        audio, sr = self._load_audio(input_path)
        audio = self._reduce_noise(audio, sr)
        audio = self._normalize_loudness(audio)
        segments = self._segment_audio(audio, sr)
        segments = self._analyze_quality(segments)
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            for i, segment in enumerate(segments):
                segment.save(output_path / f"{Path(input_path).stem}_seg_{i:03d}.wav")
        return segments
    
    def _load_audio(self, path: str) -> Tuple[np.ndarray, int]:
        # Using soundfile instead of librosa
        audio, sr = sf.read(path, dtype='float32')
        
        if sr != self.target_sr:
            num_samples = int(len(audio) * self.target_sr / sr)
            audio = signal.resample(audio, num_samples)
            sr = self.target_sr
        
        if audio.ndim > 1:
            audio = np.mean(audio, axis=0)
        return audio, sr
    
    def _reduce_noise(self, audio: np.ndarray, sr: int) -> np.ndarray:
        if nr is None: return audio
        prop = {"basic": 0.5, "advanced": 0.8, "studio": 1.0}.get(self.tier_features.noise_reduction_quality, 0.0)
        return nr.reduce_noise(y=audio, sr=sr, stationary=(prop < 1.0), prop_decrease=prop)
    
    def _normalize_loudness(self, audio: np.ndarray) -> np.ndarray:
        rms = np.sqrt(np.mean(audio ** 2))
        if rms > 0:
            audio *= (10 ** (self.target_db / 20)) / rms
            if np.max(np.abs(audio)) > 1.0: audio /= np.max(np.abs(audio)) * 0.99
        return audio
    
    def _segment_audio(self, audio: np.ndarray, sr: int) -> List[AudioSegment]:
        # Native energy calculation (25ms frames)
        frame_size = int(0.025 * sr)
        hop_size = int(0.010 * sr)
        
        # Power calculation
        energy = np.array([np.mean(audio[i:i+frame_size]**2) for i in range(0, len(audio)-frame_size, hop_size)])
        energy_db = 10 * np.log10(energy + 1e-9)
        
        # Segmentation (using simple threshold)
        active = energy_db > self.silence_threshold
        
        segments = []
        seg_samples = int(self.segment_length * sr)
        step = int((self.segment_length - self.overlap) * sr)
        
        for start in range(0, len(audio) - int(0.5 * sr), step):
            end = min(start + seg_samples, len(audio))
            segment = AudioSegment(
                audio=audio[start:end], sample_rate=sr,
                start_time=start/sr, end_time=end/sr, duration=(end-start)/sr,
                quality_score=0.0, snr_db=self._estimate_snr(audio[start:end])
            )
            segments.append(segment)
        return segments
    
    def _estimate_snr(self, audio: np.ndarray) -> float:
        # Energy ratio (signal/noise floor)
        p = audio**2
        if len(p) < 100: return 0.0
        signal_p = np.mean(np.sort(p)[-len(p)//10:])
        noise_p = np.mean(np.sort(p)[:len(p)//10])
        return float(10 * np.log10(signal_p / (noise_p + 1e-9)))
    
    def _analyze_quality(self, segments: List[AudioSegment]) -> List[AudioSegment]:
        for s in segments:
            snr_s = min(100, max(0, (s.snr_db + 10) / 30 * 100))
            dur_s = max(0, 100 - (abs(s.duration - self.segment_length) / self.segment_length * 100))
            s.quality_score = round(0.6 * snr_s + 0.4 * dur_s, 2)
        segments.sort(key=lambda s: s.quality_score, reverse=True)
        return segments

    def get_statistics(self, segments: List[AudioSegment]) -> Dict:
        if not segments: return {"count": 0}
        return {
            "count": len(segments),
            "avg_quality": round(np.mean([s.quality_score for s in segments]), 2)
        }
    