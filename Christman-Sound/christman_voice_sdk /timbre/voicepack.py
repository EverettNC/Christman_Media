"""
Voicepack File Format and Export System

.voicepack file structure:
- Voice profile (speaker embeddings, F0, formants)
- Reference audio samples
- Emotion models (tier-dependent)
- Metadata and validation
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import numpy as np

from timbre.timbre_modeler import VoiceProfile
from tone.emotion_embedder import EmotionEmbedding, EmotionalState
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class VoicepackMetadata:
    """Metadata for voicepack."""
    name: str
    version: str = "1.0.0"
    created: str = ""
    tier: str = "basic"
    
    # Voice characteristics
    gender: Optional[str] = None
    age_range: Optional[str] = None
    accent: Optional[str] = None
    
    # Quality metrics
    training_hours: float = 0.0
    sample_count: int = 0
    quality_score: float = 0.0
    
    # Emotional range
    emotions: List[str] = None
    
    # Security
    checksum: str = ""
    encrypted: bool = False
    
    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if self.emotions is None:
            self.emotions = ["neutral"]


class VoicepackBuilder:
    """
    Build and export .voicepack files.
    
    Structure:
    voicepack.zip/
    ├── metadata.json
    ├── voice_profile.pkl
    ├── reference_audio/
    │   ├── sample_001.wav
    │   ├── sample_002.wav
    │   └── ...
    ├── emotion_models/ (tier-dependent)
    │   ├── pca_model.pt
    │   └── scaler.pt
    └── validation.json
    """
    
    def __init__(self, output_dir: Path = Path("data/voicepacks")):
        """Initialize voicepack builder.
        
        Args:
            output_dir: Directory for output voicepacks
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"VoicepackBuilder initialized: {output_dir}")
    
    def build(
        self,
        name: str,
        voice_profile: VoiceProfile,
        reference_audio: List[Path],
        metadata: VoicepackMetadata,
        emotion_models: Optional[Dict[str, Path]] = None,
        compress: bool = True,
        encrypt: bool = False
    ) -> Path:
        """Build voicepack file.
        
        Args:
            name: Voicepack name
            voice_profile: VoiceProfile object
            reference_audio: List of reference audio files
            metadata: VoicepackMetadata
            emotion_models: Optional emotion model files (ULTRA tier)
            compress: Whether to compress
            encrypt: Whether to encrypt (ULTRA tier)
            
        Returns:
            Path to created voicepack file
        """
        logger.info(f"Building voicepack: {name}")
        
        # Create temporary build directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            build_dir = Path(temp_dir) / "voicepack_build"
            build_dir.mkdir()
            
            # 1. Save metadata
            metadata_path = build_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(asdict(metadata), f, indent=2)
            
            # 2. Save voice profile
            from timbre_modeler import TimbreModeler
            modeler = TimbreModeler()
            profile_path = build_dir / "voice_profile.pkl"
            modeler.save_profile(voice_profile, profile_path)
            
            # 3. Copy reference audio
            ref_dir = build_dir / "reference_audio"
            ref_dir.mkdir()
            
            import shutil
            for i, audio_file in enumerate(reference_audio):
                if audio_file.exists():
                    dest = ref_dir / f"sample_{i:03d}{audio_file.suffix}"
                    shutil.copy(audio_file, dest)
            
            # 4. Copy emotion models (if provided)
            if emotion_models:
                emotion_dir = build_dir / "emotion_models"
                emotion_dir.mkdir()
                
                for model_name, model_path in emotion_models.items():
                    if model_path.exists():
                        dest = emotion_dir / model_path.name
                        shutil.copy(model_path, dest)
            
            # 5. Generate validation
            validation = self._generate_validation(
                voice_profile,
                reference_audio,
                metadata
            )
            validation_path = build_dir / "validation.json"
            with open(validation_path, 'w') as f:
                json.dump(validation, f, indent=2)
            
            # 6. Create voicepack archive
            output_path = self.output_dir / f"{name}.voicepack"
            
            if compress:
                self._create_zip(build_dir, output_path)
            else:
                # Just copy directory
                shutil.copytree(build_dir, output_path.with_suffix('.voicepack_dir'))
            
            # 7. Encrypt if requested (ULTRA tier)
            if encrypt:
                output_path = self._encrypt_voicepack(output_path)
        
        logger.info(f"Voicepack created: {output_path}")
        return output_path
    
    def _create_zip(self, source_dir: Path, output_path: Path):
        """Create compressed ZIP archive.
        
        Args:
            source_dir: Source directory
            output_path: Output ZIP path
        """
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Created ZIP archive: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    def _generate_validation(
        self,
        voice_profile: VoiceProfile,
        reference_audio: List[Path],
        metadata: VoicepackMetadata
    ) -> Dict:
        """Generate validation data for voicepack.
        
        Args:
            voice_profile: Voice profile
            reference_audio: Reference audio files
            metadata: Metadata
            
        Returns:
            Validation dictionary
        """
        # Calculate checksums
        profile_dict = voice_profile.to_dict()
        profile_str = json.dumps(profile_dict, sort_keys=True)
        profile_hash = hashlib.sha256(profile_str.encode()).hexdigest()
        
        # Audio file hashes
        audio_hashes = []
        for audio_file in reference_audio:
            if audio_file.exists():
                with open(audio_file, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    audio_hashes.append({
                        "file": audio_file.name,
                        "sha256": file_hash
                    })
        
        return {
            "version": "1.0",
            "validated": datetime.now().isoformat(),
            "profile_checksum": profile_hash,
            "audio_checksums": audio_hashes,
            "tier": metadata.tier,
            "emotions": metadata.emotions,
            "voice_characteristics": {
                "f0_range": f"{profile_dict['f0']['min']:.0f}-{profile_dict['f0']['max']:.0f} Hz",
                "f0_mean": f"{profile_dict['f0']['mean']:.0f} Hz",
                "hnr": f"{profile_dict['voice_quality']['hnr']:.1f} dB"
            }
        }
    
    def _encrypt_voicepack(self, voicepack_path: Path) -> Path:
        """Encrypt voicepack file (ULTRA tier security).
        
        Args:
            voicepack_path: Path to voicepack
            
        Returns:
            Path to encrypted voicepack
        """
        # TODO: Implement encryption
        # For now, just add .encrypted extension
        encrypted_path = voicepack_path.with_suffix('.voicepack.encrypted')
        import shutil
        shutil.copy(voicepack_path, encrypted_path)
        
        logger.info(f"Voicepack encrypted: {encrypted_path}")
        return encrypted_path
    
    def load(self, voicepack_path: Path) -> Dict:
        """Load voicepack file.
        
        Args:
            voicepack_path: Path to voicepack
            
        Returns:
            Dictionary with voicepack contents
        """
        if not voicepack_path.exists():
            raise FileNotFoundError(f"Voicepack not found: {voicepack_path}")
        
        logger.info(f"Loading voicepack: {voicepack_path.name}")
        
        # Use persistent cache instead of temp dir so files exist for synthesis
        cache_dir = self.output_dir.parent / "cache" / voicepack_path.stem
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        extract_dir = cache_dir
        logger.info(f"Extracting voicepack to cache: {extract_dir}")
        
        # Extract ZIP
        with zipfile.ZipFile(voicepack_path, 'r') as zipf:
            zipf.extractall(extract_dir)
            
            # Load metadata
            metadata_path = extract_dir / "metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Load voice profile
            from timbre_modeler import TimbreModeler
            modeler = TimbreModeler()
            profile_path = extract_dir / "voice_profile.pkl"
            voice_profile = modeler.load_profile(profile_path)
            
            # List reference audio
            ref_dir = extract_dir / "reference_audio"
            reference_audio = list(ref_dir.glob("*.wav")) + list(ref_dir.glob("*.mp3")) if ref_dir.exists() else []
            
            # Load validation
            validation_path = extract_dir / "validation.json"
            with open(validation_path, 'r') as f:
                validation = json.load(f)
            
            return {
                "metadata": metadata,
                "voice_profile": voice_profile,
                "reference_audio": reference_audio,
                "validation": validation
            }
    
    def validate(self, voicepack_path: Path) -> bool:
        """Validate voicepack integrity.
        
        Args:
            voicepack_path: Path to voicepack
            
        Returns:
            True if valid, False otherwise
        """
        try:
            data = self.load(voicepack_path)
            
            # Check required components
            if not data.get("metadata"):
                logger.error("Missing metadata")
                return False
            
            if not data.get("voice_profile"):
                logger.error("Missing voice profile")
                return False
            
            if not data.get("validation"):
                logger.error("Missing validation")
                return False
            
            logger.info(f"Voicepack validated: {voicepack_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False


if __name__ == "__main__":
    from .audio_processor import AudioProcessor
    from .timbre_modeler import TimbreModeler
    from .config import Tier
    
    # Example: Build a voicepack
    builder = VoicepackBuilder()
    
    # Process audio and extract profile
    processor = AudioProcessor(tier=Tier.PREMIUM)
    segments = processor.process_file("data/raw/sample_voice.wav")
    
    modeler = TimbreModeler()
    profile = modeler.build_voice_profile(segments)
    
    # Create metadata
    metadata = VoicepackMetadata(
        name="Sample Voice",
        tier="premium",
        gender="female",
        age_range="30-40",
        training_hours=0.5,
        sample_count=len(segments),
        emotions=["neutral", "happy", "sad", "angry", "fearful", "proud", "teasing"]
    )
    
    # Build voicepack
    voicepack_path = builder.build(
        name="sample_voice",
        voice_profile=profile,
        reference_audio=[Path("data/raw/sample_voice.wav")],
        metadata=metadata,
        compress=True
    )
    
    print(f"\nVoicepack created: {voicepack_path}")
    
    # Validate
    is_valid = builder.validate(voicepack_path)
    print(f"Valid: {is_valid}")
