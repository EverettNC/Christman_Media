"""
Shorty Voice Engine V2 - ULTRA Tier Implementation

Integrates:
1. Real emotion detection from audio (Wav2Vec2 + PCA)
2. XTTS v2 voice cloning
3. Emotion-driven synthesis parameters

This is the REAL implementation that uses christman_emotion.py
"""

import numpy as np
import torch
from pathlib import Path
from typing import Optional, Dict, List
import time

from engines.xtts_engine import XTTSEngine
from timbre.shorty_emotion import ShortyEmotionDetector
from utils.logger import get_logger

logger = get_logger(__name__)


class ShortyVoiceEngineV2:
    """
    Shorty's complete voice system - ULTRA tier.

    Combines:
    - Wav2Vec2 emotion detection from audio
    - Custom PCA model for Shorty's emotional fingerprint
    - XTTS v2 voice cloning
    - Emotion-driven synthesis

    This is what you actually wanted.
    """

    # Shorty's 11 emotional states
    SHORTY_EMOTIONS = [
        "neutral", "happy", "proud", "teasing", "annoyed",
        "sarcastic", "sweetheart", "laugh", "tremble",
        "emphasis", "last_breath"
    ]

    def __init__(
        self,
        reference_audio: Optional[Path] = None,
        pca_model_path: str = "models/shorty_emotion_pca.pt",
        scaler_path: str = "models/shorty_emotion_scaler.pt",
        device: str = "auto"
    ):
        """Initialize Shorty's voice engine V2.

        Args:
            reference_audio: Path to Shorty's reference audio (6+ seconds)
            pca_model_path: Path to Shorty's trained PCA model
            scaler_path: Path to Shorty's scaler
            device: Device to use (auto, cuda, mps, cpu)
        """
        self.device = device

        # Initialize emotion detector (Wav2Vec2 + PCA)
        logger.info("Loading Shorty's emotion detector...")
        self.emotion_detector = ShortyEmotionDetector(
            pca_model_path=pca_model_path,
            scaler_path=scaler_path
        )

        # Initialize XTTS engine for synthesis
        logger.info("Loading XTTS voice synthesis engine...")
        self.xtts = XTTSEngine(device=device)

        # Store reference audio for emotion analysis
        self.reference_audio = None
        self.emotion_baseline = None

        # Load reference voice if provided
        if reference_audio:
            self.load_voice(reference_audio)
        else:
            logger.info("Shorty voice engine V2 initialized (no reference loaded)")

    def load_voice(self, reference_audio: Path):
        """Load Shorty's voice from reference audio.

        This does TWO things:
        1. Loads voice into XTTS for synthesis
        2. Analyzes audio with Wav2Vec2 to extract emotion baseline

        Args:
            reference_audio: Path to audio file (6+ seconds recommended)
        """
        logger.info(f"Loading Shorty's voice from {reference_audio.name}")

        if not reference_audio.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio}")

        self.reference_audio = reference_audio

        # Load into XTTS for voice cloning
        self.xtts.load_voice(reference_audio)

        # Analyze reference audio to get emotion baseline
        logger.info("Analyzing reference audio for emotional baseline...")
        try:
            emotion_result = self.emotion_detector.detect_emotion_from_audio(
                str(reference_audio)
            )
            self.emotion_baseline = emotion_result['scores']

            logger.info(f"Baseline emotion: {emotion_result['dominant_emotion']} "
                       f"({emotion_result['confidence']:.2%})")
            logger.info(f"Cadence fingerprint: {emotion_result['cadence_fingerprint']}")

            # Log all emotion scores
            for emotion, score in self.emotion_baseline.items():
                if emotion != "cadence_fingerprint" and isinstance(score, (int, float)):
                    logger.info(f"  {emotion:12s}: {score:.4f}")

        except Exception as e:
            logger.warning(f"Could not analyze emotion baseline: {e}")
            logger.warning("Will use default baseline scores")
            self.emotion_baseline = self._get_default_baseline()

        logger.info("Shorty's voice loaded and ready")

    def _get_default_baseline(self) -> Dict[str, float]:
        """Get default baseline if PCA model not available.

        Returns:
            Dictionary of default emotion scores
        """
        return {
            "neutral": 0.5000,
            "happy": 0.9123,
            "proud": 0.9567,
            "teasing": 0.8341,
            "annoyed": 0.7845,
            "sarcastic": 0.8912,
            "sweetheart": 0.9234,
            "laugh": 0.9874,
            "tremble": 0.5678,
            "emphasis": 0.9456,
            "last_breath": 0.0123
        }

    def synthesize(
        self,
        text: str,
        emotion_params: Optional[Dict] = None,
        **kwargs
    ) -> "SynthesisResult": # pyright: ignore[reportUndefinedVariable]
        """Compat method for VoiceSDK."""
        # Extract emotion if passed in params, otherwise default
        emotion = "neutral"
        exaggeration = 0.0
        
        if emotion_params:
            emotion = emotion_params.get("emotion", "neutral")
            exaggeration = emotion_params.get("exaggeration", 0.0)

        # Use generate_voice logic but return the inner SynthesisResult logic
        # Actually generate_voice returns a dict. We should call xtts directly 
        # but configured with our quantified emotion params.
        
        # 1. Quantify emotion
        quant = self.quantify_emotion(text, emotion, exaggeration)
        
        # 2. Call XTTS
        result = self.xtts.synthesize(
            text=text,
            emotion_params=quant["voice_params"],
            **kwargs
        )
        return result


    def quantify_emotion(
        self,
        text: str,
        emotion: str = "neutral",
        exaggeration: float = 0.0,
        analyze_audio: Optional[Path] = None
    ) -> Dict:
        """Quantify emotion parameters for synthesis.

        Args:
            text: Input text
            emotion: Emotion name from SHORTY_EMOTIONS
            exaggeration: Exaggeration factor (-1.0 to +1.0)
            analyze_audio: Optional audio to analyze for emotion (overrides emotion param)

        Returns:
            Dictionary with quantified parameters
        """
        # If audio provided, analyze it for emotion
        if analyze_audio and analyze_audio.exists():
            logger.info(f"Analyzing audio for emotion: {analyze_audio.name}")
            try:
                result = self.emotion_detector.detect_emotion_from_audio(str(analyze_audio))
                emotion = result['dominant_emotion']
                base_score = result['confidence']
                logger.info(f"Detected: {emotion} ({base_score:.2%})")
            except Exception as e:
                logger.warning(f"Emotion analysis failed: {e}, using specified emotion")
                base_score = self._get_emotion_score(emotion)
        else:
            # Use baseline score for specified emotion
            base_score = self._get_emotion_score(emotion)

        # Validate emotion
        if emotion not in self.SHORTY_EMOTIONS:
            logger.warning(f"Unknown emotion '{emotion}', using neutral")
            emotion = "neutral"
            base_score = 0.5000

        # Apply exaggeration (clamp to valid range)
        exaggeration = max(-1.0, min(1.0, exaggeration))

        # Calculate adjusted score
        if exaggeration >= 0:
            # Amplify emotion
            adjusted_score = base_score + (1.0 - base_score) * exaggeration * 0.5
        else:
            # Dampen emotion
            adjusted_score = base_score + (base_score - 0.5) * exaggeration

        # Clamp to [0, 1]
        adjusted_score = max(0.0, min(1.0, adjusted_score))

        # Map to voice parameters
        voice_params = self._emotion_to_voice_params(emotion, adjusted_score, exaggeration)

        return {
            "emotion": emotion,
            "base_score": round(base_score, 4),
            "adjusted_score": round(adjusted_score, 4),
            "exaggeration": round(exaggeration, 4),
            "voice_params": voice_params
        }

    def _get_emotion_score(self, emotion: str) -> float:
        """Get baseline emotion score.

        Args:
            emotion: Emotion name

        Returns:
            Baseline score for emotion
        """
        if self.emotion_baseline and emotion in self.emotion_baseline:
            return self.emotion_baseline[emotion]
        else:
            # Fallback to defaults
            defaults = self._get_default_baseline()
            return defaults.get(emotion, 0.5000)

    def _emotion_to_voice_params(
        self,
        emotion: str,
        score: float,
        exaggeration: float
    ) -> Dict:
        """Convert emotion to voice synthesis parameters.

        Uses score from actual emotion detection to inform parameters.

        Args:
            emotion: Emotion name
            score: Emotion score (0-1)
            exaggeration: Exaggeration factor

        Returns:
            Voice parameters for synthesis
        """
        # Base parameters
        params = {
            "pitch_shift": 0.0,
            "tempo_factor": 1.0,
            "energy_boost": 1.0
        }

        # Use score to scale the emotion intensity
        # Higher scores = more pronounced emotional characteristics
        intensity = score * (1.0 + exaggeration * 0.5)

        # Emotion-specific modifications
        if emotion == "happy":
            params["pitch_shift"] = 1.0 * intensity + (exaggeration * 1.5)
            params["tempo_factor"] = 1.0 + (0.05 * intensity) + (exaggeration * 0.15)
            params["energy_boost"] = 1.0 + (0.1 * intensity) + (exaggeration * 0.3)

        elif emotion == "proud":
            params["pitch_shift"] = 0.5 * intensity + (exaggeration * 1.0)
            params["tempo_factor"] = 1.0 - (0.05 * intensity) - (exaggeration * 0.05)
            params["energy_boost"] = 1.0 + (0.15 * intensity) + (exaggeration * 0.25)

        elif emotion == "teasing":
            params["pitch_shift"] = 1.5 * intensity + (exaggeration * 1.0)
            params["tempo_factor"] = 1.0 + (0.1 * intensity) + (exaggeration * 0.1)
            params["energy_boost"] = 1.0 + (0.05 * intensity) + (exaggeration * 0.2)

        elif emotion == "annoyed":
            params["pitch_shift"] = -0.5 * intensity - (exaggeration * 0.5)
            params["tempo_factor"] = 1.0 + (0.15 * intensity) + (exaggeration * 0.15)
            params["energy_boost"] = 1.0 + (0.2 * intensity) + (exaggeration * 0.3)

        elif emotion == "sarcastic":
            params["pitch_shift"] = -1.0 * intensity - (exaggeration * 1.0)
            params["tempo_factor"] = 1.0 - (0.1 * intensity) - (exaggeration * 0.1)
            params["energy_boost"] = 0.95 + (exaggeration * 0.15)

        elif emotion == "sweetheart":
            params["pitch_shift"] = 2.0 * intensity + (exaggeration * 1.0)
            params["tempo_factor"] = 1.0 - (0.15 * intensity) - (exaggeration * 0.1)
            params["energy_boost"] = 0.9 + (exaggeration * 0.1)

        elif emotion == "laugh":
            params["pitch_shift"] = 3.0 * intensity + (exaggeration * 2.0)
            params["tempo_factor"] = 1.0 + (0.2 * intensity) + (exaggeration * 0.2)
            params["energy_boost"] = 1.0 + (0.3 * intensity) + (exaggeration * 0.4)

        elif emotion == "tremble":
            params["pitch_shift"] = -1.5 * intensity - (exaggeration * 0.5)
            params["tempo_factor"] = 1.0 - (0.2 * intensity) - (exaggeration * 0.1)
            params["energy_boost"] = 1.0 - (0.3 * intensity) - (exaggeration * 0.2)

        elif emotion == "emphasis":
            params["pitch_shift"] = 1.0 * intensity + (exaggeration * 2.0)
            params["tempo_factor"] = 1.0 - (0.1 * intensity) - (exaggeration * 0.05)
            params["energy_boost"] = 1.0 + (0.4 * intensity) + (exaggeration * 0.5)

        elif emotion == "last_breath":
            # This is special - very low intensity
            params["pitch_shift"] = -3.0 - (exaggeration * 1.0)
            params["tempo_factor"] = 0.6 - (exaggeration * 0.2)
            params["energy_boost"] = 0.4 - (exaggeration * 0.3)

        # Clamp parameters to safe ranges
        params["pitch_shift"] = max(-12.0, min(12.0, params["pitch_shift"]))
        params["tempo_factor"] = max(0.5, min(2.0, params["tempo_factor"]))
        params["energy_boost"] = max(0.1, min(2.0, params["energy_boost"]))

        return params

    def generate_voice(
        self,
        text: str,
        emotion: str = "neutral",
        exaggeration: float = 0.0,
        analyze_audio: Optional[Path] = None,
        output_path: Optional[Path] = None
    ) -> Dict:
        """Generate Shorty's voice with emotion.

        Args:
            text: Text to synthesize
            emotion: Emotion from SHORTY_EMOTIONS (or auto-detect if analyze_audio provided)
            exaggeration: Exaggeration factor (-1.0 to +1.0)
            analyze_audio: Optional audio to analyze for emotion detection
            output_path: Optional path to save audio

        Returns:
            Dictionary with audio data and metadata
        """
        logger.info(f"Generating: '{text[:50]}...' [{emotion}, exag={exaggeration:.2f}]")

        start_time = time.time()

        # Quantify emotion (with optional audio analysis)
        quant = self.quantify_emotion(text, emotion, exaggeration, analyze_audio)

        # Synthesize with XTTS
        result = self.xtts.synthesize(
            text=text,
            emotion_params=quant["voice_params"]
        )

        # Save if output path provided
        if output_path:
            result.save(output_path)
            logger.info(f"Saved to {output_path}")

        generation_time = time.time() - start_time

        return {
            "audio": result.audio,
            "sample_rate": result.sample_rate,
            "duration": result.duration,
            "emotion": quant["emotion"],
            "quant_score": quant["adjusted_score"],
            "base_score": quant["base_score"],
            "exaggeration": quant["exaggeration"],
            "voice_params": quant["voice_params"],
            "generation_time": generation_time,
            "synthesis_time": result.synthesis_time,
            "quality_mos": result.naturalness_mos,
            "output_path": str(output_path) if output_path else None,
            "cadence_fingerprint": self.emotion_baseline.get("cadence_fingerprint", "") if self.emotion_baseline else ""
        }

    def analyze_and_clone(
        self,
        text: str,
        sample_audio: Path,
        output_path: Optional[Path] = None
    ) -> Dict:
        """Analyze audio for emotion, then synthesize with that emotion.

        This is the magic: analyze Shorty's actual emotional state from a clip,
        then use that to drive synthesis.

        Args:
            text: Text to synthesize
            sample_audio: Audio to analyze for emotion
            output_path: Optional output path

        Returns:
            Generation result with emotion analysis
        """
        logger.info(f"Analyzing {sample_audio.name} for emotional clone...")

        # Detect emotion from sample
        emotion_result = self.emotion_detector.detect_emotion_from_audio(str(sample_audio))

        detected_emotion = emotion_result['dominant_emotion']
        confidence = emotion_result['confidence']

        logger.info(f"Detected: {detected_emotion} ({confidence:.2%})")

        # Generate with detected emotion at high confidence
        return self.generate_voice(
            text=text,
            emotion=detected_emotion,
            exaggeration=0.5,  # Moderate exaggeration
            output_path=output_path
        )

    def get_available_emotions(self) -> List[str]:
        """Get list of available emotions.

        Returns:
            List of emotion names
        """
        return self.SHORTY_EMOTIONS.copy()


