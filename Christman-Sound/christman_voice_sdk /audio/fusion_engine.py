"""
Christman Fusion Engine
=======================

Carbon ↔ Silicon Symbiosis Core

Combines emotional intuition (Carbon) with structured reasoning (Silicon)
while maintaining safety boundaries (Aegis).
"""

from __future__ import annotations
import random
import re
from typing import List, Dict, Any

from voice_stack.utils.logger import get_logger

logger = get_logger(__name__)
random.seed(42)


def tokenize(text: str) -> List[str]:
    """Simple tokenization."""
    return [w.lower() for w in text.split() if w.strip()]


def bow(text: str) -> Dict[str, float]:
    """Bag-of-words vector."""
    vector = {}
    for token in tokenize(text):
        vector[token] = vector.get(token, 0.0) + 1.0
    return vector


def cosine_sim(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity between sparse vectors."""
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
    norm_a = (sum(v * v for v in a.values()) ** 0.5) or 1.0
    norm_b = (sum(v * v for v in b.values()) ** 0.5) or 1.0
    return dot / (norm_a * norm_b)


class Carbon:
    """Emotional / intuitive layer."""
    def __init__(self, affect_bias: float = 0.6):
        self.affect_bias = affect_bias
        self.emotion_lexicon = {
            "love": 1.0, "care": 0.9, "safe": 0.8, "help": 0.8,
            "angry": -0.9, "attack": -0.9, "hurt": -0.8
        }

    def encode(self, text: str) -> Dict[str, float]:
        """Encode text with emotional weighting."""
        vector = bow(text)
        for word, weight in self.emotion_lexicon.items():
            if word in vector:
                vector[word] *= (1.0 + self.affect_bias * abs(weight))
        return vector


class Silicon:
    """Structured / logical layer."""
    def __init__(self):
        self.knowledge_patterns = [
            ("recipe", "bake cook oven sugar butter"),
            ("safety", "safe calm plan confirm"),
            ("voice", "speak say read listen"),
            ("memory", "remember remind schedule"),
        ]

    def retrieve(self, intent_vec: Dict[str, float]) -> Dict[str, float]:
        """Retrieve relevant structural patterns."""
        best = {}
        best_score = -1.0

        for label, text in self.knowledge_patterns:
            pattern_vec = bow(text)
            score = cosine_sim(intent_vec, pattern_vec)
            if score > best_score:
                best_score = score
                best = pattern_vec

        return best


class Aegis:
    """Safety and sanitization layer."""
    def __init__(self):
        self.blocklist = {"kill", "attack", "fraud", "harm"}

    def sanitize(self, text: str) -> str:
        """Basic safety sanitization."""
        for word in self.blocklist:
            text = re.sub(rf'\b{word}\b', '[REDACTED]', text, flags=re.IGNORECASE)
        return text


class FusionEngine:
    """
    Main Fusion Engine - Combines Carbon (emotion) + Silicon (structure)
    under Aegis (safety).
    """

    def __init__(self):
        self.carbon = Carbon()
        self.silicon = Silicon()
        self.aegis = Aegis()
        self.shared_state = {}  # Entanglement memory
        logger.info("Christman Fusion Engine initialized")

    def fuse(self, user_input: str) -> Dict[str, Any]:
        """Run one fusion cycle."""
        # 1. Carbon encodes emotional intent
        intent_vec = self.carbon.encode(user_input)

        # 2. Silicon retrieves structure
        structure = self.silicon.retrieve(intent_vec)

        # 3. Combine (fusion)
        fused = {**intent_vec, **structure}

        # 4. Safety check
        safe_text = self.aegis.sanitize(user_input)

        # 5. Update shared state
        self.shared_state = {**self.shared_state, **fused}

        coherence = cosine_sim(intent_vec, structure)

        return {
            "input": user_input,
            "sanitized": safe_text,
            "fused_vector_size": len(fused),
            "coherence": round(coherence, 3),
            "output": safe_text[:200] + "..." if len(safe_text) > 200 else safe_text,
        }


# Singleton
_fusion_engine = None


def get_fusion_engine() -> FusionEngine:
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = FusionEngine()
    return _fusion_engine