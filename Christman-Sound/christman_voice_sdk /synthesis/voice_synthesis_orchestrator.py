from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
import tempfile
import time

from audio.audio_processor import AudioProcessor
from synthesis.phoneme_labeler import PhonemeLabeler
from timbre.voicepack import VoicepackBuilder, VoicepackMetadata
from timbre.timbre_modeler import TimbreModeler, VoiceProfile
from tone.emotion_embedder import EmotionEmbedder
from engines.gpt_sovits_engine import GPTSoVITSEngine
from tone.tonescore_engine import ToneScoreEngine
from audio.config import Config, Tier, get_config
from logger import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class SynthesisResult:
    audio: Any
    sample_rate: int
    duration: float
    emotion: str
    emotion_intensity: float
    lipsync_data: Optional[List[Dict[str, Any]]]
    synthesis_time: float
    quality_score: Optional[float]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audio": self.audio,
            "sample_rate": self.sample_rate,
            "duration": self.duration,
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
            "lipsync_data": self.lipsync_data,
            "synthesis_time": self.synthesis_time,
            "quality_score": self.quality_score,
            "metadata": self.metadata,
        }


class VoiceSynthesisOrchestrator:
    """
    Coordinates the complete voice synthesis pipeline:
    Stage 1: Audio intake → Stage 2: Timbre → Stage 3: Expression
    Stage 4: Emotion → Stage 5: Synthesis
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        tier: Tier = Tier.BASIC,
        use_mfa: bool = True,
        auto_load_engine: bool = False,
    ) -> None:
        self.config = config or get_config()
        self.tier = tier
        self.tier_features = self.config.get_tier_features(tier)

        # Core components
        self.audio_processor = AudioProcessor(config=self.config, tier=tier)
        self.phoneme_labeler = PhonemeLabeler(use_mfa=use_mfa)
        self.timbre_modeler = TimbreModeler()
        self.emotion_embedder = EmotionEmbedder(tier=tier)
        self.voicepack_builder = VoicepackBuilder()

        # Synthesis engine (GPT-SoVITS) and state
        self.engine: Optional[GPTSoVITSEngine] = None
        self.current_voicepack: Optional[Dict[str, Any]] = None
        self.current_voice_profile: Optional[VoiceProfile] = None

        if auto_load_engine:
            self._ensure_engine()

        logger.info(
            "VoiceSynthesisOrchestrator initialized",
            extra={"tier": tier.value},
        )

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _ensure_engine(self) -> GPTSoVITSEngine:
        if self.engine is None:
            self.engine = GPTSoVITSEngine(config=self.config, tier=self.tier)
            logger.info("GPT-SoVITS engine initialized")
        return self.engine

    def _validate_training_inputs(
        self,
        audio_files: Sequence[Path],
        voice_name: str,
    ) -> None:
        if not voice_name or not voice_name.strip():
            raise ValueError("voice_name must be a non-empty string")
        if not audio_files:
            raise ValueError("audio_files must contain at least one file")

    # -------------------------------------------------------------------------
    # Training: audio → voicepack
    # -------------------------------------------------------------------------

    def train_voice(
        self,
        audio_files: List[Path],
        voice_name: str,
        metadata: Optional[VoicepackMetadata] = None,
        custom_emotions: Optional[List[str]] = None,
    ) -> Path:
        """
        Complete training pipeline: audio → voicepack.
        """
        self._validate_training_inputs(audio_files, voice_name)

        logger.info(
            "Starting voice training",
            extra={"voice_name": voice_name, "file_count": len(audio_files)},
        )
        start_time = time.time()

        all_segments: List[Any] = []
        reference_audio: List[Path] = []
        total_duration = 0.0

        # Stage 1: audio intake / preprocessing
        logger.info("Stage 1/5: Audio preprocessing")
        for audio_file in audio_files:
            if not audio_file.exists():
                logger.warning(
                    "Skipping missing file",
                    extra={"path": str(audio_file)},
                )
                continue

            segments = self.audio_processor.process_file(str(audio_file))
            if not segments:
                logger.warning(
                    "No usable segments produced",
                    extra={"path": str(audio_file)},
                )
                continue

            all_segments.extend(segments)
            total_duration += sum(getattr(s, "duration", 0.0) for s in segments)

            if len(reference_audio) < 5:
                reference_audio.append(audio_file)

        if not all_segments:
            raise RuntimeError(
                "No valid speech segments were produced from the provided audio files"
            )

        # Stage 2: timbre / base voice model
        logger.info("Stage 2/5: Timbre extraction")
        voice_profile = self.timbre_modeler.build_voice_profile(
            all_segments,
            extract_detailed=True,
        )
        self.current_voice_profile = voice_profile

        logger.info(
            "Voice profile built",
            extra={
                "f0_mean_hz": round(getattr(voice_profile, "f0_mean", 0.0), 2),
                "hnr_mean_db": round(getattr(voice_profile, "hnr_mean", 0.0), 2),
            },
        )

        # Stage 3: expression patterns (captured via prosody in profile)
        logger.info("Stage 3/5: Expression pattern learning")
        expression_summary = {
            "prosody_captured": True,
            "segment_count": len(all_segments),
            "duration_seconds": total_duration,
        }

        # Stage 4: emotion model
        emotion_models = None
        if self.tier == Tier.ULTRA and custom_emotions:
            logger.info("Stage 4/5: Custom emotion training (ULTRA)")
            emotion_models = self._build_custom_emotion_models(
                all_segments,
                custom_emotions,
            )
        else:
            logger.info("Stage 4/5: Standard emotion model mapping")

        # Stage 5: voicepack build
        logger.info("Stage 5/5: Building voicepack")

        if metadata is None:
            metadata = VoicepackMetadata(
                name=voice_name,
                tier=self.tier.value,
                training_hours=total_duration / 3600,
                sample_count=len(all_segments),
                emotions=custom_emotions or self.tier_features.available_emotions,
            )

        voicepack_path = self.voicepack_builder.build(
            name=voice_name,
            voice_profile=voice_profile,
            reference_audio=reference_audio,
            metadata=metadata,
            emotion_models=emotion_models,
            compress=True,
            encrypt=(self.tier == Tier.ULTRA),
            extras={"expression_summary": expression_summary},
        )

        logger.info(
            "Voice training complete",
            extra={
                "voicepack_path": str(voicepack_path),
                "training_time_seconds": round(time.time() - start_time, 2),
            },
        )
        return voicepack_path

    def _build_custom_emotion_models(
        self,
        segments: Sequence[Any],
        custom_emotions: Sequence[str],
    ) -> Dict[str, Dict[str, Any]]:
        """
        Placeholder for ULTRA-tier custom emotion PCA/embedding logic.
        """
        models: Dict[str, Dict[str, Any]] = {}
        for emotion_name in custom_emotions:
            models[emotion_name] = {
                "label": emotion_name,
                "segment_count": len(segments),
                "status": "placeholder-ready",
            }
        return models

    # -------------------------------------------------------------------------
    # Voicepack loading
    # -------------------------------------------------------------------------

    def load_voicepack(self, voicepack_path: Path) -> None:
        """
        Load a voicepack file and prime the GPT-SoVITS engine with its profile.
        """
        logger.info("Loading voicepack", extra={"path": str(voicepack_path)})

        if not voicepack_path.exists():
            raise FileNotFoundError(f"Voicepack not found: {voicepack_path}")

        if not self.voicepack_builder.validate(voicepack_path):
            raise ValueError(f"Invalid voicepack: {voicepack_path}")

        self.current_voicepack = self.voicepack_builder.load(voicepack_path)
        self.current_voice_profile = self.current_voicepack.get("voice_profile")

        engine = self._ensure_engine()
        reference_audio = self.current_voicepack.get("reference_audio") or []
        profile = self.current_voice_profile

        engine.load_voice(
            reference_audio=str(reference_audio[0]) if reference_audio else None,
            speaker_embedding=getattr(profile, "x_vector", None),
            metadata=self.current_voicepack.get("metadata"),
        )

        logger.info("Voicepack loaded and ready")

    # -------------------------------------------------------------------------
    # Synthesis
    # -------------------------------------------------------------------------

    def _resolve_emotion_embedding(
        self,
        emotion: Optional[str],
        emotion_intensity: float,
        sierra_signal: Optional[Dict[str, Any]],
        tonescore: Optional[float],
    ) -> Any:
        """
        Route to the right emotion embedding path:
        - Sierra signal (CHRISTMAN_MIND)
        - ToneScore™ adaptive response
        - Explicit emotion
        - Default neutral
        """
        if sierra_signal:
            return self.emotion_embedder.from_sierra_signal(
                sierra_signal["primary_emotion"],
                sierra_signal["intensity"],
            )

        if tonescore is not None:
            return self.emotion_embedder.get_response_mode_emotion(tonescore)

        if emotion:
            return self.emotion_embedder.embed_emotion(
                emotion,
                emotion_intensity,
            )

        return self.emotion_embedder.embed_emotion("neutral", 0.7)

    def synthesize(
        self,
        text: str,
        emotion: Optional[str] = None,
        emotion_intensity: float = 1.0,
        sierra_signal: Optional[Dict[str, Any]] = None,
        tonescore: Optional[float] = None,
        generate_lipsync: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text with emotional control.

        Returns a dict payload compatible with your original shape.
        """
        if self.current_voicepack is None:
            raise ValueError("No voicepack loaded. Call load_voicepack() first.")
        if not text or not text.strip():
            raise ValueError("text must be non-empty")

        logger.info(
            "Starting synthesis",
            extra={"text_preview": text[:80]},
        )
        start_time = time.time()
        engine = self._ensure_engine()

        emotion_embedding = self._resolve_emotion_embedding(
            emotion=emotion,
            emotion_intensity=emotion_intensity,
            sierra_signal=sierra_signal,
            tonescore=tonescore,
        )

        result = engine.synthesize(
            text=text,
            emotion_params=emotion_embedding.to_dict(),
            speaker_embedding=getattr(self.current_voice_profile, "x_vector", None),
            reference_audio=(self.current_voicepack.get("reference_audio") or [None])[
                0
            ],
            **kwargs,
        )

        lipsync_data = None
        if generate_lipsync:
            logger.info("Generating lip-sync data")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            try:
                if hasattr(result, "save"):
                    result.save(temp_path)
                else:
                    # Fallback if engine returns raw audio
                    engine.save_audio(result.audio, result.sample_rate, temp_path)

                phonemes = self.phoneme_labeler.label_audio(temp_path, text)
                lipsync_data = self.phoneme_labeler.phonemes_to_visemes(
                    phonemes,
                    fps=60,
                )
            finally:
                if temp_path.exists():
                    temp_path.unlink()

        payload = SynthesisResult(
            audio=result.audio,
            sample_rate=result.sample_rate,
            duration=result.duration,
            emotion=emotion_embedding.state.value,
            emotion_intensity=emotion_embedding.intensity,
            lipsync_data=lipsync_data,
            synthesis_time=time.time() - start_time,
            quality_score=getattr(result, "naturalness_mos", None),
            metadata={
                "voice": self.current_voicepack.get("metadata", {}).get("name"),
                "tier": self.tier.value,
                "engine": getattr(result, "engine", "gpt-sovits"),
            },
        )

        return payload.to_dict()

    def synthesize_to_file(
        self,
        text: str,
        output_path: Path,
        emotion: Optional[str] = None,
        emotion_intensity: float = 1.0,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Convenience wrapper: synthesize and persist to an audio file.
        """
        result = self.synthesize(
            text=text,
            emotion=emotion,
            emotion_intensity=emotion_intensity,
            **kwargs,
        )
        engine = self._ensure_engine()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        engine.save_audio(
            result["audio"],
            result["sample_rate"],
            output_path,
        )
        result["output_path"] = str(output_path)
        return result

    # -------------------------------------------------------------------------
    # Tone analysis / utilities
    # -------------------------------------------------------------------------

    def analyze_audio_tone(self, audio_path: Path) -> Dict[str, Any]:
        """
        Analyze tone of existing audio (ToneScore™).
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info("Analyzing tone", extra={"path": str(audio_path)})
        engine = ToneScoreEngine()
        return engine.analyze_tone(str(audio_path))

    def get_available_emotions(self) -> List[str]:
        """
        Emotions available for the current tier.
        """
        return list(self.tier_features.available_emotions)


__all__ = ["VoiceSynthesisOrchestrator", "SynthesisResult"]