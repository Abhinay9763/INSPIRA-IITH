"""
Scoring agent for final candidate evaluation and interview preparation.
Combines candidate profile and GitHub signals to generate comprehensive scoring.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..models.candidate import (
    CandidateProfile, GitHubSignals, ScoreBreakdown,
    InterviewThread, FinalCandidateProfile
)
from ..utils.groq_client import groq_client
from ..config import SCORING_AGENT_MODEL, WEIGHTS

logger = logging.getLogger(__name__)


class ScoringAgent:
    """Agent for comprehensive candidate evaluation and scoring."""

    @staticmethod
    async def score_candidate(
        candidate_profile: CandidateProfile,
        github_signals: Optional[GitHubSignals],
        target_company: str,
        target_role: str
    ) -> FinalCandidateProfile:
        """
        Generate comprehensive candidate scoring and interview guidance.

        Args:
            candidate_profile: Extracted candidate profile from resume
            github_signals: GitHub analysis results (can be None if GitHub unavailable)
            target_company: Target company name
            target_role: Target role description

        Returns:
            FinalCandidateProfile with scoring and interview recommendations
        """
        try:
            logger.info(f"Starting candidate scoring for {target_role} at {target_company}")

            # Prepare data for LLM analysis
            analysis_data = ScoringAgent._prepare_analysis_data(
                candidate_profile, github_signals, target_company, target_role
            )

            # Get LLM evaluation
            evaluation = await ScoringAgent._get_llm_evaluation(analysis_data)

            # Calculate weighted overall score
            score_breakdown = ScoringAgent._create_score_breakdown(evaluation['score_breakdown'])

            # Parse interview threads
            interview_threads = [
                InterviewThread(**thread) for thread in evaluation.get('interview_threads', [])
            ]

            # Create final candidate profile
            final_profile = FinalCandidateProfile(
                candidate_profile=candidate_profile,
                github_signals=github_signals,
                target_company=target_company,
                target_role=target_role,
                score_breakdown=score_breakdown,
                strong_signals=evaluation.get('strong_signals', []),
                weak_signals=evaluation.get('weak_signals', []),
                interview_threads=interview_threads,
                analysis_date=datetime.now().isoformat()
            )

            logger.info(f"Scoring completed. Overall score: {score_breakdown.overall_score:.1f}")
            return final_profile

        except Exception as e:
            logger.error(f"Candidate scoring failed: {str(e)}")
            raise Exception(f"Failed to score candidate: {str(e)}")

    @staticmethod
    def _prepare_analysis_data(
        candidate_profile: CandidateProfile,
        github_signals: Optional[GitHubSignals],
        target_company: str,
        target_role: str
    ) -> str:
        """
        Prepare structured data for LLM analysis.

        Args:
            candidate_profile: Candidate profile data
            github_signals: GitHub signals data
            target_company: Target company
            target_role: Target role

        Returns:
            Formatted data string for LLM
        """
        # Convert Pydantic models to dictionaries for JSON serialization
        data = {
            "target_company": target_company,
            "target_role": target_role,
            "candidate_profile": candidate_profile.model_dump(),
            "github_signals": github_signals.model_dump() if github_signals else None
        }

        # Format as readable text for the LLM
        analysis_text = f"""
TARGET POSITION:
Company: {target_company}
Role: {target_role}

CANDIDATE PROFILE:
Name: {candidate_profile.name}
Location: {candidate_profile.location or 'Not specified'}
Email: {candidate_profile.email or 'Not specified'}

Summary: {candidate_profile.summary or 'No summary provided'}

Technical Skills ({len(candidate_profile.skills)} total):
{', '.join(candidate_profile.skills[:15])}{'...' if len(candidate_profile.skills) > 15 else ''}

Experience ({len(candidate_profile.experience)} positions):
"""

        # Add experience details
        for i, exp in enumerate(candidate_profile.experience[:5]):  # Limit to top 5
            analysis_text += f"""
{i+1}. {exp.get('title', 'Unknown Title')} at {exp.get('company', 'Unknown Company')}
   Duration: {exp.get('duration', 'Unknown')}
   Description: {exp.get('description', 'No description')[:200]}...
"""

        # Add education
        if candidate_profile.education:
            analysis_text += "\nEducation:\n"
            for edu in candidate_profile.education:
                analysis_text += f"- {edu.get('degree', 'Unknown Degree')} from {edu.get('institution', 'Unknown Institution')}\n"

        # Add GitHub data if available
        if github_signals:
            analysis_text += f"""
GITHUB PROFILE:
Username: {github_signals.username}
Public Repos: {github_signals.public_repos}
Followers: {github_signals.followers}
Total Stars: {github_signals.total_stars}

