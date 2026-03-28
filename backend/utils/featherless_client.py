"""Featherless client utility for optional post-processing tasks."""

import logging
from typing import Optional

import httpx

from ..config import (
    FEATHERLESS_API_KEY,
    FEATHERLESS_BASE_URL,
    FEATHERLESS_STRONGER_ANSWER_MODEL,
)

logger = logging.getLogger(__name__)


class FeatherlessClient:
    """Minimal async Featherless client using OpenAI-compatible chat endpoint."""

    def __init__(self):
        self.api_key = FEATHERLESS_API_KEY
        self.base_url = FEATHERLESS_BASE_URL.rstrip("/")
        self.model = FEATHERLESS_STRONGER_ANSWER_MODEL

    @property
    def is_enabled(self) -> bool:
        return bool(self.api_key)

    async def generate_stronger_answer(
        self,
        question: str,
        candidate_answer_summary: str,
        target_company: Optional[str] = None,
        target_role: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a concise stronger-answer example for debrief feedback."""
        if not self.is_enabled:
            return None

        system_prompt = (
            "You are an interview coach. Rewrite the candidate response into a stronger model answer. "
            "Be concise, practical, and specific. Return plain text only."
        )

        user_prompt = (
            f"Target Company: {target_company or 'Generic tech company'}\n"
            f"Target Role: {target_role or 'Software Engineer'}\n"
            f"Interview Question: {question}\n"
            f"Candidate Answer Summary: {candidate_answer_summary}\n\n"
            "Write a stronger answer example in 2-4 sentences (max 90 words)."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 180,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(30.0, connect=10.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            detail = response.text[:300]
            raise RuntimeError(f"Featherless error ({response.status_code}): {detail}")

        data = response.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        return text or None


_featherless_client: Optional[FeatherlessClient] = None


def get_featherless_client() -> FeatherlessClient:
    """Get or create global Featherless client instance."""
    global _featherless_client
    if _featherless_client is None:
        _featherless_client = FeatherlessClient()
    return _featherless_client
