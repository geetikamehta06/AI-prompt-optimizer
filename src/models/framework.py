"""
Framework data models — types for framework definitions, recommendations, and chains.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FrameworkField(BaseModel):
    """A single field/component of a prompt engineering framework."""
    name: str
    description: str
    prompt_hint: str = ""


class Framework(BaseModel):
    """Complete definition of a prompt engineering framework."""
    id: str
    name: str
    acronym: str
    description: str
    category: str  # structuring, goal_oriented, problem_solving, reasoning, constraint, persona, iterative
    complexity: str  # simple, moderate, advanced
    enabled: bool = True
    fields: list[FrameworkField] = Field(default_factory=list)
    best_for: list[str] = Field(default_factory=list)
    combinable_with: list[str] = Field(default_factory=list)


class FrameworkRecommendation(BaseModel):
    """AI recommendation for which framework(s) to use."""
    framework_id: str
    framework_name: str
    confidence: float = 0.0  # 0.0 to 1.0
    reasoning: str = ""
    is_primary: bool = False


class FrameworkChain(BaseModel):
    """A chain of multiple frameworks to apply sequentially."""
    frameworks: list[str]  # framework IDs in order
    chain_reasoning: str = ""
    expected_improvement: str = ""


class FrameworkSelection(BaseModel):
    """Complete framework selection result from the AI selector."""
    primary: FrameworkRecommendation
    alternatives: list[FrameworkRecommendation] = Field(default_factory=list)
    suggested_chain: Optional[FrameworkChain] = None
    should_chain: bool = False
    selection_reasoning: str = ""
