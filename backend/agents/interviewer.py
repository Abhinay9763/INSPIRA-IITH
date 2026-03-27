"""Interviewer Agent - handles one interview turn
Uses llama-3.1-8b-instant model for low latency conversations"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..models.interview import (
    QuestionBank, ConversationTurn, InterviewPhase,
    InterviewState
)
from ..utils.groq_client import get_groq_client
from ..utils.tts import generate_speech
from ..config import INTERVIEWER_MODEL, PROMPTS_DIR, MAX_CONTEXT_TURNS

logger = logging.getLogger(__name__)

class InterviewerAgent:
    """Conducts interview turns with context management"""

    def __init__(self):
        """Initialize the interviewer agent"""
        self.client = get_groq_client()
        self.model = INTERVIEWER_MODEL
        logger.info("Interviewer Agent initialized")

    def _load_prompt(self) -> str:
        """Load the interviewer prompt from file"""
        prompt_path = Path(PROMPTS_DIR) / "interviewer.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Prompt file not found: {prompt_path}")
            raise
        except Exception as e:
            logger.error(f"Error loading prompt: {str(e)}")
            raise

    def _summarize_phase1(self, turns: List[ConversationTurn]) -> str:
        """Summarize Phase 1 (warmup) into 3-4 lines"""
        if not turns:
            return "No warmup phase recorded."

        # Extract the key points from Phase 1
        summary_parts = []

        for turn in turns:
            if turn.phase == InterviewPhase.WARMUP:
                if turn.role == "user":
                    # Extract key info from candidate's intro
                    content = turn.content[:200]  # Truncate if too long
                    summary_parts.append(f"Candidate: {content}")
                elif turn.role == "assistant":
                    # Brief note about what interviewer asked
                    if "introduce" in turn.content.lower() or "tell me about" in turn.content.lower():
                        summary_parts.append("Interviewer conducted standard introduction.")

        if not summary_parts:
            return "Phase 1: Standard warmup and introductions completed."

        # Join and limit to 3-4 lines
        summary = "Phase 1 Summary: " + " | ".join(summary_parts[:3])
        return summary[:300] + "..." if len(summary) > 300 else summary

    def _manage_context(self, interview_state: InterviewState) -> List[Dict[str, str]]:
        """
        Manage conversation context for LLM calls

        After Phase 1 ends (turn 2):
        - Summarize Phase 1 into 3-4 lines
        - Keep summary + last MAX_CONTEXT_TURNS turns only
        """
        full_history = interview_state.full_conversation_history

        if interview_state.turn_count <= 2:
            # Phase 1: Use all turns as-is
            context_turns = []
            for turn in full_history:
                context_turns.append({
                    "role": turn.role,
                    "content": turn.content
                })
        else:
            # Phase 2+: Use summarized Phase 1 + recent turns
            phase1_turns = [t for t in full_history if t.phase == InterviewPhase.WARMUP]
            post_phase1_turns = [t for t in full_history if t.phase != InterviewPhase.WARMUP]

            # Create summary
            phase1_summary = self._summarize_phase1(phase1_turns)

            # Take last MAX_CONTEXT_TURNS from post-Phase1
            recent_turns = post_phase1_turns[-MAX_CONTEXT_TURNS:]

            context_turns = []

            # Add summary as system message
            if phase1_summary:
                context_turns.append({
                    "role": "system",
                    "content": f"Previous conversation context: {phase1_summary}"
                })

            # Add recent turns
            for turn in recent_turns:
                context_turns.append({
                    "role": turn.role,
                    "content": turn.content
                })

        return context_turns

    def _construct_system_prompt(
        self,
        candidate_profile: Dict[str, Any],
        question_bank: QuestionBank,
        current_phase: InterviewPhase,
        target_company: str = None,
        target_role: str = None,
        turn_count: int = 0
    ) -> str:
        """Construct system prompt with current context"""
        base_prompt = self._load_prompt()

        # Phase-specific guidance
        phase_guidance = {
            InterviewPhase.WARMUP: "Focus on warm introductions and getting the candidate comfortable. Ask about their background and current role.",
            InterviewPhase.RESUME_DEEP_DIVE: "Deep dive into the candidate's resume. Ask follow-up questions about their experience, projects, and technologies mentioned.",
            InterviewPhase.TECHNICAL: f"Focus on technical questions from your question bank. For {question_bank.seniority_level} level, emphasize problem-solving and technical depth.",
            InterviewPhase.CLOSING: "Start wrapping up. Ask if they have questions for you, discuss next steps, and provide a positive closing."
        }

        current_guidance = phase_guidance.get(current_phase, "Continue the conversation naturally.")

        system_prompt = f"""{base_prompt}