if __name__ == "__main__":
    import sys

    # Example usage
    if len(sys.argv) < 2:
        print("Usage: python shorty_voice_engine_v2.py <shorty_reference.wav>")
        print("\nExample:")
        print('  python shorty_voice_engine_v2.py data/raw/shorty.wav')
        sys.exit(1)

    reference = Path(sys.argv[1])

    # Initialize engine (will analyze reference audio for emotion baseline)
    print("Initializing Shorty's voice engine V2 (with emotion detection)...")
    engine = ShortyVoiceEngineV2(reference_audio=reference)

    # Test generation
    test_text = "I love you, sweetheart"

    print(f"\n=== Testing Voice Generation ===")
    print(f"Text: '{test_text}'\n")

    # Test with proud emotion
    result = engine.generate_voice(
        text=test_text,
        emotion="proud",
        exaggeration=0.8,
        output_path=Path("test_shorty_v2_proud.wav")
    )

    print(f"Emotion: {result['emotion']}")
    print(f"Base score: {result['base_score']:.4f}")
    print(f"Adjusted score: {result['quant_score']:.4f}")
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Generation time: {result['generation_time']:.2f}s")
    print(f"Cadence fingerprint: {result['cadence_fingerprint']}")
    print(f"\nOutput: test_shorty_v2_proud.wav")
    print(f"\n✅ Test complete!")
