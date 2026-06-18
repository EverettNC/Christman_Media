import os
import subprocess
import sys

# Christman Triad Orchestrator
class ChristmanOrchestrator:
    def __init__(self, media_installer_path="/Users/EverettN/ChristmanMediaInstaller", 
                 sdk_path="/Users/EverettN/christman_voice_sdk"):
        self.installer_path = media_installer_path
        self.sdk_path = sdk_path
        sys.path.append(sdk_path) # Direct injection of your SDK

    def verify_readiness(self, being_path):
        """Invoke Media Installer Truth Report."""
        print(f"[Orchestrator] Running Truth Report on: {being_path}")
        result = subprocess.run(
            ["python3", "cli.py", "verify", "--target", being_path], 
            cwd=self.installer_path, capture_output=True, text=True
        )
        print(result.stdout)
        return "READY" in result.stdout or "READY WITH WARNINGS" in result.stdout

    def speak(self, text, emotion="warm"):
        """Invoke Christman-Sound SPEAK.py."""
        from CHRISTMAN_EAR_CANAL import speak
        print(f"[Orchestrator] Speaking: {text}")
        speak(text, emotion=emotion)
