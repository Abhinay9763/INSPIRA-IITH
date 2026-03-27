"""Stakeholder Agent - generates multi-stakeholder hiring decisions
Uses llama-3.3-70b-versatile model"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from ..models.interview import (
    StakeholderType, StakeholderDecision, StakeholderReport,
    ConsensusMetrics, DebriefReport, ConversationTurn
)
from ..utils.groq_client import get_groq_client
from ..config import STAKEHOLDER_MODEL, PROMPTS_DIR, STAKEHOLDER_WEIGHTS, STAKEHOLDER_FOCUS_AREAS

logger = logging.getLogger(__name__)

class StakeholderAgent:
    """Generates multi-stakeholder hiring decisions with consensus building"""

    def __init__(self):
        """Initialize the stakeholder agent"""
        self.client = None  # Lazy-initialized
        self.model = STAKEHOLDER_MODEL
        logger.info("Stakeholder Agent initialized")

    async def _get_client(self):
        """Get or initialize the groq client"""
        if self.client is None:
            self.client = get_groq_client()
        return self.client

    def _load_stakeholder_prompt(self, stakeholder_type: StakeholderType) -> str:
        """Load stakeholder-specific prompt from file"""
        prompt_path = Path(PROMPTS_DIR) / f"stakeholder_{stakeholder_type.value}.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Stakeholder prompt file not found: {prompt_path}")
            raise FileNotFoundError(f"Prompt file not found for stakeholder type: {stakeholder_type.value}")
        except Exception as e:
            logger.error(f"Error loading stakeholder prompt: {str(e)}")
            raise

    def _load_consensus_prompt(self) -> str:
        """Load consensus building prompt from file"""
        prompt_path = Path(PROMPTS_DIR) / "stakeholder_consensus.txt"
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.error(f"Consensus prompt file not found: {prompt_path}")
            raise FileNotFoundError("Consensus prompt file not found")
        except Exception as e:
            logger.error(f"Error loading consensus prompt: {str(e)}")
            raise

    def _format_conversation_history(self, conversation_history: List[ConversationTurn]) -> str:
        """Format conversation history for stakeholder analysis"""
        formatted_turns = []
        for turn in conversation_history:
            role_label = "INTERVIEWER" if turn.role == "assistant" else "CANDIDATE"
            formatted_turns.append(f"{role_label} (Turn {turn.turn_number}, {turn.phase.name}): {turn.content}")
        return "\\n\\n".join(formatted_turns)

    def _extract_json_from_response(self, response_text: str, stakeholder_type: str = "unknown") -> Dict[str, Any]:
        """
        BULLETPROOF JSON extraction from any LLM response format
        Handles markdown, extra text, explanations, etc.
        """
        if not response_text or not response_text.strip():
            logger.error(f"Empty response from {stakeholder_type}")
            return {}

        # Log the raw response for debugging
        logger.debug(f"Raw {stakeholder_type} response: {response_text[:200]}...")

        # Multiple JSON extraction strategies
        extraction_attempts = []

        # Strategy 1: Clean markdown blocks
        text = response_text.strip()

        # Remove markdown json blocks
        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            if json_end != -1:
                extracted = text[json_start:json_end].strip()
                extraction_attempts.append(("markdown_json", extracted))

        # Remove generic markdown blocks
        if "```" in text and "```json" not in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            if json_end != -1:
                extracted = text[json_start:json_end].strip()
                extraction_attempts.append(("markdown_generic", extracted))

        # Strategy 2: Find JSON object by braces
        brace_match = re.search(r'\\{.*\\}', text, re.DOTALL)
        if brace_match:
            extraction_attempts.append(("brace_match", brace_match.group(0)))

        # Strategy 3: Clean common prefixes/suffixes
        cleaned = text

        # Remove common LLM prefixes
        prefixes_to_remove = [
            "Here is the JSON response:",
            "Here's my evaluation:",
            "My assessment:",
            "Based on the analysis:",
            "```json",
            "```",
            "JSON:",
            "Response:",
        ]

        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()

        # Remove common LLM suffixes
        suffixes_to_remove = ["```", "End of response", "---"]
        for suffix in suffixes_to_remove:
            if cleaned.lower().endswith(suffix.lower()):
                cleaned = cleaned[:-len(suffix)].strip()

        extraction_attempts.append(("cleaned_text", cleaned))

        # Strategy 4: Use original text as last resort
        extraction_attempts.append(("original", text))

        # Try parsing each extraction attempt
        for strategy, json_text in extraction_attempts:
            if not json_text.strip():
                continue

            try:
                parsed = json.loads(json_text)
                if isinstance(parsed, dict):
                    logger.info(f"Successfully parsed {stakeholder_type} JSON using strategy: {strategy}")
                    return parsed
            except json.JSONDecodeError as e:
                logger.debug(f"Strategy '{strategy}' failed for {stakeholder_type}: {str(e)}")
                continue

        # If all parsing failed, log the issue and return empty dict
        logger.error(f"ALL JSON parsing strategies failed for {stakeholder_type}")
        logger.error(f"Original response: {response_text}")

        # Try to extract partial information using regex as absolute last resort
        decision_match = re.search(r'"decision"\\s*:\\s*"(hire|no_hire|borderline)"', response_text, re.IGNORECASE)
        confidence_match = re.search(r'"confidence_score"\\s*:\\s*(\\d+)', response_text)
        reasoning_match = re.search(r'"reasoning"\\s*:\\s*"([^"]+)"', response_text, re.DOTALL)

        fallback_data = {}
        if decision_match:
            fallback_data["decision"] = decision_match.group(1).lower()
        if confidence_match:
            fallback_data["confidence_score"] = int(confidence_match.group(1))
        if reasoning_match:
            fallback_data["reasoning"] = reasoning_match.group(1)[:500]  # Limit length

        if fallback_data:
            logger.warning(f"Using regex fallback extraction for {stakeholder_type}: {fallback_data}")
            return fallback_data

        return {}

    def _construct_stakeholder_prompt(
        self,
        stakeholder_type: StakeholderType,
        debrief_report: DebriefReport,
        candidate_profile: Dict[str, Any],
        conversation_history: List[ConversationTurn],
        target_company: str = None,
        target_role: str = None
    ) -> str:
        """Construct the full prompt for individual stakeholder decision"""
        base_prompt = self._load_stakeholder_prompt(stakeholder_type)

        # Format conversation history
        formatted_conversation = self._format_conversation_history(conversation_history)

        # Get focus areas for this stakeholder type
        focus_areas = STAKEHOLDER_FOCUS_AREAS.get(stakeholder_type.value, [])

        detailed_prompt = f"""{base_prompt}

