"""
Text-to-Speech Service
Generates audio files from text using Coqui TTS or pyttsx3 fallback.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional
import subprocess

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class TTSService:
    """
    Service for converting text to speech audio files.
    
    Supports:
    - Coqui TTS (higher quality, requires GPU for best results)
    - pyttsx3 (fallback, works everywhere)
    """
    
    def __init__(
        self,
        provider: str = "pyttsx3",
        output_dir: str = "media/replies",
        coqui_model: str = "tts_models/en/ljspeech/tacotron2-DDC"
    ):
        """
        Initialize TTS service.
        
        Args:
            provider: TTS provider ("coqui" or "pyttsx3")
            output_dir: Directory to save audio files
            coqui_model: Coqui TTS model name
        """
        self.provider = provider.lower()
        self.output_dir = output_dir
        self.coqui_model = coqui_model
        
        self._coqui_tts = None
        self._pyttsx3_engine = None
        self._initialized = False
        
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def _init_coqui(self) -> bool:
        """Initialize Coqui TTS."""
        if self._coqui_tts is not None:
            return True
        
        try:
            from TTS.api import TTS
            
            logger.info(f"Loading Coqui TTS model: {self.coqui_model}")
            self._coqui_tts = TTS(model_name=self.coqui_model)
            logger.info("Coqui TTS loaded successfully")
            return True
            
        except ImportError:
            logger.warning("Coqui TTS not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to load Coqui TTS: {e}")
            return False
    
    def _init_pyttsx3(self) -> bool:
        """Initialize pyttsx3."""
        if self._pyttsx3_engine is not None:
            return True
        
        try:
            import pyttsx3
            
            logger.info("Initializing pyttsx3")
            self._pyttsx3_engine = pyttsx3.init()
            
            # Configure voice
            self._pyttsx3_engine.setProperty('rate', 150)  # Speed
            self._pyttsx3_engine.setProperty('volume', 0.9)
            
            # Try to use a female voice if available
            voices = self._pyttsx3_engine.getProperty('voices')
            for voice in voices:
                if 'female' in voice.name.lower():
                    self._pyttsx3_engine.setProperty('voice', voice.id)
                    break
            
            logger.info("pyttsx3 initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3: {e}")
            return False
    
    def initialize(self) -> bool:
        """Initialize the configured TTS provider."""
        if self._initialized:
            return True
        
        if self.provider == "coqui":
            if self._init_coqui():
                self._initialized = True
                return True
            # Fallback to pyttsx3
            logger.warning("Falling back to pyttsx3")
            self.provider = "pyttsx3"
        
        if self.provider == "pyttsx3":
            if self._init_pyttsx3():
                self._initialized = True
                return True
        
        logger.error("No TTS provider available")
        return False
    
    def generate(
        self,
        text: str,
        output_path: Optional[str] = None,
        message_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Generate audio file from text.
        
        Args:
            text: Text to convert to speech
            output_path: Optional specific output path
            message_id: Optional message ID for naming the file
        
        Returns:
            Path to generated audio file, or None on failure
        """
        if not text:
            return None
        
        if not self.initialize():
            return None
        
        # Generate output path if not provided
        if output_path is None:
            if message_id:
                filename = f"{message_id}.mp3"
            else:
                import uuid
                filename = f"{uuid.uuid4().hex[:12]}.mp3"
            output_path = os.path.join(self.output_dir, filename)
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Clean text for TTS
        clean_text = self._clean_text_for_tts(text)
        
        try:
            if self.provider == "coqui":
                return self._generate_coqui(clean_text, output_path)
            else:
                return self._generate_pyttsx3(clean_text, output_path)
                
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Clean text for better TTS output."""
        import re
        
        # Remove URLs
        text = re.sub(r'https?://\S+', 'link', text)
        
        # Replace common abbreviations
        replacements = {
            "e.g.": "for example",
            "i.e.": "that is",
            "etc.": "etcetera",
            "vs.": "versus",
            "Dr.": "Doctor",
            "Mr.": "Mister",
            "Mrs.": "Missus",
            "Ms.": "Miss",
            "&": "and",
        }
        for abbr, full in replacements.items():
            text = text.replace(abbr, full)
        
        # Remove excessive punctuation
        text = re.sub(r'[!?]{2,}', '.', text)
        text = re.sub(r'\.{2,}', '.', text)
        
        # Remove emojis
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+', '', text)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _generate_coqui(self, text: str, output_path: str) -> Optional[str]:
        """Generate audio using Coqui TTS."""
        try:
            # Coqui TTS generates WAV by default
            wav_path = output_path.replace('.mp3', '.wav')
            
            self._coqui_tts.tts_to_file(text=text, file_path=wav_path)
            
            # Convert to MP3 if ffmpeg is available
            if output_path.endswith('.mp3'):
                try:
                    subprocess.run(
                        ['ffmpeg', '-y', '-i', wav_path, '-acodec', 'libmp3lame', '-q:a', '2', output_path],
                        check=True,
                        capture_output=True
                    )
                    os.remove(wav_path)
                    logger.info(f"Generated MP3: {output_path}")
                    return output_path
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # ffmpeg not available, return WAV
                    logger.warning("ffmpeg not available, returning WAV")
                    return wav_path
            
            return wav_path
            
        except Exception as e:
            logger.error(f"Coqui TTS generation failed: {e}")
            return None
    
    def _generate_pyttsx3(self, text: str, output_path: str) -> Optional[str]:
        """Generate audio using pyttsx3."""
        try:
            # pyttsx3 can only save to WAV or use system default
            wav_path = output_path.replace('.mp3', '.wav')
            
            # Save to file
            self._pyttsx3_engine.save_to_file(text, wav_path)
            self._pyttsx3_engine.runAndWait()
            
            # Verify file was created
            if not os.path.exists(wav_path):
                logger.error("pyttsx3 failed to create output file")
                return None
            
            # Convert to MP3 if ffmpeg is available
            if output_path.endswith('.mp3'):
                try:
                    subprocess.run(
                        ['ffmpeg', '-y', '-i', wav_path, '-acodec', 'libmp3lame', '-q:a', '2', output_path],
                        check=True,
                        capture_output=True
                    )
                    os.remove(wav_path)
                    logger.info(f"Generated MP3: {output_path}")
                    return output_path
                except (subprocess.CalledProcessError, FileNotFoundError):
                    logger.warning("ffmpeg not available, returning WAV")
                    return wav_path
            
            return wav_path
            
        except Exception as e:
            logger.error(f"pyttsx3 generation failed: {e}")
            return None
    
    def get_audio_url(self, audio_path: str) -> str:
        """
        Get the URL for an audio file.
        
        Args:
            audio_path: Path to audio file
        
        Returns:
            URL path for the audio file
        """
        # Convert file path to URL path
        if audio_path.startswith(self.output_dir):
            relative_path = audio_path[len(self.output_dir):].lstrip('/')
            return f"/media/replies/{relative_path}"
        
        # Just return the filename
        filename = os.path.basename(audio_path)
        return f"/media/replies/{filename}"


def generate_tts(text: str, out_path: str) -> Optional[str]:
    """
    Generate TTS audio file.
    
    Convenience function that uses the global TTS service.
    
    Args:
        text: Text to convert
        out_path: Output file path
    
    Returns:
        Path to generated audio file
    """
    service = TTSService(
        provider=settings.tts_provider,
        output_dir=settings.media_path,
        coqui_model=settings.coqui_model
    )
    return service.generate(text, out_path)


# Global singleton
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """Get the global TTS service instance."""
    global _tts_service
    
    if _tts_service is None:
        _tts_service = TTSService(
            provider=settings.tts_provider,
            output_dir=settings.media_path,
            coqui_model=settings.coqui_model
        )
    
    return _tts_service
