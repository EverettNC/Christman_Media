"""
Christman Emotion Detection System - Shorty-Specific Implementation

This is the ULTRA tier ($1,999 custom) emotion detection system.
Based on the original christman_emotion.py with 11 precise emotional states.

For Aunt Shorty specifically.
"""

import torch
import torchaudio
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import numpy as np
import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple
import pickle

from .logger import get_logger

logger = get_logger(__name__)


# Shorty's 11 precise emotional states
SHORTY_EMOTION_LABELS = [
    "neutral",      # Baseline, calm state
    "happy",        # Genuine joy, warmth
    "proud",        # Pride in someone/something
    "teasing",      # Playful, messing with you
    "annoyed",      # Irritation, frustration
    "sarcastic",    # "I'm about to talk some shit" tone
    "sweetheart",   # Warm, affectionate, caring
    "laugh",        # Little laugh between words
    "tremble",      # Trembling voice in tender moments
    "emphasis",     # Strong emphasis on specific words
    "last_breath"   # The most precious moments
]


class ShortyEmotionDetector:
    """
    Shorty-specific emotion detection using custom-trained PCA model.
    
    This is for the ULTRA tier only - personalized emotion detection
    that captures Shorty's unique emotional fingerprint.
    """
    
    def __init__(
        self,
        pca_model_path: str = "models/shorty_emotion_pca.pt",
        scaler_path: str = "models/shorty_emotion_scaler.pt",
        wav2vec_model: str = "jonatasgrosman/wav2vec2-large-xlsr-53-english"
    ):
        """Initialize Shorty's emotion detector.
        
        Args:
            pca_model_path: Path to Shorty's trained PCA model
            scaler_path: Path to Shorty's scaler (optional)
            wav2vec_model: Base Wav2Vec2 model for embeddings
        """
        logger.info("Initializing Shorty emotion detector...")
        
        # Load Wav2Vec2 processor and model
        self.processor = Wav2Vec2Processor.from_pretrained(wav2vec_model)
        self.model = Wav2Vec2Model.from_pretrained(wav2vec_model)
        self.model.eval()
        
        # Device setup - matches Shorty's original code exactly
        self.device = torch.device(
            "mps" if torch.backends.mps.is_available()
            else "cuda" if torch.cuda.is_available()
            else "cpu"
        )
        self.model.to(self.device)
        logger.info(f"Using device: {self.device}")
        
        # Load Shorty's custom PCA model
        pca_path = Path(pca_model_path)
        if pca_path.exists():
            self.shorty_pca = torch.load(pca_path, map_location='cpu')
            logger.info(f"Loaded Shorty's PCA model from {pca_path}")
        else:
            logger.warning(f"PCA model not found at {pca_path}. Will use generic embeddings.")
            self.shorty_pca = None
        
        # Load optional scaler
        scaler_path = Path(scaler_path)
        if scaler_path.exists():
            self.shorty_scaler = torch.load(scaler_path, map_location='cpu')
            logger.info(f"Loaded Shorty's scaler from {scaler_path}")
        else:
            logger.info("No scaler found. Using raw PCA values.")
            self.shorty_scaler = None
        
        self.emotion_labels = SHORTY_EMOTION_LABELS
    
    def _load_and_preprocess_audio(
        self,
        wav_path: str,
        target_sr: int = 16000
    ) -> Tuple[torch.Tensor, int]:
        """Load and preprocess audio file.
        
        This matches Shorty's exact preprocessing from the original code.
        
        Args:
            wav_path: Path to audio file
            target_sr: Target sample rate (16000 Hz for Shorty)
            
        Returns:
            Preprocessed audio tensor and sample rate
        """
        # Load audio
        speech, sr = torchaudio.load(wav_path)
        
        # Mix stereo → mono if needed (exactly as in original code)
        if speech.ndim == 2:
            speech = speech.mean(dim=0)
        
        # Force 16kHz (Shorty's exact sample rate)
        if sr != target_sr:
            speech = torchaudio.transforms.Resample(sr, target_sr)(speech)
            sr = target_sr
        
        return speech, sr
    
    def embed_shorty_audio(self, wav_path: str) -> Dict[str, float]:
        """
        Extract Shorty's emotional signature from audio.
        
        This is the exact method from the original christman_emotion.py,
        reproduced faithfully.
        
        Args:
            wav_path: Path to audio file
            
        Returns:
            Dictionary with emotion scores and cadence fingerprint
        """
        # Load and preprocess
        speech, sr = self._load_and_preprocess_audio(wav_path)
        
        # Process through Wav2Vec2
        input_values = self.processor(
            speech.numpy(),
            return_tensors="pt",
            sampling_rate=16000
        ).input_values.to(self.device)
        
        # Extract embeddings
        with torch.no_grad():
            hidden = self.model(input_values).last_hidden_state  # (1, T, 1024)
            embeddings = hidden.mean(dim=1).cpu().numpy()        # (1, 1024)
        
        # Transform through Shorty's PCA
        if self.shorty_pca is not None:
            emotion_vec = self.shorty_pca.transform(embeddings)[0]  # (11,)
        else:
            # Fallback: use raw embeddings (won't be as accurate)
            logger.warning("Using raw embeddings - PCA model not loaded")
            emotion_vec = embeddings[0][:11]  # Take first 11 dimensions
        
        # Apply scaler if available
        if self.shorty_scaler is not None:
            emotion_vec = self.shorty_scaler.transform([emotion_vec])[0]
        
        # Build emotion scores
        scores = {}
        for i, label in enumerate(self.emotion_labels):
            if i < len(emotion_vec):
                val = float(emotion_vec[i])
                # Clip to [0, 1] range for stability
                val = max(0.0, min(1.0, val))
                scores[label] = round(val, 4)
            else:
                scores[label] = 0.0
        
        # Deterministic cadence fingerprint (exactly as in original)
        fingerprint = hashlib.sha1(emotion_vec.tobytes()).hexdigest()[:16]
        scores["cadence_fingerprint"] = fingerprint
        
        return scores
    
    def get_dominant_emotion(self, scores: Dict[str, float]) -> str:
        """Get the dominant emotion from scores.
        
        Args:
            scores: Emotion scores dictionary
            
        Returns:
            Name of dominant emotion
        """
        # Remove fingerprint from consideration
        emotion_scores = {
            k: v for k, v in scores.items()
            if k != "cadence_fingerprint" and isinstance(v, (int, float))
        }
        
        if not emotion_scores:
            return "neutral"
        
        return max(emotion_scores.items(), key=lambda x: x[1])[0]
    
    def detect_emotion_from_audio(self, wav_path: str) -> Dict:
        """
        Full emotion detection with metadata.
        
        Args:
            wav_path: Path to audio file
            
        Returns:
            Dictionary with scores, dominant emotion, and metadata
        """
        scores = self.embed_shorty_audio(wav_path)
        dominant = self.get_dominant_emotion(scores)
        
        return {
            "scores": scores,
            "dominant_emotion": dominant,
            "confidence": scores.get(dominant, 0.0),
            "cadence_fingerprint": scores.get("cadence_fingerprint", ""),
            "model_type": "shorty_custom_pca",
            "emotion_labels": self.emotion_labels
        }


def load_shorty_detector(
    pca_path: Optional[str] = None,
    scaler_path: Optional[str] = None
) -> ShortyEmotionDetector:
    """Convenience function to load Shorty's emotion detector.
    
    Args:
        pca_path: Path to PCA model (optional)
        scaler_path: Path to scaler (optional)
        
    Returns:
        Initialized ShortyEmotionDetector
    """
    kwargs = {}
    if pca_path:
        kwargs['pca_model_path'] = pca_path
    if scaler_path:
        kwargs['scaler_path'] = scaler_path
    
    return ShortyEmotionDetector(**kwargs)


# Example usage
if __name__ == "__main__":
    detector = load_shorty_detector()
    
    # Test with a sample audio file
    result = detector.detect_emotion_from_audio("data/raw/shorty_sample.wav")
    
    print("\n=== Shorty Emotion Detection ===")
    print(f"Dominant emotion: {result['dominant_emotion']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Cadence fingerprint: {result['cadence_fingerprint']}")
    print("\nAll scores:")
    for emotion, score in result['scores'].items():
        if emotion != "cadence_fingerprint":
            print(f"  {emotion:15s}: {score:.4f}")
