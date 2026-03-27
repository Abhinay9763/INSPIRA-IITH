# AI Interview Preparation Platform - Stage 2

## 🎯 Overview

Stage 2 provides **Mock Interview and Post-Interview Debrief** functionality for the AI-powered technical interview preparation platform. Built with FastAPI, it conducts realistic technical interviews and provides comprehensive feedback.

## 🏗️ Architecture

### Pipeline Flow
1. **Question Generator** → Creates interview questions based on candidate profile
2. **Interviewer Agent** → Conducts conversation across 4 phases
3. **Debrief Agent** → Analyzes full transcript and generates detailed feedback

### Interview Phases
- **Phase 1** (Turns 1-2): Warmup and introductions
- **Phase 2** (Turns 3-6): Resume deep dive
- **Phase 3** (Turns 7-11): Technical questions (DSA/System Design based on seniority)
- **Phase 4** (Turn 12+): Closing questions

### Seniority-Based Question Distribution
- **Junior (0-2 years)**: 60% DSA, 20% behavioral, 20% resume deep dive
- **Mid-level (2-5 years)**: 30% DSA, 40% system design, 30% behavioral
- **Senior (5+ years)**: 20% DSA, 50% system design, 30% behavioral

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Run the Server
```bash
cd backend
python main.py
```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`.

## 📡 API Endpoints

### Start Interview
```http
POST /interview/start
```
**Request:**
```json
{
  "candidate_profile": {
    /* Stage 1 output including: */
    "name": "John Doe",
    "years_of_experience": 5,
    "skills": [...],
    "target_company": "Google",
    "target_role": "Senior Software Engineer",
    /* ... other profile data ... */
  }
}
```

**Response:**
```json
{
  "text": "Hi there! I'm excited to chat with you today...",
  "session_id": "uuid-session-id"
}
```

### Interview Turn
```http
POST /interview/turn
```
**Request:**
```json
{
  "user_message": "Hi! I'm a software engineer with 5 years of experience...",
  "session_id": "uuid-session-id"
}
```

**Response:**
```json
{
  "text": "Great! Can you tell me more about your experience with...",
  "current_phase": "RESUME_DEEP_DIVE",
  "turn_count": 3
}
```

### End Interview
```http
POST /interview/end?session_id=uuid-session-id
```

**Response:**
```json
{
  "debrief_report": {
    "overall_score": 75,
    "summary": "The candidate demonstrated solid technical knowledge...",
    "phase_breakdown": { /* detailed scoring */ },
    "answer_feedback": [ /* per-answer analysis */ ],
    "resume_vs_reality": [ /* gaps identified */ ],
    "study_recommendations": [ /* actionable advice */ ],
    "conversation_history": [ /* full transcript */ ]
  },
  "success": true
}
```

## ⚙️ Configuration

Key environment variables in `.env`:

```bash
# Required
GROQ_API_KEY=your_api_key_here

# Optional overrides
INTERVIEWER_MODEL=llama-3.1-8b-instant
QUESTION_GEN_MODEL=llama-3.3-70b-versatile
DEBRIEF_MODEL=llama-3.3-70b-versatile
API_HOST=0.0.0.0
API_PORT=8000
```

## 🧪 Tech Stack

- **FastAPI + uvicorn** - REST API framework
- **Pydantic** - Data validation and serialization
- **Groq SDK** - LLM inference with high-speed models
- **Groq** - LLM inference provider

### Models Used
- **Question Generator**: llama-3.3-70b-versatile (high capability)
- **Interviewer**: llama-3.1-8b-instant (low latency)
- **Debrief**: llama-3.3-70b-versatile (comprehensive analysis)

## 📁 Project Structure

```
backend/
├── main.py                    # FastAPI app with routes
├── orchestrator.py            # Interview flow management
├── config.py                  # Configuration settings
├── agents/
│   ├── question_generator.py  # Question bank generation
│   ├── interviewer.py         # Conversation management
│   └── debrief.py            # Post-interview analysis
├── models/
│   └── interview.py          # Pydantic data models
├── prompts/
│   ├── question_generator.txt # LLM prompts (loaded at runtime)
│   ├── interviewer.txt
│   └── debrief.txt
└── utils/
    └── groq_client.py         # API client wrapper
```

## 🔄 Context Management

The system maintains two conversation histories:

1. **Full History** - Complete transcript preserved for debrief
2. **Trimmed History** - Summarized Phase 1 + last 6 turns for LLM context

This prevents context window overflow while maintaining conversation quality.

## 🎯 Key Features

- **Smart Question Generation** - Tailored to candidate's seniority and background
- **Phase-Based Flow** - Structured interview progression
- **Context-Aware Responses** - Interviewer references previous answers
- **Comprehensive Analysis** - Detailed feedback with actionable recommendations
- **Session Management** - Multiple concurrent interviews supported
- **Resume Gap Detection** - Compares claims vs demonstrated skills

## 🚨 Important Notes

- **Question Bank Security**: Never exposed to frontend - internal use only
- **LLM Provider**: Uses Groq SDK for high-speed inference
- **Prompt Loading**: All prompts loaded from `.txt` files at runtime
- **Session Cleanup**: Automatic cleanup after interview completion

## 🔧 Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black backend/
isort backend/
```

### Health Check
```bash
curl http://localhost:8000/health
```

## 📊 Monitoring

- **Active Sessions**: `GET /interview/sessions/count`
- **Session Info**: `GET /interview/session/{session_id}`
- **Manual Cleanup**: `DELETE /interview/session/{session_id}`

## 🤝 Integration with Stage 1

Stage 2 expects the final candidate profile JSON from Stage 1 as input to `/interview/start`. This profile should include:

- Candidate name and contact info
- Years of experience
- Skills and technologies
- Work experience history
- Education background
- Any ATS parsing results

## 📝 License

[Add your license information here]

\# init

