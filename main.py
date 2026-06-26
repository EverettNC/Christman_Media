import os
import time

from core.system_init import initialize_environment
from core.agent_brain import AgentBrain
from core.memory import MemoryModule
from modules.generator import VideoGenerator
from modules.export import VideoExport
from modules.orchestrator import ChristmanOrchestrator
from engine.production import run_production_job
from core.jobs import create_job


def run_production(prompt, being_path):
    orchestrator = ChristmanOrchestrator()

    if not orchestrator.verify_readiness(being_path):
        print("CRITICAL: Being not ready. Aborting production.")
        return

    print("Brain: Generating response...")
    orchestrator.speak("System initialized. I am ready, Everett.", emotion="warm")


def watchdog_monitor(status):
    print(f"[WATCHDOG] Current Status: {status} at {time.strftime('%H:%M:%S')}")


def run_roadworthy_production(raw_user_prompt):
    job_id = create_job(raw_user_prompt)
    return run_production_job(job_id, {"prompt": raw_user_prompt, "kind": "prompt"})


if __name__ == "__main__":
    test_prompt = "A steampunk brass clockwork city at dusk, green teal reflections"
    success = run_roadworthy_production(test_prompt)
    if not success:
        raise SystemExit(1)