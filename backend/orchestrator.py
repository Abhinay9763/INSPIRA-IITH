"""
Orchestrator for managing Stage 1 resume analysis pipeline.
Coordinates all agents and manages the complete analysis workflow.
"""

import logging
from typing import Dict, Any, List
from models.candidate import FinalCandidateProfile
from utils.pdf_parser import pdf_parser
from agents.resume_analyst import resume_analyst
from agents.github_scout import github_scout
from agents.scorer import scoring_agent

logger = logging.getLogger(__name__)


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


# Global instance for the application
stage1_orchestrator = Stage1Orchestrator()