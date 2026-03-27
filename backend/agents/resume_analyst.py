"""
Resume Analyst agent for extracting structured candidate profiles.
Uses Groq LLM to parse resume text and extract candidate information.
"""

import logging
from models.candidate import CandidateProfile
from utils.groq_client import groq_client
from config import RESUME_ANALYST_MODEL

logger = logging.getLogger(__name__)


class ResumeAnalyst:
    """Agent for analyzing resume text and extracting candidate profiles."""

    @staticmethod
    async def analyze_resume(raw_text: str) -> CandidateProfile:
        """
        Analyze raw resume text and extract structured candidate profile.

        Args:
            raw_text: Raw text extracted from resume PDF

        Returns:
            CandidateProfile with structured candidate information

        Raises:
            Exception: If analysis fails
        """
        try:
            logger.info("Starting resume analysis")

            # Truncate text if too long to prevent timeouts, but preserve contact info
            max_chars = 4000  # Reasonable limit for LLM processing
            if len(raw_text) > max_chars:
                logger.warning(f"Resume text too long ({len(raw_text)} chars). Truncating to {max_chars} chars.")

                # Strategy: Keep first 2000 chars (contact info + early content) and recent content
                contact_section = raw_text[:2000]  # Preserve contact info and early sections

                # For the rest, take the last portion which usually has recent projects/experience
                remaining_chars = max_chars - 2000 - 50  # Leave space for separator
                if remaining_chars > 0:
                    recent_section = raw_text[-remaining_chars:]
                    raw_text = contact_section + "\n\n[... MIDDLE SECTION TRUNCATED ...]\n\n" + recent_section
                else:
                    raw_text = contact_section

            # Load the prompt template
            prompt_template = groq_client.load_prompt_template("resume_analyst.txt")

            # Create the full prompt with resume text
            full_prompt = f"{prompt_template}\n\n{raw_text}"

            # Call Groq LLM for analysis with optimized settings
            response = await groq_client.send_prompt(
                model=RESUME_ANALYST_MODEL,
                prompt=full_prompt,
                temperature=0.1,  # Low temperature for factual extraction
                max_tokens=2000,  # Limit response length for faster processing
                json_mode=True,
                timeout=45  # Shorter timeout for resume analysis
            )

            logger.info("Resume analysis completed successfully")

            # Parse and validate the response
            candidate_data = ResumeAnalyst._parse_candidate_response(response)

            return CandidateProfile(**candidate_data)

        except Exception as e:
            logger.error(f"Resume analysis failed: {str(e)}")
            raise Exception(f"Failed to analyze resume: {str(e)}")

    @staticmethod
    def _parse_candidate_response(response: dict) -> dict:
        """
        Parse and validate the LLM response for candidate profile.

        Args:
            response: Raw response from Groq LLM

        Returns:
            Parsed candidate data dictionary

        Raises:
            Exception: If response format is invalid
        """
        try:
            # Expected fields in the response
            expected_fields = [
                'name', 'email', 'phone', 'location', 'github_url',
                'linkedin_url', 'website_url', 'summary', 'skills',
                'experience', 'education', 'projects'
            ]

            candidate_data = {}

            # Extract basic information
            candidate_data['name'] = response.get('name', '').strip()
            candidate_data['email'] = response.get('email')
            candidate_data['phone'] = response.get('phone')
            candidate_data['location'] = response.get('location')
            candidate_data['summary'] = response.get('summary')

            # Extract URLs and clean them
            candidate_data['github_url'] = ResumeAnalyst._clean_url(response.get('github_url'))
            candidate_data['linkedin_url'] = ResumeAnalyst._clean_url(response.get('linkedin_url'))
            candidate_data['website_url'] = ResumeAnalyst._clean_url(response.get('website_url'))

            # Extract skills array
            skills = response.get('skills', [])
            candidate_data['skills'] = skills if isinstance(skills, list) else []

            # Extract experience array
            experience = response.get('experience', [])
            candidate_data['experience'] = experience if isinstance(experience, list) else []

            # Extract education array
            education = response.get('education', [])
            candidate_data['education'] = education if isinstance(education, list) else []

            # Extract projects array
            projects = response.get('projects', [])
            candidate_data['projects'] = projects if isinstance(projects, list) else []

            # Validate required fields
            if not candidate_data['name']:
                logger.warning("No name found in resume")
                candidate_data['name'] = "Unknown"

            logger.info(f"Extracted profile for: {candidate_data['name']}")
            logger.info(f"Found {len(candidate_data['skills'])} skills, "
                       f"{len(candidate_data['experience'])} experience entries, "
                       f"{len(candidate_data['education'])} education entries, "
                       f"{len(candidate_data['projects'])} projects")

            return candidate_data

        except Exception as e:
            logger.error(f"Failed to parse candidate response: {str(e)}")
            raise Exception(f"Invalid response format from resume analysis: {str(e)}")

    @staticmethod
    def _clean_url(url: str) -> str:
        """
        Clean and validate a URL.

        Args:
            url: Raw URL string

        Returns:
            Cleaned URL or None if invalid
        """
        if not url or not isinstance(url, str):
            return None

        url = url.strip()

        if not url:
            return None

        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        return url


# Instance for easy importing
resume_analyst = ResumeAnalyst()