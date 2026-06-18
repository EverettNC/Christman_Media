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

# speech/speech_response.py

import logging

import pyttsx3

logger = logging.getLogger(__name__)

try:
    engine = pyttsx3.init(driverName="nsss")  # macOS driver
    engine.setProperty("rate", 180)
    engine.setProperty("volume", 1.0)
except Exception as e:
    engine = None
    logger.warning(f"Speech engine init failed: {e}")


def speak(text, tone_profile=None):
    print(f"🗣️ Speaking response: {text}")
    if not engine:
        print("❌ Speech engine not available.")
        return

    original_rate = engine.getProperty("rate")
    original_volume = engine.getProperty("volume")

    try:
        if tone_profile:
            rate = tone_profile.get("speech_rate")
            if rate:
                engine.setProperty("rate", rate)
            volume = tone_profile.get("volume")
            if volume is not None:
                engine.setProperty("volume", volume)

        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"❌ Failed to speak: {e}")
    finally:
        if tone_profile:
            engine.setProperty("rate", original_rate)
            engine.setProperty("volume", original_volume)


__all__ = ["speak"]
