"""
XTTS v2 Voice Synthesis Engine

Real, working voice synthesis using Coqui XTTS v2.
Supports voice cloning from short audio samples.
Integrates with ICanHearYou emotion system.
"""

import torch # pyright: ignore[reportMissingImports]
import torchaudio # pyright: ignore[reportMissingImports]
import numpy as np # pyright: ignore[reportMissingImports]
from pathlib import Path
from typing import Optional, Dict
import time
import warnings

from .base_synthesizer import BaseSynthesizer, SynthesisResult
from .logger import get_logger

logger = get_logger(__name__)


class XTTSEngine(BaseSynthesizer):
    """
    XTTS v2 Engine - Real voice cloning and synthesis.

    Features:
    - Zero-shot voice cloning from 6+ seconds of audio
    - Multi-lingual support (13 languages)
    - Emotion control via prosody manipulation
    - GPU acceleration support
    - HIPAA-safe local processing

    Best for: Quick voice cloning, emotional synthesis, production use
    """

    def __init__(
        self,
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        device: str = "auto"
    ):
        """Initialize XTTS engine.

        Args:
            model_name: XTTS model identifier
            device: Device to use
        """
        super().__init__(None, device)

        self.model_name = model_name
        self.tts = None
        self.speaker_wav = None
        self.language = "en"

        logger.info(f"XTTS engine initialized (lazy loading)")

    def _load_model(self):
        """Load XTTS model (lazy loading)."""
        if self.tts is not None:
            return

        try:
            from TTS.api import TTS # pyright: ignore[reportMissingImports]

            logger.info(f"Loading XTTS model: {self.model_name}")

            # Initialize XTTS
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.tts = TTS(self.model_name)

            # Move to device
            if self.device == "cuda" and torch.cuda.is_available():
                self.tts = self.tts.to("cuda")
                logger.info("XTTS loaded on CUDA")
            elif self.device == "mps" and torch.backends.mps.is_available():
                # XTTS may not fully support MPS, fallback to CPU
                logger.warning("MPS detected but XTTS works best on CUDA/CPU")
                self.tts = self.tts.to("cpu")
            else:
                self.tts = self.tts.to("cpu")
                logger.info("XTTS loaded on CPU")

        except ImportError:
            logger.error("TTS library not installed. Run: pip install TTS")
            raise
        except Exception as e:
            logger.error(f"Failed to load XTTS model: {e}")
            raise

    def load_voice(
        self,
        reference_audio: Path,
        speaker_embedding: Optional[np.ndarray] = None
    ):
        """Load voice from reference audio.

        XTTS requires 6-10 seconds of clean audio for best results.

        Args:
            reference_audio: Path to reference audio (6+ seconds recommended)
            speaker_embedding: Ignored for XTTS (uses audio directly)
        """
        self._load_model()

        if not reference_audio.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio}")

        # Validate audio length
        audio, sr = torchaudio.load(str(reference_audio))
        duration = audio.shape[1] / sr

        if duration < 3.0:
            logger.warning(f"Reference audio is only {duration:.1f}s. Recommend 6+ seconds for best quality.")
        elif duration > 30.0:
            logger.warning(f"Reference audio is {duration:.1f}s. Recommend 6-15 seconds. Will use first 15s.")
            # Trim to 15 seconds
            audio = audio[:, :int(15.0 * sr)]

            # Save trimmed version
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = Path(f.name)
                torchaudio.save(str(temp_path), audio, sr)
                self.speaker_wav = str(temp_path)
        else:
            self.speaker_wav = str(reference_audio)

        if self.speaker_wav != str(reference_audio):
            logger.info(f"Using trimmed audio: {duration:.1f}s → 15.0s")
        else:
            logger.info(f"Loaded voice from {reference_audio.name} ({duration:.1f}s)")

    def synthesize(
        self,
        text: str,
        emotion_params: Optional[Dict] = None,
        language: str = "en",
        temperature: float = 0.7,
        repetition_penalty: float = 5.0,
        **kwargs
    ) -> SynthesisResult:
        """Synthesize speech from text.

        Args:
            text: Input text
            emotion_params: Emotion parameters from EmotionEmbedding
            language: Language code (en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh)
            temperature: Sampling temperature (0.1-1.0, default 0.7)
            repetition_penalty: Repetition penalty (1.0-10.0, default 5.0)
            **kwargs: Additional parameters

        Returns:
            SynthesisResult with audio and metadata
        """
        self._load_model()

        if self.speaker_wav is None:
            raise ValueError("No voice loaded. Call load_voice() first.")

        logger.info(f"Synthesizing: '{text[:50]}{'...' if len(text) > 50 else ''}'")

        start_time = time.time()

        try:
            # XTTS synthesis
            # Note: XTTS doesn't have direct emotion parameters
            # We'll apply emotion post-synthesis via audio manipulation
            wav = self.tts.tts(
                text=text,
                speaker_wav=self.speaker_wav,
                language=language,
                split_sentences=True  # Better for long text
            )

            # Convert to numpy array
            if isinstance(wav, list):
                audio = np.array(wav, dtype=np.float32)
            else:
                audio = wav.astype(np.float32)

            # XTTS outputs at 24kHz
            sample_rate = 24000

            # Apply emotion modifications if provided
            if emotion_params:
                audio = self.apply_emotion(audio, emotion_params, sample_rate)

            synthesis_time = time.time() - start_time

            # Estimate quality
            quality = self.estimate_quality(audio)

            return SynthesisResult(
                audio=audio,
                sample_rate=sample_rate,
                duration=len(audio) / sample_rate,
                speaker_similarity=quality.get("speaker_similarity"),
                naturalness_mos=quality.get("naturalness_mos"),
                engine="xtts_v2",
                synthesis_time=synthesis_time
            )

        except Exception as e:
            logger.error(f"Synthesis failed: {e}", exc_info=True)
            raise

    def get_optimal_reference_length(self) -> tuple:
        """Get optimal reference audio length for XTTS.

        Returns:
            (min_seconds, max_seconds, optimal_seconds)
        """
        return (6, 15, 10)  # 6-15 seconds, optimal is 10 seconds

    def get_supported_languages(self) -> list:
        """Get list of supported languages.

        Returns:
            List of language codes
        """
        return [
            "en",  # English
            "es",  # Spanish
            "fr",  # French
            "de",  # German
            "it",  # Italian
            "pt",  # Portuguese
            "pl",  # Polish
            "tr",  # Turkish
            "ru",  # Russian
            "nl",  # Dutch
            "cs",  # Czech
            "ar",  # Arabic
            "zh",  # Chinese (Mandarin)
        ]


