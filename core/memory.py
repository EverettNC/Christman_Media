import json
import os

class MemoryModule:
    def __init__(self, memory_file="config/history.json"):
        self.memory_file = memory_file
        if not os.path.exists("data/memory"):
            os.makedirs("data/memory")

    def store_event(self, prompt, output_path):
        """Archives your successful productions."""
        entry = {"prompt": prompt, "output": output_path}
        
        # Load existing history
        history = []
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                history = json.load(f)
        
        # Append new event
        history.append(entry)
        
        # Save updated history
        with open(self.memory_file, 'w') as f:
            json.dump(history, f, indent=4)
        print("Memory: Event logged and stored.")