CURRENT CONTEXT:
- Phase: {current_phase.name} (Turn {turn_count})
- Candidate Seniority: {question_bank.seniority_level}
- Target Company: {target_company or "Generic Tech Company"}
- Target Role: {target_role or "Software Engineer"}
- Phase Guidance: {current_guidance}

CANDIDATE PROFILE SUMMARY:
{json.dumps(candidate_profile, indent=2)[:1000]}...

INTERNAL QUESTION BANK (for reference only, never reveal):
{len(question_bank.questions)} questions across categories: {question_bank.category_distribution}

Remember:
- Respond only in plain text suitable for text-to-speech
- Never mention this is a mock interview or reference the question bank
- Stay in character as a real interviewer
- Keep responses concise but engaging"""

        return system_prompt

    async def conduct_interview_turn(
        self,
        interview_state: InterviewState,
        user_message: Optional[str] = None
    ) -> tuple[str, Optional[str]]:
        """
        Conduct one interview turn

        Args:
            interview_state: Current interview state
            user_message: User's message (None for first turn)

        Returns:
            Tuple of (response_text, audio_base64)
        """
        try:
            # Construct system prompt
            system_prompt = self._construct_system_prompt(
                interview_state.candidate_profile,
                interview_state.question_bank,
                interview_state.current_phase,
                interview_state.target_company,
                interview_state.target_role,
                interview_state.turn_count
            )

            # Get managed conversation context
            context_messages = self._manage_context(interview_state)

            # Build full message list
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(context_messages)

            # Add user message if this isn't the first turn
            if user_message is not None:
                messages.append({"role": "user", "content": user_message})

            logger.debug(f"Sending {len(messages)} messages to LLM for turn {interview_state.turn_count + 1}")

            # Make API call
            response = await self.client.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.8,  # Slightly higher for more natural conversation
                max_tokens=300    # Keep responses concise for spoken format
            )

            # Extract response text
            response_text = response.choices[0].message.content.strip()

            # Generate audio
            audio_base64 = await generate_speech(response_text)
            if audio_base64 is None:
                logger.warning("TTS generation failed, continuing with text only")

            logger.info(f"Interview turn completed successfully (turn {interview_state.turn_count + 1})")

            return response_text, audio_base64

        except Exception as e:
            logger.error(f"Interview turn failed: {str(e)}")
            raise

    def determine_phase(self, turn_count: int) -> InterviewPhase:
        """Determine current phase based on turn count"""
        if turn_count <= 2:
            return InterviewPhase.WARMUP
        elif turn_count <= 6:
            return InterviewPhase.RESUME_DEEP_DIVE
        elif turn_count <= 11:
            return InterviewPhase.TECHNICAL
        else:
            return InterviewPhase.CLOSING

    def should_end_interview(self, turn_count: int, current_phase: InterviewPhase) -> bool:
        """Determine if interview should end"""
        # End after a reasonable number of turns in closing phase
        return current_phase == InterviewPhase.CLOSING and turn_count >= 15

# Global instance
_interviewer_agent = None

def get_interviewer_agent() -> InterviewerAgent:
    """Get or create global interviewer agent instance"""
    global _interviewer_agent
    if _interviewer_agent is None:
        _interviewer_agent = InterviewerAgent()
    return _interviewer_agent