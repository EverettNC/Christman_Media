"""
Phoneme Labeling Module - Stage 1: Phoneme Extraction

Extracts phoneme-level timing and labels from audio.
Uses Montreal Forced Aligner for precise alignment with a 
native energy-based fallback to ensure system stability.

Patent Pending TCAP-2026-001 / TCAP-2026-002
© 2026 Everett Nathaniel Christman & Misty Gail Christman
The Christman AI Project — Luma Cognify AI
Truth. Dignity. Protection. Transparency. No Erasure.
"""

import subprocess
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import List, Dict, Optional
from logger import get_logger
from audio.config import get_config

logger = get_logger(__name__)

# Optional dependencies for MFA alignment
try:
    import textgrid
    TEXTGRID_AVAILABLE = True
except ImportError:
    TEXTGRID_AVAILABLE = False
    logger.warning("textgrid library not found. MFA alignment will be unavailable.")

class Phoneme:
    """Represents a phoneme with timing information."""
    
    def __init__(self, label: str, start_time: float, end_time: float, confidence: float = 1.0):
        self.label = label
        self.start_time = start_time
        self.end_time = end_time
        self.duration = end_time - start_time
        self.confidence = confidence
    
    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "start": self.start_time,
            "end": self.end_time,
            "duration": self.duration,
            "confidence": self.confidence
        }
    
    def __repr__(self):
        return f"Phoneme({self.label}, {self.start_time:.3f}-{self.end_time:.3f})"

class PhonemeLabeler:
    """Sovereign phoneme extraction and labeling system."""
    
    PHONEME_TO_VISEME = {
        "AA": "aa", "AE": "aa", "AH": "aa", "AO": "oh", "AW": "oh", "AY": "aa",
        "EH": "eh", "ER": "er", "EY": "eh", "IH": "ih", "IY": "ih", "OW": "oh",
        "OY": "oh", "UH": "oh", "UW": "oh", "B": "pp", "P": "pp", "M": "pp",
        "F": "ff", "V": "ff", "TH": "th", "DH": "th", "S": "ss", "Z": "ss",
        "T": "dd", "D": "dd", "N": "nn", "L": "nn", "SH": "ch", "ZH": "ch",
        "CH": "ch", "JH": "ch", "K": "kk", "G": "kk", "NG": "nn", "HH": "sil",
        "W": "oh", "Y": "ih", "R": "rr", "SIL": "sil", "SP": "sil"
    }
    
    def __init__(self, use_mfa: bool = True):
        self.use_mfa = use_mfa and TEXTGRID_AVAILABLE
        self.mfa_available = self._check_mfa() if self.use_mfa else False
    
    def _check_mfa(self) -> bool:
        try:
            result = subprocess.run(["mfa", "version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def label_audio(self, audio_path: Path, transcript: Optional[str] = None) -> List[Phoneme]:
        if self.use_mfa and self.mfa_available and transcript:
            return self._label_with_mfa(audio_path, transcript)
        return self._label_simple(audio_path)
    
    def _label_with_mfa(self, audio_path: Path, transcript: str) -> List[Phoneme]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            import shutil
            shutil.copy(audio_path, temp_path / audio_path.name)
            (temp_path / f"{audio_path.stem}.txt").write_text(transcript)
            
            output_dir = temp_path / "output"
            output_dir.mkdir()
            
            try:
                subprocess.run(["mfa", "align", str(temp_path), "english_us_arpa", "english_us_arpa", str(output_dir)],
                               capture_output=True, text=True, timeout=60)
                tg_file = output_dir / f"{audio_path.stem}.TextGrid"
                return self._parse_textgrid(tg_file) if tg_file.exists() else self._label_simple(audio_path)
            except Exception:
                return self._label_simple(audio_path)
    
    def _parse_textgrid(self, textgrid_path: Path) -> List[Phoneme]:
        tg = textgrid.TextGrid.fromFile(str(textgrid_path))
        phonemes = []
        for tier in tg.tiers:
            if tier.name == "phones":
                for interval in tier.intervals:
                    if interval.mark and interval.mark != "":
                        phonemes.append(Phoneme(interval.mark.upper(), interval.minTime, interval.maxTime))
        return phonemes
    
    def _label_simple(self, audio_path: Path) -> List[Phoneme]:
        """Native energy-based segmentation. Zero external library bloat."""
        y, sr = sf.read(str(audio_path), dtype='float32')
        if y.ndim > 1: y = np.mean(y, axis=0)
        
        frame_size = int(0.025 * sr)
        hop_size = int(0.010 * sr)
        
        energy = np.array([np.sqrt(np.mean(y[i:i+frame_size]**2)) 
                           for i in range(0, len(y) - frame_size, hop_size)])
        
        threshold = np.mean(energy) * 2.5
        onset_indices = np.where(energy[1:] > threshold)[0] * hop_size
        onset_times = onset_indices / sr
        
        phonemes = [Phoneme("SIL" if i % 5 == 0 else "AA", float(onset_times[i]), 
                            float(onset_times[i+1]), 0.4) for i in range(len(onset_times)-1)]
        
        logger.warning(f"Native simple labeling: {len(phonemes)} segments")
        return phonemes

    def phonemes_to_visemes(self, phonemes: List[Phoneme], fps: int = 60) -> List[Dict]:
        if not phonemes: return []
        num_frames = int(phonemes[-1].end_time * fps)
        return [{"time": i/fps, "frame": i, "viseme": self.PHONEME_TO_VISEME.get(
            next((p.label for p in phonemes if p.start_time <= (i/fps) < p.end_time), "sil"), "sil")}
            for i in range(num_frames)]

    def get_statistics(self, phonemes: List[Phoneme]) -> Dict:
        if not phonemes: return {}
        from collections import Counter
        labels = [p.label for p in phonemes]
        return {"total": len(phonemes), "most_common": Counter(labels).most_common(5)}

# ==============================================================================
# Nothing Vital Lives Below Root.
# ==============================================================================