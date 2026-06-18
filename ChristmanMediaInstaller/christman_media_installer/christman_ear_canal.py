"""
CHRISTMAN_EAR_CANAL — Template
The Christman AI Project / Luma Cognify AI

Drop this file into any being's package root as `christman_ear_canal.py`
to give them microphone capture, voice level detection, and audio passthrough.

This template is wired and functional for sounddevice.
Swap the backend if your being needs pyaudio.
"""

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger("christman.ear_canal")

CHRISTMAN_EAR_CANAL = True   # Signature flag — searched by detector.py

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_BLOCKSIZE = 1024


class EarCanal:
    """Microphone capture and audio relay for the Christman family.

    Usage:
        ear = EarCanal(on_audio=my_callback)
        ear.start()
        # ... do work ...
        ear.stop()
    """

    def __init__(
        self,
        on_audio: Optional[Callable] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        blocksize: int = DEFAULT_BLOCKSIZE,
    ):
        self.on_audio = on_audio
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        self._stream = None
        self._running = False

    def start(self) -> None:
        try:
            import sounddevice as sd
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.blocksize,
                callback=self._callback,
            )
            self._stream.start()
            self._running = True
            logger.info("✅ EarCanal: microphone capture started.")
        except ImportError:
            logger.error("❌ EarCanal: sounddevice not installed. Install: pip install sounddevice")
            raise
        except Exception as e:
            logger.error(f"❌ EarCanal: failed to start microphone: {e}")
            raise

    def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._running = False
        logger.info("EarCanal: microphone capture stopped.")

    def _callback(self, indata, frames, time, status) -> None:
        if status:
            logger.warning(f"EarCanal audio status: {status}")
        if self.on_audio:
            self.on_audio(indata.copy(), frames, time, status)

    @property
    def is_running(self) -> bool:
        return self._running
