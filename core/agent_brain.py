class AgentBrain:
    def __init__(self):
        self.style_guide = "steampunk aesthetic, intricate clockwork details, warm brass and deep teal color palette"

    def process_prompt(self, user_input):
        """Translates intent into a technical prompt for the generation engine."""
        # We append the steampunk aesthetic automatically so every 
        # creation aligns with your vision.
        refined_prompt = f"{user_input}, {self.style_guide}"
        print(f"Brain: Intent decoded. Executing: {refined_prompt}")
        return refined_prompt
