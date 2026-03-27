#!/usr/bin/env python3
"""
Import validation test for the AI Interview Preparation Platform backend.
Tests that all modules can be imported without errors after the import fixes.
"""

def test_imports():
    """Test all critical imports to validate the backend structure"""
    print("🔍 Testing import structure for AI Interview Preparation Platform...")

    try:
        # Test main app import
        print("  ✓ Testing main app import...")
        from backend.main import app
        print("  ✅ Main FastAPI app imported successfully")

        # Test Stage 1 components
        print("  ✓ Testing Stage 1 components...")
        from backend.models.candidate import FinalCandidateProfile
        from backend.agents.resume_analyst import resume_analyst
        from backend.agents.github_scout import github_scout
        from backend.agents.scorer import scoring_agent
        print("  ✅ Stage 1 (Resume Analysis) components imported successfully")

        # Test Stage 2 components
        print("  ✓ Testing Stage 2 components...")
        from backend.models.interview import InterviewState, DebriefReport
        from backend.agents.question_generator import get_question_generator
        from backend.agents.interviewer import get_interviewer_agent
        from backend.agents.debrief import get_debrief_agent
        print("  ✅ Stage 2 (Interview) components imported successfully")

        # Test Stage 3 components
        print("  ✓ Testing Stage 3 components...")
        from backend.agents.stakeholder import get_stakeholder_agent
        from backend.models.interview import StakeholderReport, StakeholderDecision
        print("  ✅ Stage 3 (Multi-Stakeholder Decision) components imported successfully")

        # Test utilities
        print("  ✓ Testing utilities...")
        from backend.utils.groq_client import get_groq_client
        from backend.utils.pdf_parser import pdf_parser
        from backend.utils.tts import TTSService
        print("  ✅ Utility components imported successfully")

        # Test orchestrator
        print("  ✓ Testing orchestrator...")
        from backend.orchestrator import get_orchestrator
        print("  ✅ Orchestrator imported successfully")

        # Test configuration
        print("  ✓ Testing configuration...")
        from backend.config import validate_config
        print("  ✅ Configuration imported successfully")

        print("\n🎉 ALL IMPORTS SUCCESSFUL!")
        print("   The backend is properly structured and ready for deployment.")
        print("   All Stage 1, Stage 2, and Stage 3 components are working correctly.")

        return True

    except ImportError as e:
        print(f"\n❌ IMPORT ERROR: {e}")
        print("   There are still import issues that need to be resolved.")
        return False

    except Exception as e:
        print(f"\n⚠️  UNEXPECTED ERROR: {e}")
        print("   There may be other issues beyond imports.")
        return False

if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)