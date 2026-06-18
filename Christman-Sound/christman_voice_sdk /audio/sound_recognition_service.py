import logging
import random
import time

import numpy as np # pyright: ignore[reportMissingImports]

# For backward compatibility, try to import the simulated speech engine
try:
    from audio.speech_recognition_engine import get_speech_recognition_engine

    SIMULATED_ENGINE_AVAILABLE = True
except ImportError:
    SIMULATED_ENGINE_AVAILABLE = False


class SoundRecognitionService:
    """Service for recognizing vocal patterns from nonverbal users.

    This service can use either a real speech recognition engine or
    simulated data for demonstration purposes.
    """

    def __init__(self, speech_engine=None):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing SoundRecognitionService")

        # Define sound patterns for classification
        self.sound_patterns = ["hum", "click", "distress", "soft", "loud"]

        # Last detected sound
        self.last_detected_sound = None
        self.last_detected_time = 0

        # Speech recognition engine
        self.speech_engine = speech_engine

        # If no engine provided, try to get simulated engine
        if self.speech_engine is None and SIMULATED_ENGINE_AVAILABLE:
            try:
                self.speech_engine = get_speech_recognition_engine()
                self.logger.info("Using simulated speech recognition engine")
            except Exception as e:
                self.logger.warning(
                    f"Could not initialize simulated speech engine: {e}"
                )
                self.speech_engine = None

        # Real speech recognition mode if engine is provided
        self.using_real_recognition = self.speech_engine is not None
        if self.using_real_recognition:
            self.logger.info("Using real speech recognition engine")
        else:
            self.logger.info("Using simulated sound recognition")

        self.logger.info("SoundRecognitionService initialized")

    def detect_sound_pattern(self, audio_data=None):
        """Detect sound pattern from audio data.

        In real mode, this uses speech recognition results collected via callback.
        In simulation mode, it generates random detections for demonstration.

        Args:
            audio_data: Audio data (optional, can be used for direct analysis)

        Returns:
            dict: Detection result with pattern and confidence
        """
        current_time = time.time()

        # If we're using real recognition and have a recent detection
        if self.using_real_recognition and self.last_detected_sound:
            # Only return each sound once (within a time window)
            if current_time - self.last_detected_time < 2.0:  # 2 second window
                sound_pattern = self.last_detected_sound
                self.last_detected_sound = None  # Reset to avoid duplicates

                confidence = 0.85  # Real detections have higher confidence

                self.logger.info(
                    f"Detected real sound pattern: {sound_pattern} "
                    f"(confidence: {confidence:.2f})"
                )

                return {
                    "pattern": sound_pattern,
                    "confidence": confidence,
                    "timestamp": current_time,
                    "real_detection": True,
                }

        # Fallback to simulation mode for demo purposes
        else:
            # Only generate new sound every 5-10 seconds
            if current_time - self.last_detected_time > random.uniform(5.0, 10.0):
                # 20% chance of detecting a sound
                if random.random() < 0.2:
                    sound_pattern = random.choice(self.sound_patterns)
                    self.last_detected_time = current_time
                    confidence = random.uniform(0.6, 0.95)

                    self.logger.info(
                        f"Detected simulated sound pattern: {sound_pattern} "
                        f"(confidence: {confidence:.2f})"
                    )

                    return {
                        "pattern": sound_pattern,
                        "confidence": confidence,
                        "timestamp": current_time,
                        "real_detection": False,
                    }

        # No sound detected
        return None

    def classify_sound_intent(self, sound_pattern):
        """Classify the intent behind a detected sound pattern.

        Args:
            sound_pattern: Detected sound pattern

        Returns:
            dict: Intent classification with confidence
        """
        # Map sound patterns to intents
        intent_map = {
            "hum": {"intent": "thinking", "confidence": 0.7},
            "click": {"intent": "select", "confidence": 0.8},
            "distress": {"intent": "help", "confidence": 0.9},
            "soft": {"intent": "unsure", "confidence": 0.6},
            "loud": {"intent": "excited", "confidence": 0.8},
            # Add speech pattern from real recognition
            "speech": {"intent": "communicate", "confidence": 0.9},
        }

        # Get intent or default to unknown
        result = intent_map.get(sound_pattern, {"intent": "unknown", "confidence": 0.4})

        # Add some randomness to confidence for simulated patterns
        # but keep higher confidence for real speech recognition
        if sound_pattern != "speech":
            confidence_variation = random.uniform(-0.1, 0.1)
            result["confidence"] = min(
                0.95, max(0.2, result["confidence"] + confidence_variation)
            )

        self.logger.debug(
            f"Classified sound {sound_pattern} as {result['intent']} "
            f"(confidence: {result['confidence']:.2f})"
        )

        return result

    def start_listening(self):
        """Start the sound recognition service.

        If a real speech recognition engine is available, it will be
        used. Otherwise, the simulation mode will be activated.
        """
        if self.using_real_recognition and self.speech_engine:
            # Define a callback for speech recognition
            def speech_callback(text, confidence, metadata):
                self.logger.info(
                    f"Speech recognized: '{text}' (confidence: {confidence:.2f})"
                )
                # Process the speech as a sound pattern
                self.last_detected_sound = "speech"
                self.last_detected_time = time.time()

                # We could analyze the text further for more specific patterns
                if any(
                    word in text.lower()
                    for word in ["help", "need", "please", "urgent"]
                ):
                    self.last_detected_sound = "distress"
                elif any(
                    word in text.lower() for word in ["select", "this", "that", "click"]
                ):
                    self.last_detected_sound = "click"
                elif any(word in text.lower() for word in ["hmm", "um", "thinking"]):
                    self.last_detected_sound = "hum"

            # Start the real speech recognition
            self.speech_engine.start_listening(callback=speech_callback)
            self.logger.info("Started real speech recognition")
        else:
            # Use simulated sound recognition
            self.logger.info("Started simulated sound recognition")

    def stop_listening(self):
        """Stop the sound recognition service.

        If a real speech recognition engine is being used, it will be
        stopped.
        """
        if self.using_real_recognition and self.speech_engine:
            # Stop the real speech recognition
            self.speech_engine.stop_listening()
            self.logger.info("Stopped real speech recognition")
        else:
            # Stop simulated sound recognition
            self.logger.info("Stopped simulated sound recognition")
