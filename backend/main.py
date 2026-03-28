"""
Combined FastAPI main application for AI-powered interview preparation platform.
Provides both Stage 1 (resume analysis) and Stage 2 (interview + multi-stakeholder decision) via REST API.
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Stage 1 Imports
from .models.candidate import FinalCandidateProfile
from .orchestrator import stage1_orchestrator
from .config import MAX_FILE_SIZE_MB, validate_config, API_HOST, API_PORT

# Stage 2 Imports
from .models.interview import (
    InterviewStartRequest, InterviewStartResponse,
    InterviewTurnRequest, InterviewTurnResponse,
    DebriefResponse, StakeholderResponse, ErrorResponse
)
from .orchestrator import get_orchestrator

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
    logger.info("Starting AI Interview Preparation Platform - Combined Stage 1 & 2")
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
    logger.info("Shutting down AI Interview Preparation Platform")

# Create FastAPI app
app = FastAPI(
    title="AI Interview Preparation Platform",
    description="Complete AI-powered technical interview preparation: Resume Analysis + Mock Interview + Multi-Stakeholder Decision",
    version="3.0.0",
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

# Dependency to get interview orchestrator
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

# === ROOT & HEALTH ROUTES ===

@app.get("/")
async def root():
    """Root endpoint with complete API information."""
    return {
        "message": "AI Interview Preparation Platform",
        "version": "3.0.0",
        "description": "Complete interview preparation pipeline",
        "stages": {
            "stage_1": "Resume Analysis - /analyze",
            "stage_2": "Mock Interview - /interview/*",
            "stage_3": "Multi-Stakeholder Decision - /interview/stakeholder-decision"
        },
        "endpoints": {
            "stage_1_analyze": "POST /analyze - Upload resume PDF for analysis",
            "stage_2_start": "POST /interview/start - Start mock interview",
            "stage_2_turn": "POST /interview/turn - Process interview turn",
            "stage_2_end": "POST /interview/end - End interview and get debrief",
            "stage_3_decision": "POST /interview/stakeholder-decision - Get hiring decision",
            "health": "GET /health - Service health check",
            "docs": "GET /docs - Interactive API documentation"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "platform": "AI Interview Preparation Platform",
        "version": "3.0.0",
        "stages": {
            "stage_1_analyses_in_memory": len(stage1_orchestrator.list_analyses()),
            "stage_2_active_sessions": get_orchestrator().get_active_session_count()
        }
    }

# === STAGE 1 ROUTES (Resume Analysis) ===

@app.post("/analyze", response_model=FinalCandidateProfile)
async def analyze_resume(
    resume: UploadFile = File(..., description="Resume PDF file"),
    company: str = Form(..., description="Target company name"),
    role: str = Form(..., description="Target role description")
) -> FinalCandidateProfile:
    """
    Analyze a resume PDF for a specific company and role (Stage 1).

    This endpoint runs the complete Stage 1 pipeline:
    1. Extract text and URLs from PDF
    2. Analyze resume content with LLM
    3. Fetch and analyze GitHub profile data
    4. Generate comprehensive scoring and interview questions

    Args:
        resume: PDF file upload
        company: Target company name (1-100 characters)
        role: Target role description (1-100 characters)

    Returns:
        FinalCandidateProfile: Complete analysis with scoring and recommendations

    Raises:
        HTTPException: If validation fails or analysis encounters errors
    """
    try:
        # Validate inputs
        await _validate_inputs(resume, company, role)

        # Read PDF content
        pdf_content = await resume.read()
        logger.info(f"Processing resume for {role} at {company}")
        logger.info(f"PDF size: {len(pdf_content)} bytes")

        # Run Stage 1 pipeline
        final_profile = await stage1_orchestrator.run_stage_one(
            resume_pdf=pdf_content,
            company=company.strip(),
            role=role.strip()
        )

        # Log successful completion
        logger.info(f"Analysis completed for {final_profile.candidate_profile.name}")
        logger.info(f"Overall score: {final_profile.score_breakdown.overall_score:.1f}/10")

        return final_profile

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Resume analysis failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Resume analysis failed: {str(e)}"
        )

@app.get("/analyses")
async def list_analyses() -> Dict[str, Any]:
    """
    List all analyses currently stored in memory.

    Returns:
        Dict containing list of analysis IDs and count
    """
    analyses = stage1_orchestrator.list_analyses()
    return {
        "total_analyses": len(analyses),
        "analyses": analyses,
        "note": "Analyses are stored in memory and will be lost on service restart"
    }

@app.delete("/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str) -> Dict[str, Any]:
    """
    Delete a specific analysis from memory.

    Args:
        analysis_id: The ID of the analysis to delete

    Returns:
        Success message or error
    """
    if stage1_orchestrator.clear_analysis(analysis_id):
        return {"message": f"Analysis {analysis_id} deleted successfully"}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis {analysis_id} not found"
        )

@app.delete("/analyses")
async def clear_all_analyses() -> Dict[str, Any]:
    """
    Clear all analyses from memory.

    Returns:
        Success message
    """
    stage1_orchestrator.clear_all_analyses()
    return {"message": "All analyses cleared successfully"}

# === STAGE 2 ROUTES (Mock Interview) ===

@app.post("/interview/start", response_model=InterviewStartResponse)
async def start_interview(
    request: InterviewStartRequest,
    orchestrator = Depends(get_interview_orchestrator)
):
    """
    Start a new mock interview session (Stage 2)

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
    Process one interview turn (Stage 2)

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
    End interview and generate comprehensive debrief (Stage 2)

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

