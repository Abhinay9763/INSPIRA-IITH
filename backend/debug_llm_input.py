"""
Debug script to test what the LLM actually receives.
This will show us the exact text being sent to the resume analyst.
"""

import sys
import asyncio
sys.path.append('.')

from utils.pdf_parser import pdf_parser
from utils.groq_client import groq_client

async def test_llm_input():
    """Test what text the resume analyst receives."""
    try:
        # Extract PDF text
        with open(r"C:\Users\sethi\Downloads\Resumé.pdf", 'rb') as f:
            pdf_content = f.read()

        extraction = pdf_parser.extract_from_pdf(pdf_content)
        raw_text = extraction.raw_text

        print("="*60)
        print("🔍 ORIGINAL TEXT (first 1000 characters)")
        print("="*60)
        print(raw_text[:1000])

        # Simulate the truncation logic from resume_analyst.py
        max_chars = 4000
        if len(raw_text) > max_chars:
            print(f"\n⚠️ Text is {len(raw_text)} characters, truncating to {max_chars}")

            contact_section = raw_text[:2000]  # Preserve contact info
            remaining_chars = max_chars - 2000 - 50
            if remaining_chars > 0:
                recent_section = raw_text[-remaining_chars:]
                truncated_text = contact_section + "\n\n[... MIDDLE SECTION TRUNCATED ...]\n\n" + recent_section
            else:
                truncated_text = contact_section
        else:
            truncated_text = raw_text

        print("\n" + "="*60)
        print("📝 TRUNCATED TEXT THAT LLM RECEIVES (first 1000 characters)")
        print("="*60)
        print(truncated_text[:1000])

        # Load the actual prompt template
        prompt_template = groq_client.load_prompt_template("resume_analyst.txt")
        full_prompt = f"{prompt_template}\n\n{truncated_text}"

        print("\n" + "="*60)
        print("🤖 FULL PROMPT TO LLM (first 1500 characters)")
        print("="*60)
        print(full_prompt[:1500])

        # Test a simple extraction manually
        print("\n" + "="*60)
        print("🔍 MANUAL PATTERN DETECTION")
        print("="*60)

        import re

        # Test name extraction patterns
        name_patterns = [
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',  # First line capitalized name
            r'([A-Z][a-z]+\s+[A-Z][a-z]+\s+[A-Z][a-z]+)',       # Three-part name
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',                      # Two-part name
        ]

        for i, pattern in enumerate(name_patterns):
            matches = re.findall(pattern, truncated_text, re.MULTILINE)
            if matches:
                print(f"Name pattern {i+1}: {matches[0]}")

        # Test email pattern
        email_matches = re.findall(r'\b\w+@\w+\.\w{2,}\b', truncated_text)
        if email_matches:
            print(f"Email found: {email_matches[0]}")

        # Test phone pattern
        phone_matches = re.findall(r'[\+]?[\d\s\-\(\)]{10,}', truncated_text)
        if phone_matches:
            print(f"Phone candidates: {phone_matches[:3]}")

        # Check if contact info is in the first few lines
        lines = truncated_text.split('\n')
        print(f"\nFirst 10 lines of text:")
        for i, line in enumerate(lines[:10]):
            print(f"{i+1:2d}: {line}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_llm_input())