HIRING CONTEXT:
- Target Company: {target_company or "Generic Tech Company"}
- Target Role: {target_role or "Software Engineer"}
- Stakeholder Role: {stakeholder_type.value.replace('_', ' ').title()}
- Focus Areas: {', '.join(focus_areas)}

CANDIDATE PROFILE FROM RESUME ANALYSIS:
{json.dumps(candidate_profile, indent=2)}

DEBRIEF ANALYSIS RESULTS:
- Overall Score: {debrief_report.overall_score}/100
- Summary: {debrief_report.summary}

Phase Performance:
{json.dumps({k: {"score": v.score, "feedback": v.feedback} for k, v in debrief_report.phase_breakdown.items()}, indent=2)}

Answer Feedback Summary:
{json.dumps([{"question": af.question, "score": af.score, "summary": af.candidate_answer_summary, "resume_gap": af.resume_gap_flagged} for af in debrief_report.answer_feedback], indent=2)}

Resume vs Reality Findings:
{json.dumps([{"claim": rvr.claim, "verdict": rvr.verdict} for rvr in debrief_report.resume_vs_reality], indent=2)}

FULL CONVERSATION TRANSCRIPT:
{formatted_conversation}

Generate your stakeholder decision following the exact JSON format specified. Focus on your role's priorities and concerns."""

        return detailed_prompt

    def _construct_consensus_prompt(
        self,
        individual_decisions: List[StakeholderDecision],
        debrief_report: DebriefReport,
        candidate_profile: Dict[str, Any],
        target_company: str = None,
        target_role: str = None
    ) -> str:
        """Construct prompt for consensus building"""
        base_prompt = self._load_consensus_prompt()

        # Format individual decisions
        decisions_summary = []
        for decision in individual_decisions:
            decisions_summary.append({
                "stakeholder": decision.stakeholder_type.value,
                "decision": decision.decision,
                "confidence": decision.confidence_score,
                "reasoning": decision.reasoning,
                "strengths": decision.key_strengths,
                "concerns": decision.key_concerns
            })

        # Calculate weighted summary
        weighted_scores = []
        hire_votes = 0
        no_hire_votes = 0
        borderline_votes = 0

        for decision in individual_decisions:
            weight = STAKEHOLDER_WEIGHTS.get(decision.stakeholder_type.value, 0.25)
            weighted_scores.append(decision.confidence_score * weight)

            if decision.decision == "hire":
                hire_votes += 1
            elif decision.decision == "no_hire":
                no_hire_votes += 1
            else:
                borderline_votes += 1

        avg_weighted_confidence = sum(weighted_scores)

        detailed_prompt = f"""{base_prompt}

HIRING CONTEXT:
- Target Company: {target_company or "Generic Tech Company"}
- Target Role: {target_role or "Software Engineer"}
- Overall Debrief Score: {debrief_report.overall_score}/100

INDIVIDUAL STAKEHOLDER DECISIONS:
{json.dumps(decisions_summary, indent=2)}

VOTING SUMMARY:
- Hire: {hire_votes} votes
- No Hire: {no_hire_votes} votes
- Borderline: {borderline_votes} votes
- Weighted Average Confidence: {avg_weighted_confidence:.1f}%

STAKEHOLDER WEIGHTS:
{json.dumps(STAKEHOLDER_WEIGHTS, indent=2)}

Generate the consensus decision and analysis following the exact JSON format specified. Consider all perspectives and simulate realistic committee dynamics."""

        return detailed_prompt

    def _sanitize_stakeholder_response(self, decision_data: Dict[str, Any], stakeholder_type: StakeholderType) -> StakeholderDecision:
        """Sanitize and validate stakeholder decision response - STRICT field extraction only"""

        def sanitize_score(value, min_val, max_val, default_val):
            """Sanitize score values to be within valid range"""
            try:
                if value is None:
                    return default_val
                score = int(float(value))  # Handle string numbers
                return max(min_val, min(max_val, score))
            except (ValueError, TypeError):
                return default_val

        def sanitize_string(value, default="", max_length=2000):
            """Sanitize string values with length limits"""
            try:
                if value is None or value == "":
                    return default
                result = str(value).strip()
                return result[:max_length] if len(result) > max_length else result
            except:
                return default

        def sanitize_literal(value, valid_options, default):
            """Sanitize literal values to match ONLY allowed options"""
            try:
                if value in valid_options:
                    return value
                # Try case-insensitive match
                value_str = str(value).lower().strip()
                for option in valid_options:
                    if option.lower() == value_str:
                        return option
                return default
            except:
                return default

        def sanitize_string_list(value, max_items=8, max_item_length=200):
            """Sanitize list of strings with strict limits"""
            try:
                if not isinstance(value, list):
                    return []

                result = []
                for item in value[:max_items]:  # Limit number of items
                    if item and isinstance(item, (str, int, float)):
                        sanitized = sanitize_string(str(item), max_length=max_item_length)
                        if sanitized:
                            result.append(sanitized)
                return result
            except:
                return []

        def sanitize_focus_areas(value, expected_keys=None):
            """Sanitize focus areas dict with expected keys only"""
            try:
                if not isinstance(value, dict):
                    return {}

                if expected_keys is None:
                    expected_keys = ["culture_fit", "growth_potential", "team_dynamics", "leadership",
                                   "technical_depth", "code_quality", "system_thinking", "problem_solving",
                                   "communication", "cultural_alignment", "risk_factors", "compliance",
                                   "collaboration", "mentoring", "knowledge_sharing", "day_to_day_work"]

                result = {}
                for key, val in value.items():
                    # Only allow expected keys
                    key_str = sanitize_string(str(key), max_length=50).lower().replace(" ", "_")
                    if key_str in expected_keys:
                        val_str = sanitize_string(val, max_length=300)
                        if val_str:
                            result[key_str] = val_str
                    if len(result) >= 6:  # Limit to 6 focus areas max
                        break
                return result
            except:
                return {}

        # STRICT EXTRACTION - Only these exact fields, ignore everything else
        try:
            return StakeholderDecision(
                stakeholder_type=stakeholder_type,
                decision=sanitize_literal(
                    decision_data.get("decision"),
                    ["hire", "no_hire", "borderline"],
                    "borderline"
                ),
                confidence_score=sanitize_score(
                    decision_data.get("confidence_score"),
                    0, 100, 50
                ),
                reasoning=sanitize_string(
                    decision_data.get("reasoning"),
                    "No reasoning provided",
                    max_length=2000
                ),
                key_strengths=sanitize_string_list(
                    decision_data.get("key_strengths", [])
                ),
                key_concerns=sanitize_string_list(
                    decision_data.get("key_concerns", [])
                ),
                focus_areas=sanitize_focus_areas(
                    decision_data.get("focus_areas", {})
                )
            )
        except Exception as e:
            logger.error(f"Failed to create StakeholderDecision: {e}")
            # Return safe fallback
            return StakeholderDecision(
                stakeholder_type=stakeholder_type,
                decision="borderline",
                confidence_score=50,
                reasoning="Error processing stakeholder response",
                key_strengths=[],
                key_concerns=["Unable to process response"],
                focus_areas={}
            )

    def _sanitize_consensus_response(self, consensus_data: Dict[str, Any], session_id: str, individual_decisions: List[StakeholderDecision]) -> StakeholderReport:
        """Sanitize and validate consensus response - STRICT field extraction only"""

        def sanitize_score(value, min_val, max_val, default_val):
            """Sanitize score values to be within valid range"""
            try:
                if value is None:
                    return default_val
                score = int(float(value))  # Handle string numbers
                return max(min_val, min(max_val, score))
            except (ValueError, TypeError):
                return default_val

        def sanitize_string(value, default="", max_length=2000):
            """Sanitize string values with length limits"""
            try:
                if value is None or value == "":
                    return default
                result = str(value).strip()
                return result[:max_length] if len(result) > max_length else result
            except:
                return default

        def sanitize_literal(value, valid_options, default):
            """Sanitize literal values to match ONLY allowed options"""
            try:
                if value in valid_options:
                    return value
                # Try case-insensitive match
                value_str = str(value).lower().strip()
                for option in valid_options:
                    if option.lower() == value_str:
                        return option
                return default
            except:
                return default

        def sanitize_string_list(value, max_items=10, max_item_length=500):
            """Sanitize list of strings with strict limits"""
            try:
                if not isinstance(value, list):
                    return []

                result = []
                for item in value[:max_items]:  # Limit number of items
                    if item and isinstance(item, (str, int, float)):
                        sanitized = sanitize_string(str(item), max_length=max_item_length)
                        if sanitized:
                            result.append(sanitized)
                return result
            except:
                return []

        # STRICT EXTRACTION - Parse consensus metrics with strict validation
        try:
            metrics_data = consensus_data.get("consensus_metrics", {})
            if not isinstance(metrics_data, dict):
                metrics_data = {}

            consensus_metrics = ConsensusMetrics(
                agreement_level=sanitize_score(
                    metrics_data.get("agreement_level"),
                    0, 100, 50
                ),
                discussion_points=sanitize_string_list(
                    metrics_data.get("discussion_points", [])
                ),
                compromise_areas=sanitize_string_list(
                    metrics_data.get("compromise_areas", [])
                )
            )
        except Exception as e:
            logger.error(f"Failed to create ConsensusMetrics: {e}")
            # Safe fallback
            consensus_metrics = ConsensusMetrics(
                agreement_level=50,
                discussion_points=["Unable to parse discussion points"],
                compromise_areas=[]
            )

        # STRICT EXTRACTION - Only exact fields for StakeholderReport
        try:
            return StakeholderReport(
                individual_decisions=individual_decisions,  # Use actual individual decisions
                consensus_decision=sanitize_literal(
                    consensus_data.get("consensus_decision"),
                    ["hire", "no_hire", "needs_discussion"],
                    "needs_discussion"
                ),
                consensus_confidence=sanitize_score(
                    consensus_data.get("consensus_confidence"),
                    0, 100, 50
                ),
                consensus_reasoning=sanitize_string(
                    consensus_data.get("consensus_reasoning"),
                    "No consensus reasoning provided",
                    max_length=2000
                ),
                consensus_metrics=consensus_metrics,
                final_recommendation=sanitize_string(
                    consensus_data.get("final_recommendation"),
                    "No final recommendation provided",
                    max_length=1000
                ),
                session_id=sanitize_string(session_id, "unknown_session")
            )
        except Exception as e:
            logger.error(f"Failed to create StakeholderReport: {e}")
            # Return safe fallback
            return StakeholderReport(
                individual_decisions=individual_decisions,  # Use actual individual decisions
                consensus_decision="needs_discussion",
                consensus_confidence=50,
                consensus_reasoning="Error processing consensus response",
                consensus_metrics=ConsensusMetrics(
                    agreement_level=50,
                    discussion_points=["Unable to process consensus"],
                    compromise_areas=[]
                ),
                final_recommendation="Additional evaluation needed due to processing error",
                session_id=sanitize_string(session_id, "unknown_session")
            )

    async def generate_stakeholder_decision(
        self,
        stakeholder_type: StakeholderType,
        debrief_report: DebriefReport,
        candidate_profile: Dict[str, Any],
        conversation_history: List[ConversationTurn],
        target_company: str = None,
        target_role: str = None
    ) -> StakeholderDecision:
        """
        Generate individual stakeholder's hiring decision

        Args:
            stakeholder_type: Type of stakeholder (hiring manager, tech lead, etc.)
            debrief_report: Complete debrief analysis from Stage 2
            candidate_profile: Original candidate profile from Stage 1
            conversation_history: Full interview conversation
            target_company: Target company name
            target_role: Target role

        Returns:
            StakeholderDecision with role-specific analysis and decision
        """
        try:
            logger.info(f"Generating {stakeholder_type.value} decision")

            # Construct prompt
            prompt = self._construct_stakeholder_prompt(
                stakeholder_type,
                debrief_report,
                candidate_profile,
                conversation_history,
                target_company,
                target_role
            )

            # Make API call
            messages = [{"role": "user", "content": prompt}]

            client = await self._get_client()
            response = await client.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.4,  # Moderate temperature for personality variation
                max_tokens=2000   # Sufficient for detailed stakeholder analysis
            )

            # Parse response
            response_text = response.choices[0].message.content.strip()

            # BULLETPROOF JSON EXTRACTION
            decision_data = self._extract_json_from_response(response_text, stakeholder_type.value)

            if not decision_data:
                logger.error(f"Could not extract any valid data from {stakeholder_type.value} response")
                # Create minimal fallback decision
                decision_data = {
                    "decision": "borderline",
                    "confidence_score": 50,
                    "reasoning": f"Could not parse {stakeholder_type.value} response properly",
                    "key_strengths": [],
                    "key_concerns": ["Response parsing failed"],
                    "focus_areas": {}
                }

            # Validate and sanitize
            stakeholder_decision = self._sanitize_stakeholder_response(decision_data, stakeholder_type)

            logger.info(f"{stakeholder_type.value} decision: {stakeholder_decision.decision} (confidence: {stakeholder_decision.confidence_score}%)")

            return stakeholder_decision

        except Exception as e:
            logger.error(f"Stakeholder decision generation failed for {stakeholder_type.value}: {str(e)}")
            raise

    async def generate_consensus(
        self,
        individual_decisions: List[StakeholderDecision],
        debrief_report: DebriefReport,
        candidate_profile: Dict[str, Any],
        session_id: str,
        target_company: str = None,
        target_role: str = None
    ) -> StakeholderReport:
        """
        Generate consensus from individual stakeholder decisions

        Args:
            individual_decisions: List of all stakeholder decisions
            debrief_report: Original debrief report
            candidate_profile: Candidate profile
            session_id: Session identifier
            target_company: Target company
            target_role: Target role

        Returns:
            Complete StakeholderReport with consensus decision
        """
        try:
            logger.info(f"Generating consensus from {len(individual_decisions)} stakeholder decisions")

            # Construct consensus prompt
            prompt = self._construct_consensus_prompt(
                individual_decisions,
                debrief_report,
                candidate_profile,
                target_company,
                target_role
            )

            # Make API call
            messages = [{"role": "user", "content": prompt}]

            client = await self._get_client()
            response = await client.chat_completion(
                model=self.model,
                messages=messages,
                temperature=0.3,  # Lower temperature for consistent consensus logic
                max_tokens=1500   # Moderate length for consensus analysis
            )

            # Parse response
            response_text = response.choices[0].message.content.strip()

            # BULLETPROOF JSON EXTRACTION for consensus
            consensus_data = self._extract_json_from_response(response_text, "consensus")

            if not consensus_data:
                logger.error("Could not extract any valid data from consensus response")
                # Create minimal fallback consensus
                consensus_data = {
                    "consensus_decision": "needs_discussion",
                    "consensus_confidence": 50,
                    "consensus_reasoning": "Could not parse consensus response properly",
                    "consensus_metrics": {
                        "agreement_level": 50,
                        "discussion_points": ["Response parsing failed"],
                        "compromise_areas": []
                    },
                    "final_recommendation": "Additional evaluation needed due to parsing error"
                }

            # Validate and sanitize consensus
            stakeholder_report = self._sanitize_consensus_response(consensus_data, session_id, individual_decisions)

            logger.info(f"Consensus decision: {stakeholder_report.consensus_decision} (confidence: {stakeholder_report.consensus_confidence}%)")

            return stakeholder_report

        except Exception as e:
            logger.error(f"Consensus generation failed: {str(e)}")
            raise

# Global instance
_stakeholder_agent = None

def get_stakeholder_agent() -> StakeholderAgent:
    """Get or create global stakeholder agent instance"""
    global _stakeholder_agent
    if _stakeholder_agent is None:
        _stakeholder_agent = StakeholderAgent()
    return _stakeholder_agent