# === STAGE 3 ROUTES (Multi-Stakeholder Decision) ===

@app.post("/interview/stakeholder-decision", response_model=StakeholderResponse)
async def generate_stakeholder_decision(
    session_id: str,
    orchestrator = Depends(get_interview_orchestrator)
):
    """
    Generate multi-stakeholder hiring decision (Stage 3)

    This endpoint:
    1. Uses existing interview and debrief data from session
    2. Simulates 4 stakeholder perspectives with different priorities
    3. Generates individual decisions with detailed reasoning
    4. Produces weighted consensus decision with discussion simulation
    5. Returns comprehensive stakeholder report
    """
    try:
        logger.info(f"Generating stakeholder decision for session: {session_id}")

        if not session_id:
            raise ValueError("Session ID is required")

        stakeholder_report = await orchestrator.run_stage_three_stakeholder_decision(session_id)

        response = StakeholderResponse(
            stakeholder_report=stakeholder_report,
            success=True,
            message="Stakeholder decisions generated successfully"
        )

        return response

    except ValueError as e:
        logger.error(f"Invalid stakeholder decision request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error_text = str(e)
        logger.error(f"Stakeholder decision failed: {error_text}")

        lowered = error_text.lower()
        if '429' in lowered or 'rate limit' in lowered or 'too many requests' in lowered:
            raise HTTPException(status_code=429, detail="Stakeholder decision is rate-limited right now. Please retry in a minute.")

        raise HTTPException(status_code=500, detail=error_text)

# === UTILITY ROUTES (Stage 2) ===

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

# === VALIDATION HELPER FUNCTIONS ===

async def _validate_inputs(resume: UploadFile, company: str, role: str):
    """
    Validate input parameters for the analyze endpoint.

    Args:
        resume: Uploaded file
        company: Company name
        role: Role description

    Raises:
        HTTPException: If validation fails
    """
    # Validate file type
    if not resume.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    if not resume.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported"
        )

    # Validate file size
    if resume.size and resume.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE_MB}MB"
        )

    # Validate company name
    if not company or not company.strip():
        raise HTTPException(status_code=400, detail="Company name is required")

    if len(company.strip()) > 100:
        raise HTTPException(
            status_code=400,
            detail="Company name must be 100 characters or less"
        )

    # Validate role description
    if not role or not role.strip():
        raise HTTPException(status_code=400, detail="Role description is required")

    if len(role.strip()) > 100:
        raise HTTPException(
            status_code=400,
            detail="Role description must be 100 characters or less"
        )

# === APPLICATION STARTUP ===

if __name__ == "__main__":
    logger.info(f"Starting server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level="info"
    )