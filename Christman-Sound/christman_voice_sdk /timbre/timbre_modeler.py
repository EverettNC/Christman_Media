"""
Timbre Modeling Module - Stage 2: Base Voice Construction

Extracts speaker identity and builds base voice model (neutral tone).
Uses X-vectors and D-vectors for speaker embeddings.
"""

from pathlib import Path
from typing import List, Optional, Dict, Tuple
import numpy as np
import torch
import ctypes
from dataclasses import dataclass

from timbre.logger import get_logger
from audio.audio_processor import AudioSegment

logger = get_logger(__name__)

# =============================================================================
# Bare-Metal DSP Engine Hook
# =============================================================================
# Proximity: The engine lives one folder up, at the root of the SDK.
DSP_LIB_PATH = Path(__file__).parent.parent / "christman_dsp.so"

try:
    _dsp_engine = ctypes.CDLL(str(DSP_LIB_PATH))
    
    # Map YIN Pitch Detection
    _dsp_engine.christman_yin.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_size_t,
        ctypes.c_int,
        ctypes.c_float,
        ctypes.POINTER(ctypes.c_float)
    ]
    
    # Map Linear Predictive Coding (LPC)
    _dsp_engine.christman_lpc.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_size_t,
        ctypes.c_int,
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS')
    ]
    _dsp_ok = True
    logger.info("Christman DSP Engine online in Timbre Modeler.")
except Exception as e:
    _dsp_ok = False
    logger.error(f"Christman DSP Engine failed to load: {e}")

def get_pitch_contour_native(audio_array: np.ndarray, sample_rate: int = 16000, threshold: float = 0.1) -> np.ndarray:
    """Native framing and YIN pitch extraction, bypassing librosa."""
    if not _dsp_ok: 
        return np.array([])
    
    # Standard framing parameters
    frame_length = 2048
    hop_length = 512
    
    if len(audio_array) < frame_length:
        return np.array([])
        
    num_frames = 1 + (len(audio_array) - frame_length) // hop_length
    pitches = np.zeros(num_frames, dtype=np.float32)
    
    out_pitch = ctypes.c_float()
    
    for i in range(num_frames):
        start = i * hop_length
        frame = np.ascontiguousarray(audio_array[start:start + frame_length], dtype=np.float32)
        _dsp_engine.christman_yin(frame, len(frame), sample_rate, threshold, ctypes.byref(out_pitch))
        pitches[i] = out_pitch.value
        
    return pitches

def get_lpc_native(audio_array: np.ndarray, order: int) -> np.ndarray:
    """Native Linear Predictive Coding, bypassing librosa."""
    if not _dsp_ok: 
        return np.zeros(order + 1, dtype=np.float32)
        
    audio_float32 = np.ascontiguousarray(audio_array, dtype=np.float32)
    out_a = np.zeros(order + 1, dtype=np.float32)
    
    _dsp_engine.christman_lpc(audio_float32, len(audio_float32), order, out_a)
    return out_a
# =============================================================================


@dataclass
class VoiceProfile:
    """Complete voice profile with timbre characteristics."""
    # Speaker embeddings
    x_vector: np.ndarray  # 512-dim TDNN embedding
    d_vector: Optional[np.ndarray] = None  # 256-dim RNN embedding
    
    # Fundamental frequency profile
    f0_mean: float = 0.0
    f0_std: float = 0.0
    f0_min: float = 0.0
    f0_max: float = 0.0
    f0_contour: Optional[np.ndarray] = None
    
    # Formant characteristics
    f1_mean: float = 0.0
    f2_mean: float = 0.0
    f3_mean: float = 0.0
    
    # Spectral envelope
    spectral_envelope: Optional[np.ndarray] = None
    
    # Voice quality
    hnr_mean: float = 15.0
    jitter_mean: float = 0.0
    shimmer_mean: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "x_vector_shape": self.x_vector.shape if self.x_vector is not None else None,
            "d_vector_shape": self.d_vector.shape if self.d_vector is not None else None,
            "f0": {
                "mean": self.f0_mean,
                "std": self.f0_std,
                "min": self.f0_min,
                "max": self.f0_max
            },
            "formants": {
                "f1": self.f1_mean,
                "f2": self.f2_mean,
                "f3": self.f3_mean
            },
            "voice_quality": {
                "hnr": self.hnr_mean,
                "jitter": self.jitter_mean,
                "shimmer": self.shimmer_mean
            }
        }


