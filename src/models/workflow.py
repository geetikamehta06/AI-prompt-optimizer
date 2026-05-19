"""
Workflow models — types for pipeline orchestration state and results.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .prompt import EnhancedPrompt, PromptAnalysis
from .framework import FrameworkSelection
from .quality import QualityReport


class WorkflowStage(str, Enum):
    """Stages in the prompt enhancement pipeline."""
    RECEIVED = "received"
    SANITIZING = "sanitizing"
    ANALYZING = "analyzing"
    SELECTING_FRAMEWORK = "selecting_framework"
    ENHANCING = "enhancing"
    EVALUATING = "evaluating"
    REFINING = "refining"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    ERROR = "error"


class StageResult(BaseModel):
    """Result from a single pipeline stage."""
    stage: WorkflowStage
    success: bool = True
    duration_ms: float = 0.0
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorkflowState(BaseModel):
    """Current state of the enhancement pipeline."""
    current_stage: WorkflowStage = WorkflowStage.RECEIVED
    stages_completed: list[StageResult] = Field(default_factory=list)
    progress: float = 0.0  # 0.0 to 1.0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class PipelineResult(BaseModel):
    """Final result from the complete enhancement pipeline."""
    success: bool = True
    enhanced_prompt: Optional[EnhancedPrompt] = None
    analysis: Optional[PromptAnalysis] = None
    framework_selection: Optional[FrameworkSelection] = None
    quality_before: Optional[QualityReport] = None
    quality_after: Optional[QualityReport] = None
    workflow: WorkflowState = Field(default_factory=WorkflowState)
    total_duration_ms: float = 0.0
    error: Optional[str] = None
