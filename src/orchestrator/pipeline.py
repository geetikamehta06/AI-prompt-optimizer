"""
Prompt Pipeline — main workflow orchestrator.

Orchestrates: Input → Sanitize → Analyze → Select Framework → Enhance → Evaluate → Refine → Finalize
"""

from __future__ import annotations
import time
from typing import Any, Callable, Coroutine, Optional

from ..engine.analyzer import PromptAnalyzer
from ..engine.enhancer import PromptEnhancer
from ..engine.evaluator import PromptEvaluator
from ..engine.refiner import IterativeRefiner
from ..engine.selector import FrameworkSelector
from ..frameworks.registry import FrameworkRegistry
from ..models.prompt import EnhancedPrompt
from ..models.workflow import PipelineResult, StageResult, WorkflowStage, WorkflowState
from ..providers.base import BaseProvider
from ..providers.provider_factory import create_provider
from ..security.sanitizer import PromptSanitizer
from ..utils.config import get_config
from ..utils.logging_setup import get_logger
from ..utils.helpers import Timer

logger = get_logger(__name__)

ProgressCallback = Callable[[str, float, str], Coroutine[Any, Any, None]]


class PromptPipeline:
    """Main enhancement pipeline orchestrator.
    
    Runs the full enhancement workflow with configurable stages,
    progress callbacks, and error handling.
    """

    def __init__(self, provider: Optional[BaseProvider] = None,
                 registry: Optional[FrameworkRegistry] = None,
                 progress_callback: Optional[ProgressCallback] = None) -> None:
        config = get_config()
        self._provider = provider or create_provider()
        self._registry = registry or FrameworkRegistry()
        self._progress = progress_callback
        self._config = config.pipeline

        # Initialize engine components
        self._sanitizer = PromptSanitizer()
        self._analyzer = PromptAnalyzer(self._provider)
        self._selector = FrameworkSelector(self._provider, self._registry)
        self._enhancer = PromptEnhancer(self._provider, self._registry)
        self._evaluator = PromptEvaluator(self._provider)
        self._refiner = IterativeRefiner(self._provider, self._evaluator)

    async def run(self, raw_prompt: str,
                  framework_id: Optional[str] = None,
                  enable_evaluation: Optional[bool] = None,
                  enable_refinement: Optional[bool] = None,
                  refinement_rounds: Optional[int] = None) -> PipelineResult:
        """Execute the full enhancement pipeline."""
        start_time = time.perf_counter()
        workflow = WorkflowState()
        result = PipelineResult(workflow=workflow)

        eval_enabled = enable_evaluation if enable_evaluation is not None else self._config.enable_evaluation
        refine_enabled = enable_refinement if enable_refinement is not None else self._config.enable_refinement
        max_rounds = refinement_rounds if refinement_rounds is not None else self._config.refinement_rounds

        try:
            # Stage 1: Sanitize
            await self._emit("Sanitizing", 0.05, "Sanitizing input...")
            workflow.current_stage = WorkflowStage.SANITIZING
            with Timer() as t:
                sanitized = self._sanitizer.sanitize(raw_prompt)
            workflow.stages_completed.append(StageResult(stage=WorkflowStage.SANITIZING, duration_ms=t.duration_ms))

            # Stage 2: Analyze
            await self._emit("Analyzing", 0.15, "Analyzing prompt intent and structure...")
            workflow.current_stage = WorkflowStage.ANALYZING
            with Timer() as t:
                analysis = await self._analyzer.analyze(sanitized)
            workflow.stages_completed.append(StageResult(stage=WorkflowStage.ANALYZING, duration_ms=t.duration_ms,
                                                          data={"type": analysis.prompt_type.value, "intent": analysis.intent.value}))
            result.analysis = analysis

            # Stage 3: Select Framework
            await self._emit("Selecting Framework", 0.30, "Selecting optimal framework...")
            workflow.current_stage = WorkflowStage.SELECTING_FRAMEWORK
            if framework_id:
                # Manual framework selection
                from ..models.framework import FrameworkRecommendation, FrameworkSelection
                fw = self._registry.get(framework_id)
                selection = FrameworkSelection(
                    primary=FrameworkRecommendation(
                        framework_id=framework_id,
                        framework_name=fw.name if fw else framework_id,
                        confidence=1.0, reasoning="Manually selected", is_primary=True,
                    ),
                    selection_reasoning="User manually selected framework",
                )
            else:
                with Timer() as t:
                    selection = await self._selector.select(analysis)
                workflow.stages_completed.append(StageResult(stage=WorkflowStage.SELECTING_FRAMEWORK, duration_ms=t.duration_ms,
                                                              data={"framework": selection.primary.framework_id}))
            result.framework_selection = selection

            # Stage 4: Enhance
            await self._emit("Enhancing", 0.50, f"Enhancing with {selection.primary.framework_name}...")
            workflow.current_stage = WorkflowStage.ENHANCING
            with Timer() as t:
                enhanced = await self._enhancer.enhance(sanitized, selection, analysis)
            workflow.stages_completed.append(StageResult(stage=WorkflowStage.ENHANCING, duration_ms=t.duration_ms))
            result.enhanced_prompt = enhanced

            # Stage 5: Evaluate (optional)
            if eval_enabled:
                await self._emit("Evaluating", 0.65, "Evaluating quality...")
                workflow.current_stage = WorkflowStage.EVALUATING
                with Timer() as t:
                    quality_before = await self._evaluator.evaluate(sanitized)
                    quality_after = await self._evaluator.evaluate(enhanced.enhanced_prompt)
                workflow.stages_completed.append(StageResult(stage=WorkflowStage.EVALUATING, duration_ms=t.duration_ms))
                result.quality_before = quality_before
                result.quality_after = quality_after
                enhanced.quality_before = quality_before.overall_score
                enhanced.quality_after = quality_after.overall_score

                # Stage 6: Refine (optional)
                if refine_enabled and quality_after.overall_score < self._config.quality_threshold:
                    await self._emit("Refining", 0.80, "Iteratively refining...")
                    workflow.current_stage = WorkflowStage.REFINING
                    with Timer() as t:
                        refined_text, history = await self._refiner.refine(
                            enhanced.enhanced_prompt, quality_after, max_rounds=max_rounds,
                            quality_threshold=self._config.quality_threshold,
                        )
                    enhanced.enhanced_prompt = refined_text
                    enhanced.refinement_rounds = len(history) - 1
                    enhanced.workflow_stages = history
                    # Re-evaluate final quality
                    final_quality = await self._evaluator.evaluate(refined_text)
                    result.quality_after = final_quality
                    enhanced.quality_after = final_quality.overall_score
                    workflow.stages_completed.append(StageResult(stage=WorkflowStage.REFINING, duration_ms=t.duration_ms))

            # Finalize
            await self._emit("Complete", 1.0, "Enhancement complete!")
            workflow.current_stage = WorkflowStage.COMPLETE
            workflow.progress = 1.0
            result.success = True

        except Exception as e:
            logger.error("Pipeline error: %s", e)
            workflow.current_stage = WorkflowStage.ERROR
            workflow.error = str(e)
            result.success = False
            result.error = str(e)

        result.total_duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Pipeline completed in %.0fms — success=%s", result.total_duration_ms, result.success)
        return result

    async def _emit(self, stage: str, progress: float, log: str) -> None:
        """Emit a progress event if callback is registered."""
        if self._progress:
            await self._progress(stage, progress, log)
