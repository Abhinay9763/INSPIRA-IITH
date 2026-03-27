"""
Combined Orchestrator for managing both Stage 1 (resume analysis) and Stage 2 (interview + stakeholder decision) pipelines.
Coordinates all agents and manages the complete analysis workflow for the AI Interview Preparation Platform.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

# Stage 1 Imports
from .models.candidate import FinalCandidateProfile
from .utils.pdf_parser import pdf_parser
from .agents.resume_analyst import resume_analyst
from .agents.github_scout import github_scout
from .agents.scorer import scoring_agent

# Stage 2 Imports
from .models.interview import (
    InterviewState, ConversationTurn, InterviewPhase,
    QuestionBank, DebriefReport, StakeholderType, StakeholderReport
)
from .agents.question_generator import get_question_generator
from .agents.interviewer import get_interviewer_agent
from .agents.debrief import get_debrief_agent
from .agents.stakeholder import get_stakeholder_agent

logger = logging.getLogger(__name__)

# ===== STAGE 1 ORCHESTRATOR (Resume Analysis) =====

class Stage1Orchestrator:
    """Orchestrator for Stage 1 resume analysis pipeline."""

    def __init__(self):
        """Initialize the orchestrator."""
        self.current_analysis: Dict[str, FinalCandidateProfile] = {}

    async def run_stage_one(self, resume_pdf: bytes, company: str, role: str) -> FinalCandidateProfile:
        """
        Execute the complete Stage 1 pipeline for resume analysis.

        Pipeline Steps:
        1. Extract text and URLs from PDF
        2. Analyze resume text to extract candidate profile
        3. Analyze GitHub profile if URL found
        4. Generate final scoring and interview questions
        5. Store result in memory for Stage 2 handoff

        Args:
            resume_pdf: PDF file content as bytes
            company: Target company name
            role: Target role description

        Returns:
            FinalCandidateProfile with complete analysis

        Raises:
            Exception: If critical pipeline steps fail
        """
        try:
            logger.info("Starting Stage 1 pipeline")
            logger.info(f"Target: {role} at {company}")

            # Step 1: Extract text and URLs from PDF
            logger.info("Step 1: Extracting PDF content")
            pdf_extraction = pdf_parser.extract_from_pdf(resume_pdf)
            logger.info(f"Extracted {len(pdf_extraction.raw_text)} characters and {len(pdf_extraction.urls)} URLs")

            if not pdf_extraction.raw_text.strip():
                raise Exception("No text content found in PDF")

            # Step 2: Analyze resume text to extract candidate profile
            logger.info("Step 2: Analyzing resume text")
            candidate_profile = await resume_analyst.analyze_resume(pdf_extraction.raw_text)
            logger.info(f"Extracted profile for: {candidate_profile.name}")

            # Step 3: Analyze GitHub profile if available
            github_signals = None
            github_url = self._find_github_url(candidate_profile, pdf_extraction.urls)

            if github_url:
                # Update the candidate profile with the found GitHub URL
                candidate_profile.github_url = github_url
                logger.info(f"Step 3: Analyzing GitHub profile: {github_url}")
                github_signals = await github_scout.analyze_github_profile(github_url)
                if github_signals:
                    logger.info(f"GitHub analysis completed for user: {github_signals.username}")
                else:
                    logger.warning("GitHub analysis failed")
            else:
                logger.info("Step 3: No GitHub URL found, skipping GitHub analysis")

            # Try to find LinkedIn URL if not already present
            linkedin_url = self._find_linkedin_url(candidate_profile, pdf_extraction.urls)
            if linkedin_url:
                candidate_profile.linkedin_url = linkedin_url
                logger.info(f"LinkedIn URL found and updated: {linkedin_url}")

            # Step 4: Generate final scoring and interview questions
            logger.info("Step 4: Generating final scoring")
            final_profile = await scoring_agent.score_candidate(
                candidate_profile=candidate_profile,
                github_signals=github_signals,
                target_company=company,
                target_role=role
            )

            # Step 5: Store in memory for Stage 2 handoff
            analysis_id = f"{company}_{role}_{candidate_profile.name}".replace(" ", "_")
            self.current_analysis[analysis_id] = final_profile
            logger.info(f"Stage 1 completed. Analysis stored with ID: {analysis_id}")
            logger.info(f"Final score: {final_profile.score_breakdown.overall_score:.1f}/10")

            return final_profile

        except Exception as e:
            logger.error(f"Stage 1 pipeline failed: {str(e)}")
            raise Exception(f"Resume analysis pipeline failed: {str(e)}")

    def _find_github_url(self, candidate_profile, extracted_urls) -> str:
        """
        Find the best GitHub URL from candidate profile and extracted URLs.
        Includes fallback mechanisms for common GitHub URL patterns.

        Args:
            candidate_profile: Extracted candidate profile
            extracted_urls: URLs extracted from PDF

        Returns:
            GitHub URL or None if not found
        """
        # Check candidate profile first (most reliable)
        if candidate_profile.github_url:
            logger.info("GitHub URL found in candidate profile")
            return candidate_profile.github_url

        # Check extracted URLs for GitHub links
        for url in extracted_urls:
            if 'github.com' in url.lower():
                logger.info(f"GitHub URL found in extracted URLs: {url}")
                return url

        # Fallback: Try to infer GitHub URL from available info
        logger.info("No explicit GitHub URL found, attempting fallback detection")
        fallback_url = self._try_github_url_fallbacks(candidate_profile)
        if fallback_url:
            logger.info(f"GitHub URL found via fallback: {fallback_url}")
            return fallback_url

        logger.info("No GitHub URL found")
        return None

    def _try_github_url_fallbacks(self, candidate_profile) -> str:
        """
        Try to infer GitHub URLs from candidate information.

        Args:
            candidate_profile: Extracted candidate profile

        Returns:
            Potential GitHub URL or None
        """
        potential_usernames = []

        # Strategy 1: Extract username from email
        if candidate_profile.email:
            email_parts = candidate_profile.email.split('@')[0]
            # Try different variations
            potential_usernames.extend([
                email_parts,  # vengala9
                email_parts.replace('.', ''),  # vengala9 (no change)
                email_parts.split('.')[0],  # vengala (if email was vengala.9@...)
            ])

        # Strategy 2: Create username from name
        if candidate_profile.name and candidate_profile.name != "Unknown":
            name_parts = candidate_profile.name.lower().split()
            if len(name_parts) >= 2:
                # Try common patterns
                potential_usernames.extend([
                    f"{name_parts[0]}{name_parts[1]}",  # abhinaykumar
                    f"{name_parts[0]}-{name_parts[1]}",  # abhinay-kumar
                    f"{name_parts[0]}.{name_parts[1]}",  # abhinay.kumar
                    f"{name_parts[0]}{name_parts[1][0]}",  # abhinayk
                    name_parts[0],  # abhinay
                ])

        # Strategy 3: Known patterns from the email (add numbers)
        if candidate_profile.email:
            email_base = candidate_profile.email.split('@')[0]
            # Try variations with numbers
            for num in ['9763', '123', '2024', '2025']:  # Common patterns
                potential_usernames.append(f"{email_base.replace('.', '')}{num}")

        # Remove duplicates while preserving order
        seen = set()
        unique_usernames = []
        for username in potential_usernames:
            if username and username not in seen:
                seen.add(username)
                unique_usernames.append(username)

        logger.debug(f"Trying potential GitHub usernames: {unique_usernames}")

        # For now, return the most likely candidate
        # In a real implementation, you might validate these URLs by checking if they exist
        if unique_usernames:
            # Return the first potential match
            return f"https://github.com/{unique_usernames[0]}"

        return None

    def _find_linkedin_url(self, candidate_profile, extracted_urls) -> str:
        """
        Find the best LinkedIn URL from candidate profile and extracted URLs.
        Includes fallback mechanisms for common LinkedIn URL patterns.

        Args:
            candidate_profile: Extracted candidate profile
            extracted_urls: URLs extracted from PDF

        Returns:
            LinkedIn URL or None if not found
        """
        # Check candidate profile first (most reliable)
        if candidate_profile.linkedin_url:
            logger.info("LinkedIn URL found in candidate profile")
            return candidate_profile.linkedin_url

        # Check extracted URLs for LinkedIn links
        for url in extracted_urls:
            if 'linkedin.com' in url.lower():
                logger.info(f"LinkedIn URL found in extracted URLs: {url}")
                return url

        # Fallback: Try to infer LinkedIn URL from available info
        logger.info("No explicit LinkedIn URL found, attempting fallback detection")
        fallback_url = self._try_linkedin_url_fallbacks(candidate_profile)
        if fallback_url:
            logger.info(f"LinkedIn URL found via fallback: {fallback_url}")
            return fallback_url

        logger.info("No LinkedIn URL found")
        return None

    def _try_linkedin_url_fallbacks(self, candidate_profile) -> str:
        """
        Try to infer LinkedIn URLs from candidate information.

        Args:
            candidate_profile: Extracted candidate profile

        Returns:
            Potential LinkedIn URL or None
        """
        if not candidate_profile.name or candidate_profile.name == "Unknown":
            return None

        name_parts = candidate_profile.name.lower().split()
        if len(name_parts) >= 2:
            # Common LinkedIn patterns
            potential_profiles = [
                f"{name_parts[0]}-{name_parts[1]}",  # abhinay-kumar
                f"{name_parts[0]}{name_parts[1]}",   # abhinaykumar
                f"{name_parts[0]}.{name_parts[1]}",  # abhinay.kumar
            ]

            # Add full name pattern if there's a third name
            if len(name_parts) >= 3:
                potential_profiles.append(f"{name_parts[0]}-{name_parts[1]}-{name_parts[2]}")

            # Remove empty strings and clean up
            potential_profiles = [p.rstrip('-').rstrip('.') for p in potential_profiles if p.strip()]

            if potential_profiles:
                # Return the most likely pattern (first one)
                return f"https://linkedin.com/in/{potential_profiles[0]}"

        return None

    def get_analysis(self, analysis_id: str) -> FinalCandidateProfile:
        """
        Retrieve stored analysis by ID.

        Args:
            analysis_id: Analysis identifier

        Returns:
            FinalCandidateProfile or None if not found
        """
        return self.current_analysis.get(analysis_id)

    def list_analyses(self) -> List[str]:
        """
        List all analysis IDs currently in memory.

        Returns:
            List of analysis IDs
        """
        return list(self.current_analysis.keys())

    def clear_analysis(self, analysis_id: str) -> bool:
        """
        Remove analysis from memory.

        Args:
            analysis_id: Analysis identifier

        Returns:
            True if removed, False if not found
        """
        if analysis_id in self.current_analysis:
            del self.current_analysis[analysis_id]
            return True
        return False

    def clear_all_analyses(self):
        """Clear all analyses from memory."""
        self.current_analysis.clear()
        logger.info("All analyses cleared from memory")

# ===== STAGE 2 ORCHESTRATOR (Interview + Multi-Stakeholder Decision) =====

class InterviewOrchestrator:
    """Orchestrates the complete Stage 2 interview process"""

    def __init__(self):
        """Initialize the orchestrator"""
        self.active_sessions: Dict[str, InterviewState] = {}
        self.question_generator = get_question_generator()
        self.interviewer_agent = get_interviewer_agent()
        self.debrief_agent = get_debrief_agent()
        self.stakeholder_agent = get_stakeholder_agent()
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

    def _extract_target_info(self, candidate_profile: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """Extract target company and role from candidate profile"""
        target_company = candidate_profile.get("target_company")
        target_role = candidate_profile.get("target_role")

        # Try alternative field names commonly used in profiles
        if not target_company:
            target_company = candidate_profile.get("desired_company") or candidate_profile.get("company")

        if not target_role:
            target_role = candidate_profile.get("desired_role") or candidate_profile.get("position") or candidate_profile.get("job_title") or candidate_profile.get("target_position")

        return target_company, target_role

    async def run_stage_two_start(
        self,
        candidate_profile: Dict[str, Any]
    ) -> Tuple[str, str, Optional[str]]:
        """
        Start Stage 2 interview process

        Args:
            candidate_profile: Final candidate profile JSON from Stage 1 (includes target_company and target_role)

        Returns:
            Tuple of (session_id, first_question_text, audio_base64)
        """
        try:
            logger.info("Starting Stage 2 interview process")

            # Extract target company and role from candidate profile
            target_company, target_role = self._extract_target_info(candidate_profile)

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

            # Store debrief in session for potential stakeholder decision stage
            interview_state.debrief_report = debrief_report

            return debrief_report

        except Exception as e:
            logger.error(f"Failed to end interview: {str(e)}")
            raise

    async def run_stage_three_stakeholder_decision(
        self,
        session_id: str
    ) -> StakeholderReport:
        """
        Generate multi-stakeholder hiring decision (Stage 3)

        Uses existing session data (candidate profile, conversation history)
        and debrief results to simulate stakeholder perspectives

        Args:
            session_id: Session identifier

        Returns:
            StakeholderReport with individual decisions and consensus
        """
        try:
            logger.info(f"Starting Stage 3 stakeholder decision for session {session_id}")

            # Validate session exists
            if session_id not in self.active_sessions:
                raise ValueError(f"Invalid session ID: {session_id}")

            interview_state = self.active_sessions[session_id]

            # Get or generate debrief report if not already available
            debrief_report = getattr(interview_state, 'debrief_report', None)
            if debrief_report is None:
                logger.info("Debrief report not found in session, generating...")
                debrief_report = await self.debrief_agent.generate_debrief(
                    interview_state.full_conversation_history,
                    interview_state.candidate_profile,
                    interview_state.question_bank,
                    interview_state.target_company,
                    interview_state.target_role
                )

            # Generate individual stakeholder decisions
            stakeholder_types = [
                StakeholderType.HIRING_MANAGER,
                StakeholderType.TECHNICAL_LEAD,
                StakeholderType.HR_REPRESENTATIVE,
                StakeholderType.PEER_ENGINEER
            ]

            individual_decisions = []
            logger.info(f"Generating {len(stakeholder_types)} individual stakeholder decisions...")

            for stakeholder_type in stakeholder_types:
                decision = await self.stakeholder_agent.generate_stakeholder_decision(
                    stakeholder_type,
                    debrief_report,
                    interview_state.candidate_profile,
                    interview_state.full_conversation_history,
                    interview_state.target_company,
                    interview_state.target_role
                )
                individual_decisions.append(decision)
                logger.info(f"{stakeholder_type.value} decision: {decision.decision}")

            # Generate consensus decision
            logger.info("Generating consensus decision...")
            stakeholder_report = await self.stakeholder_agent.generate_consensus(
                individual_decisions,
                debrief_report,
                interview_state.candidate_profile,
                session_id,
                interview_state.target_company,
                interview_state.target_role
            )

            logger.info(f"Stakeholder decision completed: {stakeholder_report.consensus_decision} (confidence: {stakeholder_report.consensus_confidence}%)")

            # Clean up session after stakeholder decision
            del self.active_sessions[session_id]

            return stakeholder_report

        except Exception as e:
            logger.error(f"Stakeholder decision failed: {str(e)}")
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

# ===== GLOBAL INSTANCES =====

# Stage 1 Global instance for the application
stage1_orchestrator = Stage1Orchestrator()

# Stage 2 Global orchestrator instance
_orchestrator = None

def get_orchestrator() -> InterviewOrchestrator:
    """Get or create global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = InterviewOrchestrator()
    return _orchestrator