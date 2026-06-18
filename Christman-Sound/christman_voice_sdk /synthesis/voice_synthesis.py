"""
Speech synthesis module.

Provides text-to-speech generation with support for:
- Multiple languages
- Regional English accents
- Adjustable speech rate
- Optional playback
- Simple emotion-aware parameter adjustment
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional

import pygame
from gtts import gTTS
from gtts.lang import tts_langs

logger = logging.getLogger(__name__)


def _initialize_audio_playback() -> bool:
    """Initialize the audio playback engine if available."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return True
    except Exception as exc:
        logger.warning("Audio playback initialization failed: %s", exc)
        return False


class SpeechSynthesisEngine:
    """General-purpose speech synthesis engine."""

    ENGLISH_ACCENT_PROFILES: Dict[str, Dict[str, str]] = {
        "us": {"tld": "com"},
        "uk": {"tld": "co.uk"},
        "au": {"tld": "com.au"},
        "ca": {"tld": "ca"},
        "in": {"tld": "co.in"},
        "za": {"tld": "co.za"},
        "ie": {"tld": "ie"},
    }

    def __init__(self, cache_dir: str = "voice_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.default_language = "en"
        self.default_accent = "us"
        self.default_slow = False
        self.audio_playback_ready = _initialize_audio_playback()
        self.is_playing = False

        try:
            self.available_languages = tts_langs()
            logger.info("Loaded %s available languages", len(self.available_languages))
        except Exception as exc:
            logger.error("Failed to load available languages: %s", exc)
            self.available_languages = {"en": "English"}

        logger.info("Speech synthesis engine initialized")

    def get_available_languages(self) -> Dict[str, str]:
        """Return available language codes and labels."""
        return self.available_languages

    def get_available_accents(self) -> list[str]:
        """Return available English accent codes."""
        return list(self.ENGLISH_ACCENT_PROFILES.keys())

    def _resolve_accent_tld(self, language: str, accent: Optional[str]) -> Optional[str]:
        """Resolve the TLD used for regional English voice output."""
        if language != "en":
            return None

        selected_accent = accent or self.default_accent
        profile = self.ENGLISH_ACCENT_PROFILES.get(selected_accent)
        if profile:
            return profile["tld"]

        fallback_profile = self.ENGLISH_ACCENT_PROFILES[self.default_accent]
        return fallback_profile["tld"]

    def generate_speech_audio(
        self,
        text: str,
        language: Optional[str] = None,
        accent: Optional[str] = None,
        slow: Optional[bool] = None,
        play_audio: bool = True,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """Generate speech audio from text and optionally play it."""
        if not text or not text.strip():
            logger.warning("No text provided for speech generation.")
            return None

        selected_language = language or self.default_language
        selected_slow = self.default_slow if slow is None else bool(slow)
        selected_tld = self._resolve_accent_tld(selected_language, accent)

        logger.info(
            "Generating speech audio: language=%s, accent=%s, slow=%s",
            selected_language,
            accent or self.default_accent,
            selected_slow,
        )

        try:
            tts = gTTS(
                text=text,
                lang=selected_language,
                slow=selected_slow,
                tld=selected_tld,
            )

            if output_path:
                audio_output_path = Path(output_path)
            else:
                with tempfile.NamedTemporaryFile(
                    suffix=".mp3",
                    dir=self.cache_dir,
                    delete=False,
                ) as temp_file:
                    audio_output_path = Path(temp_file.name)

            tts.save(str(audio_output_path))
            logger.info("Audio saved to %s", audio_output_path)

            if play_audio:
                self.play_audio_file(str(audio_output_path))

            return str(audio_output_path)

        except Exception as exc:
            logger.error("Speech generation failed: %s", exc)
            return None

    def play_audio_file(self, audio_path: str) -> bool:
        """Play an audio file if playback is available."""
        if not self.audio_playback_ready:
            logger.warning("Audio playback is not available in this environment.")
            return False

        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            self.is_playing = True
            logger.info("Playing audio: %s", audio_path)
            return True

        except Exception as exc:
            logger.error("Audio playback failed: %s", exc)
            self.is_playing = False
            return False

    def stop_audio_playback(self) -> bool:
        """Stop active audio playback."""
        if not self.audio_playback_ready:
            return False

        if self.is_audio_playing():
            pygame.mixer.music.stop()
            self.is_playing = False
            logger.info("Audio playback stopped")
            return True

        return False

    def is_audio_playing(self) -> bool:
        """Return True when audio is currently playing."""
        if not self.audio_playback_ready:
            return False
        return pygame.mixer.music.get_busy()

    def update_default_settings(
        self,
        language: Optional[str] = None,
        accent: Optional[str] = None,
        slow: Optional[bool] = None,
    ) -> Dict[str, object]:
        """Update default synthesis settings."""
        if language:
            if language in self.available_languages:
                self.default_language = language
            else:
                logger.warning(
                    "Language '%s' is not available; keeping %s",
                    language,
                    self.default_language,
                )

        if accent:
            if accent in self.ENGLISH_ACCENT_PROFILES:
                self.default_accent = accent
            else:
                logger.warning(
                    "Accent '%s' is not available; keeping %s",
                    accent,
                    self.default_accent,
                )

        if slow is not None:
            self.default_slow = bool(slow)

        settings = {
            "language": self.default_language,
            "accent": self.default_accent,
            "slow": self.default_slow,
        }

        logger.info("Default settings updated: %s", settings)
        return settings

    def generate_emotion_adjusted_speech(
        self,
        text: str,
        emotion: Optional[str] = None,
        emotion_intensity: Optional[str] = None,
        language: Optional[str] = None,
        accent: Optional[str] = None,
    ) -> Optional[str]:
        """Generate speech with simple emotion-aware adjustments."""
        selected_slow = self.default_slow
        adjusted_text = text

        if emotion:
            normalized_emotion = emotion.lower()
            logger.info(
                "Applying emotional context: emotion=%s, intensity=%s",
                normalized_emotion,
                emotion_intensity,
            )

            if normalized_emotion in {"sad", "unhappy", "depressed"}:
                selected_slow = True

            if emotion_intensity == "strong":
                adjusted_text = f"[With strong {emotion}] {text}"
            elif emotion_intensity == "moderate":
                adjusted_text = f"[With moderate {emotion}] {text}"
            elif emotion_intensity:
                adjusted_text = f"[With mild {emotion}] {text}"

        return self.generate_speech_audio(
            adjusted_text,
            language=language,
            accent=accent,
            slow=selected_slow,
        )


_speech_synthesis_engine: Optional[SpeechSynthesisEngine] = None


def get_speech_synthesis_engine() -> SpeechSynthesisEngine:
    """Return the shared speech synthesis engine instance."""
    global _speech_synthesis_engine

    if _speech_synthesis_engine is None:
        _speech_synthesis_engine = SpeechSynthesisEngine()

    return _speech_synthesis_engine

# ==============================================================================
# Patent Pending
# Christman-AI Family
# Shared-neutral implementation for internal system use.
# ==============================================================================
