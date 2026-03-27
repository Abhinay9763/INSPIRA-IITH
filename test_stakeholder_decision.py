"""
Example usage of the Multi-Stakeholder Hiring Decision Simulator (Stage 3)
This script demonstrates the complete 3-stage interview process including the new stakeholder decision feature.
"""

import asyncio
import json
import time
from typing import Dict, Any
import httpx

# API Configuration
BASE_URL = "http://localhost:8000"

# Example candidate profile - using the candidate from our previous session
EXAMPLE_CANDIDATE_PROFILE = {
    "name": "Abhinay Kumar Vengala",
    "email": "abhinay.vengala@email.com",
    "years_of_experience": 4,
    "target_company": "Apple",
    "target_role": "Software Engineer",
    "skills": [
        "Python", "Java", "JavaScript", "React", "Node.js",
        "PostgreSQL", "MongoDB", "Docker", "AWS", "Git", "Kubernetes"
    ],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "Tech Innovations Inc",
            "duration": "2022-2024",
            "description": "Led development of microservices architecture, built scalable web applications"
        },
        {
            "title": "Full Stack Developer",
            "company": "Digital Solutions LLC",
            "duration": "2020-2022",
            "description": "Developed REST APIs, worked with React frontend and Node.js backend"
        }
    ],
    "education": {
        "degree": "Bachelor of Technology in Computer Science",
        "university": "Indian Institute of Technology Hyderabad",
        "graduation_year": 2020
    },
    "projects": [
        {
            "name": "Real-time Analytics Dashboard",
            "technologies": ["React", "Node.js", "MongoDB", "WebSocket"],
            "description": "Built real-time data visualization platform for IoT devices"
        }
    ]
}

# Example interview responses for a mid-level candidate
EXAMPLE_RESPONSES = [
    "Hello! I'm Abhinay Kumar Vengala, a software engineer with 4 years of experience. I've been working primarily with full-stack development using technologies like Python, Java, React, and Node.js. I'm particularly interested in scalable system design and have experience with microservices architecture.",

    "At Tech Innovations, I led the development of a microservices-based e-commerce platform. I was responsible for designing the overall architecture, implementing individual services using Python and Java, and ensuring they could handle high traffic. I also worked on the frontend using React and integrated with various AWS services for deployment and scaling.",

    "One of my most challenging projects was building a real-time analytics dashboard for IoT devices. The system needed to process thousands of data points per second and provide real-time visualizations. I used Node.js with WebSockets for real-time communication, MongoDB for storing time-series data, and React for the frontend. The biggest challenge was optimizing the database queries and implementing efficient data aggregation to handle the scale.",

    "For the two-sum problem, I'd use a hash map approach. I'd iterate through the array once, and for each element, check if the complement (target minus current element) exists in the hash map. If it exists, I return the indices. Otherwise, I store the current element and its index in the hash map. This gives O(n) time complexity and O(n) space complexity, which is optimal.",

    "For designing a URL shortener like bit.ly, I'd start with the requirements - handling millions of URLs, fast redirects, and analytics. I'd use a base62 encoding for short URLs, a SQL database for URL mappings with proper indexing, Redis for caching popular URLs, and implement rate limiting. For scale, I'd use horizontal sharding by URL hash and deploy across multiple regions. I'd also add analytics tracking and implement proper monitoring.",

    "I'm really excited about Apple's focus on innovation and quality. Could you tell me more about the team structure and how engineering teams collaborate across different products? Also, what are some of the most interesting technical challenges the team is currently working on?"
]

class ExtendedInterviewClient:
    """Extended client that includes stakeholder decision functionality"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session_id = None

    async def health_check(self) -> Dict[str, Any]:
        """Check if the API is healthy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def start_interview(self, candidate_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new interview session"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/interview/start",
                json={"candidate_profile": candidate_profile}
            )
            response.raise_for_status()
            result = response.json()
            self.session_id = result.get("session_id")
            return result

    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message during the interview"""
        if not self.session_id:
            raise ValueError("No active session. Start an interview first.")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/interview/turn",
                json={
                    "user_message": message,
                    "session_id": self.session_id
                }
            )
            response.raise_for_status()
            return response.json()

    async def end_interview(self) -> Dict[str, Any]:
        """End the interview and get debrief (Stage 2)"""
        if not self.session_id:
            raise ValueError("No active session. Start an interview first.")

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/interview/end",
                params={"session_id": self.session_id}
            )
            response.raise_for_status()
            return response.json()

    async def generate_stakeholder_decision(self) -> Dict[str, Any]:
        """Generate multi-stakeholder hiring decision (Stage 3)"""
        if not self.session_id:
            raise ValueError("No active session. Complete interview and debrief first.")

        async with httpx.AsyncClient(timeout=180.0) as client:  # Longer timeout for stakeholder analysis
            response = await client.post(
                f"{self.base_url}/interview/stakeholder-decision",
                params={"session_id": self.session_id}
            )
            response.raise_for_status()
            return response.json()

    async def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        if not self.session_id:
            raise ValueError("No active session.")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/interview/session/{self.session_id}"
            )
            response.raise_for_status()
            return response.json()

def print_separator(title: str):
    """Print a formatted separator"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70 + "\n")

