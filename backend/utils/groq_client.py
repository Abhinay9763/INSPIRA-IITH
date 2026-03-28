"""
Combined Groq client utility for LLM interactions.
Supports both Stage 1 (resume analysis) and Stage 2 (interview) API patterns.
Centralized module for all Groq API calls with error handling.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from groq import Groq
from ..config import GROQ_API_KEY, validate_config

logger = logging.getLogger(__name__)


class GroqClient:
    """Unified Groq client for LLM interactions supporting both Stage 1 and Stage 2 patterns."""

    def __init__(self):
        """Initialize the Groq client"""
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is required")

        validate_config()
        # Disable SDK auto-retries to avoid long hidden backoff delays (20-40s).
        # We implement explicit short retries in chat_completion instead.
        self.client = Groq(api_key=GROQ_API_KEY, max_retries=0)
        self._client = self.client  # Stage 2 compatibility
        logger.info("Groq client initialized successfully")

    @property
    def client_property(self) -> Groq:
        """Get the Groq client instance (Stage 2 compatibility)"""
        return self._client

    # === STAGE 1 METHODS (Resume Analysis) ===

    async def send_prompt(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        json_mode: bool = True,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Send a prompt to Groq and return the response (Stage 1 method).

        Args:
            model: The model name to use
            prompt: The prompt text
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            json_mode: Whether to request JSON output
            timeout: Request timeout in seconds

        Returns:
            Dict response from the model

        Raises:
            Exception: If the API call fails
        """
        try:
            # Prepare messages
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            # Prepare request parameters
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }

            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            # Make the API call asynchronously with timeout
            logger.info(f"Making Groq API call with model: {model}")
            loop = asyncio.get_event_loop()

            try:
                completion = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, lambda: self.client.chat.completions.create(**kwargs)
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Groq API call timed out after {timeout} seconds")
                raise Exception(f"LLM API call timed out after {timeout} seconds")

            # Extract response content
            content = completion.choices[0].message.content

            if json_mode:
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {content}")
                    raise Exception(f"Invalid JSON response from model: {str(e)}")
            else:
                return {"response": content}

        except Exception as e:
            logger.error(f"Groq API call failed: {str(e)}")
            raise Exception(f"LLM API call failed: {str(e)}")

    def load_prompt_template(self, prompt_file: str) -> str:
        """
        Load a prompt template from the prompts directory (Stage 1 method).

        Args:
            prompt_file: Name of the prompt file (e.g., 'resume_analyst.txt')

        Returns:
            The prompt template as a string
        """
        try:
            from ..config import PROMPTS_DIR
            prompt_path = f"{PROMPTS_DIR}/{prompt_file}"
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {PROMPTS_DIR}/{prompt_file}")
        except Exception as e:
            raise Exception(f"Failed to load prompt template: {str(e)}")

    # === STAGE 2 METHODS (Interview) ===

    async def chat_completion(
        self,
        model: str,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Create a chat completion using the Groq API (Stage 2 method)

        Args:
            model: The model to use (e.g., "llama-3.1-70b-versatile")
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters to pass to the API

        Returns:
            Chat completion response
        """
        def _is_rate_limit_error(error: Exception) -> bool:
            message = str(error).lower()
            return '429' in message or 'rate limit' in message or 'too many requests' in message

        max_attempts = 3
        backoff_seconds = [1, 2, 4]
        last_error = None

        for attempt in range(max_attempts):
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
                last_error = e
                if _is_rate_limit_error(e) and attempt < max_attempts - 1:
                    wait_seconds = backoff_seconds[attempt]
                    logger.warning(f"Rate limited on model {model}, retrying in {wait_seconds}s (attempt {attempt + 1}/{max_attempts})")
                    await asyncio.sleep(wait_seconds)
                    continue

                logger.error(f"Chat completion failed for model {model}: {str(e)}")
                raise

        raise last_error if last_error else RuntimeError('Unknown chat completion failure')

    def test_connection(self) -> bool:
        """Test the connection to Groq API (Stage 2 method)"""
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


# === GLOBAL INSTANCES (Supporting both Stage 1 and Stage 2 patterns) ===

# Stage 1 Global instance
groq_client = GroqClient()

# Stage 2 Global client instance
_groq_client: Optional[GroqClient] = None

def get_groq_client() -> GroqClient:
    """Get or create the global Groq client instance (Stage 2 pattern)"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client