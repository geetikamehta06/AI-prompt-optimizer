"""
Prompt Analyzer — detects intent, classifies type, and identifies weaknesses.

This is the first stage of the enhancement pipeline. It takes a raw prompt
and produces a comprehensive analysis that informs framework selection.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models.prompt import PromptAnalysis, PromptType, PromptIntent
from ..providers.base import BaseProvider
from ..utils.logging_setup import get_logger
from ..utils.helpers import Timer

logger = get_logger(__name__)


class _AnalysisSchema(BaseModel):
    """Schema for structured AI analysis output."""
    prompt_type: str = "general"
    intent: str = "other"
    detected_domain: str = "general"
    target_audience: str = "general"
    complexity: str = "moderate"
    weaknesses: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    key_entities: list[str] = Field(default_factory=list)
    summary: str = ""


_ANALYSIS_SYSTEM_PROMPT = """You are an expert prompt engineering analyst. Your job is to analyze raw prompts and identify their characteristics, strengths, and weaknesses.

You must be thorough but concise. Focus on actionable insights that will help improve the prompt."""

_ANALYSIS_PROMPT = """Analyze the following prompt and provide a comprehensive assessment.

PROMPT TO ANALYZE:
\"\"\"
{raw_prompt}
\"\"\"

Provide your analysis as JSON with these fields:
- prompt_type: one of [creative, technical, analytical, strategic, conversational, instructional, persuasive, investigative, operational, general]
- intent: one of [generate, analyze, transform, explain, summarize, compare, decide, debug, plan, create, evaluate, brainstorm, other]
- detected_domain: the domain this prompt relates to (e.g., "software engineering", "marketing", "finance")
- target_audience: who the output seems intended for
- complexity: one of [simple, moderate, complex]
- weaknesses: list of specific weaknesses (e.g., "lacks context", "ambiguous action verb", "no output format specified")
- strengths: list of what the prompt does well
- missing_elements: list of important elements that are missing (e.g., "no role specified", "missing constraints", "no examples provided")
- key_entities: important entities/concepts mentioned in the prompt
- summary: 1-2 sentence summary of what the prompt is trying to accomplish"""


class PromptAnalyzer:
    """Analyzes raw prompts to detect intent, type, and weaknesses.
    
    Uses AI to semantically understand the prompt and produce
    structured analysis that informs framework selection.
    """

    def __init__(self, provider: BaseProvider) -> None:
        self._provider = provider

    async def analyze(self, raw_prompt: str) -> PromptAnalysis:
        """Analyze a raw prompt and return structured analysis."""
        with Timer() as timer:
            try:
                result = await self._provider.generate_structured(
                    _ANALYSIS_PROMPT.format(raw_prompt=raw_prompt),
                    schema=_AnalysisSchema,
                    system=_ANALYSIS_SYSTEM_PROMPT,
                )

                # Map string values to enums safely
                prompt_type = self._safe_enum(PromptType, result.prompt_type, PromptType.GENERAL)
                intent = self._safe_enum(PromptIntent, result.intent, PromptIntent.OTHER)

                analysis = PromptAnalysis(
                    prompt_type=prompt_type,
                    intent=intent,
                    detected_domain=result.detected_domain,
                    target_audience=result.target_audience,
                    complexity=result.complexity,
                    weaknesses=result.weaknesses,
                    strengths=result.strengths,
                    missing_elements=result.missing_elements,
                    key_entities=result.key_entities,
                    summary=result.summary,
                )

            except Exception as e:
                logger.error("Prompt analysis failed: %s — using defaults", e)
                analysis = PromptAnalysis(
                    summary=f"Analysis failed: {str(e)}",
                    weaknesses=["Analysis could not be completed"],
                )

        logger.info("Prompt analyzed in %.0fms: type=%s, intent=%s",
                     timer.duration_ms, analysis.prompt_type.value, analysis.intent.value)
        return analysis

    @staticmethod
    def _safe_enum(enum_class, value: str, default):
        """Safely convert a string to an enum value."""
        try:
            return enum_class(value.lower())
        except (ValueError, AttributeError):
            return default
