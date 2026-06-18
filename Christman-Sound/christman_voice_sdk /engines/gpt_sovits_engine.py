"""
GPT-SoVITS Engine Wrapper

Integrates GPT-SoVITS v3 (407M parameters) for high-quality voice synthesis.
Primary synthesis engine for ICanHearYou.

NOTE:
- This implementation keeps the SDK shape (BaseSynthesizer + SynthesisResult).
- If no real GPT-SoVITS model is wired, it falls back to using the reference audio
  to generate audible output (looped/reshaped), instead of writing silence.
"""

from pathlib import Path
from typing import Optional, Dict, Tuple
import time
import math

import numpy as np # pyright: ignore[reportMissingImports]
import soundfile as sf  # pyright: ignore[reportMissingImports] # uses your existing soundfile dependency
import torch  # pyright: ignore[reportMissingImports] # kept for future real-model integration

from base_synthesizer import BaseSynthesizer, SynthesisResult
from tone.emotion_embedder import EmotionEmbedding
from logger import get_logger

logger = get_logger(__name__)


class GPTSoVITSEngine(BaseSynthesizer):
    """
    GPT-SoVITS v3 synthesis engine.

    Features (target design):
    - 407M parameters (v3)
    - Few-shot voice cloning (1 minute of audio)
    - Cross-lingual generation
    - Preserves emotional expression
    - High-quality prosody and natural rhythm

    Current behavior:
    - If no model is wired, uses a reference-audio-based fallback that produces
      audible output shaped by the reference clip, not pure silence.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        device: str = "auto",
    ):
        """
        Initialize GPT-SoVITS engine.

        Args:
            model_path: Path to GPT-SoVITS checkpoint (if available)
            config_path: Path to config JSON (if available)
            device: Device to use ("auto", "cpu", "cuda", "mps")
        """
        if model_path is not None and not isinstance(model_path, Path):
            model_path = Path(model_path)

        super().__init__(model_path, device)

        self.config_path: Optional[Path] = (
            Path(config_path) if config_path is not None else None
        )
        self.tokenizer = None

        self.reference_audio: Optional[Path] = None
        self.speaker_embedding: Optional[np.ndarray] = None

        # Cached reference waveform for fallback synthesis
        self._reference_wave: Optional[np.ndarray] = None
        self._reference_sr: int = 16000

        # Explicitly track model state
        self.model = None

        logger.info("GPT-SoVITS engine initialized (lazy loading, model optional).")

    # -------------------------------------------------------------------------
    # Model loading
    # -------------------------------------------------------------------------
    def _load_model(self) -> None:
        """
        Load GPT-SoVITS model (lazy loading).

        This is intentionally conservative:
        - If no model_path is provided or file is missing, we stay in fallback mode.
        - When you are ready to wire the real GPT-SoVITS code, implement the
          actual load here.
        """
        if self.model is not None:
            return

        if self.model_path is None:
            logger.warning(
                "GPT-SoVITS model_path is None; running in fallback mode (no TTS model)."
            )
            self.model = None
            return

        if not self.model_path.exists():
            logger.warning(
                f"GPT-SoVITS model path does not exist: {self.model_path}. "
                "Running in fallback mode (no TTS model)."
            )
            self.model = None
            return

        # TODO: integrate real GPT-SoVITS here
        try:
            # from GPTSoVITS import GPTSoVITS
            # self.model = GPTSoVITS.load(self.model_path, self.config_path)
            # self.model.to(self.device)
            logger.info(
                f"GPT-SoVITS model path exists at {self.model_path}, "
                "but loader is not yet wired; staying in fallback mode."
            )
            self.model = None
        except Exception as e:
            logger.error(f"Failed to initialize GPT-SoVITS model: {e}")
            self.model = None

    # -------------------------------------------------------------------------
    # Voice loading
    # -------------------------------------------------------------------------
    def load_voice(
        self,
        reference_audio: Path,
        speaker_embedding: Optional[np.ndarray] = None,
    ) -> None:
        """
        Load voice from reference audio.

        GPT-SoVITS works with 3-10 seconds of reference audio in the full design.
        Here we also cache the waveform for fallback synthesis when no model
        is available.

        Args:
            reference_audio: Path to reference audio (3-60 seconds)
            speaker_embedding: Optional pre-computed embedding
        """
        self._load_model()

        reference_audio = Path(reference_audio)
        if not reference_audio.exists():
            raise FileNotFoundError(f"Reference audio not found: {reference_audio}")

        self.reference_audio = reference_audio

        # Load waveform for fallback mode
        try:
            data, sr = sf.read(str(reference_audio), always_2d=False)
            if data.ndim > 1:
                # Mix down to mono if stereo/multi-channel
                data = data.mean(axis=1)
            self._reference_wave = data.astype(np.float32)
            self._reference_sr = int(sr)
            logger.info(
                f"Loaded reference audio '{reference_audio.name}' "
                f"(sr={self._reference_sr}, samples={len(self._reference_wave)})"
            )
        except Exception as e:
            logger.error(f"Failed to load reference audio {reference_audio}: {e}")
            self._reference_wave = None
            self._reference_sr = 16000

        # Speaker embedding stub (replace when real encoder is wired)
        if speaker_embedding is not None:
            self.speaker_embedding = speaker_embedding
        else:
            self.speaker_embedding = self._extract_speaker_embedding(reference_audio)

    def _extract_speaker_embedding(self, audio_path: Path) -> np.ndarray:
        """
        Extract speaker embedding from audio.

        Current behavior:
        - Uses simple statistics over the cached reference waveform as a
          deterministic placeholder instead of pure random noise.

        Args:
            audio_path: Path to audio file (unused except for logging)

        Returns:
            Speaker embedding vector of fixed dimension.
        """
        embedding_dim = 256

        if self._reference_wave is None or len(self._reference_wave) == 0:
            logger.warning(
                "No reference waveform available for speaker embedding; "
                "returning zero embedding."
            )
            return np.zeros(embedding_dim, dtype=np.float32)

        wav = self._reference_wave
        wav = wav.astype(np.float32)

        # Simple deterministic stats as a placeholder
        mean_val = float(wav.mean())
        std_val = float(wav.std())
        max_abs = float(np.max(np.abs(wav))) if len(wav) > 0 else 0.0

        emb = np.zeros(embedding_dim, dtype=np.float32)
        emb[:3] = np.array([mean_val, std_val, max_abs], dtype=np.float32)

        logger.info(
            f"Computed placeholder speaker embedding from {audio_path.name}: "
            f"mean={mean_val:.5f}, std={std_val:.5f}, max_abs={max_abs:.5f}"
        )
        return emb

    # -------------------------------------------------------------------------
    # Synthesis
    # -------------------------------------------------------------------------
    def synthesize(
        self,
        text: str,
        emotion_params: Optional[Dict] = None,
        temperature: float = 0.7,
        top_k: int = 50,
        top_p: float = 0.9,
        **kwargs,
    ) -> SynthesisResult:
        """
        Synthesize speech from text.

        Args:
            text: Input text
            emotion_params: Emotion parameters from EmotionEmbedding
            temperature: Sampling temperature (future real model use)
            top_k: Top-k sampling (future)
            top_p: Top-p (nucleus) sampling (future)
            **kwargs: Additional parameters

        Returns:
            SynthesisResult with audio and metadata
        """
        self._load_model()

        if self.reference_audio is None:
            raise ValueError("No voice loaded. Call load_voice() first.")

        start_time = time.time()

        if self.model is None:
            # Fallback: use reference-audio-driven synthesis instead of silence
            logger.warning(
                "GPT-SoVITS model not loaded; using reference-audio fallback synthesis."
            )
            audio, sample_rate = self._synthesize_from_reference_fallback(
                text=text,
                emotion_params=emotion_params,
            )
        else:
            # TODO: Real GPT-SoVITS inference once wired.
            # audio, sample_rate = self.model.synthesize(
            #     text=text,
            #     reference_audio=str(self.reference_audio),
            #     speaker_embedding=self.speaker_embedding,
            #     temperature=temperature,
            #     top_k=top_k,
            #     top_p=top_p,
            # )
            sample_rate = self._reference_sr or 16000
            duration = max(1.5, len(text) * 0.1)
            num_samples = int(duration * sample_rate)
            audio = (
                np.random.randn(num_samples).astype(np.float32) * 0.05
            )  # gentle noise placeholder

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
            engine="gpt_sovits_v3_fallback"
            if self.model is None
            else "gpt_sovits_v3",
            synthesis_time=synthesis_time,
        )

    def _synthesize_from_reference_fallback(
        self,
        text: str,
        emotion_params: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Fallback synthesis that uses the reference waveform to generate audible
        output when no real TTS model is wired.

        This does NOT do true phonetic synthesis; it:
        - Loads the cached reference waveform
        - Chooses a target duration based on text length
        - Tiles / trims the reference to that duration
        - Normalizes and applies simple fade + optional energy scaling
        """
        sr = self._reference_sr or 16000

        if self._reference_wave is None or len(self._reference_wave) == 0:
            # Hard fallback: generate a simple sine tone so you at least get
            # audible output instead of silence.
            logger.warning(
                "No reference waveform available; generating simple tone fallback."
            )
            duration = max(1.5, len(text) * 0.12)
            t = np.linspace(0, duration, int(sr * duration), endpoint=False)
            audio = 0.2 * np.sin(2 * math.pi * 440.0 * t).astype(np.float32)
            return audio, sr

        ref = self._reference_wave.astype(np.float32)

        # Determine target duration based on text length (words → seconds)
        word_count = max(1, len(text.split()))
        target_duration = max(2.0, min(10.0, word_count * 0.6))  # clamp 2–10s
        target_len = int(target_duration * sr)

        # Tile or trim reference to match target duration
        if len(ref) >= target_len:
            audio = ref[:target_len].copy()
        else:
            reps = int(np.ceil(target_len / len(ref)))
            audio = np.tile(ref, reps)[:target_len].copy()

        # Normalize to sensible range
        max_abs = float(np.max(np.abs(audio))) or 1.0
        audio = (0.9 * audio / max_abs).astype(np.float32)

        # Simple energy scaling from emotion params
        if emotion_params:
            energy_boost = float(emotion_params.get("energy_boost", 1.0))
            energy_boost = float(np.clip(energy_boost, 0.5, 2.0))
            audio *= energy_boost

        # Fade in/out to avoid hard edges
        fade_len = min(len(audio) // 20, int(sr * 0.1))  # up to 100ms or 5% of clip
        if fade_len > 0:
            fade_in = np.linspace(0.0, 1.0, fade_len, dtype=np.float32)
            fade_out = fade_in[::-1]
            audio[:fade_len] *= fade_in
            audio[-fade_len:] *= fade_out

        return audio.astype(np.float32), sr

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    def get_optimal_reference_length(self) -> tuple:
        """
        Get optimal reference audio length for GPT-SoVITS.

        Returns:
            (min_seconds, max_seconds, optimal_seconds)
        """
        return (3, 60, 10)  # 3–60 seconds, optimal ~10 seconds


if __name__ == "__main__":
    # Minimal smoke test; runs in fallback mode unless a real model is wired.
    engine = GPTSoVITSEngine()

    reference = Path("data/raw/reference_voice.wav")
    if reference.exists():
        engine.load_voice(reference)

        result = engine.synthesize(
            text="Hello, this is a fallback synthesis test for ICanHearYou.",
            emotion_params={
                "pitch_shift": 1.0,
                "tempo_factor": 1.0,
                "energy_boost": 1.1,
            },
        )

        print(f"Synthesized {result.duration:.2f}s in {result.synthesis_time:.2f}s")
        print(f"Approx quality: {result.naturalness_mos}")
    else:
        print("No reference audio found at data/raw/reference_voice.wav")
