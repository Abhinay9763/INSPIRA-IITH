"""Configuration for AI Interview Preparation Platform - Stage 2"""

import os
from typing import Dict
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
# Look for .env file in the project root (parent of backend)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Model Configuration - Using Groq-available models
INTERVIEWER_MODEL = "llama-3.1-8b-instant"  # Fast model for real-time conversation
QUESTION_GEN_MODEL = "llama-3.3-70b-versatile"  # High capability for question generation
DEBRIEF_MODEL = "llama-3.3-70b-versatile"  # High capability for analysis

# Interview Flow Configuration
MAX_CONTEXT_TURNS = 6  # Maximum number of conversation turns to keep in context
PHASE_TURN_THRESHOLDS = {
    1: 2,   # Phase 1 ends after turn 2
    2: 6,   # Phase 2 ends after turn 6
    3: 11   # Phase 3 ends after turn 11, Phase 4 starts at 12+
}

# Text-to-Speech Configuration
TTS_VOICE = "en-US-GuyNeural"  # Default voice for edge-tts

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

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Paths
PROMPTS_DIR = "backend/prompts"

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
    return True