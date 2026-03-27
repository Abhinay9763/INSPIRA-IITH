"""Featherless API client setup using OpenAI SDK"""

from openai import OpenAI
from typing import Optional
import logging
from ..config import FEATHERLESS_API_KEY, FEATHERLESS_BASE_URL, validate_config

logger = logging.getLogger(__name__)

class FeatherlessClient:
    """Wrapper for OpenAI client configured to use Featherless API"""

    def __init__(self):
        """Initialize the Featherless client"""
        validate_config()
        self._client = OpenAI(
            base_url=FEATHERLESS_BASE_URL,
            api_key=FEATHERLESS_API_KEY
        )
        logger.info("Featherless client initialized successfully")

    @property
    def client(self) -> OpenAI:
        """Get the OpenAI client instance"""
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
        Create a chat completion using the Featherless API

        Args:
            model: The model to use (e.g., "meta-llama/Llama-3.3-70B-Instruct")
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
        """Test the connection to Featherless API"""
        try:
            # Make a simple test call
            response = self._client.chat.completions.create(
                model="meta-llama/Llama-3.3-70B-Instruct",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            logger.info("Featherless API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Featherless API connection test failed: {str(e)}")
            return False

# Global client instance
_featherless_client: Optional[FeatherlessClient] = None

def get_featherless_client() -> FeatherlessClient:
    """Get or create the global Featherless client instance"""
    global _featherless_client
    if _featherless_client is None:
        _featherless_client = FeatherlessClient()
    return _featherless_client