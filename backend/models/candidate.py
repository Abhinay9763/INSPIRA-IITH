"""
Pydantic models for the Resume Analysis application.
Defines all request and response shapes.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# API Request Models
class AnalyzeRequest(BaseModel):
    """Request model for the /analyze endpoint."""
    # Note: PDF file is handled separately in FastAPI multipart form
    company: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)


# Core Data Models
class CandidateProfile(BaseModel):
    """Candidate profile extracted from resume."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    website_url: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    projects: List[Dict[str, Any]] = []


class Repository(BaseModel):
    """GitHub repository information."""
    name: str
    description: Optional[str] = None
    languages: Dict[str, int] = {}  # Language -> bytes count
    stars: int = 0
    forks: int = 0
    readme_content: Optional[str] = None
    readme_score: Optional[int] = None  # 1-10 scale
    originality_verdict: Optional[str] = None


class GitHubSignals(BaseModel):
    """GitHub profile and repository signals."""
    username: str
    profile_url: str
    public_repos: int = 0
    followers: int = 0
    following: int = 0
    total_stars: int = 0
    repositories: List[Repository] = []


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown."""
    technical_skills: float = Field(..., ge=0.0, le=10.0)
    project_quality: float = Field(..., ge=0.0, le=10.0)
    github_activity: float = Field(..., ge=0.0, le=10.0)
    experience_depth: float = Field(..., ge=0.0, le=10.0)
    communication: float = Field(..., ge=0.0, le=10.0)
    overall_score: float = Field(..., ge=0.0, le=10.0)


class InterviewThread(BaseModel):
    """Suggested interview question thread."""
    topic: str
    questions: List[str]
    rationale: str


class FinalCandidateProfile(BaseModel):
    """Complete candidate analysis with scoring."""
    candidate_profile: CandidateProfile
    github_signals: Optional[GitHubSignals] = None
    target_company: str
    target_role: str
    score_breakdown: ScoreBreakdown
    strong_signals: List[str] = []
    weak_signals: List[str] = []
    interview_threads: List[InterviewThread] = []
    analysis_date: str


# Internal Models for Pipeline
class PDFExtraction(BaseModel):
    """PDF extraction results."""
    raw_text: str
    urls: List[str] = []


class README(BaseModel):
    """README analysis data."""
    content: str
    word_count: int
    has_headers: bool
    has_code_blocks: bool
    heuristic_score: Optional[int] = None  # From NLP analysis
    llm_score: Optional[int] = None  # From Groq LLM
    final_score: int  # The score used for evaluation