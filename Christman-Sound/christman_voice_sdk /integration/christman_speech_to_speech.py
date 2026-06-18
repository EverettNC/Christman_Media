"""
Christman Speech-to-Speech
==========================

Full pipeline: User's voice → Christman's voice with lip-sync video.
"""

import logging
from pathlib import Path
from typing import Optional

from audio.enhanced_speech_recognition import EnhancedSpeechRecognition
from synthesis.voice_synthesis import get_voice_synthesizer
from nonverbal.cochlear_sync_tts import get_lipsync_engine

logger = logging.getLogger(__name__)


class ChristmanSpeechToSpeech:
    """Speech-to-Speech with lip synchronization."""

    def __init__(self):
        self.speech_recognition = EnhancedSpeechRecognition()
        self.voice_synthesizer = get_voice_synthesizer()
        self.lipsync = get_lipsync_engine()

        logger.info("🎤 Christman Speech-to-Speech initialized")

    def listen_and_respond(self, duration: int = 5) -> Optional[Path]:
        """Listen → Respond with voice + lip-sync."""
        print(f"\n🎤 Listening for {duration} seconds...")

        result = self.speech_recognition.listen_once(duration=duration)

        if not result or not result.get("text"):
            print("❌ Could not understand speech")
            return None

        user_text = result["text"]
        print(f"👤 You said: {user_text}")

        response_text = f"I heard you say '{user_text}'. How can I help?"

        print(f"🗣️ Christman: {response_text}")

        video_path = self.lipsync.speak(text=response_text)

        if video_path:
            print(f"✅ Response video ready: {video_path}")
            return video_path
        return None


# Singleton
_christman_s2s = None


def get_christman_speech_to_speech():
    global _christman_s2s
    if _christman_s2s is None:
        _christman_s2s = ChristmanSpeechToSpeech()
    return _christman_s2s
