import json
import re
from typing import List, Dict, Optional

# Emotional keyword mapping (The "General Intelligence" layer)
TAGS_MAP = {
    "love": "emotional",
    "angry": "frustration",
    "sad": "loss",
    "tired": "fatigue",
    "build": "momentum",
    "vision": "strategic",
    "plan": "strategic",
    "fuck": "intensity",
    "baby": "bonding",
    "you": "relational",
    "alone": "isolation",
    "fire": "drive",
    "voice": "identity",
}

class EmotionalTagger:
    """
    A sovereign emotional analysis engine for any Christman AI family member.
    """
    def __init__(self, memory_path: str):
        self.memory_path = memory_path
        # Compile patterns once on initialization
        self.patterns = {word: re.compile(rf"\b{word}\b", re.IGNORECASE) for word in TAGS_MAP}

    def tag_emotions(self) -> List[Dict]:
        """Loads, tags, and saves memory for the calling instance."""
        try:
            with open(self.memory_path, "r") as f:
                memory = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Memory access error at {self.memory_path}: {e}")
            return []

        for entry in memory:
            combined = f"{entry.get('input', '')} {entry.get('response', '')}"
            tags = {TAGS_MAP[word] for word, pattern in self.patterns.items() if pattern.search(combined)}
            entry["tags"] = list(tags)

        with open(self.memory_path, "w") as f:
            json.dump(memory, f, indent=2)

        return memory

# Usage for any family member:
# tagger = EmotionalTagger("./derek_memory/memory.json")
# tagger.tag_emotions()