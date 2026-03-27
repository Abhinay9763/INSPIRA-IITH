"""Question Generator Agent - generates internal question bank
Uses llama-3.3-70b-versatile model"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
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

            # Clean up response if it has markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            logger.info("Parsing JSON response...")
            response_json = json.loads(response_text)
            logger.info(f"JSON parsed successfully, has {len(response_json.get('questions', []))} questions")

            # Convert to our models
            questions = []
            category_count = {}

            for q_data in response_json.get("questions", []):
                try:
                    question = Question(
                        question_text=q_data["question_text"],
                        category=QuestionCategory(q_data["category"]),
                        difficulty=QuestionDifficulty(q_data["difficulty"]),
                        talking_points=q_data.get("talking_points", []),
                        follow_up_questions=q_data.get("follow_up_questions", [])
                    )
                    questions.append(question)

                    # Count categories
                    cat = question.category.value
                    category_count[cat] = category_count.get(cat, 0) + 1

                except Exception as e:
                    logger.warning(f"Skipping invalid question: {e}")
                    continue

            # Create question bank
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
            raise Exception("Invalid JSON response from question generator")

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