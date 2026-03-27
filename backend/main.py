"""Main FastAPI application with Stage 2 routes"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models.interview import (
    InterviewStartRequest, InterviewStartResponse,
    InterviewTurnRequest, InterviewTurnResponse,
    DebriefResponse, ErrorResponse
)
from .orchestrator import get_orchestrator
from .config import validate_config, API_HOST, API_PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting AI Interview Preparation Platform - Stage 2")
    try:
        validate_config()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # Test connections
    try:
        from .utils.groq_client import get_groq_client
        client = get_groq_client()
        is_connected = client.test_connection()
        if is_connected:
            logger.info("Groq API connection successful")
        else:
            logger.warning("Groq API connection test failed")
    except Exception as e:
        logger.warning(f"Could not test Groq connection: {e}")

    yield

    # Shutdown
    logger.info("Shutting down AI Interview Preparation Platform - Stage 2")

# Create FastAPI app
app = FastAPI(
    title="AI Interview Preparation Platform - Stage 2",
    description="Mock Interview and Post-Interview Debrief API",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get orchestrator
def get_interview_orchestrator():
    """Dependency to get orchestrator instance"""
    return get_orchestrator()

# === EXCEPTION HANDLERS ===

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    logger.error(f"Value error: {str(exc)}")
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            message=str(exc),
            error_type="ValueError"
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            message="Internal server error",
            error_type="InternalError"
        ).dict()
    )

# === STAGE 2 ROUTES ===

@app.post("/interview/start", response_model=InterviewStartResponse)
async def start_interview(
    request: InterviewStartRequest,
    orchestrator = Depends(get_interview_orchestrator)
):
    """
    Start a new mock interview session

    This endpoint:
    1. Receives candidate profile from Stage 1 (including target company/role)
    2. Generates question bank based on candidate seniority
    3. Initiates interview with first question
    4. Returns first question as text + audio
    """
    try:
        logger.info("Starting new interview session")

        # Validate candidate profile
        if not request.candidate_profile:
            raise ValueError("Candidate profile is required")

        # Start interview
        session_id, first_question, audio_base64 = await orchestrator.run_stage_two_start(
            request.candidate_profile
        )

        response = InterviewStartResponse(
            text=first_question,
            audio=audio_base64,
            session_id=session_id
        )

        logger.info(f"Interview started successfully with session: {session_id}")
        return response

    except Exception as e:
        logger.error(f"Failed to start interview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interview/turn", response_model=InterviewTurnResponse)
async def interview_turn(
    request: InterviewTurnRequest,
    orchestrator = Depends(get_interview_orchestrator)
):
    """
    Process one interview turn

    This endpoint:
    1. Receives user's response message
    2. Processes it through the interviewer agent
    3. Manages conversation context and phase transitions
    4. Returns AI response as text + audio + current phase
    """
    try:
        logger.info(f"Processing interview turn for session: {request.session_id}")

        # Validate request
        if not request.user_message or not request.user_message.strip():
            raise ValueError("User message cannot be empty")

        if not request.session_id:
            raise ValueError("Session ID is required")

        # Process turn
        ai_response, audio_base64, current_phase, turn_count = await orchestrator.run_stage_two_turn(
            request.session_id,
            request.user_message.strip()
        )

        response = InterviewTurnResponse(
            text=ai_response,
            audio=audio_base64,
            current_phase=current_phase,
            turn_count=turn_count
        )

        logger.info(f"Turn processed. Phase: {current_phase.name}, Turn: {turn_count}")
        return response

    except ValueError as e:
        logger.error(f"Invalid request in interview turn: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to process interview turn: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/interview/end", response_model=DebriefResponse)
async def end_interview(
    session_id: str,
    orchestrator = Depends(get_interview_orchestrator)
):
    """
    End interview and generate comprehensive debrief

    This endpoint:
    1. Triggers the debrief agent
    2. Analyzes full conversation transcript
    3. Generates comprehensive feedback report
    4. Returns debrief report + conversation history
    """
    try:
        logger.info(f"Ending interview for session: {session_id}")

        # Validate session
        if not session_id:
            raise ValueError("Session ID is required")

        # Generate debrief
        debrief_report = await orchestrator.run_stage_two_end(session_id)

        response = DebriefResponse(
            debrief_report=debrief_report,
            success=True,
            message="Interview completed and debrief generated successfully"
        )

        logger.info(f"Interview ended successfully. Overall score: {debrief_report.overall_score}")
        return response

    except ValueError as e:
        logger.error(f"Invalid request in end interview: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to end interview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# === UTILITY ROUTES ===

@app.get("/interview/session/{session_id}")
async def get_session_info(
    session_id: str,
    orchestrator = Depends(get_interview_orchestrator)
):
    """Get information about an active session"""
    session_info = orchestrator.get_session_info(session_id)
    if session_info is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session_info

@app.delete("/interview/session/{session_id}")
async def cleanup_session(
    session_id: str,
    orchestrator = Depends(get_interview_orchestrator)
):
    """Manually clean up a session"""
    success = orchestrator.cleanup_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session cleaned up successfully"}

@app.get("/interview/sessions/count")
async def get_active_sessions_count(
    orchestrator = Depends(get_interview_orchestrator)
):
    """Get count of active sessions"""
    count = orchestrator.get_active_session_count()
    return {"active_sessions": count}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Interview Preparation Platform - Stage 2",
        "version": "2.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Interview Preparation Platform - Stage 2",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# === APPLICATION STARTUP ===

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )