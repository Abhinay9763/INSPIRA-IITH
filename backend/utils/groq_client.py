"""
Groq client utility for LLM interactions.
Centralized module for all Groq API calls with error handling.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional
from groq import Groq
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)


class GroqClient:
    """Centralized Groq client for LLM interactions."""

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is required")

        self.client = Groq(api_key=GROQ_API_KEY)

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
        Send a prompt to Groq and return the response.

        Args:
            model: The model name to use
            prompt: The prompt text
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            json_mode: Whether to request JSON output

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
        Load a prompt template from the prompts directory.

        Args:
            prompt_file: Name of the prompt file (e.g., 'resume_analyst.txt')

        Returns:
            The prompt template as a string
        """
        try:
            with open(f"prompts/{prompt_file}", 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: prompts/{prompt_file}")
        except Exception as e:
            raise Exception(f"Failed to load prompt template: {str(e)}")


# Global instance
groq_client = GroqClient()