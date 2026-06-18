# © 2025 The Christman AI Project. All rights reserved.
#
# This code is released as part of a trauma-informed, dignity-first AI ecosystem
# designed to protect, empower, and elevate vulnerable populations.
#
# By using, modifying, or distributing this software, you agree to uphold the following:
# 1. Truth — No deception, no manipulation.
# 2. Dignity — Respect the autonomy and humanity of all users.
# 3. Protection — Never use this to exploit or harm vulnerable individuals.
# 4. Transparency — Disclose all modifications and contributions clearly.
# 5. No Erasure — Preserve the mission and ethical origin of this work.
#
# This is not just code. This is redemption in code.
# Contact: lumacognify@thechristmanaiproject.com
# https://thechristmanaiproject.com

"""
BROCKSTON - Speech Integration Module
-----------------------------------
This module provides integration between the BROCKSTON system and
speech recognition services, both internal and external.
"""

import logging
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Singleton instance
_speech_integration = None


class SpeechIntegration:
    """
    Handles integration between BROCKSTON and speech recognition services.

    This class provides:
    - Access to the speech recognition engine
    - Processing of speech data
    - Management of speech recognition models
    - Access to enhanced speech recognition from attached assets
    """

    def __init__(self):
        """Initialize speech integration"""
        # Speech recognition engine
        self.speech_engine = None
        self.enhanced_recognition = None

        # Recognition parameters
        self.default_language = "en-US"
        self.confidence_threshold = 0.65

        # Initialize components
        self._initialize_components()

        logger.info("Speech Integration initialized")

    def _initialize_components(self):
        """Initialize speech recognition components"""
        # Try to load the real speech recognition engine
        try:
            from audio.real_speech_recognition import get_speech_recognition_engine

            self.speech_engine = get_speech_recognition_engine()
            logger.info("Real speech recognition engine loaded")
        except ImportError:
            logger.warning("Real speech recognition engine not available")

        # Try to load enhanced speech recognition
        try:
            from audio.enhanced_speech_recognition import (
                EnhancedSpeechRecognition,
            )

            self.enhanced_recognition = EnhancedSpeechRecognition()
            logger.info("Enhanced speech recognition loaded")
        except ImportError:
            logger.warning("Enhanced speech recognition not available")

    def process_audio_data(
        self, audio_data: bytes, sample_rate: int = 16000
    ) -> Dict[str, Any]:
        """
        Process audio data for speech recognition

        Args:
            audio_data: Raw audio data bytes
            sample_rate: Sample rate of the audio data

        Returns:
            Dict with recognition results
        """
        # Try enhanced recognition first if available
        if self.enhanced_recognition:
            try:
                result = self.enhanced_recognition.recognize_speech(
                    audio_data, sample_rate
                )
                if result and not result.get("error"):
                    return result
            except Exception as e:
                logger.error(f"Error in enhanced speech recognition: {e}")

        # Fall back to real speech recognition
        if self.speech_engine:
            try:
                result = self.speech_engine.process_audio_data(audio_data, sample_rate)
                return result
            except Exception as e:
                logger.error(f"Error in real speech recognition: {e}")

        # Return error if no recognition available
        return {"error": "Speech recognition not available", "status": "error"}

    def get_available_languages(self) -> List[Dict[str, str]]:
        """
        Get available recognition languages

        Returns:
            List of language dictionaries with code and name
        """
        # Try to get languages from enhanced recognition
        if self.enhanced_recognition and hasattr(
            self.enhanced_recognition, "get_available_languages"
        ):
            try:
                return self.enhanced_recognition.get_available_languages()
            except Exception as e:
                logger.error(f"Error getting languages from enhanced recognition: {e}")

        # Try to get languages from speech engine
        if self.speech_engine and hasattr(
            self.speech_engine, "get_available_languages"
        ):
            try:
                return self.speech_engine.get_available_languages()
            except Exception as e:
                logger.error(f"Error getting languages from speech engine: {e}")

        # Fallback to basic languages
        return [
            {"code": "en-US", "name": "English (US)"},
            {"code": "en-GB", "name": "English (UK)"},
            {"code": "fr-FR", "name": "French"},
            {"code": "de-DE", "name": "German"},
            {"code": "es-ES", "name": "Spanish"},
            {"code": "it-IT", "name": "Italian"},
            {"code": "ja-JP", "name": "Japanese"},
            {"code": "zh-CN", "name": "Chinese (Simplified)"},
            {"code": "ru-RU", "name": "Russian"},
            {"code": "pt-BR", "name": "Portuguese (Brazil)"},
        ]

    def set_recognition_language(self, language_code: str) -> Dict[str, Any]:
        """
        Set the speech recognition language

        Args:
            language_code: ISO language code (e.g., 'en-US')

        Returns:
            Dict with status information
        """
        # Try to set language in enhanced recognition
        if self.enhanced_recognition and hasattr(
            self.enhanced_recognition, "set_language"
        ):
            try:
                result = self.enhanced_recognition.set_language(language_code)
                if result and result.get("status") == "success":
                    self.default_language = language_code
                    return result
            except Exception as e:
                logger.error(f"Error setting language in enhanced recognition: {e}")

        # Try to set language in speech engine
        if self.speech_engine and hasattr(self.speech_engine, "set_language"):
            try:
                result = self.speech_engine.set_language(language_code)
                if result:
                    self.default_language = language_code
                    return result
            except Exception as e:
                logger.error(f"Error setting language in speech engine: {e}")

        # Return status
        self.default_language = language_code
        return {"status": "success", "message": f"Language set to {language_code}"}


def get_speech_integration():
    """Get or create the speech integration singleton"""
    global _speech_integration
    if _speech_integration is None:
        _speech_integration = SpeechIntegration()
    return _speech_integration


__all__ = ["get_speech_integration", "SpeechIntegration"]
