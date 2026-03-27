"""Orchestrator for managing Stage 2 interview flow"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from uuid import uuid4

from .models.interview import (
    InterviewState, ConversationTurn, InterviewPhase,
    QuestionBank, DebriefReport
)
from .agents.question_generator import get_question_generator
from .agents.interviewer import get_interviewer_agent
from .agents.debrief import get_debrief_agent

logger = logging.getLogger(__name__)

class InterviewOrchestrator:
    """Orchestrates the complete Stage 2 interview process"""

    def __init__(self):
        """Initialize the orchestrator"""
        self.active_sessions: Dict[str, InterviewState] = {}
        self.question_generator = get_question_generator()
        self.interviewer_agent = get_interviewer_agent()
        self.debrief_agent = get_debrief_agent()
        logger.info("Interview Orchestrator initialized")

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return str(uuid4())

    def _add_conversation_turn(
        self,
        interview_state: InterviewState,
        role: str,
        content: str,
        phase: InterviewPhase
    ) -> None:
        """Add a turn to both full and trimmed conversation history"""
        interview_state.turn_count += 1

        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            turn_number=interview_state.turn_count,
            phase=phase
        )

        # Add to full history (never trimmed)
        interview_state.full_conversation_history.append(turn)

        # Add to trimmed history (managed by interviewer agent)
        interview_state.trimmed_history.append(turn)

        logger.debug(f"Added turn {interview_state.turn_count} to session")

    async def run_stage_two_start(
        self,
        candidate_profile: Dict[str, Any],
        target_company: str = None,
        target_role: str = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Start Stage 2 interview process

        Args:
            candidate_profile: Final candidate profile JSON from Stage 1
            target_company: Target company for interview
            target_role: Target role for interview

        Returns:
            Tuple of (session_id, first_question_text, audio_base64)
        """
        try:
            logger.info("Starting Stage 2 interview process")

            # Generate session ID
            session_id = self._generate_session_id()

            # Step 1: Generate question bank
            logger.info("Generating question bank...")
            question_bank = await self.question_generator.generate_question_bank(
                candidate_profile,
                target_company,
                target_role
            )

            # Step 2: Initialize interview state
            interview_state = InterviewState(
                candidate_profile=candidate_profile,
                question_bank=question_bank,
                target_company=target_company,
                target_role=target_role
            )

            # Step 3: Generate first interviewer turn (Phase 1, Turn 1)
            logger.info("Generating first interview question...")
            first_response, audio_base64 = await self.interviewer_agent.conduct_interview_turn(
                interview_state
            )

            # Update state with first turn
            current_phase = self.interviewer_agent.determine_phase(interview_state.turn_count + 1)
            interview_state.current_phase = current_phase

            self._add_conversation_turn(
                interview_state,
                "assistant",  # Interviewer
                first_response,
                current_phase
            )

            # Store session
            self.active_sessions[session_id] = interview_state

            logger.info(f"Interview started successfully with session ID: {session_id}")

            return session_id, first_response, audio_base64

        except Exception as e:
            logger.error(f"Failed to start Stage 2 interview: {str(e)}")
            raise

    async def run_stage_two_turn(
        self,
        session_id: str,
        user_message: str
    ) -> Tuple[str, Optional[str], InterviewPhase, int]:
        """
        Process one interview turn

        Args:
            session_id: Session identifier
            user_message: User's response message

        Returns:
            Tuple of (ai_response_text, audio_base64, current_phase, turn_count)
        """
        try:
            # Get session state
            if session_id not in self.active_sessions:
                raise ValueError(f"Invalid session ID: {session_id}")

            interview_state = self.active_sessions[session_id]

            logger.info(f"Processing turn for session {session_id}, turn {interview_state.turn_count + 1}")

            # Add user message to history
            current_phase = self.interviewer_agent.determine_phase(interview_state.turn_count + 1)
            self._add_conversation_turn(
                interview_state,
                "user",  # Candidate
                user_message,
                current_phase
            )

            # Update phase
            interview_state.current_phase = current_phase

            # Generate AI response
            ai_response, audio_base64 = await self.interviewer_agent.conduct_interview_turn(
                interview_state,
                user_message
            )

            # Add AI response to history
            next_phase = self.interviewer_agent.determine_phase(interview_state.turn_count + 1)
            interview_state.current_phase = next_phase

            self._add_conversation_turn(
                interview_state,
                "assistant",  # Interviewer
                ai_response,
                next_phase
            )

            logger.info(f"Turn completed. Phase: {next_phase.name}, Turn: {interview_state.turn_count}")

            return ai_response, audio_base64, next_phase, interview_state.turn_count

        except Exception as e:
            logger.error(f"Failed to process interview turn: {str(e)}")
            raise

    async def run_stage_two_end(
        self,
        session_id: str
    ) -> DebriefReport:
        """
        End interview and generate debrief report

        Args:
            session_id: Session identifier

        Returns:
            Complete debrief report
        """
        try:
            # Get session state
            if session_id not in self.active_sessions:
                raise ValueError(f"Invalid session ID: {session_id}")

            interview_state = self.active_sessions[session_id]

            logger.info(f"Ending interview and generating debrief for session {session_id}")

            # Generate debrief using full conversation history
            debrief_report = await self.debrief_agent.generate_debrief(
                interview_state.full_conversation_history,
                interview_state.candidate_profile,
                interview_state.question_bank,
                interview_state.target_company,
                interview_state.target_role
            )

            logger.info(f"Debrief completed. Overall score: {debrief_report.overall_score}")

            # Clean up session
            del self.active_sessions[session_id]

            return debrief_report

        except Exception as e:
            logger.error(f"Failed to end interview: {str(e)}")
            raise

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current session information"""
        if session_id not in self.active_sessions:
            return None

        interview_state = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "current_phase": interview_state.current_phase.name,
            "turn_count": interview_state.turn_count,
            "target_company": interview_state.target_company,
            "target_role": interview_state.target_role,
            "candidate_name": interview_state.candidate_profile.get("name", "Unknown"),
            "questions_available": len(interview_state.question_bank.questions)
        }

    def should_end_interview(self, session_id: str) -> bool:
        """Check if interview should be ended"""
        if session_id not in self.active_sessions:
            return True

        interview_state = self.active_sessions[session_id]
        return self.interviewer_agent.should_end_interview(
            interview_state.turn_count,
            interview_state.current_phase
        )

    def cleanup_session(self, session_id: str) -> bool:
        """Clean up a session manually"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Session {session_id} cleaned up manually")
            return True
        return False

    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.active_sessions)

# Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> InterviewOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = InterviewOrchestrator()
    return _orchestrator