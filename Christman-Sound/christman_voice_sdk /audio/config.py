"""
Configuration management for ICanHearYou voice cloning system.
Handles tier-based configuration, model paths, and system settings.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from enum import Enum
from dataclasses import dataclass

class Tier(Enum):
    """Pricing tiers with corresponding feature access."""
    FREE = "free"             # $0 - Basic voice cloning
    BASIC = "basic"           # $1.99/month - Enhanced quality
    PREMIUM = "premium"       # $29.99 one-time - High quality
    ELITE = "elite"           # $199 one-time - Active avatar
    ULTRA = "ultra"           # $1,999 custom - Full personalization

@dataclass
class TierFeatures:
    """Feature flags for each tier."""
    # Audio processing
    noise_reduction_quality: str  # "basic", "advanced", "studio"
    max_audio_duration_hours: float
    
    # Voice synthesis
    synthesis_engines: list  # Which engines are available
    emotional_range: int  # Number of emotions (3, 7, 11+)
    prosody_control: bool
    cadence_fingerprinting: bool
    
    # Advanced features
    custom_emotion_model: bool
    realtime_synthesis: bool
    avatar_integration: bool
    batch_processing: bool
    
    # Performance
    max_concurrent_requests: int
    priority_queue: str  # "low", "normal", "high", "ultra"

# Tier feature definitions
TIER_FEATURES: Dict[Tier, TierFeatures] = {
    Tier.FREE: TierFeatures(
        noise_reduction_quality="basic",
        max_audio_duration_hours=0.5,
        synthesis_engines=["gpt_sovits"],
        emotional_range=3,  # neutral, happy, sad only
        prosody_control=False,
        cadence_fingerprinting=False,
        custom_emotion_model=False,
        realtime_synthesis=False,
        avatar_integration=False,
        batch_processing=False,
        max_concurrent_requests=1,
        priority_queue="low"
    ),
    Tier.BASIC: TierFeatures(
        noise_reduction_quality="advanced",
        max_audio_duration_hours=2.0,
        synthesis_engines=["gpt_sovits", "f5_tts"],
        emotional_range=7,  # Extended emotions
        prosody_control=True,
        cadence_fingerprinting=False,
        custom_emotion_model=False,
        realtime_synthesis=False,
        avatar_integration=False,
        batch_processing=True,
        max_concurrent_requests=3,
        priority_queue="normal"
    ),
    Tier.PREMIUM: TierFeatures(
        noise_reduction_quality="studio",
        max_audio_duration_hours=5.0,
        synthesis_engines=["gpt_sovits", "f5_tts", "style_tts2"],
        emotional_range=7,
        prosody_control=True,
        cadence_fingerprinting=True,
        custom_emotion_model=False,
        realtime_synthesis=True,
        avatar_integration=False,
        batch_processing=True,
        max_concurrent_requests=5,
        priority_queue="high"
    ),
    Tier.ELITE: TierFeatures(
        noise_reduction_quality="studio",
        max_audio_duration_hours=10.0,
        synthesis_engines=["gpt_sovits", "f5_tts", "style_tts2"],
        emotional_range=11,  # Full emotional spectrum
        prosody_control=True,
        cadence_fingerprinting=True,
        custom_emotion_model=False,
        realtime_synthesis=True,
        avatar_integration=True,  # Active avatar support
        batch_processing=True,
        max_concurrent_requests=10,
        priority_queue="high"
    ),
    Tier.ULTRA: TierFeatures(
        noise_reduction_quality="studio",
        max_audio_duration_hours=float('inf'),  # Unlimited
        synthesis_engines=["gpt_sovits", "f5_tts", "style_tts2"],
        emotional_range=11,  # Including custom emotions
        prosody_control=True,
        cadence_fingerprinting=True,
        custom_emotion_model=True,  # Custom PCA-based emotion detection
        realtime_synthesis=True,
        avatar_integration=True,
        batch_processing=True,
        max_concurrent_requests=float('inf'),
        priority_queue="ultra"
    )
}

class Config:
    """Main configuration manager."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        self.root_dir = Path(__file__).parent
        self.config_path = config_path or self.root_dir / "config" / "default_config.yaml"
        
        # Load config from YAML
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f)
        else:
            self._config = self._get_default_config()
            
        # Set up paths
        self.models_dir = self.root_dir / "models"
        self.data_dir = self.root_dir / "data"
        self.logs_dir = self.root_dir / "logs"
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "system": {
                "device": "auto",  # auto, cpu, cuda, mps
                "log_level": "INFO",
                "num_workers": 4
            },
            "audio": {
                "sample_rate": 16000,  # Shorty's exact sample rate
                "target_db": -20.0,
                "silence_threshold_db": -40.0,
                "segment_length_seconds": 10.0,
                "overlap_seconds": 2.0
            },
            "models": {
                "wav2vec2_model": "jonatasgrosman/wav2vec2-large-xlsr-53-english",
                "gpt_sovits_checkpoint": "models/gpt_sovits_v3.pth",
                "f5_tts_checkpoint": "models/f5_tts.pth",
                "style_tts2_checkpoint": "models/style_tts2.pth"
            },
            "synthesis": {
                "max_length": 1000,
                "temperature": 0.7,
                "top_k": 50,
                "top_p": 0.9
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_tier_features(self, tier: Tier) -> TierFeatures:
        """Get feature set for a specific tier."""
        return TIER_FEATURES[tier]
    
    def save(self, path: Optional[Path] = None):
        """Save configuration to YAML file."""
        save_path = path or self.config_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False)

_global_config: Optional[Config] = None

def get_config(config_path: Optional[Path] = None) -> Config:
    """Get global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = Config(config_path)
    return _global_config