"""
Combined Configuration for AI Interview Preparation Platform.
Includes settings for both Stage 1 (resume analysis) and Stage 2 (interview + stakeholder decision).
"""

import os
from typing import Dict
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Look for .env file in the project root (parent of backend)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Required for Stage 1 only

# === STAGE 1 MODEL CONFIGURATION (Resume Analysis) ===
RESUME_ANALYST_MODEL = "llama-3.3-70b-versatile"
SCORING_AGENT_MODEL = "llama-3.3-70b-versatile"
README_SCORER_MODEL = "llama-3.1-8b-instant"

# === STAGE 2 MODEL CONFIGURATION (Interview) ===
INTERVIEWER_MODEL = os.getenv("INTERVIEWER_MODEL", "llama-3.1-8b-instant")  # Fast model for real-time conversation
QUESTION_GEN_MODEL = os.getenv("QUESTION_GEN_MODEL", "llama-3.3-70b-versatile")  # High capability for question generation
DEBRIEF_MODEL = os.getenv("DEBRIEF_MODEL", "llama-3.3-70b-versatile")  # High capability for analysis
STAKEHOLDER_MODEL = os.getenv("STAKEHOLDER_MODEL", "llama-3.1-8b-instant")  # Lower-latency default to reduce rate-limit failures

# === STAGE 1 CONSTANTS (Resume Analysis) ===

# Pipeline Constants
MAX_REPOS_TO_SCAN = 5

# Rubric Weight Constants
WEIGHTS = {
    "technical_skills": 0.25,
    "project_quality": 0.25,
    "github_activity": 0.20,
    "experience_depth": 0.20,
    "communication": 0.10
}

# README NLP Heuristics Thresholds
README_MIN_WORDS = 100
README_LOW_QUALITY_SCORE = 2
README_MEDIUM_QUALITY_SCORE = 3

# === STAGE 2 CONSTANTS (Interview) ===

# Interview Flow Configuration
MAX_CONTEXT_TURNS = 6  # Maximum number of conversation turns to keep in context
PHASE_TURN_THRESHOLDS = {
    1: 2,   # Phase 1 ends after turn 2
    2: 6,   # Phase 2 ends after turn 6
    3: 11   # Phase 3 ends after turn 11, Phase 4 starts at 12+
}

# Text-to-Speech Configuration
TTS_VOICE = "en-US-SteffanNeural"  # Default voice for edge-tts

# Interview Flavor Configuration based on candidate seniority
INTERVIEW_FLAVORS = {
    "junior": {  # 0-2 years
        "dsa_percentage": 60,
        "system_design_percentage": 0,
        "behavioral_percentage": 20,
        "resume_percentage": 20
    },
    "mid": {  # 2-5 years
        "dsa_percentage": 30,
        "system_design_percentage": 40,
        "behavioral_percentage": 15,
        "resume_percentage": 15
    },
    "senior": {  # 5+ years
        "dsa_percentage": 20,
        "system_design_percentage": 50,
        "behavioral_percentage": 15,
        "resume_percentage": 15
    }
}

# === STAGE 3 CONSTANTS (Multi-Stakeholder Decision) ===

# Stakeholder Configuration
STAKEHOLDER_FOCUS_AREAS = {
    "hiring_manager": ["culture_fit", "growth_potential", "team_dynamics", "leadership"],
    "technical_lead": ["technical_depth", "code_quality", "system_thinking", "problem_solving"],
    "hr_representative": ["communication", "cultural_alignment", "risk_factors", "compliance"],
    "peer_engineer": ["collaboration", "mentoring", "knowledge_sharing", "day_to_day_work"]
}

STAKEHOLDER_WEIGHTS = {
    "hiring_manager": 0.35,
    "technical_lead": 0.30,
    "hr_representative": 0.20,
    "peer_engineer": 0.15
}

# === SHARED CONFIGURATION ===

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000
MAX_FILE_SIZE_MB = 10  # For resume PDF uploads

# Paths
PROMPTS_DIR = "backend/prompts"

# === UTILITY FUNCTIONS ===

def get_seniority_level(years_of_experience: int) -> str:
    """Determine seniority level based on years of experience"""
    if years_of_experience <= 2:
        return "junior"
    elif years_of_experience <= 5:
        return "mid"
    else:
        return "senior"

def validate_config() -> bool:
    """Validate that all required configuration is present"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable is required")

    # Note: GITHUB_TOKEN is only required for Stage 1 analyze endpoint
    # Stage 2 (interview) can work without it

    return True