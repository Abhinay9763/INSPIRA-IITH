"""Text-to-Speech wrapper using edge-tts"""

import asyncio
import base64
import io
import logging
from typing import Optional
import edge_tts
from ..config import TTS_VOICE

logger = logging.getLogger(__name__)

class TTSService:
    """Text-to-Speech service using edge-tts"""

    def __init__(self, default_voice: str = TTS_VOICE):
        """Initialize TTS service with default voice"""
        self.default_voice = default_voice
        logger.info(f"TTS Service initialized with voice: {default_voice}")

    async def text_to_speech(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech and return base64 encoded audio

        Args:
            text: The text to convert to speech
            voice: Voice to use (defaults to configured voice)

        Returns:
            Base64 encoded audio string, or None if generation fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to TTS")
            return None

        voice_to_use = voice or self.default_voice

        try:
            # Create TTS communicate object
            communicate = edge_tts.Communicate(text, voice_to_use)

            # Generate audio data
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]

            if not audio_data:
                logger.error("No audio data generated from TTS")
                return None

            # Encode to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            logger.debug(f"TTS successful for text length: {len(text)}")
            return audio_base64

        except Exception as e:
            logger.error(f"TTS generation failed: {str(e)}")
            return None

    async def get_available_voices(self) -> list:
        """Get list of available voices from edge-tts"""
        try:
            voices = await edge_tts.list_voices()
            return voices
        except Exception as e:
            logger.error(f"Failed to get available voices: {str(e)}")
            return []

    def test_voice(self, voice: str) -> bool:
        """Test if a voice is available"""
        try:
            # Simple test with edge-tts
            asyncio.run(self._test_voice_async(voice))
            return True
        except Exception as e:
            logger.error(f"Voice test failed for {voice}: {str(e)}")
            return False

    async def _test_voice_async(self, voice: str):
        """Async helper for voice testing"""
        communicate = edge_tts.Communicate("test", voice)
        async for _ in communicate.stream():
            break

# Global TTS service instance
_tts_service: Optional[TTSService] = None

def get_tts_service() -> TTSService:
    """Get or create the global TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

async def generate_speech(text: str, voice: Optional[str] = None) -> Optional[str]:
    """
    Convenience function to generate speech from text

    Args:
        text: The text to convert to speech
        voice: Optional voice override

    Returns:
        Base64 encoded audio string, or None if generation fails
    """
    tts_service = get_tts_service()
    return await tts_service.text_to_speech(text, voice)