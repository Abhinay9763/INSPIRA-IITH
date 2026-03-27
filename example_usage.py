"""
Example usage of the AI Interview Preparation Platform - Stage 2 API
This script demonstrates how to conduct a complete mock interview session.
"""

import asyncio
import json
import time
from typing import Dict, Any
import httpx

# API Configuration
BASE_URL = "http://localhost:8000"

# Example candidate profile from Stage 1
EXAMPLE_CANDIDATE_PROFILE = {
    "name": "John Doe",
    "email": "john.doe@email.com",
    "years_of_experience": 3,
    "target_company": "Google",
    "target_role": "Software Engineer",
    "skills": [
        "Python", "JavaScript", "React", "Node.js",
        "PostgreSQL", "Docker", "AWS", "Git"
    ],
    "experience": [
        {
            "title": "Software Engineer",
            "company": "TechCorp Inc",
            "duration": "2021-2024",
            "description": "Built web applications using React and Node.js"
        },
        {
            "title": "Junior Developer",
            "company": "StartupXYZ",
            "duration": "2020-2021",
            "description": "Developed REST APIs and worked with databases"
        }
    ],
    "education": {
        "degree": "Bachelor of Computer Science",
        "university": "State University",
        "graduation_year": 2020
    },
    "projects": [
        {
            "name": "E-commerce Platform",
            "technologies": ["React", "Node.js", "PostgreSQL"],
            "description": "Full-stack web application for online shopping"
        }
    ]
}

# Example interview conversation
EXAMPLE_RESPONSES = [
    "Hi! I'm John, I'm a software engineer with about 3 years of experience working primarily with web technologies like React and Node.js.",

    "Sure! At TechCorp, I worked on building customer-facing web applications. I was responsible for both frontend development using React and backend API development with Node.js. I also worked with PostgreSQL databases and deployed applications using Docker and AWS.",

    "One of the projects I'm most proud of is an e-commerce platform I built. It was a full-stack application where customers could browse products, add items to cart, and complete purchases. I used React for the frontend, Node.js with Express for the backend APIs, and PostgreSQL for data storage. The challenging part was implementing the payment processing system and ensuring the application could handle concurrent orders safely.",

    "I'd use a hash table approach. I'd iterate through the array once, and for each number, I'd check if the complement (target minus current number) exists in the hash table. If it does, I found the pair. If not, I'd add the current number and its index to the hash table. This gives us O(n) time complexity and O(n) space complexity.",

    "Great question! I'd consider the scale first. For the data layer, I'd probably use a combination of SQL databases for transactional data and NoSQL for product catalogs. I'd implement caching with Redis, use a load balancer to distribute traffic, and design the system with microservices for scalability. For high availability, I'd deploy across multiple regions with database replication.",

    "I'm curious about the engineering culture here and what a typical day looks like for someone in this role. Also, what are the biggest technical challenges the team is currently facing?"
]

class InterviewClient:
    """Client for interacting with the Interview API"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session_id = None

    async def health_check(self) -> Dict[str, Any]:
        """Check if the API is healthy"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()

    async def start_interview(
        self,
        candidate_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Start a new interview session"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/interview/start",
                json={
                    "candidate_profile": candidate_profile
                }
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
        """End the interview and get debrief"""
        if not self.session_id:
            raise ValueError("No active session. Start an interview first.")

        async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for debrief
            response = await client.post(
                f"{self.base_url}/interview/end",
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
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60 + "\n")

def print_response(response: Dict[str, Any], show_audio: bool = False):
    """Print API response in a readable format"""
    if "text" in response:
        print("🤖 Interviewer:")
        print(f"   {response['text']}")

        if "current_phase" in response:
            print(f"\n📊 Phase: {response['current_phase']} | Turn: {response.get('turn_count', 'N/A')}")

        if show_audio and response.get("audio"):
            print(f"🔊 Audio: {len(response['audio'])} characters (base64)")

    print()

async def run_example_interview():
    """Run a complete example interview"""
    print_separator("AI Interview Preparation Platform - Stage 2 Demo")

    client = InterviewClient()

    try:
        # Health check
        print("🔍 Checking API health...")
        health = await client.health_check()
        print(f"✅ API Status: {health.get('status', 'unknown')}")

        # Start interview
        print_separator("Starting Interview")
        print("📋 Using example candidate profile:")
        print(json.dumps(EXAMPLE_CANDIDATE_PROFILE, indent=2)[:500] + "...")

        print("\n🚀 Starting interview session...")
        start_response = await client.start_interview(
            EXAMPLE_CANDIDATE_PROFILE
        )

        print(f"✅ Session started: {client.session_id}")
        print_response(start_response, show_audio=True)

        # Simulate conversation
        print_separator("Interview Conversation")

        for i, user_message in enumerate(EXAMPLE_RESPONSES, 1):
            print(f"👤 User (Turn {i}):")
            print(f"   {user_message}")
            print()

            # Add slight delay to simulate real conversation
            await asyncio.sleep(1)

            # Send message and get response
            response = await client.send_message(user_message)
            print_response(response)

            # Check session info occasionally
            if i == 3:
                session_info = await client.get_session_info()
                print(f"📊 Session Info: Phase {session_info['current_phase']}, "
                      f"Turn {session_info['turn_count']}")
                print()

            # Add delay between turns
            await asyncio.sleep(2)

        # End interview and get debrief
        print_separator("Ending Interview & Getting Debrief")
        print("🏁 Ending interview and generating debrief...")

        debrief_response = await client.end_interview()

        if debrief_response.get("success"):
            debrief = debrief_response["debrief_report"]

            print("📊 INTERVIEW DEBRIEF REPORT")
            print("-" * 40)
            print(f"Overall Score: {debrief['overall_score']}/100")
            print(f"\nSummary: {debrief['summary'][:200]}...")

            print(f"\n📈 Phase Breakdown:")
            for phase_name, phase_data in debrief["phase_breakdown"].items():
                print(f"  • {phase_name}: {phase_data['score']}/100")

            print(f"\n💡 Study Recommendations ({len(debrief['study_recommendations'])}):")
            for rec in debrief["study_recommendations"][:3]:  # Show top 3
                print(f"  • [{rec['priority'].upper()}] {rec['topic']}")

            print(f"\n📝 Conversation History: {len(debrief['conversation_history'])} turns")

        else:
            print("❌ Failed to generate debrief")

        print_separator("Demo Complete")
        print("✅ Interview demo completed successfully!")
        print("\n🔗 API Documentation: http://localhost:8000/docs")
        print("📊 Health Check: http://localhost:8000/health")

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Starting AI Interview Demo...")
    print("Make sure the API server is running on http://localhost:8000")
    print("\nCtrl+C to cancel at any time.")

    try:
        asyncio.run(run_example_interview())
    except KeyboardInterrupt:
        print("\n\n❌ Demo cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {str(e)}")