if __name__ == "__main__":
    # Example usage
    import sys

    # Check if reference audio provided
    if len(sys.argv) < 2:
        print("Usage: python xtts_engine.py <reference_audio.wav>")
        sys.exit(1)

    reference = Path(sys.argv[1])
    if not reference.exists():
        print(f"Error: {reference} not found")
        sys.exit(1)

    # Initialize engine
    print("Initializing XTTS engine...")
    engine = XTTSEngine()

    # Load voice
    print(f"Loading voice from {reference.name}...")
    engine.load_voice(reference)

    # Test synthesis
    test_text = "Hello, this is a test of the voice cloning system. How does it sound?"
    print(f"\nSynthesizing: '{test_text}'")

    result = engine.synthesize(
        text=test_text,
        emotion_params={
            "pitch_shift": 0.0,
            "tempo_factor": 1.0,
            "energy_boost": 1.0
        }
    )

    # Save output
    output_path = Path("xtts_test_output.wav")
    result.save(output_path)

    print(f"\n✅ Synthesis complete!")
    print(f"   Duration: {result.duration:.2f}s")
    print(f"   Synthesis time: {result.synthesis_time:.2f}s")
    print(f"   Quality (MOS): {result.naturalness_mos:.2f}")
    print(f"   Output: {output_path}")
    print(f"\nPlay with: ffplay {output_path}")