def print_stakeholder_report(stakeholder_report: Dict[str, Any]):
    """Print stakeholder report in a readable format"""
    print("👥 MULTI-STAKEHOLDER HIRING DECISION REPORT")
    print("-" * 50)

    # Individual stakeholder decisions
    print("📊 Individual Stakeholder Decisions:")
    print()

    stakeholder_icons = {
        "hiring_manager": "👔",
        "technical_lead": "⚙️",
        "hr_representative": "👥",
        "peer_engineer": "👨‍💻"
    }

    for decision in stakeholder_report["individual_decisions"]:
        stakeholder_type = decision["stakeholder_type"]
        icon = stakeholder_icons.get(stakeholder_type, "📋")

        print(f"{icon} {stakeholder_type.replace('_', ' ').title()}")
        print(f"   Decision: {decision['decision'].upper()} ({decision['confidence_score']}% confidence)")
        print(f"   Reasoning: {decision['reasoning'][:100]}...")
        print(f"   Key Strengths: {', '.join(decision['key_strengths'][:2])}")
        if decision['key_concerns']:
            print(f"   Key Concerns: {', '.join(decision['key_concerns'][:2])}")
        print()

    # Consensus decision
    print("🤝 CONSENSUS DECISION")
    print("-" * 30)
    consensus_decision = stakeholder_report["consensus_decision"]
    confidence = stakeholder_report["consensus_confidence"]

    decision_emoji = {
        "hire": "✅",
        "no_hire": "❌",
        "needs_discussion": "🤔"
    }

    print(f"{decision_emoji.get(consensus_decision, '❓')} Final Decision: {consensus_decision.upper()}")
    print(f"🎯 Consensus Confidence: {confidence}%")
    print(f"📝 Consensus Reasoning: {stakeholder_report['consensus_reasoning'][:200]}...")

    # Consensus metrics
    metrics = stakeholder_report["consensus_metrics"]
    print(f"\n📈 Agreement Level: {metrics['agreement_level']}%")

    if metrics['discussion_points']:
        print(f"💬 Key Discussion Points:")
        for point in metrics['discussion_points'][:3]:
            print(f"   • {point}")

    if metrics['compromise_areas']:
        print(f"🤝 Compromise Areas:")
        for area in metrics['compromise_areas']:
            print(f"   • {area}")

    print(f"\n🎯 Final Recommendation: {stakeholder_report['final_recommendation']}")

