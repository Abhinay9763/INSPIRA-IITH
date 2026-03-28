"""Debrief Agent - post interview analysis and feedback
Uses llama-3.3-70b-versatile model"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from ..models.interview import (
    QuestionBank, ConversationTurn, DebriefReport,
    PhaseBreakdown, AnswerFeedback, ResumeVsReality, StudyRecommendation
)
from ..utils.groq_client import get_groq_client
from ..utils.featherless_client import get_featherless_client
from ..config import DEBRIEF_MODEL, PROMPTS_DIR, USE_FEATHERLESS_FOR_STRONGER_ANSWERS

logger = logging.getLogger(__name__)

class DebriefAgent:
    """Generates comprehensive post-interview feedback and analysis"""

    def __init__(self):
        """Initialize the debrief agent"""
        self.client = None  # Lazy-initialized
        self.model = DEBRIEF_MODEL
        logger.info("Debrief Agent initialized")

    async def _get_client(self):
        """Get or initialize the groq client"""
        if self.client is None:
            self.client = get_groq_client()
        return self.client

    async def _rewrite_stronger_answers_with_featherless(
        self,
        answer_feedback: List[AnswerFeedback],
        target_company: str = None,
        target_role: str = None,
    ) -> List[AnswerFeedback]:
        """Optionally refine stronger-answer examples via Featherless."""
        if not USE_FEATHERLESS_FOR_STRONGER_ANSWERS:
            return answer_feedback

        featherless = get_featherless_client()
        if not featherless.is_enabled:
            logger.info("Featherless API key not set; skipping stronger-answer refinement")
            return answer_feedback

        async def _rewrite(item: AnswerFeedback) -> None:
            try:
                improved = await featherless.generate_stronger_answer(
                    question=item.question,
                    candidate_answer_summary=item.candidate_answer_summary,
                    target_company=target_company,
                    target_role=target_role,
                )
                if improved:
                    item.stronger_answer_example = improved
            except Exception as e:
                logger.warning(f"Featherless stronger-answer rewrite failed, keeping original: {str(e)}")

        # Keep this bounded so debrief latency doesn't spike.
        tasks = [_rewrite(item) for item in answer_feedback[:6]]
        if tasks:
            await asyncio.gather(*tasks)

        return answer_feedback

    def _load_prompt(self) -> str:
        """Load the debrief prompt from file"""
        prompt_path = Path(PROMPTS_DIR) / "debrief.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt: {str(e)}")
            raise

    def _format_conversation_history(self, conversation_history: List[ConversationTurn]) -> str:
        """Format conversation history for the LLM"""
        formatted_turns = []

        for turn in conversation_history:
            role_label = "INTERVIEWER" if turn.role == "assistant" else "CANDIDATE"
            formatted_turns.append(f"{role_label} (Turn {turn.turn_number}, {turn.phase.name}): {turn.content}")

        return "\n\n".join(formatted_turns)

    def _format_question_bank(self, question_bank: QuestionBank) -> str:
        """Format question bank for reference in debrief"""
        formatted_questions = []

        for i, question in enumerate(question_bank.questions, 1):
            formatted_questions.append(
                f"{i}. [{question.category.value}/{question.difficulty.value}] {question.question_text}"
            )

        return "\n".join(formatted_questions)

    def _construct_debrief_prompt(
        self,
        conversation_history: List[ConversationTurn],
        candidate_profile: Dict[str, Any],
        question_bank: QuestionBank,
        target_company: str = None,
        target_role: str = None
    ) -> str:
        """Construct the full debrief prompt"""
        base_prompt = self._load_prompt()

        # Format all the context
        formatted_conversation = self._format_conversation_history(conversation_history)
        formatted_questions = self._format_question_bank(question_bank)

        detailed_prompt = f"""{base_prompt}

INTERVIEW CONTEXT:
- Target Company: {target_company or "Generic Tech Company"}
- Target Role: {target_role or "Software Engineer"}
- Candidate Seniority: {question_bank.seniority_level}
- Total Turns: {len(conversation_history)}

CANDIDATE PROFILE FROM RESUME ANALYSIS:
{json.dumps(candidate_profile, indent=2)}

AVAILABLE QUESTION BANK (for reference):
{formatted_questions}

FULL CONVERSATION TRANSCRIPT:
{formatted_conversation}

