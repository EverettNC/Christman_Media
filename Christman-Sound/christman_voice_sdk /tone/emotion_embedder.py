"""
Emotion Embedder Module - Stage 4: Emotional Embedding

Maps emotional states to voice synthesis parameters.
Integrates with Sierra (CHRISTMAN_MIND emotional intelligence agent).
"""

import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from logger import get_logger
from audio.config import Tier

logger = get_logger(__name__)


class EmotionalState(Enum):
    """Standard emotional states for voice synthesis."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    SURPRISED = "surprised"
    # Extended for higher tiers
    PROUD = "proud"
    TEASING = "teasing"
    ANNOYED = "annoyed"
    SARCASTIC = "sarcastic"
    # Shorty-specific (ULTRA tier only)
    SWEETHEART = "sweetheart"
    LAUGH = "laugh"
    TREMBLE = "tremble"
    EMPHASIS = "emphasis"
    LAST_BREATH = "last_breath"


@dataclass
class EmotionEmbedding:
    """Emotional parameters for voice synthesis."""
    state: EmotionalState
    intensity: float  # 0-1
    valence: float    # -1 (negative) to +1 (positive)
    arousal: float    # 0 (calm) to 1 (excited)
    dominance: float  # 0 (submissive) to 1 (dominant)
    
    # Voice modification parameters
    pitch_shift: float      # Semitones (-12 to +12)
    tempo_factor: float     # Speed multiplier (0.5 to 2.0)
    energy_boost: float     # Energy multiplier (0.5 to 2.0)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "intensity": round(self.intensity, 3),
            "valence": round(self.valence, 3),
            "arousal": round(self.arousal, 3),
            "dominance": round(self.dominance, 3),
            "pitch_shift": round(self.pitch_shift, 2),
            "tempo_factor": round(self.tempo_factor, 2),
            "energy_boost": round(self.energy_boost, 2)
        }


class EmotionEmbedder:
    """
    Stage 4: Emotional Embedding System
    
    Maps emotional states to voice synthesis parameters.
    Integrates with:
    - Sierra (CHRISTMAN_MIND emotional intelligence)
    - ToneScore™ engine (real-time emotion detection)
    - Voice synthesizers (GPT-SoVITS, F5-TTS, StyleTTS2)
    """
    
    # Emotion parameter templates (based on psychological research)
    EMOTION_TEMPLATES = {
        EmotionalState.NEUTRAL: {
            "valence": 0.0,
            "arousal": 0.4,
            "dominance": 0.5,
            "pitch_shift": 0.0,
            "tempo_factor": 1.0,
            "energy_boost": 1.0
        },
        EmotionalState.HAPPY: {
            "valence": 0.8,
            "arousal": 0.7,
            "dominance": 0.6,
            "pitch_shift": 2.0,    # Slightly higher pitch
            "tempo_factor": 1.1,    # Slightly faster
            "energy_boost": 1.2
        },
        EmotionalState.SAD: {
            "valence": -0.7,
            "arousal": 0.3,
            "dominance": 0.3,
            "pitch_shift": -2.0,   # Lower pitch
            "tempo_factor": 0.8,    # Slower
            "energy_boost": 0.7
        },
        EmotionalState.ANGRY: {
            "valence": -0.6,
            "arousal": 0.9,
            "dominance": 0.8,
            "pitch_shift": 3.0,     # Higher, tense
            "tempo_factor": 1.3,    # Faster
            "energy_boost": 1.5
        },
        EmotionalState.FEARFUL: {
            "valence": -0.5,
            "arousal": 0.8,
            "dominance": 0.2,
            "pitch_shift": 4.0,     # Higher, shaky
            "tempo_factor": 1.2,
            "energy_boost": 0.9
        },
        EmotionalState.PROUD: {
            "valence": 0.7,
            "arousal": 0.6,
            "dominance": 0.8,
            "pitch_shift": 1.0,
            "tempo_factor": 0.9,
            "energy_boost": 1.3
        },
        EmotionalState.TEASING: {
            "valence": 0.5,
            "arousal": 0.6,
            "dominance": 0.6,
            "pitch_shift": 1.5,
            "tempo_factor": 1.05,
            "energy_boost": 1.1
        },
        EmotionalState.SARCASTIC: {
            "valence": -0.2,
            "arousal": 0.5,
            "dominance": 0.7,
            "pitch_shift": -1.0,
            "tempo_factor": 0.95,
            "energy_boost": 1.0
        },
        EmotionalState.SWEETHEART: {
            "valence": 0.8,
            "arousal": 0.4,
            "dominance": 0.5,
            "pitch_shift": 0.5,
            "tempo_factor": 0.9,
            "energy_boost": 0.9
        },
        EmotionalState.TREMBLE: {
            "valence": -0.3,
            "arousal": 0.5,
            "dominance": 0.3,
            "pitch_shift": -0.5,
            "tempo_factor": 0.85,
            "energy_boost": 0.8
        }
    }
    
    def __init__(self, tier: Tier = Tier.BASIC):
        """Initialize emotion embedder.
        
        Args:
            tier: Processing tier (determines available emotions)
        """
        self.tier = tier
        
        # Get available emotions based on tier
        if tier == Tier.FREE:
            self.available_emotions = [
                EmotionalState.NEUTRAL,
                EmotionalState.HAPPY,
                EmotionalState.SAD
            ]
        elif tier in [Tier.BASIC, Tier.PREMIUM]:
            self.available_emotions = [
                EmotionalState.NEUTRAL,
                EmotionalState.HAPPY,
                EmotionalState.SAD,
                EmotionalState.ANGRY,
                EmotionalState.FEARFUL,
                EmotionalState.PROUD,
                EmotionalState.TEASING
            ]
        else:  # ELITE and ULTRA
            self.available_emotions = list(EmotionalState)
        
        logger.info(f"EmotionEmbedder initialized for tier {tier.value}")
        logger.info(f"Available emotions: {len(self.available_emotions)}")
    
    def embed_emotion(
        self,
        emotion: str,
        intensity: float = 1.0
    ) -> EmotionEmbedding:
        """
        Create emotion embedding for synthesis.
        
        Args:
            emotion: Emotion name (string)
            intensity: Emotion intensity (0-1)
            
        Returns:
            EmotionEmbedding object
        """
        # Parse emotion string to enum
        try:
            state = EmotionalState(emotion.lower())
        except ValueError:
            logger.warning(f"Unknown emotion '{emotion}', defaulting to neutral")
            state = EmotionalState.NEUTRAL
        
        # Check tier availability
        if state not in self.available_emotions:
            logger.warning(f"Emotion '{emotion}' not available in tier {self.tier.value}")
            state = EmotionalState.NEUTRAL
        
        # Get template
        template = self.EMOTION_TEMPLATES.get(
            state,
            self.EMOTION_TEMPLATES[EmotionalState.NEUTRAL]
        )
        
        # Apply intensity scaling
        embedding = EmotionEmbedding(
            state=state,
            intensity=min(1.0, max(0.0, intensity)),
            valence=template["valence"] * intensity,
            arousal=template["arousal"] + (intensity - 0.5) * 0.3,  # Intensity affects arousal
            dominance=template["dominance"],
            pitch_shift=template["pitch_shift"] * intensity,
            tempo_factor=1.0 + (template["tempo_factor"] - 1.0) * intensity,
            energy_boost=1.0 + (template["energy_boost"] - 1.0) * intensity
        )
        
        return embedding
    
    def from_sierra_signal(
        self,
        sierra_emotion: str,
        sierra_intensity: float
    ) -> EmotionEmbedding:
        """
        Convert Sierra EmotionalSignal to voice synthesis embedding.
        
        Integration with CHRISTMAN_MIND Sierra agent.
        
        Args:
            sierra_emotion: Primary emotion from Sierra (grief, trauma, healing, anger)
            sierra_intensity: Intensity from Sierra (0-1)
            
        Returns:
            EmotionEmbedding for voice synthesis
        """
        # Map Sierra emotions to voice synthesis emotions
        sierra_to_voice = {
            "grief": EmotionalState.SAD,
            "trauma": EmotionalState.FEARFUL,
            "healing": EmotionalState.HAPPY,
            "anger": EmotionalState.ANGRY,
            "neutral": EmotionalState.NEUTRAL
        }
        
        voice_emotion = sierra_to_voice.get(
            sierra_emotion.lower(),
            EmotionalState.NEUTRAL
        )
        
        return self.embed_emotion(voice_emotion.value, sierra_intensity)
    
    def from_tonescore(
        self,
        tonescore_result: Dict
    ) -> EmotionEmbedding:
        """
        Convert ToneScore™ analysis to voice synthesis embedding.
        
        Args:
            tonescore_result: Result from ToneScoreEngine.analyze_tone()
            
        Returns:
            EmotionEmbedding for voice synthesis
        """
        # Get dominant emotion from ToneScore™
        emotions = tonescore_result.get("emotions", {})
        if emotions:
            dominant = max(emotions.items(), key=lambda x: x[1])
            emotion_name = dominant[0]
            confidence = dominant[1]
        else:
            emotion_name = "neutral"
            confidence = 0.5
        
        # Map ToneScore™ emotion to our enum
        tonescore_to_voice = {
            "anger": EmotionalState.ANGRY,
            "joy": EmotionalState.HAPPY,
            "sadness": EmotionalState.SAD,
            "fear": EmotionalState.FEARFUL,
            "disgust": EmotionalState.DISGUSTED,
            "surprise": EmotionalState.SURPRISED,
            "neutral": EmotionalState.NEUTRAL
        }
        
        voice_emotion = tonescore_to_voice.get(
            emotion_name,
            EmotionalState.NEUTRAL
        )
        
        # Create embedding with ToneScore™ intensity
        emotion_intensity = tonescore_result.get("emotion_intensity", 50) / 100.0
        
        return self.embed_emotion(voice_emotion.value, emotion_intensity)
    
    def interpolate_emotions(
        self,
        emotion1: EmotionEmbedding,
        emotion2: EmotionEmbedding,
        alpha: float = 0.5
    ) -> EmotionEmbedding:
        """
        Interpolate between two emotional states.
        
        Useful for:
        - Smooth emotional transitions
        - Blended emotional expressions
        - Dynamic emotion evolution
        
        Args:
            emotion1: First emotion
            emotion2: Second emotion
            alpha: Interpolation factor (0=emotion1, 1=emotion2)
            
        Returns:
            Interpolated emotion embedding
        """
        alpha = min(1.0, max(0.0, alpha))
        
        return EmotionEmbedding(
            state=emotion1.state if alpha < 0.5 else emotion2.state,
            intensity=(1 - alpha) * emotion1.intensity + alpha * emotion2.intensity,
            valence=(1 - alpha) * emotion1.valence + alpha * emotion2.valence,
            arousal=(1 - alpha) * emotion1.arousal + alpha * emotion2.arousal,
            dominance=(1 - alpha) * emotion1.dominance + alpha * emotion2.dominance,
            pitch_shift=(1 - alpha) * emotion1.pitch_shift + alpha * emotion2.pitch_shift,
            tempo_factor=(1 - alpha) * emotion1.tempo_factor + alpha * emotion2.tempo_factor,
            energy_boost=(1 - alpha) * emotion1.energy_boost + alpha * emotion2.energy_boost
        )
    
    def get_response_mode_emotion(
        self,
        tonescore: float
    ) -> EmotionEmbedding:
        """
        Get appropriate response emotion based on ToneScore™.
        
        Implements adaptive response modes:
        - ToneScore > 75: "hold-space" mode (calming)
        - ToneScore < 35: "gentle-lift" mode (supportive)
        - ToneScore 35-75: Standard (neutral)
        
        Args:
            tonescore: ToneScore™ value (0-100)
            
        Returns:
            Appropriate emotion for response
        """
        if tonescore > 75:
            # Hold-space mode: calm, grounding
            return EmotionEmbedding(
                state=EmotionalState.NEUTRAL,
                intensity=0.6,
                valence=0.2,
                arousal=0.2,   # Very calm
                dominance=0.5,
                pitch_shift=-1.0,  # Slightly lower
                tempo_factor=0.85,  # Slower
                energy_boost=0.8
            )
        elif tonescore < 35:
            # Gentle-lift mode: warm, supportive
            return EmotionEmbedding(
                state=EmotionalState.SWEETHEART if self.tier == Tier.ULTRA else EmotionalState.HAPPY,
                intensity=0.5,
                valence=0.6,
                arousal=0.5,
                dominance=0.4,
                pitch_shift=0.5,
                tempo_factor=0.95,
                energy_boost=1.1
            )
        else:
            # Standard mode: neutral, balanced
            return self.embed_emotion("neutral", 0.7)


if __name__ == "__main__":
    embedder = EmotionEmbedder(tier=Tier.ULTRA)
    
    print("\n=== Emotion Embedding Examples ===\n")
    
    # Example 1: Direct emotion embedding
    happy = embedder.embed_emotion("happy", intensity=0.8)
    print(f"Happy (80% intensity):")
    print(f"  Pitch shift: {happy.pitch_shift:+.1f} semitones")
    print(f"  Tempo: {happy.tempo_factor:.2f}x")
    print(f"  Energy: {happy.energy_boost:.2f}x")
    print(f"  VAD: v={happy.valence:.2f}, a={happy.arousal:.2f}, d={happy.dominance:.2f}\n")
    
    # Example 2: From Sierra signal
    sierra_grief = embedder.from_sierra_signal("grief", 0.85)
    print(f"Sierra grief signal (85% intensity):")
    print(f"  State: {sierra_grief.state.value}")
    print(f"  Pitch shift: {sierra_grief.pitch_shift:+.1f} semitones")
    print(f"  Tempo: {sierra_grief.tempo_factor:.2f}x\n")
    
    # Example 3: Response mode for high ToneScore™
    high_stress = embedder.get_response_mode_emotion(82)
    print(f"Response mode for ToneScore™ 82 (hold-space):")
    print(f"  Arousal: {high_stress.arousal:.2f} (calming)")
    print(f"  Tempo: {high_stress.tempo_factor:.2f}x (slower)")
    print(f"  Pitch: {high_stress.pitch_shift:+.1f} (deeper)\n")
