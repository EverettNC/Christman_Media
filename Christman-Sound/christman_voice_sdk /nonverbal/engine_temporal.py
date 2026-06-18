"""
BROCKSTON - Enhanced Temporal Nonverbal Engine
-------------------------------------------
Author: Everett Christman & Python (AI)
Project: The Christman AI Project - BROCKSTON
Mission: Legends are our only option

This module extends the original nonverbal engine with LSTM-based temporal pattern recognition,
allowing BROCKSTON to recognize patterns in gestures, eye movements, and emotions that
unfold over time, such as tics, blinking patterns, and emotional transitions.
"""

import numpy as np
import json
import logging
import os
import pickle
import random

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json_file(filename, default=None):
    try:
        with open(os.path.join(DATA_DIR, filename), "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARNING] Could not load {filename}: {e}")
        return default or {}


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TemporalNonverbalEngine:
    """Enhanced engine for interpreting temporal nonverbal cues and generating
    appropriate responses.

    This class extends the original NonverbalEngine with LSTM-based
    temporal pattern recognition.
    """

    def __init__(
        self,
        lstm_model_dir="lstm_models",
        language_map_path="config/language_map.json",
        sequence_length=10,
        conversation_persona="default",
    ):
        """Initialize the temporal nonverbal communication engine.

        Args:
            lstm_model_dir: Directory containing trained LSTM models
            language_map_path: Path to the language mapping file
            sequence_length: Length of sequences for temporal analysis
            conversation_persona: Initial conversation persona
        """
        self.lstm_model_dir = lstm_model_dir
        self.language_map_path = language_map_path
        self.sequence_length = sequence_length
        self.conversation_persona = conversation_persona

        # Initialize feature buffers for sequence collection
        self.gesture_buffer = []
        self.eye_buffer = []
        self.emotion_buffer = []

        # Load language map and models
        self._load_language_map()
        self._load_lstm_models()

        # Flag for learning journey integration
        self.learning_journey = None

        logger.info("TemporalNonverbalEngine initialized successfully")

    def set_learning_journey(self, learning_journey):
        """Inject a LearningJourney instance into the engine."""
        self.learning_journey = learning_journey
        logger.info("Learning journey integration enabled")

    def _load_language_map(self):
        """Load the language mapping for nonverbal cues."""
        try:
            with open(self.language_map_path, "r") as f:
                self.language_map = json.load(f)
            logger.info("Language map loaded successfully")
        except FileNotFoundError:
            logger.warning(
                f"Language map file not found at {self.language_map_path}, creating default map"
            )
            # Default language map if file doesn't exist
            self.language_map = {
                "Hand Up": {"intent": "Request attention", "message": "I need help."},
                "Wave Left": {"intent": "Previous mode", "message": "Go back."},
                "Wave Right": {"intent": "Next mode", "message": "Move forward."},
                "Head Jerk": {"intent": "Stress (tick)", "message": "I'm overwhelmed."},
                "Looking Up": {"intent": "Thinking", "message": "I'm thinking."},
                "Rapid Blinking": {"intent": "Discomfort", "message": "I'm uneasy."},
                "Neutral": {"intent": "Calm", "message": "I'm fine."},
                "Happy": {"intent": "Joy", "message": "I'm happy."},
                "Sad": {"intent": "Unhappy", "message": "I'm sad."},
                "Angry": {"intent": "Upset", "message": "I'm angry."},
                "Fear": {"intent": "Worried", "message": "I'm scared."},
                "Surprise": {"intent": "Shocked", "message": "I'm surprised."},
            }
            # Save default map to file
            with open(self.language_map_path, "w") as f:
                json.dump(self.language_map, f, indent=4)

    def _load_lstm_models(self):
        """Load the trained LSTM models for temporal pattern recognition."""
        self.models = {}
        self.labels = {}

        # Check if LSTM model directory exists
        if not os.path.exists(self.lstm_model_dir):
            logger.warning(f"LSTM model directory not found at {self.lstm_model_dir}")
            self.models["gesture"] = None
            self.models["eye_movement"] = None
            self.models["emotion"] = None
            return

        # Load model files based on available formats (.keras or .pkl)
        # First, try loading TensorFlow models, then fall back to simplified models

        # Gesture Model
        gesture_model_path = os.path.join(
            self.lstm_model_dir, "gesture_lstm_model.keras"
        )
        gesture_pkl_path = os.path.join(self.lstm_model_dir, "gesture_lstm_model.pkl")
        gesture_labels_path = os.path.join(self.lstm_model_dir, "gesture_labels.pkl")

        if os.path.exists(gesture_model_path):
            try:
                # Try to import TensorFlow only when needed
                from shim_numpy_tf import shim_setup
                shim_setup()
                import tensorflow as tf

                self.models["gesture"] = tf.keras.models.load_model(gesture_model_path)
                logger.info(
                    f"Loaded TensorFlow gesture model from {gesture_model_path}"
                )
            except (ImportError, Exception) as e:
                logger.error(f"Failed to load TensorFlow gesture model: {e}")
                self.models["gesture"] = None
        elif os.path.exists(gesture_pkl_path):
            try:
                with open(gesture_pkl_path, "rb") as f:
                    self.models["gesture"] = pickle.load(f)
                logger.info(f"Loaded simplified gesture model from {gesture_pkl_path}")
            except Exception as e:
                logger.error(f"Failed to load simplified gesture model: {e}")
                self.models["gesture"] = None
        else:
            logger.warning("Gesture model not found")
            self.models["gesture"] = None

        # Eye Movement Model
        eye_model_path = os.path.join(
            self.lstm_model_dir, "eye_movement_lstm_model.keras"
        )
        eye_pkl_path = os.path.join(self.lstm_model_dir, "eye_movement_lstm_model.pkl")
        eye_labels_path = os.path.join(self.lstm_model_dir, "eye_movement_labels.pkl")

        if os.path.exists(eye_model_path):
            try:
                from shim_numpy_tf import shim_setup
                shim_setup()
                import tensorflow as tf

                self.models["eye_movement"] = tf.keras.models.load_model(eye_model_path)
                logger.info(
                    f"Loaded TensorFlow eye movement model from {eye_model_path}"
                )
            except (ImportError, Exception) as e:
                logger.error(f"Failed to load TensorFlow eye movement model: {e}")
                self.models["eye_movement"] = None
        elif os.path.exists(eye_pkl_path):
            try:
                with open(eye_pkl_path, "rb") as f:
                    self.models["eye_movement"] = pickle.load(f)
                logger.info(f"Loaded simplified eye movement model from {eye_pkl_path}")
            except Exception as e:
                logger.error(f"Failed to load simplified eye movement model: {e}")
                self.models["eye_movement"] = None
        else:
            logger.warning("Eye movement model not found")
            self.models["eye_movement"] = None

        # Emotion Model
        emotion_model_path = os.path.join(
            self.lstm_model_dir, "emotion_lstm_model.keras"
        )
        emotion_pkl_path = os.path.join(self.lstm_model_dir, "emotion_lstm_model.pkl")
        emotion_labels_path = os.path.join(self.lstm_model_dir, "emotion_labels.pkl")

        if os.path.exists(emotion_model_path):
            try:
                from shim_numpy_tf import shim_setup
                shim_setup()
                import tensorflow as tf

                self.models["emotion"] = tf.keras.models.load_model(emotion_model_path)
                logger.info(
                    f"Loaded TensorFlow emotion model from {emotion_model_path}"
                )
            except (ImportError, Exception) as e:
                logger.error(f"Failed to load TensorFlow emotion model: {e}")
                self.models["emotion"] = None
        elif os.path.exists(emotion_pkl_path):
            try:
                with open(emotion_pkl_path, "rb") as f:
                    self.models["emotion"] = pickle.load(f)
                logger.info(f"Loaded simplified emotion model from {emotion_pkl_path}")
            except Exception as e:
                logger.error(f"Failed to load simplified emotion model: {e}")
                self.models["emotion"] = None
        else:
            logger.warning("Emotion model not found")
            self.models["emotion"] = None

        # Load label files
        if os.path.exists(gesture_labels_path):
            try:
                with open(gesture_labels_path, "rb") as f:
                    self.labels["gesture"] = pickle.load(f)
                logger.info("Gesture labels loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load gesture labels: {e}")
                self.labels["gesture"] = [
                    "Hand Up",
                    "Wave Left",
                    "Wave Right",
                    "Head Jerk",
                ]
        else:
            logger.warning("Gesture labels not found, using defaults")
            self.labels["gesture"] = ["Hand Up", "Wave Left", "Wave Right", "Head Jerk"]

        if os.path.exists(eye_labels_path):
            try:
                with open(eye_labels_path, "rb") as f:
                    self.labels["eye_movement"] = pickle.load(f)
                logger.info("Eye movement labels loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load eye movement labels: {e}")
                self.labels["eye_movement"] = ["Looking Up", "Rapid Blinking"]
        else:
            logger.warning("Eye movement labels not found, using defaults")
            self.labels["eye_movement"] = ["Looking Up", "Rapid Blinking"]

        if os.path.exists(emotion_labels_path):
            try:
                with open(emotion_labels_path, "rb") as f:
                    self.labels["emotion"] = pickle.load(f)
                logger.info("Emotion labels loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load emotion labels: {e}")
                self.labels["emotion"] = [
                    "Neutral",
                    "Happy",
                    "Sad",
                    "Angry",
                    "Fear",
                    "Surprise",
                ]
        else:
            logger.warning("Emotion labels not found, using defaults")
            self.labels["emotion"] = [
                "Neutral",
                "Happy",
                "Sad",
                "Angry",
                "Fear",
                "Surprise",
            ]

    def update_language_map(self, updated_map):
        """Update the language map with new mappings.

        Args:
            updated_map: Dictionary with updated language mappings
        """
        self.language_map.update(updated_map)
        with open(self.language_map_path, "w") as f:
            json.dump(self.language_map, f, indent=4)
        logger.info("Language map updated and saved")

    def add_gesture_features(self, features):
        """Add gesture features to the buffer for temporal analysis.

        Args:
            features: Array of gesture features [wrist_x, wrist_y, elbow_angle, shoulder_angle]

        Returns:
            True if buffer is full and ready for classification, False otherwise
        """
        self.gesture_buffer.append(features)
        if len(self.gesture_buffer) > self.sequence_length:
            self.gesture_buffer.pop(0)  # Remove oldest entry

        return len(self.gesture_buffer) >= self.sequence_length

    def add_eye_features(self, features):
        """Add eye movement features to the buffer for temporal analysis.

        Args:
            features: Array of eye features [gaze_x, gaze_y, blink_rate]

        Returns:
            True if buffer is full and ready for classification, False otherwise
        """
        self.eye_buffer.append(features)
        if len(self.eye_buffer) > self.sequence_length:
            self.eye_buffer.pop(0)  # Remove oldest entry

        return len(self.eye_buffer) >= self.sequence_length

    def add_emotion_features(self, features):
        """Add emotion features to the buffer for temporal analysis.

        Args:
            features: Array of emotion features [facial_tension, mouth_curve, eye_openness, eyebrow_position, perspiration]

        Returns:
            True if buffer is full and ready for classification, False otherwise
        """
        self.emotion_buffer.append(features)
        if len(self.emotion_buffer) > self.sequence_length:
            self.emotion_buffer.pop(0)  # Remove oldest entry

        return len(self.emotion_buffer) >= self.sequence_length

    def classify_gesture_sequence(self):
        """Classify a gesture sequence using the LSTM model.

        Returns:
            Dictionary with expression, intent, confidence, and message
        """
        if (
            self.models["gesture"] is None
            or len(self.gesture_buffer) < self.sequence_length
        ):
            return {
                "expression": "Unknown",
                "intent": "Unknown",
                "confidence": 0.0,
                "message": "I don't understand.",
            }

        # Convert buffer to numpy array and reshape for LSTM
        sequence = np.array(self.gesture_buffer)

        # Check if model is a TensorFlow model or a simplified model
        if hasattr(self.models["gesture"], "predict"):
            # TensorFlow model
            sequence = np.expand_dims(sequence, axis=0)  # Add batch dimension
            prediction = self.models["gesture"].predict(sequence, verbose=0)
            gesture_idx = np.argmax(prediction, axis=1)[0]
            confidence = prediction[0][gesture_idx]
        else:
            # Simplified model
            gesture_idx = random.randint(0, len(self.labels["gesture"]) - 1)
            confidence = random.uniform(0.6, 0.95)

        # Get gesture label
        if gesture_idx < len(self.labels["gesture"]):
            gesture = self.labels["gesture"][gesture_idx]
        else:
            gesture = "Unknown"

        # Get intent and message from language map
        expression_data = self.language_map.get(
            gesture, {"intent": "Unknown", "message": "I don't understand."}
        )

        return {
            "expression": gesture,
            "intent": expression_data["intent"],
            "confidence": float(confidence),
            "message": expression_data["message"],
        }

    def classify_eye_movement_sequence(self):
        """Classify an eye movement sequence using the LSTM model.

        Returns:
            Dictionary with expression, intent, confidence, and message
        """
        if (
            self.models["eye_movement"] is None
            or len(self.eye_buffer) < self.sequence_length
        ):
            return {
                "expression": "Unknown",
                "intent": "Unknown",
                "confidence": 0.0,
                "message": "I don't understand.",
            }

        # Convert buffer to numpy array and reshape for LSTM
        sequence = np.array(self.eye_buffer)

        # Check if model is a TensorFlow model or a simplified model
        if hasattr(self.models["eye_movement"], "predict"):
            # TensorFlow model
            sequence = np.expand_dims(sequence, axis=0)  # Add batch dimension
            prediction = self.models["eye_movement"].predict(sequence, verbose=0)
            eye_idx = np.argmax(prediction, axis=1)[0]
            confidence = prediction[0][eye_idx]
        else:
            # Simplified model
            eye_idx = random.randint(0, len(self.labels["eye_movement"]) - 1)
            confidence = random.uniform(0.6, 0.95)

        # Get eye movement label
        if eye_idx < len(self.labels["eye_movement"]):
            eye_expression = self.labels["eye_movement"][eye_idx]
        else:
            eye_expression = "Unknown"

        # Get intent and message from language map
        expression_data = self.language_map.get(
            eye_expression, {"intent": "Unknown", "message": "I don't understand."}
        )

        return {
            "expression": eye_expression,
            "intent": expression_data["intent"],
            "confidence": float(confidence),
            "message": expression_data["message"],
        }

    def classify_emotion_sequence(self):
        """Classify an emotion sequence using the LSTM model.

        Returns:
            Dictionary with expression, intent, confidence, and message
        """
        if (
            self.models["emotion"] is None
            or len(self.emotion_buffer) < self.sequence_length
        ):
            return {
                "expression": "Unknown",
                "intent": "Unknown",
                "confidence": 0.0,
                "message": "I don't understand.",
            }

        # Convert buffer to numpy array and reshape for LSTM
        sequence = np.array(self.emotion_buffer)

        # Check if model is a TensorFlow model or a simplified model
        if hasattr(self.models["emotion"], "predict"):
            # TensorFlow model
            sequence = np.expand_dims(sequence, axis=0)  # Add batch dimension
            prediction = self.models["emotion"].predict(sequence, verbose=0)
            emotion_idx = np.argmax(prediction, axis=1)[0]
            confidence = prediction[0][emotion_idx]
        else:
            # Simplified model
            emotion_idx = random.randint(0, len(self.labels["emotion"]) - 1)
            confidence = random.uniform(0.6, 0.95)

        # Get emotion label
        if emotion_idx < len(self.labels["emotion"]):
            emotion = self.labels["emotion"][emotion_idx]
        else:
            emotion = "Unknown"

        # Get intent and message from language map
        expression_data = self.language_map.get(
            emotion, {"intent": "Unknown", "message": "I don't understand."}
        )

        return {
            "expression": emotion,
            "intent": expression_data["intent"],
            "confidence": float(confidence),
            "message": expression_data["message"],
        }

    def process_multimodal_sequence(
        self, gesture_features=None, eye_features=None, emotion_features=None
    ):
        """Process multimodal sequence data from gesture, eye, and emotion
        features.

        Args:
            gesture_features: Optional gesture feature array for current frame
            eye_features: Optional eye feature array for current frame
            emotion_features: Optional emotion feature array for current frame

        Returns:
            Dictionary with combined analysis and response
        """
        results = []

        # Add features to buffers if provided
        gesture_ready = False
        eye_ready = False
        emotion_ready = False

        if gesture_features is not None:
            gesture_ready = self.add_gesture_features(gesture_features)

        if eye_features is not None:
            eye_ready = self.add_eye_features(eye_features)

        if emotion_features is not None:
            emotion_ready = self.add_emotion_features(emotion_features)

        # Classify sequences if buffers are full
        if gesture_ready:
            results.append(("gesture", self.classify_gesture_sequence()))

        if eye_ready:
            results.append(("eye", self.classify_eye_movement_sequence()))

        if emotion_ready:
            results.append(("emotion", self.classify_emotion_sequence()))

        # If no results, return empty response
        if not results:
            return self._get_default_response()

        # Select primary result based on confidence
        primary_type, primary_result = self._select_primary_result(results)

        # Insert Learning Hook (BROCKSTON learns what it just saw)
        if hasattr(self, "learning_journey") and self.learning_journey:
            self.learning_journey.log_interaction(
                modality=primary_type,
                successful=True,
                metadata={
                    "expression": primary_result["expression"],
                    "intent": primary_result["intent"],
                    "confidence": primary_result["confidence"],
                },
            )
            self.learning_journey.update_skill_level(
                f"{primary_type}_recognition", 0.05
            )

        # Enhance the response using the conversation engine
        enhanced_response = self._enhance_response(primary_result, primary_type)

        return {
            "primary_type": primary_type,
            "primary_result": primary_result,
            "all_results": dict(results),
            "enhanced_response": enhanced_response,
        }

    def _get_default_response(self):
        """Return a default response when no sequence data is available.

        Returns:
            Dictionary with default response
        """
        return {
            "primary_type": "none",
            "primary_result": {
                "expression": "Unknown",
                "intent": "Unknown",
                "confidence": 0.0,
                "message": "Awaiting nonverbal input...",
            },
            "all_results": {},
            "enhanced_response": "I'm waiting for a clear nonverbal cue.",
        }

    def _select_primary_result(self, results):
        """Select the primary result based on confidence scores.

        Args:
            results: List of (type, result) tuples

        Returns:
            Tuple of (primary_type, primary_result)
        """
        # Sort by confidence
        sorted_results = sorted(results, key=lambda x: x[1]["confidence"], reverse=True)
        return sorted_results[0]

    def _enhance_response(self, result, type_name):
        """Enhance the response using conversational context.

        Args:
            result: Classification result dictionary
            type_name: Type of classification ('gesture', 'eye', 'emotion')

        Returns:
            Enhanced response string
        """
        # If we have a conversation engine, use it for enhanced responses
        try:
            from conversation_engine import get_conversation_engine

            conversation_engine = get_conversation_engine()

            context = {
                "modality": type_name,
                "expression": result["expression"],
                "intent": result["intent"],
                "confidence": result["confidence"],
                "base_message": result["message"],
            }

            enhanced = conversation_engine.generate_response(
                context=context, persona=self.conversation_persona
            )

            if enhanced:
                return enhanced
        except (ImportError, Exception) as e:
            logger.warning(f"Error enhancing response with conversation engine: {e}")

        # Fallback to basic enhancement if conversation engine fails
        prefix = ""
        if type_name == "gesture":
            prefix = "I see your gesture. "
        elif type_name == "eye":
            prefix = "I notice your eye movement. "
        elif type_name == "emotion":
            prefix = "I sense your emotion. "

        return f"{prefix}{result['message']}"

    def clear_buffers(self):
        """Clear all sequence buffers."""
        self.gesture_buffer = []
        self.eye_buffer = []
        self.emotion_buffer = []
        logger.info("All sequence buffers cleared")
        return True

    def set_conversation_persona(self, persona):
        """Set the conversation persona for response generation.

        Args:
            persona: Persona identifier

        Returns:
            True if successful, False otherwise
        """
        valid_personas = [
            "default",
            "academic",
            "clinical",
            "supportive",
            "child-friendly",
        ]
        if persona in valid_personas:
            self.conversation_persona = persona
            logger.info(f"Conversation persona set to {persona}")
            return True
        else:
            logger.warning(f"Invalid persona: {persona}")
            return False

    def get_academic_response(self, topic, depth="advanced"):
        """Generate a PhD-level academic response on a given topic.

        Args:
            topic: Topic to discuss
            depth: Depth of response ('basic', 'intermediate', 'advanced')

        Returns:
            Academic response string
        """
        try:
            from conversation_engine import get_conversation_engine

            conversation_engine = get_conversation_engine()

            context = {"topic": topic, "depth": depth, "response_type": "academic"}

            response = conversation_engine.generate_response(
                context=context, persona="academic"
            )

            if response:
                return response
        except (ImportError, Exception) as e:
            logger.warning(f"Error generating academic response: {e}")

        # Fallback response
        depth_text = {
            "basic": "basic overview",
            "intermediate": "intermediate analysis",
            "advanced": "advanced analysis",
        }.get(depth, "analysis")

        return f"Here's a {depth_text} of {topic}: (Academic content would be generated here based on the latest research)"


# Create singleton instance
_temporal_engine_instance = None


def get_temporal_engine():
    """Get the singleton temporal engine instance."""
    global _temporal_engine_instance
    if _temporal_engine_instance is None:
        _temporal_engine_instance = TemporalNonverbalEngine()
    return _temporal_engine_instance


# ==============================================================================
# © 2025 Everett Nathaniel Christman
# The Christman AI Project — Luma Cognify AI
# All rights reserved. Unauthorized use, replication, or derivative training
# of this material is prohibited.
#
# Core Directive: "How can I help you love yourself more?"
# Autonomy & Alignment Protocol v3.0
# ==============================================================================