Generate comprehensive debrief following the exact JSON format specified. Be thorough, honest, and constructive."""

        return detailed_prompt

    async def generate_debrief(
        self,
        conversation_history: List[ConversationTurn],
        candidate_profile: Dict[str, Any],
        question_bank: QuestionBank,
        target_company: str = None,
        target_role: str = None
    ) -> DebriefReport:
        """
        Generate comprehensive debrief report

        Args:
            conversation_history: Complete interview transcript
            candidate_profile: Original candidate profile from Stage 1
            question_bank: Questions that were available during interview
            target_company: Target company
            target_role: Target role

        Returns:
            DebriefReport with comprehensive analysis
        """
        try:
            logger.info(f"Generating debrief for interview with {len(conversation_history)} turns")

            # Construct prompt
            prompt = self._construct_debrief_prompt(
                conversation_history,
                candidate_profile,
                question_bank,
                target_company,
                target_role
            )

            # Make API call
            messages = [{"role": "user", "content": prompt}]

            client = await self._get_client()
            response = await client.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=4000   # Generous limit for comprehensive feedback
            )

            # Parse response
            response_text = response.choices[0].message.content.strip()

            # Clean up response if it has markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            # Parse JSON
            try:
                debrief_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse debrief JSON: {e}")
                logger.error(f"Response text: {response_text}")
                raise Exception("Invalid JSON response from debrief agent")

            # Convert conversation history to serializable format
            conversation_for_response = []
            for turn in conversation_history:
                conversation_for_response.append({
                    "role": turn.role,
                    "content": turn.content,
                    "turn_number": turn.turn_number,
                    "phase": turn.phase.name,
                    "timestamp": turn.timestamp
                })

            # Add conversation history to the response
            debrief_data["conversation_history"] = conversation_for_response

            # Parse into Pydantic models with comprehensive validation
            def sanitize_score(value, min_val, max_val, default_val):
                """Sanitize score values to be within valid range"""
                try:
                    score = int(value) if value is not None else default_val
                    return max(min_val, min(max_val, score))
                except (ValueError, TypeError):
                    return default_val

            def sanitize_string(value, default=""):
                """Sanitize string values"""
                return str(value).strip() if value is not None else default

            def sanitize_literal(value, valid_options, default):
                """Sanitize literal values to match allowed options"""
                if value in valid_options:
                    return value
                # Try case-insensitive match
                value_lower = str(value).lower().strip()
                for option in valid_options:
                    if option.lower() == value_lower:
                        return option
                return default

            def sanitize_boolean(value):
                """Sanitize boolean values"""
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return len(value.strip()) > 0 and value.lower() not in ['false', 'no', '0', 'none']
                return bool(value)

            # Parse phase breakdown with validation
            phase_breakdown = {}
            for phase_name, phase_data in debrief_data.get("phase_breakdown", {}).items():
                phase_breakdown[phase_name] = PhaseBreakdown(
                    score=sanitize_score(phase_data.get("score"), 0, 100, 50),
                    feedback=sanitize_string(phase_data.get("feedback"), "No feedback provided")
                )

            # Parse answer feedback with validation
            answer_feedback = []
            for feedback_item in debrief_data.get("answer_feedback", []):
                # Handle resume_gap_flagged field specially
                resume_gap_flagged_value = feedback_item.get("resume_gap_flagged", False)
                resume_gap_note_value = sanitize_string(feedback_item.get("resume_gap_note"))

                if isinstance(resume_gap_flagged_value, str):
                    # If it's a string, convert to boolean and preserve text in note
                    resume_gap_flagged = sanitize_boolean(resume_gap_flagged_value)
                    if not resume_gap_note_value and resume_gap_flagged_value.strip():
                        resume_gap_note_value = resume_gap_flagged_value.strip()
                else:
                    resume_gap_flagged = sanitize_boolean(resume_gap_flagged_value)

                answer_feedback.append(AnswerFeedback(
                    question=sanitize_string(feedback_item.get("question"), "No question"),
                    candidate_answer_summary=sanitize_string(feedback_item.get("candidate_answer_summary"), "No summary provided"),
                    score=sanitize_score(feedback_item.get("score"), 1, 10, 5),  # 1-10 range
                    stronger_answer_example=sanitize_string(feedback_item.get("stronger_answer_example"), "No example provided"),
                    resume_gap_flagged=resume_gap_flagged,
                    resume_gap_note=resume_gap_note_value
                ))

            answer_feedback = await self._rewrite_stronger_answers_with_featherless(
                answer_feedback,
                target_company=target_company,
                target_role=target_role,
            )

            # Parse resume vs reality with validation
            resume_vs_reality = []
            for rvr_item in debrief_data.get("resume_vs_reality", []):
                resume_vs_reality.append(ResumeVsReality(
                    claim=sanitize_string(rvr_item.get("claim"), "No claim"),
                    demonstrated=sanitize_string(rvr_item.get("demonstrated"), "No demonstration"),
                    verdict=sanitize_literal(rvr_item.get("verdict"), ["matched", "gap", "exceeded"], "gap")
                ))

            # Parse study recommendations with validation
            study_recommendations = []
            for rec_item in debrief_data.get("study_recommendations", []):
                study_recommendations.append(StudyRecommendation(
                    priority=sanitize_literal(rec_item.get("priority"), ["high", "medium", "low"], "medium"),
                    topic=sanitize_string(rec_item.get("topic"), "General study"),
                    reason=sanitize_string(rec_item.get("reason"), "No reason provided")
                ))

            # Create final debrief report
            debrief_report = DebriefReport(
                overall_score=sanitize_score(debrief_data.get("overall_score"), 0, 100, 50),
                summary=sanitize_string(debrief_data.get("summary"), "No summary provided"),
                phase_breakdown=phase_breakdown,
                answer_feedback=answer_feedback,
                resume_vs_reality=resume_vs_reality,
                study_recommendations=study_recommendations,
                conversation_history=conversation_for_response
            )

            logger.info(f"Debrief generated successfully with overall score: {debrief_report.overall_score}")

            return debrief_report

        except Exception as e:
            logger.error(f"Debrief generation failed: {str(e)}")
            raise

# Global instance
_debrief_agent = None

def get_debrief_agent() -> DebriefAgent:
    """Get or create global debrief agent instance"""
    global _debrief_agent
    if _debrief_agent is None:
        _debrief_agent = DebriefAgent()
    return _debrief_agent