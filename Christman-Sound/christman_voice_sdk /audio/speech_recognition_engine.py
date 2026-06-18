#!/usr/bin/env python3
"""
Shared-neutral speech recognition engine.

Features:
- Live microphone recognition
- File-based recognition
- Simulated recognition mode
- Callback-based result delivery
"""

import logging
import os
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

import speech_recognition_engine as sr

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

AUDIO_CACHE_DIR = "audio_cache"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)


class SpeechRecognitionEngine:
    """
    Speech recognition engine using the speech_recognition library.

    Modes:
    - simulate: generate canned phrases on a timer
    - file: recognize from a configured test audio file
    - microphone: recognize from the selected input device
    """

    def __init__(
        self,
        language: str = "en-US",
        simulate: bool = False,
        device_index: Optional[int] = None,
    ) -> None:
        self.language: str = language
        self.simulate: bool = simulate
        self.device_index: Optional[int] = device_index

        self.is_listening: bool = False
        self.callbacks: list[Callable[[str, float, Dict[str, Any]], None]] = []

        self.recognizer = sr.Recognizer()

        logger.info(
            "SpeechRecognitionEngine init: language=%s simulate=%s device_index=%s",
            language,
            simulate,
            device_index,
        )

    # -------------------------------------------------------------------------
    # Public control methods
    # -------------------------------------------------------------------------

    def start_listening(
        self,
        callback: Optional[Callable[[str, float, Dict[str, Any]], None]] = None,
    ) -> bool:
        """
        Start background recognition according to the configured mode.

        Args:
            callback: Optional callback invoked with (text, confidence, metadata).

        Returns:
            True if started; False if already active.
        """
        if self.is_listening:
            logger.warning("Speech recognition is already active.")
            return False

        if callback is not None:
            self.callbacks.append(callback)

        self.is_listening = True
        self._start_listening_thread()
        return True

    def stop_listening(self) -> bool:
        """
        Stop background recognition.

        Returns:
            True if stopped; False if it was not active.
        """
        if not self.is_listening:
            logger.warning("Speech recognition is not active.")
            return False

        self.is_listening = False
        return True

    # -------------------------------------------------------------------------
    # Core recognition entrypoint
    # -------------------------------------------------------------------------

    def recognize_from_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Recognize speech from raw audio bytes.

        Args:
            audio_bytes: Raw PCM audio data.
            sample_rate: Sample rate of audio in Hz.

        Returns:
            (text, confidence, metadata) triple.
        """
        audio_data = sr.AudioData(audio_bytes, sample_rate, 2)

        try:
            text = self.recognizer.recognize_google(
                audio_data,
                language=self.language,
            )
            metadata: Dict[str, Any] = {
                "language": self.language,
                "duration": len(audio_bytes) / (sample_rate * 2),
                "timestamp": time.time(),
            }
            return text, 0.9, metadata

        except sr.UnknownValueError:
            return "[Unrecognized speech]", 0.0, {"error": "unrecognized"}

        except sr.RequestError as exc:
            return "[Speech API error]", 0.0, {"error": str(exc)}

    # -------------------------------------------------------------------------
    # Background loops
    # -------------------------------------------------------------------------

    def _start_listening_thread(self) -> None:
        thread = threading.Thread(target=self._audio_processing_loop)
        thread.daemon = True
        thread.start()

    def _audio_processing_loop(self) -> None:
        if self.simulate:
            self._simulate_loop()
        elif self.device_index == -1:
            self._file_audio_loop()
        else:
            self._microphone_loop()

    def _simulate_loop(self) -> None:
        phrases = [
            "Hello, how are you?",
            "What can you help me with?",
            "I need assistance.",
        ]

        while self.is_listening:
            text = phrases[int(time.time()) % len(phrases)]
            metadata = {
                "language": self.language,
                "duration": 1.0,
                "timestamp": time.time(),
                "mode": "simulate",
            }
            for cb in self.callbacks:
                try:
                    cb(text, 0.95, metadata)
                except Exception as exc:
                    logger.error("Callback error in simulate loop: %s", exc)
            time.sleep(5.0)

    def _file_audio_loop(self) -> None:
        logger.info("Loading audio from fallback test file.")
        test_file = os.getenv("TEST_SPEECH_AUDIO", "media/audio/test_input.wav")

        if not os.path.exists(test_file):
            logger.warning("Test file not found: %s", test_file)
            return

        with sr.AudioFile(test_file) as source:
            audio = self.recognizer.record(source)

        try:
            text = self.recognizer.recognize_google(
                audio,
                language=self.language,
            )
            logger.info("Recognized from file: %s", text)
            metadata = {
                "mode": "file",
                "timestamp": time.time(),
                "language": self.language,
            }
            for cb in self.callbacks:
                try:
                    cb(text, 0.99, metadata)
                except Exception as exc:
                    logger.error("Callback error in file loop: %s", exc)

        except Exception as exc:
            logger.error("File recognition error: %s", exc)
            for cb in self.callbacks:
                try:
                    cb("", 0.0, {"error": str(exc), "mode": "file"})
                except Exception as cb_exc:
                    logger.error("Callback error after file error: %s", cb_exc)

    def _microphone_loop(self) -> None:
        """
        Microphone-based live recognition loop.

        Uses the configured device_index; if None, default microphone is used.
        """
        try:
            mic = sr.Microphone(device_index=self.device_index)
        except Exception as exc:
            logger.error("Microphone initialization error: %s", exc)
            for cb in self.callbacks:
                try:
                    cb("", 0.0, {"error": str(exc), "mode": "mic_init"})
                except Exception as cb_exc:
                    logger.error("Callback error after mic init error: %s", cb_exc)
            return

        with mic as source:
            self.recognizer.energy_threshold = 300  # Static threshold
            logger.info(
                "Listening started (PyAudio Mic) with threshold %s",
                self.recognizer.energy_threshold,
            )

            while self.is_listening:
                try:
                    audio = self.recognizer.listen(source, timeout=None)

                    # Debug dump of raw input for inspection
                    os.makedirs("media/audio", exist_ok=True)
                    debug_path = "media/audio/debug_input.wav"
                    with open(debug_path, "wb") as f:
                        f.write(audio.get_wav_data())

                    text = self.recognizer.recognize_google(
                        audio,
                        language=self.language,
                    )
                    logger.info("Recognized: %s", text)

                    metadata = {
                        "mode": "live",
                        "timestamp": time.time(),
                        "language": self.language,
                    }

                    for cb in self.callbacks:
                        try:
                            cb(text, 0.9, metadata)
                        except Exception as cb_exc:
                            logger.error("Callback error in mic loop: %s", cb_exc)

                except sr.UnknownValueError:
                    logger.warning("Could not understand audio.")
                    for cb in self.callbacks:
                        try:
                            cb("", 0.0, {"error": "unrecognized", "mode": "live"})
                        except Exception as cb_exc:
                            logger.error("Callback error after unrecognized audio: %s", cb_exc)

                except Exception as exc:
                    logger.error("Microphone recognition error: %s", exc)
                    for cb in self.callbacks:
                        try:
                            cb("", 0.0, {"error": str(exc), "mode": "live"})
                        except Exception as cb_exc:
                            logger.error("Callback error after mic error: %s", cb_exc)

    # -------------------------------------------------------------------------
    # Utility functions
    # -------------------------------------------------------------------------


_speech_recognition_engine: Optional[SpeechRecognitionEngine] = None


def get_speech_recognition_engine(
    simulate: bool = False,
    device_index: Optional[int] = None,
    language: str = "en-US",
) -> SpeechRecognitionEngine:
    """
    Get or create the shared SpeechRecognitionEngine instance.
    """
    global _speech_recognition_engine
    if _speech_recognition_engine is None:
        _speech_recognition_engine = SpeechRecognitionEngine(
            language=language,
            simulate=simulate,
            device_index=device_index,
        )
    return _speech_recognition_engine


def list_microphones() -> list[str]:
    """
    List available microphone device names.
    """
    return sr.Microphone.list_microphone_names()


if __name__ == "__main__":
    print("Available microphones:")
    for i, name in enumerate(list_microphones()):
        print(f"{i}: {name}")


# ==============================================================================
# Patent Pending
# Christman-AI Family
# Shared-neutral implementation for internal system use.
# ==============================================================================
