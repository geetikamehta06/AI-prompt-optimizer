"""
Prompt data models — core types for raw, enhanced, and versioned prompts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PromptType(str, Enum):
    """Detected prompt type classification."""
    CREATIVE = "creative"
    TECHNICAL = "technical"
    ANALYTICAL = "analytical"
    STRATEGIC = "strategic"
    CONVERSATIONAL = "conversational"
    INSTRUCTIONAL = "instructional"
    PERSUASIVE = "persuasive"
    INVESTIGATIVE = "investigative"
    OPERATIONAL = "operational"
    GENERAL = "general"


class PromptIntent(str, Enum):
    """Detected prompt intent."""
    GENERATE = "generate"
    ANALYZE = "analyze"
    TRANSFORM = "transform"
    EXPLAIN = "explain"
    SUMMARIZE = "summarize"
    COMPARE = "compare"
    DECIDE = "decide"
    DEBUG = "debug"
    PLAN = "plan"
    CREATE = "create"
    EVALUATE = "evaluate"
    BRAINSTORM = "brainstorm"
    OTHER = "other"


class PromptAnalysis(BaseModel):
    """Result of analyzing a raw prompt."""
    prompt_type: PromptType = PromptType.GENERAL
    intent: PromptIntent = PromptIntent.OTHER
    detected_domain: str = "general"
    target_audience: str = "general"
    complexity: str = "moderate"  # simple, moderate, complex
    weaknesses: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    key_entities: list[str] = Field(default_factory=list)
    summary: str = ""


class RawPrompt(BaseModel):
    """User-submitted raw prompt."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    team: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class EnhancedPrompt(BaseModel):
    """AI-enhanced prompt output."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_prompt: str
    enhanced_prompt: str
    frameworks_used: list[str] = Field(default_factory=list)
    framework_details: dict = Field(default_factory=dict)
    reasoning: str = ""
    improvement_summary: str = ""
    analysis: Optional[PromptAnalysis] = None
    quality_before: Optional[float] = None
    quality_after: Optional[float] = None
    refinement_rounds: int = 0
    provider_used: str = ""
    model_used: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: float = 0.0
    workflow_stages: list[dict] = Field(default_factory=list)


class PromptVersion(BaseModel):
    """A versioned snapshot of a prompt."""
    version: int
    prompt_text: str
    frameworks_used: list[str] = Field(default_factory=list)
    quality_score: Optional[float] = None
    changes_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromptComparison(BaseModel):
    """Side-by-side comparison of two prompts."""
    prompt_a: str
    prompt_b: str
    score_a: Optional[float] = None
    score_b: Optional[float] = None
    frameworks_a: list[str] = Field(default_factory=list)
    frameworks_b: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    recommendation: str = ""
