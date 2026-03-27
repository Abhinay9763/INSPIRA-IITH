"""
FastAPI main application for AI-powered resume analysis.
Provides Stage 1 resume analysis pipeline via REST API.
"""

import logging
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models.candidate import FinalCandidateProfile
from orchestrator import stage1_orchestrator
from config import MAX_FILE_SIZE_MB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Resume Analysis API",
    description="AI-powered technical interview preparation platform - Stage 1: Resume Analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Resume Analysis API",
        "version": "1.0.0",
        "stage": "Stage 1 - Resume Analysis",
        "endpoints": {
            "analyze": "POST /analyze - Upload resume PDF for analysis",
            "health": "GET /health - Service health check",
            "docs": "GET /docs - Interactive API documentation"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "stage": "Stage 1",
        "analyses_in_memory": len(stage1_orchestrator.list_analyses())
    }


@app.post("/analyze", response_model=FinalCandidateProfile)
async def analyze_resume(
    resume: UploadFile = File(..., description="Resume PDF file"),
    company: str = Form(..., description="Target company name"),
    role: str = Form(..., description="Target role description")
) -> FinalCandidateProfile:
    """
    Analyze a resume PDF for a specific company and role.

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


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error occurred",
            "error": str(exc) if logger.level <= logging.DEBUG else "Contact support"
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )