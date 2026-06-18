import os
import sys
import platform
import subprocess
import json

def check_dependencies():
    """Verify that FFmpeg is installed, as it's the foundation for our video processing."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def initialize_environment():
    """Detect OS and setup the local workspace."""
    print(f"--- Christman AI Engine: Initializing on {platform.system()} {platform.release()} ---")
    
    # 1. Ensure the directory structure exists
    dirs = ['core', 'modules', 'data', 'assets', 'logs', 'config']
    for folder in dirs:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created: /{folder}")
    
    # 2. Check dependencies
    if not check_dependencies():
        print("CRITICAL: FFmpeg not found. Please install FFmpeg to proceed.")
        return False
    
    # 3. Create or Update local system configuration
    sys_config = {
        "os": platform.system(),
        "arch": platform.machine(),
        "initialized_at": "2026-05-22",
        "aesthetic_profile": "steampunk_v1"
    }
    
    with open("config/system.json", "w") as f:
        json.dump(sys_config, f, indent=4)
        
    print("Environment verified and ready. All systems nominal.")
    return True

if __name__ == "__main__":
    initialize_environment()
