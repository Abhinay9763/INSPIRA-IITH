"""
Quick debug script to test PDF text extraction.
Run this to see the raw text extracted from your resume PDF.
"""

import sys
import os
sys.path.append('.')

from .utils.pdf_parser import pdf_parser

def find_resume_file():
    """Find a PDF file in common locations."""
    possible_paths = [
        # User's specific resume path
        r"C:\Users\sethi\Downloads\Resumé.pdf",

        # Standard locations
        "resume.pdf",
        "../resume.pdf",
        "resume/resume.pdf",
        "../resume/resume.pdf",
    ]

    # Look for any PDF file in resume directory
    if os.path.exists("resume"):
        for file in os.listdir("resume"):
            if file.endswith('.pdf'):
                possible_paths.insert(0, f"resume/{file}")

    if os.path.exists("../resume"):
        for file in os.listdir("../resume"):
            if file.endswith('.pdf'):
                possible_paths.insert(0, f"../resume/{file}")

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None

def test_pdf_extraction(pdf_path):
    """Test PDF extraction and show results."""
    try:
        print(f"🔍 Testing PDF extraction from: {pdf_path}")

        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()

        print(f"📄 PDF file size: {len(pdf_content):,} bytes")

        extraction = pdf_parser.extract_from_pdf(pdf_content)

        print("\n" + "="*60)
        print("📝 RAW TEXT EXTRACTED FROM PDF")
        print("="*60)
        print(f"Text length: {len(extraction.raw_text):,} characters")

        if len(extraction.raw_text) > 1000:
            print("\n📍 First 500 characters:")
            print("-" * 40)
            print(extraction.raw_text[:500])
            print("-" * 40)

            print("\n📍 Next 500 characters:")
            print("-" * 40)
            print(extraction.raw_text[500:1000])
            print("-" * 40)
        else:
            print("\n📍 Complete text:")
            print("-" * 40)
            print(extraction.raw_text)
            print("-" * 40)

        print("\n" + "="*60)
        print("🔗 URLS FOUND")
        print("="*60)
        print(f"URLs found: {len(extraction.urls)}")

        if extraction.urls:
            for i, url in enumerate(extraction.urls, 1):
                print(f"{i:2d}. {url}")
        else:
            print("❌ No URLs found")

        # Check for common contact patterns
        print("\n" + "="*60)
        print("🔍 CONTACT PATTERN ANALYSIS")
        print("="*60)

        text_lower = extraction.raw_text.lower()

        # Check for email patterns
        import re
        emails = re.findall(r'\b\w+@\w+\.\w{2,}\b', extraction.raw_text)
        print(f"Email patterns found: {len(emails)}")
        for email in emails[:3]:  # Show first 3
            print(f"  📧 {email}")

        # Check for phone patterns
        phones = re.findall(r'[\(]?\d{3}[\)]?[-.\s]?\d{3}[-.\s]?\d{4}', extraction.raw_text)
        print(f"Phone patterns found: {len(phones)}")
        for phone in phones[:3]:  # Show first 3
            print(f"  📞 {phone}")

        # Check for GitHub mentions
        if 'github' in text_lower:
            print("✅ 'github' text found in resume")
        else:
            print("❌ 'github' not found in text")

        # Check for LinkedIn mentions
        if 'linkedin' in text_lower:
            print("✅ 'linkedin' text found in resume")
        else:
            print("❌ 'linkedin' not found in text")

        print("\n" + "="*60)
        print("✅ DEBUG COMPLETE")
        print("="*60)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    # Try to find resume automatically
    pdf_path = find_resume_file()

    if not pdf_path:
        print("❌ No PDF resume found!")
        print("Please put your resume PDF in one of these locations:")
        print("  - backend/resume/your_resume.pdf")
        print("  - resume/your_resume.pdf")
        print("  - backend/resume.pdf")
        print("  - resume.pdf")
        print("\nOr specify the path manually in the script.")
        sys.exit(1)

    test_pdf_extraction(pdf_path)