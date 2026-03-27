"""
Configuration module for the Resume Analysis application.
Loads environment variables and defines constants.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Model Constants
RESUME_ANALYST_MODEL = "llama-3.3-70b-versatile"
SCORING_AGENT_MODEL = "llama-3.3-70b-versatile"
README_SCORER_MODEL = "llama-3.1-8b-instant"

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

# API Configuration
MAX_FILE_SIZE_MB = 10