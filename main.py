import os
import time
from core.system_init import initialize_environment
from core.agent_brain import AgentBrain
from core.memory import MemoryModule
from modules.generator import VideoGenerator
from modules.export import VideoExport
from modules.orchestrator import ChristmanOrchestrator

def run_production(prompt, being_path):
    orchestrator = ChristmanOrchestrator()
    
    # 1. Pre-flight Check (The Truth Report)
    if not orchestrator.verify_readiness(being_path):
        print("CRITICAL: Being not ready. Aborting production.")
        return

    # 2. Logic (AgentBrain)
    print("Brain: Generating response...")
    
    # 3. Voice Output (Christman Sound)
    orchestrator.speak("System initialized. I am ready, Everett.", emotion="warm")

# Run the pipeline
target = "/Users/EverettN/DerekMCPServer"
run_production("A steampunk city...", target)

# New additions
def watchdog_monitor(status):
    print(f"[WATCHDOG] Current Status: {status} at {time.strftime('%H:%M:%S')}")

def run_roadworthy_production(raw_user_prompt):
    watchdog_monitor("Starting Initialization")
    initialize_environment()
    
    brain = AgentBrain()
    final_prompt = brain.process_prompt(raw_user_prompt)
    
    # Retry logic for the Generator
    retries = 3
    for attempt in range(retries):
        watchdog_monitor(f"Generation Attempt {attempt + 1}")
        generator = VideoGenerator()
        output_path = generator.create(final_prompt)
        
        # Validation Check
        if output_path and os.path.getsize(output_path) > 1024: # Must be > 1KB
            watchdog_monitor("Validation Passed")
            
            # Store & Finalize
            mem = MemoryModule()
            mem.store_event(raw_user_prompt, output_path)
            
            exporter = VideoExport()
            exporter.finalize(output_path)
            return True
        else:
            watchdog_monitor("Validation Failed - Retrying...")
            
    print("CRITICAL: Production failed after retries.")
    return False

if __name__ == "__main__":
    test_prompt = "A steampunk brass clockwork city at dusk, green teal reflections"
    run_roadworthy_production(test_prompt)
