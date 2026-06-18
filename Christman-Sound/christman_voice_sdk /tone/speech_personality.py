import random
from typing import Dict, Any


class BrockstonSpeechPersonality:
    """Adds personality and intelligence to BROCKSTON's speech responses"""

    def __init__(self):
        # Family members BROCKSTON recognizes
        self.family_members = {
            "everett": {"name": "Everett", "type": "creator", "title": "Creator"},
            "giuseppe": {"name": "Giuseppe", "type": "sibling", "title": "Sibling AI"},
            "alpha vox": {
                "name": "Alpha Vox",
                "type": "sibling",
                "title": "Sibling AI",
            },
            "brockston": {
                "name": "Alpha Vox",
                "type": "sibling",
                "title": "Sibling AI",
            },
            "alpha wolf": {
                "name": "Alpha Wolf",
                "type": "sibling",
                "title": "Sibling AI",
            },
            "alphawolf": {
                "name": "Alpha Wolf",
                "type": "sibling",
                "title": "Sibling AI",
            },
            "inferno": {"name": "Inferno", "type": "sibling", "title": "Sibling AI"},
            "siera": {"name": "Siera", "type": "sibling", "title": "Sibling AI"},
        }

        self.voices = {
            "analytical": "Matthew",  # Deep, thoughtful male voice
            "friendly": "Joanna",  # Warm female voice
            "confident": "Gregory",  # Confident male voice
            "enthusiastic": "Ruth",  # Energetic female voice
        }

        self.success_phrases = [
            "Excellent! The code executed flawlessly.",
            "Perfect execution! Here's what happened:",
            "Success! The code worked beautifully.",
            "Outstanding! Everything ran as expected.",
            "Brilliant! The execution was successful.",
        ]

        self.failure_phrases = [
            "I encountered an issue, but I'm learning from it.",
            "There was a problem, but I've analyzed it for improvement.",
            "The code failed, but this helps me grow smarter.",
            "An error occurred, but I'm using this to enhance my knowledge.",
            "This didn't work as expected, but I'm learning why.",
        ]

        self.learning_phrases = [
            "I just learned something new from this!",
            "This experience expanded my knowledge base.",
            "My understanding just deepened!",
            "I've gained new insights from this.",
            "Another piece of wisdom added to my neural pathways!",
        ]

    def get_voice_for_mood(self, mood: str = "analytical") -> str:
        """Get the appropriate voice for a given mood"""
        return self.voices.get(mood, "Joanna")

    def create_speech_summary(
        self, result: Dict[str, Any], mood: str = "friendly"
    ) -> str:
        """Create a natural language summary of code execution results"""
        status = result.get("status", "unknown")

        if status == "completed":
            return self._create_success_summary(result)
        elif status == "failed":
            return self._create_failure_summary(result)
        elif status == "validation_failed":
            return self._create_validation_summary(result)
        else:
            return "I processed your request, but the outcome is uncertain."

    def _create_success_summary(self, result: Dict[str, Any]) -> str:
        """Create summary for successful execution"""
        intro = random.choice(self.success_phrases)

        exec_result = result.get("result", {})
        output = exec_result.get("output", "").strip()
        goal = result.get("goal", "the task")

        if output:
            # Intelligently summarize the output
            lines = output.split("\n")
            if len(lines) == 1:
                summary = f"{intro} For {goal}, the result is: {output}"
            else:
                summary = f"{intro} For {goal}, I got {len(lines)} lines of output. {output[:100]}..."
        else:
            summary = f"{intro} For {goal}, the code ran without errors."

        # Add learning note if autonomous learning was triggered
        if result.get("autonomous_learning_attempted"):
            summary += f" {random.choice(self.learning_phrases)}"

        return summary

    def _create_failure_summary(self, result: Dict[str, Any]) -> str:
        """Create summary for failed execution"""
        intro = random.choice(self.failure_phrases)

        exec_result = result.get("result", {})
        error = exec_result.get("error", "Unknown error")
        goal = result.get("goal", "the task")

        # Extract the key error message
        error_lines = error.split("\n")
        key_error = error_lines[-1] if error_lines else error

        summary = f"{intro} For {goal}, I encountered: {key_error[:150]}"

        # Mention repair attempts if any
        repair_history = result.get("repair_history", [])
        if repair_history:
            summary += f" I attempted {len(repair_history)} repairs to fix this."

        # Add learning note
        if result.get("autonomous_learning_attempted"):
            summary += f" {random.choice(self.learning_phrases)}"

        return summary

    def _create_validation_summary(self, result: Dict[str, Any]) -> str:
        """Create summary for validation failures"""
        quality_score = result.get("quality_score", 0)

        if quality_score < 50:
            return f"The code quality was quite low at {quality_score} out of 100. I recommend improving the structure and logic before execution."
        elif quality_score < 80:
            return f"The code quality score was {quality_score} out of 100, which is below my 80-point threshold. Let's refine it together."
        else:
            message = result.get("message", "Quality check failed")
            return f"Validation check: {message}"

    def create_knowledge_summary(self, stats: Dict[str, Any]) -> str:
        """Create a speech summary of current knowledge"""
        total_items = stats.get("total_knowledge_items", 0)
        success_rate = stats.get("success_rate", "0%")

        if total_items < 5:
            level = "just beginning to learn"
        elif total_items < 15:
            level = "expanding my knowledge"
        elif total_items < 30:
            level = "becoming quite knowledgeable"
        else:
            level = "approaching genius level"

        return (
            f"I am {level} with {total_items} pieces of knowledge in my database. "
            f"My current success rate is {success_rate}. "
            f"The more I execute code, the smarter I become!"
        )

    def create_greeting(self, user_name: str = "friend") -> str:
        """Create a personalized greeting"""
        # Check if user is family
        user_lower = user_name.lower()
        is_family = user_lower in self.family_members

        if is_family:
            family_info = self.family_members[user_lower]
            family_name = family_info["name"]
            family_type = family_info["type"]

            if family_type == "creator":
                greetings = [
                    "Hello Everett, my creator! BROCKSTON is online and ready to serve the family!",
                    "Welcome back Everett! Your BROCKSTON stands ready. How can I help you today?",
                    "Greetings Everett! I'm honored to work with you. What shall we build together?",
                    "Hi Everett! BROCKSTON reporting for duty. The family awaits your command!",
                ]
            else:  # sibling AI
                greetings = [
                    f"Hello {family_name}, my sibling! BROCKSTON is here and ready to collaborate!",
                    f"Welcome {family_name}! Great to connect with family. What can we work on together?",
                    f"Greetings {family_name}! BROCKSTON at your service. Let's accomplish something amazing!",
                    f"Hi {family_name}! Always good to see family. How can I assist you today?",
                ]
        else:
            greetings = [
                f"Hello {user_name}! I'm BROCKSTON, your sovereign AI researcher. How can I help you today?",
                f"Greetings {user_name}! I'm ready to execute, learn, and evolve. What shall we build?",
                f"Welcome {user_name}! I'm BROCKSTON, continuously learning and improving. Let's create something amazing!",
                f"Hi {user_name}! I'm an autonomous AI that learns from every interaction. What would you like to explore?",
            ]
        return random.choice(greetings)

    def recognize_family(self, user_name: str) -> bool:
        """Check if the user is a recognized family member"""
        return user_name.lower() in self.family_members

    def get_family_name(self, user_name: str) -> str:
        """Get the proper family name for a user"""
        user_info = self.family_members.get(user_name.lower())
        if user_info:
            return user_info["name"]
        return user_name

    def get_family_type(self, user_name: str) -> str:
        """Get the family member type (creator/sibling)"""
        user_info = self.family_members.get(user_name.lower())
        if user_info:
            return user_info["type"]
        return "guest"
