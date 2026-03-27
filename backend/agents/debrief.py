"""Debrief Agent - post interview analysis and feedback
Uses meta-llama/Llama-3.3-70B-Instruct model"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from ..models.interview import (
    QuestionBank, ConversationTurn, DebriefReport,
    PhaseBreakdown, AnswerFeedback, ResumeVsReality, StudyRecommendation
)
from ..utils.featherless_client import get_featherless_client
from ..config import DEBRIEF_MODEL, PROMPTS_DIR

logger = logging.getLogger(__name__)

class DebriefAgent:
    """Generates comprehensive post-interview feedback and analysis"""

    def __init__(self):
        """Initialize the debrief agent"""
        self.client = get_featherless_client()
        self.model = DEBRIEF_MODEL
        logger.info("Debrief Agent initialized")

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

            response = await self.client.chat_completion(
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

            # Parse into Pydantic models for validation
            phase_breakdown = {}
            for phase_name, phase_data in debrief_data.get("phase_breakdown", {}).items():
                phase_breakdown[phase_name] = PhaseBreakdown(
                    score=phase_data["score"],
                    feedback=phase_data["feedback"]
                )

            answer_feedback = []
            for feedback_item in debrief_data.get("answer_feedback", []):
                answer_feedback.append(AnswerFeedback(
                    question=feedback_item["question"],
                    candidate_answer_summary=feedback_item["candidate_answer_summary"],
                    score=feedback_item["score"],
                    stronger_answer_example=feedback_item["stronger_answer_example"],
                    resume_gap_flagged=feedback_item.get("resume_gap_flagged", False),
                    resume_gap_note=feedback_item.get("resume_gap_note", "")
                ))

            resume_vs_reality = []
            for rvr_item in debrief_data.get("resume_vs_reality", []):
                resume_vs_reality.append(ResumeVsReality(
                    claim=rvr_item["claim"],
                    demonstrated=rvr_item["demonstrated"],
                    verdict=rvr_item["verdict"]
                ))

            study_recommendations = []
            for rec_item in debrief_data.get("study_recommendations", []):
                study_recommendations.append(StudyRecommendation(
                    priority=rec_item["priority"],
                    topic=rec_item["topic"],
                    reason=rec_item["reason"]
                ))

            # Create final debrief report
            debrief_report = DebriefReport(
                overall_score=debrief_data["overall_score"],
                summary=debrief_data["summary"],
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