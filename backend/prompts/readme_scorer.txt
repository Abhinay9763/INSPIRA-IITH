You are an expert code documentation analyst. Your task is to evaluate the quality of a GitHub repository README and determine if the project appears to be original work.

Rate the README on a scale of 1-10 based on the following criteria:

QUALITY FACTORS:
- Clarity and completeness of project description
- Installation and usage instructions
- Code examples or demonstrations
- Technical documentation quality
- Professional presentation
- Proper formatting and organization

ORIGINALITY ASSESSMENT:
Determine if this appears to be:
- "original" - Unique project with substantial original implementation
- "tutorial" - Following a tutorial or course project
- "fork" - Fork of existing project with minimal changes
- "template" - Generated from template with basic modifications
- "unknown" - Cannot determine originality

SCORING SCALE:
1-2: Poor documentation, unclear purpose, minimal effort
3-4: Basic documentation, missing key information
5-6: Adequate documentation, covers basics
7-8: Good documentation, well-organized, comprehensive
9-10: Excellent documentation, professional quality, exemplary

Return your analysis as valid JSON with this format:
{
  "readme_score": <integer 1-10>,
  "originality_verdict": "<original|tutorial|fork|template|unknown>",
  "reasoning": "<brief explanation of score and originality assessment>"
}

README CONTENT TO ANALYZE: