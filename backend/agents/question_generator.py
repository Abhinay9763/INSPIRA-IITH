"""Question Generator Agent - generates internal question bank
Uses llama-3.3-70b-versatile model"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List
from ..models.interview import QuestionBank, Question, QuestionCategory, QuestionDifficulty
from ..utils.groq_client import get_groq_client
from ..config import QUESTION_GEN_MODEL, PROMPTS_DIR, get_seniority_level, INTERVIEW_FLAVORS

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """Generates question bank for technical interviews based on candidate profile"""

    def __init__(self):
        """Initialize the question generator"""
        self.client = None  # Lazy-initialized on first use
        self.model = QUESTION_GEN_MODEL
        logger.info("Question Generator initialized")

    async def _get_client(self):
        """Get or initialize the groq client"""
        if self.client is None:
            self.client = get_groq_client()
        return self.client

    def _load_prompt(self) -> str:
        """Load the question generator prompt from file"""
        prompt_path = Path(PROMPTS_DIR) / "question_generator.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt: {str(e)}")
            raise

    def _extract_experience_years(self, candidate_profile: Dict[str, Any]) -> int:
        """Extract years of experience from candidate profile"""
        try:
            # Look for years_of_experience field or calculate from work history
            if "years_of_experience" in candidate_profile:
                return int(candidate_profile["years_of_experience"])

            # Try to extract from work experience
            experience = candidate_profile.get("experience", [])
            if isinstance(experience, list) and experience:
                # Rough calculation based on number of positions
                return min(len(experience) * 2, 10)  # Cap at 10 years

            # Default to mid-level if unclear
            return 3
        except Exception as e:
            logger.warning(f"Could not extract experience years: {e}, defaulting to 3")
            return 3

    def _construct_prompt(
        self,
        candidate_profile: Dict[str, Any],
        seniority_level: str,
        target_company: str = None,
        target_role: str = None
    ) -> str:
        """Construct the full prompt for question generation"""
        base_prompt = self._load_prompt()

        # Get interview flavor based on seniority
        flavor = INTERVIEW_FLAVORS[seniority_level]

        # Construct the detailed prompt
        detailed_prompt = f"""{base_prompt}

CANDIDATE PROFILE:
{json.dumps(candidate_profile, indent=2)}

INTERVIEW PARAMETERS:
- Seniority Level: {seniority_level}
- Target Company: {target_company or "Generic tech company"}
- Target Role: {target_role or "Software Engineer"}
- Required Distribution:
  - DSA Questions: {flavor['dsa_percentage']}%
  - System Design: {flavor['system_design_percentage']}%
  - Behavioral: {flavor['behavioral_percentage']}%
  - Resume Deep Dive: {flavor['resume_percentage']}%

Generate exactly 20 questions following this distribution. Ensure questions are:
1. Appropriate for the seniority level
2. Tailored to the candidate's background and technologies mentioned in their profile
3. Realistic for the target company and role
4. Well-distributed across difficulty levels within each category

Return ONLY a valid JSON object with no additional text."""

        return detailed_prompt

    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Extract JSON from noisy LLM output (markdown, prefixes, trailing prose)."""
        text = (response_text or "").strip()
        if not text:
            return {}

        candidates: List[str] = []

        # Markdown JSON block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                candidates.append(text[start:end].strip())

        # Generic markdown block
        if "```" in text and "```json" not in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                candidates.append(text[start:end].strip())

        # First top-level JSON object
        obj_match = re.search(r"\{[\s\S]*\}", text)
        if obj_match:
            candidates.append(obj_match.group(0).strip())

        # Raw text fallback
        candidates.append(text)

        for candidate in candidates:
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

        return {}

    def _normalize_category(self, value: Any) -> QuestionCategory:
        """Normalize category values from common LLM variants."""
        raw = str(value or "").strip().lower().replace("_", "").replace(" ", "")
        mapping = {
            "dsa": QuestionCategory.DSA,
            "systemdesign": QuestionCategory.SYSTEM_DESIGN,
            "behavioral": QuestionCategory.BEHAVIORAL,
            "resumedeepdive": QuestionCategory.RESUME_DEEP_DIVE,
            "resume": QuestionCategory.RESUME_DEEP_DIVE,
        }
        return mapping.get(raw, QuestionCategory.BEHAVIORAL)

    def _normalize_difficulty(self, value: Any) -> QuestionDifficulty:
        """Normalize difficulty values from common LLM variants."""
        raw = str(value or "").strip().lower()
        mapping = {
            "easy": QuestionDifficulty.EASY,
            "medium": QuestionDifficulty.MEDIUM,
            "hard": QuestionDifficulty.HARD,
        }
        return mapping.get(raw, QuestionDifficulty.MEDIUM)

    def _fallback_question_bank(self, seniority_level: str) -> QuestionBank:
        """Deterministic fallback question bank if LLM JSON is invalid."""
        fallback_questions = [
            Question(
                question_text="Walk me through one project you built and your exact ownership in it.",
                category=QuestionCategory.RESUME_DEEP_DIVE,
                difficulty=QuestionDifficulty.EASY,
                talking_points=["scope", "personal contribution", "tradeoffs"],
                follow_up_questions=["What would you redesign now?"]
            ),
            Question(
                question_text="Explain a production bug you debugged recently and how you isolated root cause.",
                category=QuestionCategory.BEHAVIORAL,
                difficulty=QuestionDifficulty.MEDIUM,
                talking_points=["diagnosis", "instrumentation", "mitigation"],
                follow_up_questions=["How did you prevent recurrence?"]
            ),
            Question(
                question_text="Given an array of integers, return indices of two numbers that add to a target.",
                category=QuestionCategory.DSA,
                difficulty=QuestionDifficulty.EASY,
                talking_points=["hash map", "time complexity"],
                follow_up_questions=["How does this change for sorted arrays?"]
            ),
            Question(
                question_text="Design a URL shortener service and discuss scaling bottlenecks.",
                category=QuestionCategory.SYSTEM_DESIGN,
                difficulty=QuestionDifficulty.MEDIUM,
                talking_points=["id generation", "read/write paths", "storage"],
                follow_up_questions=["How would you handle hot keys?"]
            ),
            Question(
                question_text="Describe a time you disagreed with a technical decision and how you resolved it.",
                category=QuestionCategory.BEHAVIORAL,
                difficulty=QuestionDifficulty.MEDIUM,
                talking_points=["communication", "evidence", "outcome"],
                follow_up_questions=["What did you learn from that conflict?"]
            ),
            Question(
                question_text="Implement LRU cache with O(1) get and put operations.",
                category=QuestionCategory.DSA,
                difficulty=QuestionDifficulty.HARD,
                talking_points=["doubly linked list", "hash map", "eviction"],
                follow_up_questions=["How would you make it thread-safe?"]
            ),
            Question(
                question_text="Tell me about your strongest and weakest resume claim after this interview.",
                category=QuestionCategory.RESUME_DEEP_DIVE,
                difficulty=QuestionDifficulty.MEDIUM,
                talking_points=["self-assessment", "evidence", "growth plan"],
                follow_up_questions=["What skill would you prioritize next month?"]
            ),
            Question(
                question_text="Design a notification system that supports email, SMS, and push delivery.",
                category=QuestionCategory.SYSTEM_DESIGN,
                difficulty=QuestionDifficulty.HARD,
                talking_points=["queues", "retry", "idempotency"],
                follow_up_questions=["How would you track delivery guarantees?"]
            ),
        ]

        category_distribution: Dict[str, int] = {}
        for question in fallback_questions:
            cat = question.category.value
            category_distribution[cat] = category_distribution.get(cat, 0) + 1

        return QuestionBank(
            questions=fallback_questions,
            seniority_level=seniority_level,
            total_questions=len(fallback_questions),
            category_distribution=category_distribution
        )

    async def generate_question_bank(
        self,
        candidate_profile: Dict[str, Any],
        target_company: str = None,
        target_role: str = None
    ) -> QuestionBank:
        """
        Generate a question bank based on candidate profile

        Args:
            candidate_profile: Final candidate profile from Stage 1
            target_company: Target company for interview
            target_role: Target role for interview

        Returns:
            QuestionBank object with generated questions
        """
        try:
            # Determine seniority level
            years_experience = self._extract_experience_years(candidate_profile)
            seniority_level = get_seniority_level(years_experience)

            logger.info(f"Generating questions for {seniority_level} level ({years_experience} years)")

            # Construct prompt
            prompt = self._construct_prompt(
                candidate_profile,
                seniority_level,
                target_company,
                target_role
            )

            # Make API call
            messages = [{"role": "user", "content": prompt}]

            client = await self._get_client()
            response = await client.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=4000
            )

            logger.info("Received response from LLM, parsing...")

            # Parse response
            response_text = response.choices[0].message.content.strip()
            logger.info(f"Response text length: {len(response_text)} chars")

            logger.info("Extracting JSON response...")
            response_json = self._extract_json_from_response(response_text)
            if not response_json:
                logger.warning("Question generator returned non-parseable JSON. Using fallback question bank.")
                return self._fallback_question_bank(seniority_level)

            logger.info(f"JSON parsed successfully, has {len(response_json.get('questions', []))} questions")

            # Convert to our models
            questions = []
            category_count = {}

            for q_data in response_json.get("questions", []):
                try:
                    question = Question(
                        question_text=str(q_data.get("question_text", "")).strip(),
                        category=self._normalize_category(q_data.get("category")),
                        difficulty=self._normalize_difficulty(q_data.get("difficulty")),
                        talking_points=q_data.get("talking_points", []),
                        follow_up_questions=q_data.get("follow_up_questions", [])
                    )

                    if not question.question_text:
                        raise ValueError("question_text missing")

                    questions.append(question)

                    # Count categories
                    cat = question.category.value
                    category_count[cat] = category_count.get(cat, 0) + 1

                except Exception as e:
                    logger.warning(f"Skipping invalid question: {e}")
                    continue

            # Create question bank
            if not questions:
                logger.warning("No valid questions parsed from LLM output. Using fallback question bank.")
                return self._fallback_question_bank(seniority_level)

            question_bank = QuestionBank(
                questions=questions,
                seniority_level=seniority_level,
                total_questions=len(questions),
                category_distribution=category_count
            )

            logger.info(f"Generated {len(questions)} questions successfully")
            logger.debug(f"Category distribution: {category_count}")

            return question_bank

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            return self._fallback_question_bank(seniority_level)

        except Exception as e:
            logger.error(f"Question generation failed: {str(e)}")
            raise

# Global instance
_question_generator = None

def get_question_generator() -> QuestionGenerator:
    """Get or create global question generator instance"""
    global _question_generator
    if _question_generator is None:
        _question_generator = QuestionGenerator()
    return _question_generator