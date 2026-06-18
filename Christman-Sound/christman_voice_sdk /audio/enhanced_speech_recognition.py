# ==============================================================================
# © 2025 Everett Nathaniel Christman & Misty Gail Christman
# The Christman AI Project — Luma Cognify AI
# All rights reserved. Unauthorized use, replication, or derivative training
# of this material is prohibited.
#
# Truth. Dignity. Protection. Transparency. No Erasure.
# Contact: contact@thechristmanaiproject.com
# https://thechristmanaiproject.com
# ==============================================================================

"""
Enhanced speech recognition.

Combines:
- Verbal speech recognition (simulated placeholder).
- Non-verbal sound pattern recognition via SoundRecognitionService.

Provides:
- Integration with the existing sound recognition service.
- Streaming / continuous listening hooks.
- Web or external microphone capture integration points.
- Recognition context tracking (recent phrases, keywords).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class EnhancedSpeechRecognition:
    """
    Enhanced speech recognition system that combines verbal speech recognition
    with non-verbal sound pattern recognition.

    This class provides:
    - Integration with SoundRecognitionService (if available).
    - Streaming / continuous listening mode.
    - Callback-based delivery of speech and sound pattern events.
    - Lightweight recognition context tracking.
    """

    def __init__(self) -> None:
        """Initialize the enhanced speech recognition system."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing EnhancedSpeechRecognition")

        self.is_listening: bool = False
        self.is_processing: bool = False
        self.current_audio_data: List[bytes] = []

        self.speech_callbacks: List[Callable[..., None]] = []
        self.sound_pattern_callbacks: List[Callable[..., None]] = []

        self.language: str = "en-US"
        self.sensitivity: float = 0.5
        self.silence_threshold: float = 0.1
        self.min_audio_length: float = 0.5

        self.recognition_context: Dict[str, Any] = {
            "recent_phrases": [],
            "current_topic": None,
            "active_keywords": [],
        }

        self.audio_cache_dir = os.path.join("static", "audio", "recognition_cache")
        os.makedirs(self.audio_cache_dir, exist_ok=True)

        try:
            from audio.sound_recognition_service import SoundRecognitionService

            self.sound_service: Optional[Any] = SoundRecognitionService()
            self.logger.info("Sound recognition service loaded")
        except ImportError:
            self.sound_service = None
            self.logger.warning("Sound recognition service not available")

        self.logger.info("EnhancedSpeechRecognition initialized")

    def start_listening(
        self,
        speech_callback: Optional[Callable[[str, float, Dict[str, Any]], None]] = None,
        sound_pattern_callback: Optional[
            Callable[[Any, float, Dict[str, Any]], None]
        ] = None,
    ) -> bool:
        """
        Start listening for speech and sound patterns.

        Args:
            speech_callback: Optional callback(text, confidence, metadata).
            sound_pattern_callback: Optional callback(pattern, confidence, metadata).

        Returns:
            True if started successfully, False otherwise.
        """
        if self.is_listening:
            self.logger.warning("Speech recognition is already active")
            return False

        if speech_callback:
            self.speech_callbacks.append(speech_callback)

        if sound_pattern_callback:
            self.sound_pattern_callbacks.append(sound_pattern_callback)

        if self.sound_service:
            self.sound_service.start_listening()

        self.is_listening = True
        self._start_listening_thread()
        self.logger.info("Speech recognition started")
        return True

    def stop_listening(self) -> bool:
        """
        Stop listening for speech and sound patterns.

        Returns:
            True if stopped successfully, False otherwise.
        """
        if not self.is_listening:
            self.logger.warning("Speech recognition is not active")
            return False

        if self.sound_service:
            self.sound_service.stop_listening()

        self.is_listening = False
        self.logger.info("Speech recognition stopped")
        return True

    def _start_listening_thread(self) -> None:
        """Start the background listening thread."""
        thread = threading.Thread(target=self._listening_loop, name="speech_listener")
        thread.daemon = True
        thread.start()

    def _listening_loop(self) -> None:
        """Main listening loop that runs in the background."""
        self.logger.debug("Listening loop started")

        while self.is_listening:
            try:
                if self.sound_service:
                    sound_result = self.sound_service.detect_sound_pattern()
                    if sound_result:
                        self._process_sound_pattern(sound_result)

                self._simulate_speech_recognition()
                time.sleep(0.1)
            except Exception as e:
                self.logger.error("Error in listening loop: %s", e, exc_info=True)

        self.logger.debug("Listening loop ended")

    def _simulate_speech_recognition(self) -> None:
        """
        Simulate speech recognition for testing and development.

        In a real implementation, this would process actual audio streams.
        """
        if not hasattr(self, "_last_simulation_time"):
            self._last_simulation_time = 0.0

        current_time = time.time()
        simulation_interval = 10.0 + (5.0 * self.sensitivity)

        if current_time - self._last_simulation_time < simulation_interval:
            return

        import random

        if random.random() < 0.1:
            self._last_simulation_time = current_time

            sample_phrases = [
                "Hello, how are you today?",
                "Can you tell me more about nonverbal communication?",
                "I would like to learn about eye tracking.",
                "Can you explain how this AI system works?",
                "Thank you for helping me communicate.",
            ]

            recognized_text = random.choice(sample_phrases)
            confidence = 0.7 + (random.random() * 0.25)

            metadata: Dict[str, Any] = {
                "confidence": confidence,
                "language": self.language,
                "timestamp": current_time,
                "audio_length": random.uniform(1.0, 3.0),
                "source": "simulation",
            }

            self.logger.info(
                "Simulated speech recognition: '%s' (confidence: %.2f)",
                recognized_text,
                confidence,
            )

            self._process_recognized_speech(recognized_text, metadata)

    def process_audio_data(
        self, audio_data: bytes, sample_rate: int = 16000, format_: str = "wav"
    ) -> Dict[str, Any]:
        """
        Process audio data and perform speech recognition.

        Args:
            audio_data: Raw audio data bytes.
            sample_rate: Sample rate of the audio.
            format_: Audio format label.

        Returns:
            Dict with recognition results or error description.
        """
        if not audio_data:
            return {"error": "No audio data provided"}

        self.logger.info("Processing %d bytes of audio data", len(audio_data))
        self.is_processing = True

        try:
            import uuid
            from datetime import datetime
            import random

            file_id = str(uuid.uuid4())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = os.path.join(
                self.audio_cache_dir, f"audio_{timestamp}_{file_id}.{format_}"
            )

            # Placeholder: in a full implementation, audio_data would be written and
            # passed to a real ASR engine.

            sample_phrases = [
                "Hello, this is a speech recognition test.",
                "Can you help me with communication?",
                "This is a test of the recognition pipeline.",
                "I would like to know more about this system.",
                "Thank you for assisting with my speech.",
            ]

            recognized_text = random.choice(sample_phrases)
            confidence = 0.7 + (random.random() * 0.25)

            result: Dict[str, Any] = {
                "text": recognized_text,
                "confidence": confidence,
                "language": self.language,
                "timestamp": time.time(),
                "audio_path": file_path,
            }

            self.logger.info(
                "Audio processing result: '%s' (confidence: %.2f)",
                recognized_text,
                confidence,
            )

            self._update_recognition_context(recognized_text)
            self._process_recognized_speech(recognized_text, result)

            return result
        except Exception as e:
            self.logger.error("Error processing audio data: %s", e, exc_info=True)
            return {"error": str(e)}
        finally:
            self.is_processing = False

    def _process_recognized_speech(self, text: str, metadata: Dict[str, Any]) -> None:
        """
        Process recognized speech and notify callbacks.

        Args:
            text: Recognized text.
            metadata: Recognition metadata.
        """
        if not text:
            return

        self._update_recognition_context(text)

        for callback in list(self.speech_callbacks):
            try:
                callback(text, metadata.get("confidence", 0.0), metadata)
            except Exception as e:
                self.logger.error("Error in speech callback: %s", e, exc_info=True)

    def _process_sound_pattern(self, sound_result: Dict[str, Any]) -> None:
        """
        Process detected sound pattern and notify callbacks.

        Args:
            sound_result: Sound pattern detection result.
        """
        if not sound_result:
            return

        pattern = sound_result.get("pattern")
        confidence = sound_result.get("confidence", 0.0)

        intent_data: Dict[str, Any] = {}
        if self.sound_service:
            try:
                intent_data = self.sound_service.classify_sound_intent(pattern)
            except Exception as e:
                self.logger.error("Error classifying sound intent: %s", e, exc_info=True)

        combined_data = {**sound_result, **intent_data}

        for callback in list(self.sound_pattern_callbacks):
            try:
                callback(pattern, confidence, combined_data)
            except Exception as e:
                self.logger.error("Error in sound pattern callback: %s", e, exc_info=True)

    def _update_recognition_context(self, text: str) -> None:
        """
        Update the recognition context with newly recognized text.

        Args:
            text: Recognized text.
        """
        phrases = self.recognition_context["recent_phrases"]
        phrases.append(text)
        if len(phrases) > 5:
            phrases.pop(0)

        # Placeholder: a full implementation would update topic and keywords using NLP.

    def set_language(self, language: str) -> bool:
        """Set the recognition language."""
        self.language = language
        self.logger.info("Recognition language set to: %s", language)
        return True

    def set_sensitivity(self, sensitivity: float) -> bool:
        """
        Set the recognition sensitivity.

        Args:
            sensitivity: Sensitivity value (0.0–1.0).
        """
        if sensitivity < 0.0 or sensitivity > 1.0:
            self.logger.error("Invalid sensitivity value: %.3f", sensitivity)
            return False

        self.sensitivity = sensitivity
        self.logger.info("Recognition sensitivity set to: %.3f", sensitivity)
        return True

    def add_recognition_keywords(self, keywords: List[str]) -> bool:
        """
        Add keywords to prioritize in recognition.

        Args:
            keywords: List of keywords to prioritize.
        """
        if not isinstance(keywords, list):
            self.logger.error("Keywords must be a list")
            return False

        self.recognition_context["active_keywords"].extend(keywords)
        self.logger.info("Added recognition keywords: %s", keywords)
        return True

    def clear_recognition_keywords(self) -> bool:
        """Clear all recognition keywords."""
        self.recognition_context["active_keywords"] = []
        self.logger.info("Cleared recognition keywords")
        return True

    def get_recognition_status(self) -> Dict[str, Any]:
        """Return the current status of the speech recognition system."""
        return {
            "is_listening": self.is_listening,
            "is_processing": self.is_processing,
            "language": self.language,
            "sensitivity": self.sensitivity,
            "context": {
                "recent_phrases_count": len(
                    self.recognition_context["recent_phrases"]
                ),
                "current_topic": self.recognition_context["current_topic"],
                "active_keywords_count": len(
                    self.recognition_context["active_keywords"]
                ),
            },
        }


_enhanced_speech_recognition: Optional[EnhancedSpeechRecognition] = None


def get_enhanced_speech_recognition() -> EnhancedSpeechRecognition:
    """Return the singleton enhanced speech recognition instance."""
    global _enhanced_speech_recognition
    if _enhanced_speech_recognition is None:
        _enhanced_speech_recognition = EnhancedSpeechRecognition()
    return _enhanced_speech_recognition


__all__ = ["EnhancedSpeechRecognition", "get_enhanced_speech_recognition"]

# ==============================================================================
# Patent Pending
# Christman-AI Family
# Shared-neutral implementation for internal system use.
# Core Directive: "How can I help you love yourself more?"
# ==============================================================================
