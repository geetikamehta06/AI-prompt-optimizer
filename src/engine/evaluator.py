"""
Prompt Evaluator — scores prompt quality across multiple dimensions.
"""

from __future__ import annotations
from pydantic import BaseModel, Field
from ..models.quality import IssueSeverity, QualityDimension, QualityIssue, QualityReport
from ..providers.base import BaseProvider
from ..utils.logging_setup import get_logger
from ..utils.helpers import Timer

logger = get_logger(__name__)


class _QualitySchema(BaseModel):
    clarity: int = 50
    specificity: int = 50
    structure: int = 50
    context_completeness: int = 50
    constraint_definition: int = 50
    audience_alignment: int = 50
    actionability: int = 50
    hallucination_safety: int = 50
    issues: list[dict] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    hallucination_risk: str = "low"


_EVAL_SYSTEM = "You are an expert prompt quality analyst. Score prompts 0-100 across 8 dimensions. Be rigorous."

_EVAL_PROMPT = """Evaluate this prompt across 8 dimensions (0-100 each):
clarity, specificity, structure, context_completeness, constraint_definition, audience_alignment, actionability, hallucination_safety.

PROMPT:
\"\"\"
{prompt_text}
\"\"\"

Also list: issues (dimension, severity, description, suggestion), strengths, improvement_suggestions, hallucination_risk (low/medium/high). Respond as JSON."""


class PromptEvaluator:
    """Evaluates prompt quality across 8 dimensions."""

    def __init__(self, provider: BaseProvider) -> None:
        self._provider = provider

    async def evaluate(self, prompt_text: str) -> QualityReport:
        with Timer() as timer:
            try:
                result = await self._provider.generate_structured(
                    _EVAL_PROMPT.format(prompt_text=prompt_text),
                    schema=_QualitySchema, system=_EVAL_SYSTEM,
                )
                report = self._build_report(result, prompt_text)
            except Exception as e:
                logger.error("Quality evaluation failed: %s", e)
                report = QualityReport(overall_score=50.0, prompt_text=prompt_text,
                                       improvement_suggestions=[f"Evaluation failed: {e}"])
        logger.info("Evaluated in %.0fms: score=%.1f grade=%s", timer.duration_ms, report.overall_score, report.grade)
        return report

    def _build_report(self, result: _QualitySchema, prompt_text: str) -> QualityReport:
        dim_names = ["Clarity", "Specificity", "Structure", "Context Completeness",
                     "Constraint Definition", "Audience Alignment", "Actionability", "Hallucination Safety"]
        dim_values = [result.clarity, result.specificity, result.structure, result.context_completeness,
                      result.constraint_definition, result.audience_alignment, result.actionability, result.hallucination_safety]
        dimensions = [QualityDimension(name=n, score=float(max(0, min(100, v)))) for n, v in zip(dim_names, dim_values)]
        overall = sum(d.score for d in dimensions) / len(dimensions)
        issues = []
        for d in result.issues:
            try:
                sev = IssueSeverity(d.get("severity", "medium").lower())
            except ValueError:
                sev = IssueSeverity.MEDIUM
            issues.append(QualityIssue(dimension=d.get("dimension", ""), severity=sev,
                                       description=d.get("description", ""), suggestion=d.get("suggestion", "")))
        return QualityReport(overall_score=round(overall, 1), dimensions=dimensions, issues=issues,
                             strengths=result.strengths, improvement_suggestions=result.improvement_suggestions,
                             hallucination_risk=result.hallucination_risk, prompt_text=prompt_text)
