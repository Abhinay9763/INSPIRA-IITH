# AI Hiring Intelligence Platform

End-to-end system for evaluating candidates beyond resumes using adaptive interviews and multi-stakeholder hiring simulation.

## What It Does

1. Resume + profile signal analysis
2. Dynamic mock interview with phase progression
3. Debrief report with strengths, gaps, and study recommendations
4. Multi-stakeholder hiring decision (Hiring Manager, Tech Lead, HR, Peer)

## Monorepo Layout

```
.
├── backend/                 # FastAPI + orchestration + LLM agents
├── frontend/                # Next.js app router UI
├── README-backend.md        # Stage-1-oriented backend notes
└── multi_agent_orchestration_dark.svg
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm 9+
- Groq API key

## Environment Setup

Create `.env` at repo root:

```bash
GROQ_API_KEY=your_key_here
GITHUB_TOKEN=optional_but_recommended

# Optional model overrides
INTERVIEWER_MODEL=llama-3.1-8b-instant
QUESTION_GEN_MODEL=llama-3.3-70b-versatile
DEBRIEF_MODEL=llama-3.3-70b-versatile
STAKEHOLDER_MODEL=llama-3.1-8b-instant

# TTS
TTS_VOICE=en-US-SteffanNeural
```

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run Locally

### 1) Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 --access-log
```

API docs: `http://localhost:8000/docs`

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: `http://localhost:3000`

## Core API Endpoints

- `POST /analyze` - Resume + company + role analysis
- `POST /interview/start` - Start interview session
- `POST /interview/turn` - Submit one candidate response
- `POST /interview/end?session_id=...` - Generate debrief report
- `POST /interview/stakeholder-decision?session_id=...` - Generate panel decision

## Frontend Flow

1. Home: upload resume and target role/company
2. Results: candidate profile, score breakdown, GitHub and threads
3. Interview: adaptive multi-phase interview with TTS responses
4. Debrief: full feedback report
5. Stakeholder: weighted panel-style final recommendation

## Pitch Routes

- Main app: `/`
- Results: `/results`
- Interview: `/interview`
- Debrief: `/debrief`
- Stakeholder: `/stakeholder`
- Architecture slide page: `/architecture`

## Notes on Scoring

- Score scale is `0-10` in backend and frontend.
- Early-career roles (intern/junior) use role-aware calibration to avoid unfair penalties for missing full-time experience.

## Troubleshooting

- If backend fails to start with `ModuleNotFoundError`, install backend requirements inside the backend venv.
- If frontend cannot call backend, verify `NEXT_PUBLIC_API_URL` and CORS.
- If stakeholder stage is slow, it may be provider rate limiting; system retries automatically.

## Tech Stack

- Backend: FastAPI, Pydantic, Groq SDK, edge-tts, pdfplumber, httpx
- Frontend: Next.js (App Router), TypeScript, Tailwind CSS


