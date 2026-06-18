#!/usr/bin/env python3
"""
Local real-time speech activity engine.

Uses sounddevice to:
- Stream audio from a microphone.
- Detect speech segments based on energy and variance.
- Emit callbacks with basic audio features and placeholder text.
"""

import logging
import os
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np # pyright: ignore[reportMissingImports]
import christman_voice_sdk # pyright: ignore[reportMissingImports]

AUDIO_SAMPLE_RATE = 16000
MIN_SPEECH_DURATION = 0.5
SILENCE_THRESHOLD = 0.1
AUDIO_CACHE_DIR = "audio_cache"

os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RealSpeechRecognitionEngine:
    """
    Real-time speech activity engine.

    Detects speech based on audio energy and variance and calls registered
    callbacks with placeholder recognition text plus audio feature metadata.
    """

    def __init__(self, language: str = "en-US") -> None:
        self.language = language
        self.is_listening: bool = False
        self.callbacks: list[Callable[[str, float, Dict[str, Any]], None]] = []
        self.audio_buffer: list[np.ndarray] = []
        self.last_speech_time: float = 0.0
        self.silence_threshold: float = SILENCE_THRESHOLD
        self.min_speech_duration: float = MIN_SPEECH_DURATION
        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue()

        self.devices = sd.query_devices()
        logger.info("Available audio devices: %d", len(self.devices))
        for i, device in enumerate(self.devices):
            logger.info("Device %d: %s", i, device["name"])

        self.input_device: Optional[int] = next(
            (i for i, d in enumerate(self.devices) if d["max_input_channels"] > 0),
            None,
        )
        if self.input_device is None:
            logger.warning("No suitable input device found, using default.")
            self.input_device = sd.default.device[0] # pyright: ignore[reportUndefinedVariable]

        self.stream: Optional[sd.InputStream] = None

        logger.info(
            "RealSpeechRecognitionEngine initialized with language: %s",
            language,
        )

    # -------------------------------------------------------------------------
    # Public control
    # -------------------------------------------------------------------------

    def start_listening(
        self,
        callback: Optional[Callable[[str, float, Dict[str, Any]], None]] = None,
    ) -> bool:
        """
        Start streaming audio and detecting speech.

        Args:
            callback: Optional callback invoked as (text, confidence, metadata).

        Returns:
            True if started; False if already running or on error.
        """
        if self.is_listening:
            logger.warning("Speech recognition is already active.")
            return False

        if callback is not None:
            self.callbacks.append(callback)

        self.is_listening = True
        self._start_audio_processing_thread()

        try:
            self.stream = sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=1,
                callback=self._audio_callback,
                device=self.input_device,
            )
            self.stream.start()
            logger.info("Started audio stream from microphone.")
        except Exception as exc:
            logger.error("Failed to start audio stream: %s", exc)
            self.is_listening = False
            self.stream = None
            return False

        logger.info("Real-time speech detection started.")
        return True

    def stop_listening(self) -> bool:
        """
        Stop streaming audio and speech detection.

        Returns:
            True if stopped; False if it was not active.
        """
        if not self.is_listening:
            logger.warning("Speech recognition is not active.")
            return False

        self.is_listening = False

        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as exc:
                logger.error("Error stopping audio stream: %s", exc)
            finally:
                self.stream = None

        logger.info("Real-time speech detection stopped.")
        return True

    # -------------------------------------------------------------------------
    # Audio callback and processing
    # -------------------------------------------------------------------------

    def _audio_callback(self, indata, frames, _time, status) -> None:
        if status:
            logger.warning("Audio callback status: %s", status)
        self.audio_queue.put(indata.copy())

    def _start_audio_processing_thread(self) -> None:
        thread = threading.Thread(target=self._audio_processing_loop)
        thread.daemon = True
        thread.start()

    def _audio_processing_loop(self) -> None:
        try:
            while self.is_listening:
                try:
                    audio_chunk = self.audio_queue.get(timeout=1.0)
                    self._process_audio_chunk(audio_chunk)
                except queue.Empty:
                    continue
        except Exception as exc:
            logger.error("Error in audio processing loop: %s", exc)
            self.is_listening = False

    def _process_audio_chunk(self, audio_chunk: np.ndarray) -> None:
        self.audio_buffer.append(audio_chunk.flatten())

        # Keep at most ~5 seconds of buffered audio
        max_buffer_size = int(AUDIO_SAMPLE_RATE * 5)
        total_samples = sum(len(chunk) for chunk in self.audio_buffer)
        while total_samples > max_buffer_size and self.audio_buffer:
            removed = self.audio_buffer.pop(0)
            total_samples -= len(removed)

        if self._detect_speech(audio_chunk):
            self.last_speech_time = time.time()
            if self._check_speech_duration():
                combined_audio = np.concatenate(self.audio_buffer)
                text, confidence, metadata = self._process_speech(combined_audio)
                if text:
                    for cb in self.callbacks:
                        try:
                            cb(text, confidence, metadata)
                        except Exception as cb_exc:
                            logger.error("Callback error: %s", cb_exc)
                    # Reset buffer after a detected segment
                    self.audio_buffer = []

    def _detect_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Basic energy-based speech detection.
        """
        energy = float(np.mean(np.abs(audio_chunk)))
        return energy > self.silence_threshold

    def _check_speech_duration(self) -> bool:
        """
        Check if enough time has passed since last detected speech sample.
        """
        if not self.audio_buffer:
            return False
        return (time.time() - self.last_speech_time) > self.min_speech_duration

    def _process_speech(
        self,
        audio_data: np.ndarray,
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Analyze audio for speech activity and return placeholder text and features.

        Returns:
            (text, confidence, metadata)
        """
        frame_size = int(AUDIO_SAMPLE_RATE * 0.02)
        frames = [
            audio_data[i : i + frame_size]
            for i in range(0, len(audio_data), frame_size)
        ]
        energies = [
            float(np.mean(np.abs(frame)))
            for frame in frames
            if len(frame) == frame_size
        ]

        if not energies:
            return "", 0.0, {"error": "No audio data"}

        avg_energy = float(np.mean(energies))
        energy_variance = float(np.var(energies))

        zero_crossings = sum(
            1
            for i in range(1, len(audio_data))
            if audio_data[i - 1] * audio_data[i] < 0
        )
        zero_crossing_rate = zero_crossings / float(len(audio_data))

        if avg_energy > self.silence_threshold * 2 and energy_variance > 0.001:
            text = (
                "I detected speech but need a speech recognition API to understand it."
            )
            confidence = float(
                min(
                    max(avg_energy / (self.silence_threshold * 4), 0.1),
                    0.9,
                )
            )
            logger.info(
                "Speech detected: energy=%.4f variance=%.6f confidence=%.2f",
                avg_energy,
                energy_variance,
                confidence,
            )
            metadata: Dict[str, Any] = {
                "language": self.language,
                "duration": len(audio_data) / float(AUDIO_SAMPLE_RATE),
                "timestamp": time.time(),
                "audio_features": {
                    "energy": avg_energy,
                    "variance": energy_variance,
                    "zero_crossing_rate": zero_crossing_rate,
                },
            }
            return text, confidence, metadata

        return "", 0.0, {"error": "No clear speech detected"}

    # -------------------------------------------------------------------------
    # Configuration helpers
    # -------------------------------------------------------------------------

    def set_language(self, language: str) -> bool:
        """
        Set the language code for downstream ASR integration.
        """
        self.language = language
        logger.info("Recognition language set to: %s", language)
        return True

    def adjust_sensitivity(
        self,
        silence_threshold: float,
        min_speech_duration: float,
    ) -> bool:
        """
        Adjust silence threshold and minimum speech duration.

        Args:
            silence_threshold: Energy threshold above which speech is considered.
            min_speech_duration: Minimum duration (seconds) before firing callbacks.

        Returns:
            True if updated; False on invalid parameters.
        """
        if silence_threshold <= 0.0 or min_speech_duration <= 0.0:
            logger.error("Invalid sensitivity parameters.")
            return False

        self.silence_threshold = silence_threshold
        self.min_speech_duration = min_speech_duration
        logger.info(
            "Sensitivity adjusted: threshold=%.4f duration=%.2f",
            silence_threshold,
            min_speech_duration,
        )
        return True

    def get_audio_devices(self) -> List[Dict[str, Any]]:
        """
        List available input-capable audio devices.
        """
        return [
            {
                "id": i,
                "name": device["name"],
                "channels": device["max_input_channels"],
                "default": i == sd.default.device[0],
            }
            for i, device in enumerate(self.devices)
            if device["max_input_channels"] > 0
        ]

    def set_input_device(self, device_id: int) -> bool:
        """
        Set the current input device by ID.

        Args:
            device_id: Index into the device list.

        Returns:
            True if updated; False if invalid.
        """
        if device_id < 0 or device_id >= len(self.devices):
            logger.error("Invalid device ID: %d", device_id)
            return False
        if self.devices[device_id]["max_input_channels"] <= 0:
            logger.error("Device %d has no input channels.", device_id)
            return False

        was_listening = self.is_listening
        if was_listening:
            self.stop_listening()

        self.input_device = device_id
        logger.info(
            "Input device set to %d: %s",
            device_id,
            self.devices[device_id]["name"],
        )

        if was_listening:
            self.start_listening()

        return True


_real_speech_recognition_engine: Optional[RealSpeechRecognitionEngine] = None


def get_real_speech_recognition_engine() -> RealSpeechRecognitionEngine:
    """
    Get or create the shared RealSpeechRecognitionEngine instance.
    """
    global _real_speech_recognition_engine
    if _real_speech_recognition_engine is None:
        _real_speech_recognition_engine = RealSpeechRecognitionEngine()
    return _real_speech_recognition_engine


# ==============================================================================
# Patent Pending
# Christman-AI Family
# Shared-neutral implementation for internal system use.
# ==============================================================================