class TimbreModeler:
    """
    Stage 2: Timbre Modeling and Base Voice Construction
    
    Extracts:
    - Speaker embeddings (X-vectors, D-vectors)
    - F0 profile (pitch characteristics)
    - Formant analysis (vowel quality)
    - Spectral envelope
    
    Builds neutral base voice model for synthesis.
    """
    
    def __init__(
        self,
        device: str = "auto",
        use_x_vectors: bool = True,
        use_d_vectors: bool = False
    ):
        """Initialize timbre modeler.
        
        Args:
            device: Computation device
            use_x_vectors: Extract X-vectors (TDNN-based)
            use_d_vectors: Extract D-vectors (RNN-based)
        """
        self.device = self._setup_device(device)
        self.use_x_vectors = use_x_vectors
        self.use_d_vectors = use_d_vectors
        
        # Models will be loaded lazily
        self.x_vector_model = None
        self.d_vector_model = None
        
        logger.info(f"TimbreModeler initialized on {self.device}")
    
    def _setup_device(self, device: str) -> str:
        """Setup computation device."""
        if device == "auto":
            if torch.backends.mps.is_available():
                return "mps"
            elif torch.cuda.is_available():
                return "cuda"
            else:
                return "cpu"
        return device
    
    def build_voice_profile(
        self,
        audio_segments: List[AudioSegment],
        extract_detailed: bool = True
    ) -> VoiceProfile:
        """Build complete voice profile from audio segments.
        
        Args:
            audio_segments: List of processed audio segments
            extract_detailed: Whether to extract detailed features
            
        Returns:
            VoiceProfile object
        """
        logger.info(f"Building voice profile from {len(audio_segments)} segments")
        
        # Extract speaker embedding
        x_vector = self._extract_x_vector(audio_segments)
        d_vector = self._extract_d_vector(audio_segments) if self.use_d_vectors else None
        
        # Extract F0 profile
        f0_profile = self._extract_f0_profile(audio_segments)
        
        # Extract formants (if detailed)
        formants = self._extract_formants(audio_segments) if extract_detailed else (0, 0, 0)
        
        # Extract voice quality metrics
        voice_quality = self._extract_voice_quality(audio_segments)
        
        profile = VoiceProfile(
            x_vector=x_vector,
            d_vector=d_vector,
            f0_mean=f0_profile["mean"],
            f0_std=f0_profile["std"],
            f0_min=f0_profile["min"],
            f0_max=f0_profile["max"],
            f0_contour=f0_profile.get("contour"),
            f1_mean=formants[0],
            f2_mean=formants[1],
            f3_mean=formants[2],
            hnr_mean=voice_quality["hnr"],
            jitter_mean=voice_quality["jitter"],
            shimmer_mean=voice_quality["shimmer"]
        )
        
        logger.info("Voice profile built successfully")
        return profile
    
    def _extract_x_vector(self, segments: List[AudioSegment]) -> np.ndarray:
        """Extract X-vector speaker embedding.
        
        X-vectors use Time-Delay Neural Networks (TDNN) trained on VoxCeleb.
        Output: 512-dimensional embedding.
        
        Args:
            segments: Audio segments
            
        Returns:
            512-dim X-vector
        """
        if self.x_vector_model is None:
            logger.warning("X-vector model not loaded, using placeholder")
            return np.random.randn(512).astype(np.float32)
        
        # TODO: Load actual X-vector model
        # from speechbrain.pretrained import EncoderClassifier
        # classifier = EncoderClassifier.from_hparams(
        #     source="speechbrain/spkrec-xvect-voxceleb"
        # )
        
        # Concatenate all segments
        all_audio = np.concatenate([seg.audio for seg in segments])
        
        # TODO: Extract X-vector from concatenated audio
        # embedding = classifier.encode_batch(audio_tensor)
        
        # Placeholder
        return np.random.randn(512).astype(np.float32)
    
    def _extract_d_vector(self, segments: List[AudioSegment]) -> np.ndarray:
        """Extract D-vector speaker embedding.
        
        D-vectors use LSTM with Generalized End-to-End (GE2E) loss.
        Output: 256-dimensional embedding.
        
        Args:
            segments: Audio segments
            
        Returns:
            256-dim D-vector
        """
        if self.d_vector_model is None:
            logger.warning("D-vector model not loaded, using placeholder")
            return np.random.randn(256).astype(np.float32)
        
        # TODO: Load actual D-vector model
        # Placeholder
        return np.random.randn(256).astype(np.float32)
    
    def _extract_f0_profile(self, segments: List[AudioSegment]) -> Dict:
        """Extract fundamental frequency profile.
        
        Args:
            segments: Audio segments
            
        Returns:
            F0 statistics dictionary
        """
        all_f0 = []
        for segment in segments:
            # Extract F0 using Native Bare-Metal YIN
            f0 = get_pitch_contour_native(segment.audio, sample_rate=segment.sample_rate)
            
            # Apply thresholds (fmin=50, fmax=500) and remove unvoiced frames
            f0_voiced = f0[(f0 > 50) & (f0 < 500)]
            all_f0.extend(f0_voiced)
        
        if len(all_f0) == 0:
            logger.warning("No F0 values extracted")
            return {"mean": 0, "std": 0, "min": 0, "max": 0}
        
        all_f0 = np.array(all_f0)
        
        return {
            "mean": float(np.mean(all_f0)),
            "std": float(np.std(all_f0)),
            "min": float(np.min(all_f0)),
            "max": float(np.max(all_f0)),
            "contour": all_f0  # Full contour for analysis
        }
    
    def _extract_formants(self, segments: List[AudioSegment]) -> Tuple[float, float, float]:
        """Extract formant frequencies (F1, F2, F3).
        
        Uses LPC (Linear Predictive Coding) analysis.
        
        Args:
            segments: Audio segments
            
        Returns:
            (F1_mean, F2_mean, F3_mean)
        """
        from scipy.signal import lfilter
        
        all_formants = []
        
        for segment in segments:
            # LPC analysis (order 12 for vocal tract modeling)
            try:
                # Estimate formants from Native Bare-Metal LPC
                lpc_order = 12
                a = get_lpc_native(segment.audio, order=lpc_order)
                
                # Find roots of LPC polynomial
                roots = np.roots(a)
                roots = roots[np.imag(roots) >= 0]  # Keep positive frequencies
                
                # Convert to frequencies
                angles = np.arctan2(np.imag(roots), np.real(roots))
                freqs = angles * (segment.sample_rate / (2 * np.pi))
                
                # Sort and take first 3 as formants
                formants = sorted(freqs)[:3]
                if len(formants) >= 3:
                    all_formants.append(formants)
                    
            except Exception as e:
                logger.debug(f"Formant extraction failed for segment: {e}")
                continue
        
        if len(all_formants) == 0:
            logger.warning("No formants extracted, using defaults")
            return (500.0, 1500.0, 2500.0)  # Typical adult male
        
        # Average formants across segments
        all_formants = np.array(all_formants)
        f1_mean = float(np.mean(all_formants[:, 0]))
        f2_mean = float(np.mean(all_formants[:, 1]))
        f3_mean = float(np.mean(all_formants[:, 2]))
        
        return (f1_mean, f2_mean, f3_mean)
    
    def _extract_voice_quality(self, segments: List[AudioSegment]) -> Dict:
        """Extract voice quality metrics (HNR, jitter, shimmer).
        
        Args:
            segments: Audio segments
            
        Returns:
            Voice quality metrics
        """
        # Use existing ToneScore engine for these metrics
        from tonescore_engine import ToneScoreEngine
        
        hnr_values = []
        jitter_values = []
        shimmer_values = []
        
        # Save segments temporarily and analyze
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for i, segment in enumerate(segments[:10]):  # Sample first 10
                seg_path = temp_path / f"segment_{i}.wav"
                segment.save(seg_path)
                
                try:
                    engine = ToneScoreEngine()
                    result = engine.analyze_tone(str(seg_path))
                    
                    hnr_values.append(result.get("hnr", 15.0))
                    jitter_values.append(result.get("jitter", 0.0))
                    shimmer_values.append(result.get("shimmer", 0.0))
                except Exception as e:
                    logger.debug(f"Voice quality extraction failed: {e}")
        
        return {
            "hnr": float(np.mean(hnr_values)) if hnr_values else 15.0,
            "jitter": float(np.mean(jitter_values)) if jitter_values else 0.0,
            "shimmer": float(np.mean(shimmer_values)) if shimmer_values else 0.0
        }
    
    def save_profile(self, profile: VoiceProfile, path: Path):
        """Save voice profile to file.
        
        Args:
            profile: VoiceProfile to save
            path: Output file path
        """
        import pickle
        
        with open(path, 'wb') as f:
            pickle.dump(profile, f)
        
        logger.info(f"Voice profile saved to {path}")
    
    def load_profile(self, path: Path) -> VoiceProfile:
        """Load voice profile from file.
        
        Args:
            path: Profile file path
            
        Returns:
            VoiceProfile object
        """
        import pickle
        
        with open(path, 'rb') as f:
            profile = pickle.load(f)
        
        logger.info(f"Voice profile loaded from {path}")
        return profile


if __name__ == "__main__":
    from audio.audio_processor import AudioProcessor
    from audio.config import Tier
    
    # Example usage
    processor = AudioProcessor(tier=Tier.PREMIUM)
    segments = processor.process_file("data/raw/sample_voice.wav")
    
    modeler = TimbreModeler()
    profile = modeler.build_voice_profile(segments)
    
    print("\n=== Voice Profile ===")
    print(f"F0 range: {profile.f0_min:.1f} - {profile.f0_max:.1f} Hz")
    print(f"F0 mean: {profile.f0_mean:.1f} Hz")
    print(f"Formants: F1={profile.f1_mean:.0f}, F2={profile.f2_mean:.0f}, F3={profile.f3_mean:.0f}")
    print(f"HNR: {profile.hnr_mean:.1f} dB")
    print(f"X-vector shape: {profile.x_vector.shape}")