"""
Quality analysis models — types for prompt quality scoring and issue detection.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    """Severity level for detected quality issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QualityDimension(BaseModel):
    """Score for a single quality dimension."""
    name: str
    score: float = 0.0  # 0-100
    max_score: float = 100.0
    feedback: str = ""


class QualityIssue(BaseModel):
    """A detected quality problem in a prompt."""
    dimension: str
    severity: IssueSeverity = IssueSeverity.MEDIUM
    description: str
    suggestion: str = ""
    location: Optional[str] = None  # where in the prompt


class QualityReport(BaseModel):
    """Comprehensive quality analysis report."""
    overall_score: float = 0.0  # 0-100
    dimensions: list[QualityDimension] = Field(default_factory=list)
    issues: list[QualityIssue] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    hallucination_risk: str = "low"  # low, medium, high
    prompt_text: str = ""

    @property
    def grade(self) -> str:
        """Letter grade based on overall score."""
        if self.overall_score >= 90:
            return "A+"
        elif self.overall_score >= 80:
            return "A"
        elif self.overall_score >= 70:
            return "B"
        elif self.overall_score >= 60:
            return "C"
        elif self.overall_score >= 50:
            return "D"
        return "F"

    @property
    def issue_count_by_severity(self) -> dict[str, int]:
        """Count issues by severity level."""
        counts: dict[str, int] = {}
        for issue in self.issues:
            counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
        return counts
