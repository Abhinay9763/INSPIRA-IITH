"""Pydantic models for Stage 2 interview components"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from enum import Enum

class InterviewPhase(Enum):
    """Interview phases"""
    WARMUP = 1
    RESUME_DEEP_DIVE = 2
    TECHNICAL = 3
    CLOSING = 4

class QuestionCategory(str, Enum):
    """Question categories"""
    DSA = "DSA"
    SYSTEM_DESIGN = "SystemDesign"
    BEHAVIORAL = "Behavioral"
    RESUME_DEEP_DIVE = "ResumeDeepDive"

class QuestionDifficulty(str, Enum):
    """Question difficulty levels"""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class Question(BaseModel):
    """Individual question model"""
    question_text: str
    category: QuestionCategory
    difficulty: QuestionDifficulty
    talking_points: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)

class QuestionBank(BaseModel):
    """Question bank generated for the interview"""
    questions: List[Question]
    seniority_level: str
    total_questions: int
    category_distribution: Dict[str, int]

class ConversationTurn(BaseModel):
    """Single conversation turn"""
    role: Literal["user", "assistant"]
    content: str
    timestamp: str
    turn_number: int
    phase: InterviewPhase

class InterviewState(BaseModel):
    """Current interview state"""
    candidate_profile: Dict[str, Any]
    question_bank: QuestionBank
    full_conversation_history: List[ConversationTurn] = Field(default_factory=list)
    trimmed_history: List[ConversationTurn] = Field(default_factory=list)
    current_phase: InterviewPhase = InterviewPhase.WARMUP
    turn_count: int = 0
    target_company: Optional[str] = None
    target_role: Optional[str] = None

# === REQUEST/RESPONSE MODELS ===

class InterviewStartRequest(BaseModel):
    """Request to start an interview"""
    candidate_profile: Dict[str, Any] = Field(..., description="Final candidate profile JSON from Stage 1 (including target_company and target_role)")

class InterviewStartResponse(BaseModel):
    """Response for starting an interview"""
    text: str = Field(..., description="First question text")
    audio: Optional[str] = Field(None, description="Base64 encoded audio")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

class InterviewTurnRequest(BaseModel):
    """Request for one interview turn"""
    user_message: str = Field(..., description="User's response message")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")

class InterviewTurnResponse(BaseModel):
    """Response for one interview turn"""
    text: str = Field(..., description="AI interviewer response")
    audio: Optional[str] = Field(None, description="Base64 encoded audio")
    current_phase: InterviewPhase = Field(..., description="Current interview phase")
    turn_count: int = Field(..., description="Current turn number")

class PhaseBreakdown(BaseModel):
    """Per-phase performance breakdown"""
    score: int = Field(..., ge=0, le=100)
    feedback: str

class AnswerFeedback(BaseModel):
    """Feedback for individual answers"""
    question: str
    candidate_answer_summary: str
    score: int = Field(..., ge=1, le=10)
    stronger_answer_example: str
    resume_gap_flagged: bool = False
    resume_gap_note: str = ""

class ResumeVsReality(BaseModel):
    """Resume claims vs demonstrated skills"""
    claim: str
    demonstrated: str
    verdict: Literal["matched", "gap", "exceeded"]

class StudyRecommendation(BaseModel):
    """Study recommendation"""
    priority: Literal["high", "medium", "low"]
    topic: str
    reason: str

class DebriefReport(BaseModel):
    """Complete debrief report"""
    overall_score: int = Field(..., ge=0, le=100)
    summary: str
    phase_breakdown: Dict[str, PhaseBreakdown]
    answer_feedback: List[AnswerFeedback]
    resume_vs_reality: List[ResumeVsReality]
    study_recommendations: List[StudyRecommendation]
    conversation_history: List[Dict[str, Any]]

class DebriefResponse(BaseModel):
    """Response for interview debrief"""
    debrief_report: DebriefReport
    success: bool = True
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    message: str
    error_type: Optional[str] = None