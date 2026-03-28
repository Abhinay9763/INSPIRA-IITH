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
    def _infer_role_level(target_role: str) -> str:
        """Infer role seniority level from target role title."""
        role = (target_role or '').lower()

        junior_markers = ['intern', 'internship', 'student', 'entry', 'junior', 'fresher', 'new grad']
        senior_markers = ['staff', 'principal', 'lead', 'architect', 'senior']

        if any(marker in role for marker in junior_markers):
            return 'early'
        if any(marker in role for marker in senior_markers):
            return 'senior'
        return 'mid'

    @staticmethod
    def _get_role_weights(role_level: str) -> Dict[str, float]:
        """Return role-aware scoring weights."""
        if role_level == 'early':
            # Early-career roles should focus on potential, projects, and learning agility.
            return {
                'technical_skills': 0.30,
                'project_quality': 0.30,
                'github_activity': 0.15,
                'experience_depth': 0.10,
                'communication': 0.15,
            }

        if role_level == 'senior':
            return {
                'technical_skills': 0.25,
                'project_quality': 0.20,
                'github_activity': 0.15,
                'experience_depth': 0.30,
                'communication': 0.10,
            }

        # Mid-level defaults to configured rubric.
        return WEIGHTS

    @staticmethod
    def _calibrate_scores_for_role(
        raw_scores: Dict[str, float],
        role_level: str,
        candidate_profile: CandidateProfile,
        github_signals: Optional[GitHubSignals],
    ) -> Dict[str, float]:
        """
        Apply deterministic guardrails so intern/junior candidates are not unfairly penalized.
        """
        scores = dict(raw_scores)

        if role_level != 'early':
            return scores

        project_count = len(candidate_profile.projects or [])
        has_any_experience = len(candidate_profile.experience or []) > 0
        public_repos = github_signals.public_repos if github_signals else 0
        has_readme_signal = bool(
            github_signals and any(repo.readme_score is not None for repo in github_signals.repositories)
        )

        # For interns, lack of full-time experience should not collapse score if projects exist.
        if not has_any_experience and project_count >= 3:
            scores['experience_depth'] = max(3.5, float(scores.get('experience_depth', 0.0)))

        # For early-career GitHub activity, stars/followers are weak signals.
        if public_repos >= 4 and has_readme_signal:
            scores['github_activity'] = max(4.0, float(scores.get('github_activity', 0.0)))

        return scores

    @staticmethod
    def _balance_overall_for_role(
        score_breakdown: ScoreBreakdown,
        role_level: str,
        candidate_profile: CandidateProfile,
    ) -> ScoreBreakdown:
        """Keep early-career outcomes realistic and balanced for project-heavy profiles."""
        if role_level != 'early':
            return score_breakdown

        project_count = len(candidate_profile.projects or [])
        skills_count = len(candidate_profile.skills or [])
        has_any_experience = len(candidate_profile.experience or []) > 0

        # For intern candidates with clear project evidence, avoid extreme outcomes.
        if project_count >= 5 and skills_count >= 8 and not has_any_experience:
            score_breakdown.overall_score = max(5.5, min(6.8, float(score_breakdown.overall_score)))

        return score_breakdown

    @staticmethod
    def _sanitize_signals_for_role(
        role_level: str,
        strong_signals: List[str],
        weak_signals: List[str],
    ) -> tuple[List[str], List[str]]:
        """Reduce speculative wording and keep feedback evidence-based."""
        cleaned_strong: List[str] = []
        for signal in strong_signals or []:
            text = str(signal).strip()
            if text and text not in cleaned_strong:
                cleaned_strong.append(text)

        cleaned_weak: List[str] = []
        for signal in weak_signals or []:
            text = str(signal).strip()
            lowered = text.lower()

            if role_level == 'early':
                if 'impact ability to work in a team' in lowered:
                    text = 'Limited formal industry collaboration evidence in the provided profile.'
                elif 'followers' in lowered or 'stars' in lowered:
                    text = 'Limited external GitHub validation (stars/followers), so practical depth should be verified in interview rounds.'
                elif 'lack of experience' in lowered or 'no experience' in lowered:
                    text = 'Limited formal industry experience (expected for intern-level candidates).'

            if text and text not in cleaned_weak:
                cleaned_weak.append(text)

        # Keep output concise for UI and pitch clarity.
        return cleaned_strong[:5], cleaned_weak[:5]

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

            role_level = ScoringAgent._infer_role_level(target_role)

            # Apply role-aware calibration before weighted scoring.
            calibrated = ScoringAgent._calibrate_scores_for_role(
                evaluation['score_breakdown'],
                role_level,
                candidate_profile,
                github_signals,
            )

            # Calculate weighted overall score
            score_breakdown = ScoringAgent._create_score_breakdown(
                calibrated,
                role_level=role_level,
            )

            score_breakdown = ScoringAgent._balance_overall_for_role(
                score_breakdown,
                role_level,
                candidate_profile,
            )

            strong_signals, weak_signals = ScoringAgent._sanitize_signals_for_role(
                role_level,
                evaluation.get('strong_signals', []),
                evaluation.get('weak_signals', []),
            )

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
                strong_signals=strong_signals,
                weak_signals=weak_signals,
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
    def _create_score_breakdown(score_data: Dict[str, float], role_level: str = 'mid') -> ScoreBreakdown:
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

        weights = ScoringAgent._get_role_weights(role_level)

        # Calculate weighted overall score
        overall_score = (
            technical_skills * weights['technical_skills'] +
            project_quality * weights['project_quality'] +
            github_activity * weights['github_activity'] +
            experience_depth * weights['experience_depth'] +
            communication * weights['communication']
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