async def run_complete_interview_with_stakeholder_decision():
    """Run the complete 3-stage interview process"""
    print_separator("AI Interview Platform - Complete 3-Stage Demo")
    print("🚀 Stages: Interview → Debrief → Multi-Stakeholder Decision")

    client = ExtendedInterviewClient()

    try:
        # Health check
        print("🔍 Checking API health...")
        health = await client.health_check()
        print(f"✅ API Status: {health.get('status', 'unknown')}")

        # Stage 1: Start interview
        print_separator("STAGE 1: Starting Interview")
        print("📋 Candidate Profile:")
        print(f"   Name: {EXAMPLE_CANDIDATE_PROFILE['name']}")
        print(f"   Experience: {EXAMPLE_CANDIDATE_PROFILE['years_of_experience']} years")
        print(f"   Target: {EXAMPLE_CANDIDATE_PROFILE['target_company']} - {EXAMPLE_CANDIDATE_PROFILE['target_role']}")

        print("\n🚀 Starting interview session...")
        start_response = await client.start_interview(EXAMPLE_CANDIDATE_PROFILE)
        print(f"✅ Session started: {client.session_id}")
        print(f"🤖 First question: {start_response['text'][:100]}...")

        # Simulate conversation turns
        print_separator("STAGE 1: Interview Conversation")

        for i, user_message in enumerate(EXAMPLE_RESPONSES, 1):
            print(f"👤 Turn {i}: {user_message[:80]}...")

            # Send message and get response
            response = await client.send_message(user_message)
            print(f"🤖 Response: {response['text'][:80]}...")
            print(f"📊 Phase: {response['current_phase']} | Turn: {response['turn_count']}")
            print()

            # Small delay to simulate conversation
            await asyncio.sleep(0.5)

        # Stage 2: End interview and get debrief
        print_separator("STAGE 2: Interview Debrief")
        print("🏁 Ending interview and generating debrief...")

        debrief_response = await client.end_interview()

        if debrief_response.get("success"):
            debrief = debrief_response["debrief_report"]

            print("📊 DEBRIEF SUMMARY")
            print("-" * 30)
            print(f"Overall Score: {debrief['overall_score']}/100")
            print(f"Summary: {debrief['summary'][:150]}...")

            print(f"\n📈 Phase Scores:")
            for phase_name, phase_data in debrief["phase_breakdown"].items():
                print(f"  • {phase_name}: {phase_data['score']}/100")

            print(f"\n💡 Top Study Recommendations:")
            for rec in debrief["study_recommendations"][:2]:
                print(f"  • [{rec['priority'].upper()}] {rec['topic']}")
        else:
            print("❌ Failed to generate debrief")
            return

        # Stage 3: Multi-Stakeholder Decision
        print_separator("STAGE 3: Multi-Stakeholder Hiring Decision")
        print("👥 Generating stakeholder perspectives and consensus...")
        print("🔄 This may take a moment as we simulate 4 different stakeholders...")

        stakeholder_response = await client.generate_stakeholder_decision()

        if stakeholder_response.get("success"):
            stakeholder_report = stakeholder_response["stakeholder_report"]
            print_stakeholder_report(stakeholder_report)
        else:
            print("❌ Failed to generate stakeholder decision")
            return

        # Summary
        print_separator("🎉 COMPLETE 3-STAGE PROCESS SUMMARY")
        print(f"✅ Interview Completed: {len(EXAMPLE_RESPONSES)} turns")
        print(f"📊 Debrief Score: {debrief['overall_score']}/100")
        print(f"👥 Stakeholder Decision: {stakeholder_report['consensus_decision'].upper()}")
        print(f"🎯 Consensus Confidence: {stakeholder_report['consensus_confidence']}%")

        print("\n🔗 Try these endpoints:")
        print("   📖 API Docs: http://localhost:8000/docs")
        print("   ❤️  Health: http://localhost:8000/health")
        print("   📊 All interview endpoints available!")

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

async def test_stakeholder_decision_only():
    """Test only the stakeholder decision functionality with a mock session"""
    print_separator("Testing Stakeholder Decision Functionality")
    print("⚠️  Note: This test requires an existing interview session")
    print("💡 First run a complete interview, then test this endpoint")

    # This would be used to test just the stakeholder endpoint
    # if you have a session ID from a previous interview
    session_id = input("Enter session ID from previous interview (or press Enter to skip): ").strip()

    if session_id:
        client = ExtendedInterviewClient()
        client.session_id = session_id

        try:
            print("👥 Generating stakeholder decision...")
            stakeholder_response = await client.generate_stakeholder_decision()

            if stakeholder_response.get("success"):
                print_stakeholder_report(stakeholder_response["stakeholder_report"])
            else:
                print("❌ Failed to generate stakeholder decision")

        except Exception as e:
            print(f"❌ Error: {str(e)}")
    else:
        print("⏩ Skipping stakeholder-only test")

if __name__ == "__main__":
    print("🚀 AI Interview Platform - Complete 3-Stage Demo")
    print("📋 This demo shows: Interview → Debrief → Multi-Stakeholder Decision")
    print("\n🔧 Make sure the API server is running on http://localhost:8000")
    print("⚡ Run with: python start_server.bat (in another terminal)")
    print("\nCtrl+C to cancel at any time.")

    # Ask user which test to run
    print("\nChoose test mode:")
    print("1. Complete 3-stage interview process (recommended)")
    print("2. Test stakeholder decision only (needs existing session)")

    choice = input("Enter choice (1 or 2): ").strip()

    try:
        if choice == "2":
            asyncio.run(test_stakeholder_decision_only())
        else:
            asyncio.run(run_complete_interview_with_stakeholder_decision())
    except KeyboardInterrupt:
        print("\n\n❌ Demo cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {str(e)}")