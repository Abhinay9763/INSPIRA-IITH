# Resume Analysis API - Stage 1

AI-powered technical interview preparation platform backend. This implements Stage 1: Resume Analysis.

## Features

- **PDF Resume Analysis**: Extract structured candidate profiles from PDF resumes
- **GitHub Profile Analysis**: Automatically analyze GitHub repositories and code quality
- **Smart Scoring**: AI-powered candidate evaluation across multiple dimensions
- **Interview Preparation**: Generate targeted interview questions based on analysis
- **REST API**: Clean FastAPI interface with automatic documentation

## Tech Stack

- **FastAPI + uvicorn**: Fast, modern API framework
- **Pydantic**: Data validation and serialization
- **Groq SDK**: Large Language Model integration
- **pdfplumber**: Robust PDF text extraction
- **httpx**: Async HTTP client for GitHub API
- **textstat**: Natural language processing for README analysis

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the environment template
cp .env.example .env

# Edit .env and add your API keys:
# - GROQ_API_KEY: Get from https://groq.com
# - GITHUB_TOKEN: Create at https://github.com/settings/tokens
```

### 3. Run the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python main.py
```

## API Usage

### Analyze Resume

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "resume=@resume.pdf" \
  -F "company=Google" \
  -F "role=Senior Software Engineer"
```

### Interactive Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Pipeline Overview

### Stage 1 Process

1. **PDF Extraction**: Extract text and URLs using pdfplumber
2. **Resume Analysis**: Use LLM to extract structured candidate profile
3. **GitHub Analysis**:
   - Fetch user profile and top repositories
   - Analyze README quality with NLP heuristics + LLM scoring
   - Assess project originality and code quality
4. **Final Scoring**: Comprehensive evaluation across 5 dimensions
5. **Interview Prep**: Generate targeted interview question threads

### Models Used

- **llama-3.3-70b-versatile**: Resume analysis and final scoring
- **llama-3.1-8b-instant**: README quality assessment

### Scoring Dimensions

- **Technical Skills** (25%): Depth and relevance of technical expertise
- **Project Quality** (25%): GitHub repository quality and originality
- **GitHub Activity** (20%): Contribution patterns and community engagement
- **Experience Depth** (20%): Career progression and role complexity
- **Communication** (10%): Documentation and presentation quality

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── orchestrator.py         # Stage 1 pipeline coordinator
├── config.py              # Environment variables and constants
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── agents/               # Analysis agents
│   ├── resume_analyst.py    # Resume content extraction
│   ├── github_scout.py      # GitHub profile analysis
│   └── scorer.py           # Final candidate scoring
├── models/               # Pydantic data models
│   └── candidate.py         # All API request/response models
├── prompts/              # LLM prompts (loaded at runtime)
│   ├── resume_analyst.txt   # Resume extraction prompt
│   ├── readme_scorer.txt    # README quality assessment
│   └── scoring_agent.txt    # Final evaluation prompt
└── utils/                # Utilities
    ├── pdf_parser.py        # PDF text extraction
    └── groq_client.py       # LLM API client
```

## Error Handling

The application includes comprehensive error handling:

- **PDF Issues**: Validates file type, size, and extraction success
- **API Failures**: Graceful fallbacks when GitHub or LLM APIs are unavailable
- **Data Validation**: Pydantic models ensure type safety throughout
- **Logging**: Detailed logging for debugging and monitoring

## Memory Management

Stage 1 analyses are held in memory for handoff to Stage 2. Use the `/analyses` endpoints to manage stored analyses.

## Development Notes

- All LLM prompts are stored in `.txt` files and loaded at runtime
- GitHub API calls are async and include rate limiting considerations
- README analysis uses NLP heuristics before expensive LLM calls
- Comprehensive fallback mechanisms ensure robustness

## Next Steps

This implements Stage 1 of the platform. The analysis results are stored in memory as the handoff point for Stage 2 (Interview Simulation) development.