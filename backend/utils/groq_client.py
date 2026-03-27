"""Groq API client setup using Groq SDK"""

from groq import Groq
from typing import Optional
import logging
from ..config import GROQ_API_KEY, validate_config

logger = logging.getLogger(__name__)

class GroqClient:
    """Wrapper for Groq client"""

    def __init__(self):
        """Initialize the Groq client"""
        validate_config()
        self._client = Groq(api_key=GROQ_API_KEY)
        logger.info("Groq client initialized successfully")

    @property
    def client(self) -> Groq:
        """Get the Groq client instance"""
        return self._client

    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Create a chat completion using the Groq API

        Args:
            model: The model to use (e.g., "llama-3.1-70b-versatile")
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API

        Returns:
            Chat completion response
        """
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            logger.debug(f"Chat completion successful for model {model}")
            return response
        except Exception as e:
            logger.error(f"Chat completion failed for model {model}: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """Test the connection to Groq API"""
        try:
            # Make a simple test call
            response = self._client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            logger.info("Groq API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Groq API connection test failed: {str(e)}")
            return False

# Global client instance
_groq_client: Optional[GroqClient] = None

def get_groq_client() -> GroqClient:
    """Get or create the global Groq client instance"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client