Top Repositories ({len(github_signals.repositories)} analyzed):
"""
            for repo in github_signals.repositories[:5]:
                languages = ', '.join(repo.languages.keys()) if repo.languages else 'Unknown'
                analysis_text += f"""
- {repo.name} ({repo.stars} ⭐)
  Languages: {languages}
  README Score: {repo.readme_score or 'N/A'}/10
  Description: {repo.description or 'No description'}
"""
        else:
            analysis_text += "\nGITHUB PROFILE: Not available or analysis failed\n"

        return analysis_text

    @staticmethod
    async def _get_llm_evaluation(analysis_data: str) -> Dict[str, Any]:
        """
        Get LLM evaluation of the candidate.

        Args:
            analysis_data: Formatted candidate data

        Returns:
            LLM evaluation results
        """
        try:
            # Load prompt template
            prompt_template = groq_client.load_prompt_template("scoring_agent.txt")

            # Create full prompt
            full_prompt = f"{prompt_template}\n\n{analysis_data}"

            # Get LLM evaluation with optimized settings
            response = await groq_client.send_prompt(
                model=SCORING_AGENT_MODEL,
                prompt=full_prompt,
                temperature=0.3,  # Moderate creativity for interview questions
                max_tokens=3000,  # Generous limit for scoring and interview questions
                json_mode=True,
                timeout=60  # Longer timeout for comprehensive analysis
            )

            # Validate response structure
            required_fields = ['score_breakdown', 'strong_signals', 'weak_signals', 'interview_threads']
            for field in required_fields:
                if field not in response:
                    logger.warning(f"Missing field in LLM response: {field}")
                    if field == 'score_breakdown':
                        response[field] = ScoringAgent._get_default_score_breakdown()
                    else:
                        response[field] = []

            return response

        except Exception as e:
            logger.error(f"LLM evaluation failed: {str(e)}")
            # Return default evaluation
            return {
                'score_breakdown': ScoringAgent._get_default_score_breakdown(),
                'strong_signals': ['Resume analysis completed'],
                'weak_signals': ['Limited data available for comprehensive analysis'],
                'interview_threads': ScoringAgent._get_default_interview_threads()
            }

    @staticmethod
    def _create_score_breakdown(score_data: Dict[str, float]) -> ScoreBreakdown:
        """
        Create ScoreBreakdown with weighted overall score.

        Args:
            score_data: Raw scores from LLM

        Returns:
            ScoreBreakdown object
        """
        # Ensure all scores are within valid range
        technical_skills = max(0.0, min(10.0, score_data.get('technical_skills', 5.0)))
        project_quality = max(0.0, min(10.0, score_data.get('project_quality', 5.0)))
        github_activity = max(0.0, min(10.0, score_data.get('github_activity', 5.0)))
        experience_depth = max(0.0, min(10.0, score_data.get('experience_depth', 5.0)))
        communication = max(0.0, min(10.0, score_data.get('communication', 5.0)))

        # Calculate weighted overall score
        overall_score = (
            technical_skills * WEIGHTS['technical_skills'] +
            project_quality * WEIGHTS['project_quality'] +
            github_activity * WEIGHTS['github_activity'] +
            experience_depth * WEIGHTS['experience_depth'] +
            communication * WEIGHTS['communication']
        )

        overall_score = max(0.0, min(10.0, overall_score))

        return ScoreBreakdown(
            technical_skills=technical_skills,
            project_quality=project_quality,
            github_activity=github_activity,
            experience_depth=experience_depth,
            communication=communication,
            overall_score=overall_score
        )

    @staticmethod
    def _get_default_score_breakdown() -> Dict[str, float]:
        """Get default score breakdown when LLM fails."""
        return {
            'technical_skills': 5.0,
            'project_quality': 5.0,
            'github_activity': 3.0,  # Lower default for GitHub
            'experience_depth': 5.0,
            'communication': 5.0
        }

    @staticmethod
    def _get_default_interview_threads() -> List[Dict[str, Any]]:
        """Get default interview threads when LLM fails."""
        return [
            {
                'topic': 'Technical Skills Assessment',
                'questions': [
                    'Walk me through a challenging technical problem you solved recently.',
                    'How do you approach debugging complex issues?',
                    'Describe your experience with the key technologies for this role.'
                ],
                'rationale': 'Essential to verify technical competency for the role.'
            },
            {
                'topic': 'Problem Solving and Architecture',
                'questions': [
                    'How do you design scalable systems?',
                    'Describe a time when you had to make important architectural decisions.',
                    'How do you handle technical trade-offs?'
                ],
                'rationale': 'Understand architectural thinking and decision-making process.'
            }
        ]


# Instance for easy importing
scoring_agent = ScoringAgent()