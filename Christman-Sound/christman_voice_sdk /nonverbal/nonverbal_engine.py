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

import json
import logging
import os
import random
import threading
import time
from collections import deque
from datetime import datetime
from typing import Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nonverbal_engine")


class NonverbalEngine:
    """
    The NonverbalEngine is responsible for classifying gestures, eye movements,
    and vocalizations to determine user intent.

    Using temporal multimodal classification, this engine processes various input types
    and combines them using an LSTM-like approach (simulated in this version).

    This engine now includes self-learning capabilities to adapt over time.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing NonverbalEngine with self-learning capabilities")

        # History of user interactions for learning
        self.interaction_history = deque(maxlen=100)

        # Last 10 interactions for adaptive confidence
        self.recent_interactions = deque(maxlen=10)

        # User profile (would be loaded from database in full implementation)
        self.user_profile = {
            "gesture_sensitivity": 0.8,  # How sensitive the system is to gestures (0-1)
            "eye_tracking_sensitivity": 0.8,  # Sensitivity for eye tracking
            "sound_sensitivity": 0.7,  # Sensitivity for sound detection
            "preferred_emotion_display": True,  # Whether to show emotional content
            "response_speed": 1.0,  # Speech rate multiplier
            "symbol_system": "default",  # Symbol system preference (PCS, ARASAAC, etc.)
        }

        # Data directory
        self.data_dir = "data/learning"
        os.makedirs(self.data_dir, exist_ok=True)

        # Load existing models or use defaults
        self.gesture_map = (
            self._load_model("gestures") or self._get_default_gesture_map()
        )
        self.symbol_map = self._load_model("symbols") or self._get_default_symbol_map()
        self.eye_region_map = (
            self._load_model("eye_regions") or self._get_default_eye_region_map()
        )
        self.sound_map = (
            self._load_model("sound_patterns") or self._get_default_sound_pattern_map()
        )

        # Learning parameters
        self.learning_rate = 0.05
        self.learning_enabled = False
        self.confidence_threshold = 0.6
        self.learning_thread = None
        self.last_update = datetime.now()

        # Tracking for multimodal processing
        self.recent_inputs = []
        self.max_recent_inputs = 10

        # Usage statistics for adaptive learning
        self.usage_stats = self._load_stats()

        # Time-based session tracking
        self.session_start = datetime.now()
        self.last_interaction = time.time()

        self.logger.info(
            "NonverbalEngine initialized with self-modification capabilities"
        )

    def _load_model(self, model_type: str) -> Dict:
        """Load a model from file if it exists"""
        model_file = os.path.join(self.data_dir, f"{model_type}_model.json")

        if os.path.exists(model_file):
            try:
                with open(model_file, "r") as file:
                    model = json.load(file)
                    self.logger.info(
                        f"Loaded {model_type} model with {len(model)} entries"
                    )
                    return model
            except json.JSONDecodeError:
                self.logger.warning(
                    f"Failed to load {model_type} model, using defaults"
                )

        return {}

    def _save_model(self, model_type: str, model_data: Dict):
        """Save a model to file"""
        model_file = os.path.join(self.data_dir, f"{model_type}_model.json")

        with open(model_file, "w") as file:
            json.dump(model_data, file, indent=2)

        self.logger.info(f"Saved {model_type} model with {len(model_data)} entries")

    def _load_stats(self) -> Dict:
        """Load usage statistics"""
        stats_file = os.path.join(self.data_dir, "usage_stats.json")

        if os.path.exists(stats_file):
            try:
                with open(stats_file, "r") as file:
                    stats = json.load(file)
                    self.logger.info(
                        f"Loaded usage stats with {sum(len(section) for section in stats.values() if isinstance(section, dict))} entries"
                    )
                    return stats
            except json.JSONDecodeError:
                self.logger.warning("Failed to load usage stats, starting fresh")

        # Default empty stats structure
        return {
            "gestures": {},
            "symbols": {},
            "eye_regions": {},
            "sound_patterns": {},
            "multimodal": {},
            "last_updated": datetime.now().isoformat(),
        }

    def _save_stats(self):
        """Save usage statistics"""
        stats_file = os.path.join(self.data_dir, "usage_stats.json")
        self.usage_stats["last_updated"] = datetime.now().isoformat()

        with open(stats_file, "w") as file:
            json.dump(self.usage_stats, file, indent=2)

    def start_learning(self) -> bool:
        """Start the autonomous learning process"""
        if not self.learning_enabled:
            self.learning_enabled = True
            self.learning_thread = threading.Thread(target=self._learning_loop)
            self.learning_thread.daemon = True
            self.learning_thread.start()
            self.logger.info("Started nonverbal engine learning process")
            return True
        return False

    def stop_learning(self) -> bool:
        """Stop the autonomous learning process"""
        if self.learning_enabled:
            self.learning_enabled = False
            if self.learning_thread:
                self.learning_thread.join(timeout=5.0)
            self.logger.info("Stopped nonverbal engine learning process")
            return True
        return False

    def _learning_loop(self):
        """Main learning loop that runs continuously"""
        update_interval = 300  # Update every 5 minutes

        while self.learning_enabled:
            try:
                # Learn from recent interactions if enough time has passed
                time_since_update = (datetime.now() - self.last_update).total_seconds()

                if time_since_update > update_interval:
                    self._update_models_from_stats()
                    self.last_update = datetime.now()

                # Sleep to prevent excessive CPU usage
                time.sleep(60)
            except Exception as e:
                self.logger.error(f"Error in learning loop: {str(e)}")
                time.sleep(300)  # Sleep longer on error

    def _update_models_from_stats(self):
        """Update models based on usage statistics"""
        changes_made = False

        # Update gesture model
        for gesture, stats in self.usage_stats.get("gestures", {}).items():
            if gesture in self.gesture_map:
                # Only update if we have enough data
                if stats.get("count", 0) >= 5:
                    # Get current values
                    current = self.gesture_map[gesture]

                    # Calculate new confidence based on success rate
                    success_rate = stats.get("success", 0) / stats.get("count", 1)
                    new_confidence = (
                        current["confidence"] * (1 - self.learning_rate)
                        + success_rate * self.learning_rate
                    )

                    # Only update if significantly different
                    if abs(new_confidence - current["confidence"]) > 0.05:
                        self.gesture_map[gesture]["confidence"] = new_confidence
                        changes_made = True

                        self.logger.info(
                            f"Updated confidence for gesture '{gesture}': {current['confidence']:.2f} -> {new_confidence:.2f}"
                        )

        # Update symbol model
        for symbol, stats in self.usage_stats.get("symbols", {}).items():
            if symbol in self.symbol_map:
                # Only update if we have enough data
                if stats.get("count", 0) >= 5:
                    # Similar adjustment for symbols
                    current = self.symbol_map[symbol]

                    # Calculate new confidence
                    success_rate = stats.get("success", 0) / stats.get("count", 1)
                    new_confidence = (
                        current["confidence"] * (1 - self.learning_rate)
                        + success_rate * self.learning_rate
                    )

                    if abs(new_confidence - current["confidence"]) > 0.05:
                        self.symbol_map[symbol]["confidence"] = new_confidence
                        changes_made = True

                        self.logger.info(
                            f"Updated confidence for symbol '{symbol}': {current['confidence']:.2f} -> {new_confidence:.2f}"
                        )

        # Save models if changes were made
        if changes_made:
            self._save_model("gestures", self.gesture_map)
            self._save_model("symbols", self.symbol_map)

            # Reset the counters in usage stats
            for section in ["gestures", "symbols"]:
                for key in self.usage_stats.get(section, {}):
                    self.usage_stats[section][key]["success"] = 0
                    self.usage_stats[section][key]["count"] = 0

            self._save_stats()

    def record_interaction(
        self, input_type: str, input_data: str, result: Dict, success: bool = None
    ):
        """
        Record an interaction for learning

        Args:
            input_type: Type of input ('gesture', 'symbol', 'eye', 'sound')
            input_data: The specific input (e.g., 'nod', 'food')
            result: The result returned by the engine
            success: Whether the interaction was successful (if known)
        """
        if not input_data:
            return

        # Map input type to stats section
        section_map = {
            "gesture": "gestures",
            "symbol": "symbols",
            "eye": "eye_regions",
            "sound": "sound_patterns",
        }

        section = section_map.get(input_type)
        if not section:
            self.logger.warning(f"Unknown input type: {input_type}")
            return

        # Initialize stats for this input if not present
        if input_data not in self.usage_stats[section]:
            self.usage_stats[section][input_data] = {
                "count": 0,
                "success": 0,
                "last_used": None,
            }

        # Update stats
        self.usage_stats[section][input_data]["count"] += 1
        self.usage_stats[section][input_data]["last_used"] = datetime.now().isoformat()

        if success is not None:
            self.usage_stats[section][input_data]["success"] += 1 if success else 0

        # Add to recent inputs for multimodal processing
        self.recent_inputs.append(
            {
                "type": input_type,
                "data": input_data,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Keep only the most recent inputs
        if len(self.recent_inputs) > self.max_recent_inputs:
            self.recent_inputs.pop(0)

        # Periodically save stats
        try:
            total_count = 0
            for section_name, section_stats in self.usage_stats.items():
                if isinstance(section_stats, dict):
                    for item_name, stats in section_stats.items():
                        if isinstance(stats, dict):
                            total_count += stats.get("count", 0)

            if total_count > 0 and total_count % 10 == 0:
                self._save_stats()
        except Exception as e:
            # Log error but don't crash the application
            print(f"Error calculating usage stats: {str(e)}")

    def classify_gesture(self, gesture_name):
        """Classify a named gesture and return intent information"""
        self.logger.debug(f"Classifying gesture: {gesture_name}")

        # Get mapping for the gesture, or return unknown
        if gesture_name in self.gesture_map:
            result = self.gesture_map[gesture_name].copy()
        else:
            result = {
                "intent": "unknown",
                "expression": "neutral",
                "emotion_tier": "mild",
                "confidence": 0.3,
            }

        # Add some randomness to confidence to simulate real-world variation
        confidence_variation = random.uniform(-0.05, 0.05)
        result["confidence"] = min(
            1.0, max(0.1, result["confidence"] + confidence_variation)
        )

        # Generate a relevant message based on the intent
        intent_messages = {
            "affirm": "Yes, I agree.",
            "deny": "No, I don't want that.",
            "help": "I need help please.",
            "greet": "Hello there!",
            "like": "I like this.",
            "dislike": "I don't like this.",
            "stop": "Please stop.",
            "unknown": "I'm trying to communicate something.",
        }

        result["message"] = intent_messages.get(
            result["intent"], "I'm trying to communicate."
        )

        # Add to interaction history for learning
        self.interaction_history.append(
            {"type": "gesture", "input": gesture_name, "result": result}
        )

        # Record for adaptive learning
        self.record_interaction("gesture", gesture_name, result)

        return result

    def process_eye_movement(self, eye_data):
        """Process eye tracking data to determine intent"""
        self.logger.debug(f"Processing eye movement: {eye_data}")

        region = eye_data.get("region", "unknown")
        if region in self.eye_region_map:
            result = self.eye_region_map[region].copy()
        else:
            result = {
                "intent": "unknown",
                "expression": "neutral",
                "emotion_tier": "mild",
                "confidence": 0.3,
            }

        # Add some randomness to confidence
        confidence_variation = random.uniform(-0.05, 0.05)
        result["confidence"] = min(
            1.0, max(0.1, result["confidence"] + confidence_variation)
        )

        # Generate appropriate message
        region_messages = {
            "top_left": "Let's go back.",
            "top_right": "Let's go forward.",
            "bottom_left": "I want to cancel.",
            "bottom_right": "I confirm this choice.",
            "center": "I select this option.",
        }

        result["message"] = region_messages.get(region, "I'm looking at something.")

        # Add to interaction history
        self.interaction_history.append(
            {"type": "eye", "input": region, "result": result}
        )

        # Record for adaptive learning
        self.record_interaction("eye", region, result)

        return result

    def process_sound(self, sound_pattern):
        """Process vocalization pattern to determine intent"""
        self.logger.debug(f"Processing sound pattern: {sound_pattern}")

        if sound_pattern in self.sound_map:
            result = self.sound_map[sound_pattern].copy()
        else:
            result = {
                "intent": "unknown",
                "expression": "neutral",
                "emotion_tier": "mild",
                "confidence": 0.4,
            }

        # Add some randomness to confidence
        confidence_variation = random.uniform(-0.05, 0.05)
        result["confidence"] = min(
            1.0, max(0.1, result["confidence"] + confidence_variation)
        )

        # Generate appropriate message
        sound_messages = {
            "hum": "I'm thinking about it.",
            "click": "I choose this option.",
            "distress": "I need help right now.",
            "soft": "I'm unsure about this.",
            "loud": "I'm excited about this!",
            "short_vowel": "I acknowledge that.",
            "repeated_sound": "Please pay attention to this.",
        }

        result["message"] = sound_messages.get(
            sound_pattern, "I'm trying to say something."
        )

        # Add to interaction history
        self.interaction_history.append(
            {"type": "sound", "input": sound_pattern, "result": result}
        )

        # Record for adaptive learning
        self.record_interaction("sound", sound_pattern, result)

        return result

    def process_multimodal_input(self, gesture=None, eye_data=None, sound=None):
        """Process combined inputs from multiple modalities"""
        self.logger.debug("Processing multimodal input")

        inputs = []
        weights = []

        # Process each input type if provided
        if gesture:
            gesture_result = self.classify_gesture(gesture)
            inputs.append(gesture_result)
            weights.append(gesture_result["confidence"])

        if eye_data:
            eye_result = self.process_eye_movement(eye_data)
            inputs.append(eye_result)
            weights.append(
                eye_result["confidence"] * 0.8
            )  # Eye input weighted slightly less

        if sound:
            sound_result = self.process_sound(sound)
            inputs.append(sound_result)
            weights.append(sound_result["confidence"])

        # If no inputs, return default
        if not inputs:
            return {
                "intent": "unknown",
                "confidence": 0.1,
                "expression": "neutral",
                "emotion_tier": "mild",
                "message": "I'm not sure what you're trying to communicate.",
            }

        # Determine primary intent based on confidence-weighted voting
        intent_votes = {}
        expression_votes = {}
        emotion_tier_votes = {"mild": 0, "moderate": 0, "strong": 0, "urgent": 0}

        for input_result, weight in zip(inputs, weights):
            # Accumulate votes for intent
            intent = input_result["intent"]
            if intent not in intent_votes:
                intent_votes[intent] = 0
            intent_votes[intent] += weight

            # Accumulate votes for expression
            expression = input_result.get("expression", "neutral")
            if expression not in expression_votes:
                expression_votes[expression] = 0
            expression_votes[expression] += weight

            # Accumulate votes for emotion tier
            tier = input_result.get("emotion_tier", "mild")
            emotion_tier_votes[tier] += weight

        # Find the winners
        best_intent = max(intent_votes.items(), key=lambda x: x[1])[0]
        best_expression = (
            max(expression_votes.items(), key=lambda x: x[1])[0]
            if expression_votes
            else "neutral"
        )
        best_emotion_tier = max(emotion_tier_votes.items(), key=lambda x: x[1])[0]

        # Calculate overall confidence
        total_weight = sum(weights)
        confidence = (
            sum(
                result["confidence"] * weight for result, weight in zip(inputs, weights)
            )
            / total_weight
            if total_weight > 0
            else 0.5
        )

        # Get a message from the best result
        for input_result in inputs:
            if input_result.get("intent") == best_intent and "message" in input_result:
                best_message = input_result["message"]
                break
        else:
            best_message = "I'm trying to communicate something."

        # Construct result
        result = {
            "intent": best_intent,
            "confidence": confidence,
            "expression": best_expression,
            "emotion_tier": best_emotion_tier,
            "message": best_message,
            "multimodal": True,
            "inputs": [i["intent"] for i in inputs],
        }

        # Record multimodal interaction for learning
        input_key = "+".join(
            sorted(
                [
                    i
                    for i in [
                        gesture,
                        sound,
                        eye_data.get("region") if eye_data else None,
                    ]
                    if i
                ]
            )
        )
        if input_key:
            self.record_interaction("multimodal", input_key, result)

        self.logger.info(
            f"Multimodal processing result: {best_intent} "
            f"(confidence: {confidence:.2f})"
        )

        return result

    def learn_from_interactions(self):
        """
        Manually trigger learning from recent interactions

        Returns:
            dict: Summary of learning results
        """
        self._update_models_from_stats()

        # Provide a summary of what was learned
        summary = {
            "gestures_updated": sum(
                1 for g in self.gesture_map if g in self.usage_stats.get("gestures", {})
            ),
            "symbols_updated": sum(
                1 for s in self.symbol_map if s in self.usage_stats.get("symbols", {})
            ),
            "timestamp": datetime.now().isoformat(),
        }

        return summary

    # Support method for the advanced interpreter
    def get_emotional_indicators(self, gesture_name: str) -> Dict[str, float]:
        """
        Extract emotional indicators from a gesture

        Args:
            gesture_name: The name of the gesture

        Returns:
            dict: Emotional indicators with values between 0.0 and 1.0
        """
        # Default emotional mapping
        emotion_map = {
            "nod": {"agreement": 0.9, "acceptance": 0.8, "interest": 0.6},
            "shake": {"disagreement": 0.9, "rejection": 0.8, "frustration": 0.5},
            "point_up": {"urgency": 0.8, "attention": 0.9, "importance": 0.7},
            "wave": {"greeting": 0.9, "friendliness": 0.8, "openness": 0.7},
            "thumbs_up": {"approval": 0.9, "satisfaction": 0.8, "happiness": 0.7},
            "thumbs_down": {
                "disapproval": 0.9,
                "dissatisfaction": 0.8,
                "disappointment": 0.7,
            },
            "open_palm": {"stopping": 0.9, "boundary": 0.8, "caution": 0.7},
            "stimming": {"anxiety": 0.8, "overwhelm": 0.7, "self-regulation": 0.9},
            "rapid_blink": {"distress": 0.7, "anxiety": 0.6, "overwhelm": 0.8},
        }

        # Return the emotional mapping for the gesture, or an empty dict if not found
        return emotion_map.get(gesture_name, {})

    def _get_default_gesture_map(self):
        """Get default gesture mappings"""
        return {
            "nod": {
                "intent": "affirm",
                "confidence": 0.9,
                "expression": "positive",
                "emotion_tier": "moderate",
            },
            "shake": {
                "intent": "deny",
                "confidence": 0.9,
                "expression": "negative",
                "emotion_tier": "moderate",
            },
            "point_up": {
                "intent": "help",
                "confidence": 0.8,
                "expression": "urgent",
                "emotion_tier": "moderate",
            },
            "wave": {
                "intent": "greet",
                "confidence": 0.8,
                "expression": "positive",
                "emotion_tier": "mild",
            },
            "thumbs_up": {
                "intent": "like",
                "confidence": 0.9,
                "expression": "positive",
                "emotion_tier": "strong",
                "message": "That's great!",
            },
            "thumbs_down": {
                "intent": "dislike",
                "confidence": 0.9,
                "expression": "negative",
                "emotion_tier": "strong",
            },
            "open_palm": {
                "intent": "stop",
                "confidence": 0.8,
                "expression": "negative",
                "emotion_tier": "strong",
            },
            "stimming": {
                "intent": "self_regulate",
                "confidence": 0.7,
                "expression": "negative",
                "emotion_tier": "strong",
            },
            "rapid_blink": {
                "intent": "overwhelmed",
                "confidence": 0.7,
                "expression": "negative",
                "emotion_tier": "urgent",
            },
        }

    def _get_default_symbol_map(self):
        """Get default symbol mappings"""
        return {
            "food": {
                "intent": "hungry",
                "confidence": 0.9,
                "expression": "urgent",
                "emotion_tier": "moderate",
            },
            "drink": {
                "intent": "thirsty",
                "confidence": 0.9,
                "expression": "urgent",
                "emotion_tier": "moderate",
            },
            "bathroom": {
                "intent": "bathroom",
                "confidence": 0.9,
                "expression": "urgent",
                "emotion_tier": "strong",
            },
            "pain": {
                "intent": "pain",
                "confidence": 0.9,
                "expression": "negative",
                "emotion_tier": "strong",
            },
            "happy": {
                "intent": "express_joy",
                "confidence": 0.9,
                "expression": "positive",
                "emotion_tier": "moderate",
            },
            "sad": {
                "intent": "express_sadness",
                "confidence": 0.9,
                "expression": "negative",
                "emotion_tier": "moderate",
            },
            "help": {
                "intent": "need_help",
                "confidence": 0.9,
                "expression": "urgent",
                "emotion_tier": "strong",
            },
            "question": {
                "intent": "ask_question",
                "confidence": 0.8,
                "expression": "inquisitive",
                "emotion_tier": "mild",
            },
            "tired": {
                "intent": "tired",
                "confidence": 0.8,
                "expression": "negative",
                "emotion_tier": "moderate",
            },
            "medicine": {
                "intent": "need_medicine",
                "confidence": 0.9,
                "expression": "urgent",
                "emotion_tier": "strong",
            },
            "yes": {
                "intent": "affirm",
                "confidence": 0.9,
                "expression": "positive",
                "emotion_tier": "moderate",
            },
            "no": {
                "intent": "deny",
                "confidence": 0.9,
                "expression": "negative",
                "emotion_tier": "moderate",
            },
            "play": {
                "intent": "want_play",
                "confidence": 0.8,
                "expression": "positive",
                "emotion_tier": "mild",
            },
            "music": {
                "intent": "want_music",
                "confidence": 0.8,
                "expression": "positive",
                "emotion_tier": "mild",
            },
            "book": {
                "intent": "want_book",
                "confidence": 0.8,
                "expression": "positive",
                "emotion_tier": "mild",
            },
            "outside": {
                "intent": "want_outside",
                "confidence": 0.8,
                "expression": "positive",
                "emotion_tier": "moderate",
            },
        }

    def _get_default_eye_region_map(self):
        """Get default eye region mappings"""
        return {
            "top_left": {
                "intent": "previous",
                "confidence": 0.7,
                "expression": "neutral",
                "emotion_tier": "mild",
            },
            "top_right": {
                "intent": "next",
                "confidence": 0.7,
                "expression": "neutral",
                "emotion_tier": "mild",
            },
            "bottom_left": {
                "intent": "cancel",
                "confidence": 0.7,
                "expression": "negative",
                "emotion_tier": "moderate",
            },
            "bottom_right": {
                "intent": "confirm",
                "confidence": 0.7,
                "expression": "positive",
                "emotion_tier": "moderate",
            },
            "center": {
                "intent": "select",
                "confidence": 0.8,
                "expression": "attentive",
                "emotion_tier": "mild",
            },
            "long_stare": {
                "intent": "focus",
                "confidence": 0.8,
                "expression": "attentive",
                "emotion_tier": "strong",
            },
            "rapid_scan": {
                "intent": "searching",
                "confidence": 0.7,
                "expression": "inquisitive",
                "emotion_tier": "moderate",
            },
        }

    def _get_default_sound_pattern_map(self):
        """Get default sound pattern mappings"""
        return {
            "hum": {
                "intent": "thinking",
                "confidence": 0.6,
                "expression": "neutral",
                "emotion_tier": "mild",
            },
            "click": {
                "intent": "select",
                "confidence": 0.7,
                "expression": "neutral",
                "emotion_tier": "mild",
            },
            "distress": {
                "intent": "help",
                "confidence": 0.9,
                "expression": "negative",
                "emotion_tier": "urgent",
            },
            "soft": {
                "intent": "unsure",
                "confidence": 0.6,
                "expression": "neutral",
                "emotion_tier": "mild",
            },
            "loud": {
                "intent": "excited",
                "confidence": 0.8,
                "expression": "positive",
                "emotion_tier": "strong",
            },
            "short_vowel": {
                "intent": "acknowledge",
                "confidence": 0.7,
                "expression": "neutral",
                "emotion_tier": "mild",
            },
            "repeated_sound": {
                "intent": "insistent",
                "confidence": 0.8,
                "expression": "urgent",
                "emotion_tier": "strong",
            },
        }


# Global singleton instance of NonverbalEngine
_nonverbal_engine = None


def get_nonverbal_engine() -> NonverbalEngine:
    """
    Get or create the singleton instance of NonverbalEngine

    Returns:
        NonverbalEngine: The singleton engine instance
    """
    global _nonverbal_engine
    if _nonverbal_engine is None:
        _nonverbal_engine = NonverbalEngine()
    return _nonverbal_engine


# For testing and demonstration
if __name__ == "__main__":
    engine = get_nonverbal_engine()

    print("Classifying gesture: nod")
    result = engine.classify_gesture("nod")
    print(result)

    print("\nClassifying gesture: thumbs_up")
    result = engine.classify_gesture("thumbs_up")
    print(result)

    print("\nEye tracking: center")
    result = engine.process_eye_movement({"region": "center", "x": 0.5, "y": 0.5})
    print(result)

    print("\nEmotional indicators for thumbs_up:")
    indicators = engine.get_emotional_indicators("thumbs_up")
    print(indicators)

__all__ = ["get_nonverbal_engine", "NonverbalEngine"]
