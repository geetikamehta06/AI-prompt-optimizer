"""
Framework Selector — AI-powered intelligent framework recommendation.

Takes prompt analysis and available frameworks, then recommends the
best framework(s) with confidence scores and reasoning.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..frameworks.registry import FrameworkRegistry
from ..models.framework import (
    FrameworkChain,
    FrameworkRecommendation,
    FrameworkSelection,
)
from ..models.prompt import PromptAnalysis
from ..providers.base import BaseProvider
from ..utils.logging_setup import get_logger
from ..utils.helpers import Timer

logger = get_logger(__name__)


class _SelectionSchema(BaseModel):
    """Schema for AI framework selection output."""
    primary_framework_id: str
    primary_confidence: float = 0.8
    primary_reasoning: str = ""
    alternative_ids: list[str] = Field(default_factory=list)
    alternative_confidences: list[float] = Field(default_factory=list)
    alternative_reasonings: list[str] = Field(default_factory=list)
    should_chain: bool = False
    chain_ids: list[str] = Field(default_factory=list)
    chain_reasoning: str = ""
    selection_reasoning: str = ""


_SELECTOR_SYSTEM_PROMPT = """You are an expert prompt engineering strategist. Your job is to select the optimal prompt engineering framework(s) for enhancing a given prompt.

You understand all major prompt engineering frameworks deeply and can recommend the best one based on the prompt's intent, type, complexity, and domain."""

_SELECTOR_PROMPT = """Based on the following prompt analysis, recommend the best prompt engineering framework(s).

PROMPT ANALYSIS:
- Type: {prompt_type}
- Intent: {intent}
- Domain: {domain}
- Audience: {audience}
- Complexity: {complexity}
- Weaknesses: {weaknesses}
- Missing elements: {missing_elements}
- Summary: {summary}

AVAILABLE FRAMEWORKS:
{frameworks_summary}

---

Select the best framework and explain why. Consider:
1. Which framework best addresses the identified weaknesses?
2. Which framework aligns with the prompt's intent and domain?
3. Should multiple frameworks be chained for better results?

Respond as JSON with:
- primary_framework_id: the ID of the best framework
- primary_confidence: confidence score 0.0-1.0
- primary_reasoning: why this framework was selected
- alternative_ids: list of alternative framework IDs (up to 2)
- alternative_confidences: confidence scores for alternatives
- alternative_reasonings: reasoning for each alternative
- should_chain: true if combining frameworks would significantly improve results
- chain_ids: list of framework IDs to chain (in order, including primary)
- chain_reasoning: why chaining is recommended
- selection_reasoning: overall reasoning for the selection"""


class FrameworkSelector:
    """AI-powered framework selector.
    
    Analyzes prompt characteristics and recommends the optimal
    framework(s) from the registry.
    """

    def __init__(self, provider: BaseProvider, registry: FrameworkRegistry) -> None:
        self._provider = provider
        self._registry = registry

    async def select(self, analysis: PromptAnalysis) -> FrameworkSelection:
        """Select the best framework(s) based on prompt analysis."""
        with Timer() as timer:
            try:
                result = await self._provider.generate_structured(
                    _SELECTOR_PROMPT.format(
                        prompt_type=analysis.prompt_type.value,
                        intent=analysis.intent.value,
                        domain=analysis.detected_domain,
                        audience=analysis.target_audience,
                        complexity=analysis.complexity,
                        weaknesses=", ".join(analysis.weaknesses) or "none identified",
                        missing_elements=", ".join(analysis.missing_elements) or "none identified",
                        summary=analysis.summary,
                        frameworks_summary=self._registry.get_all_summaries(),
                    ),
                    schema=_SelectionSchema,
                    system=_SELECTOR_SYSTEM_PROMPT,
                )

                selection = self._build_selection(result)

            except Exception as e:
                logger.error("Framework selection failed: %s — using default", e)
                selection = self._default_selection(analysis)

        logger.info("Framework selected in %.0fms: %s (confidence=%.2f, chain=%s)",
                     timer.duration_ms,
                     selection.primary.framework_id,
                     selection.primary.confidence,
                     selection.should_chain)
        return selection

    def _build_selection(self, result: _SelectionSchema) -> FrameworkSelection:
        """Build a FrameworkSelection from the AI's response."""
        # Validate primary framework exists
        primary_fw = self._registry.get(result.primary_framework_id)
        if not primary_fw:
            # Fallback to CRAFT
            primary_fw = self._registry.get("craft")
            result.primary_framework_id = "craft"

        primary = FrameworkRecommendation(
            framework_id=result.primary_framework_id,
            framework_name=primary_fw.name if primary_fw else "CRAFT",
            confidence=min(max(result.primary_confidence, 0.0), 1.0),
            reasoning=result.primary_reasoning,
            is_primary=True,
        )

        # Build alternatives
        alternatives = []
        for i, alt_id in enumerate(result.alternative_ids[:2]):
            alt_fw = self._registry.get(alt_id)
            if alt_fw:
                conf = result.alternative_confidences[i] if i < len(result.alternative_confidences) else 0.5
                reason = result.alternative_reasonings[i] if i < len(result.alternative_reasonings) else ""
                alternatives.append(FrameworkRecommendation(
                    framework_id=alt_id,
                    framework_name=alt_fw.name,
                    confidence=min(max(conf, 0.0), 1.0),
                    reasoning=reason,
                    is_primary=False,
                ))

        # Build chain if suggested
        chain = None
        if result.should_chain and result.chain_ids:
            valid_chain = [cid for cid in result.chain_ids if self._registry.get(cid)]
            if len(valid_chain) >= 2:
                chain = FrameworkChain(
                    frameworks=valid_chain,
                    chain_reasoning=result.chain_reasoning,
                )

        return FrameworkSelection(
            primary=primary,
            alternatives=alternatives,
            suggested_chain=chain,
            should_chain=result.should_chain and chain is not None,
            selection_reasoning=result.selection_reasoning,
        )

    def _default_selection(self, analysis: PromptAnalysis) -> FrameworkSelection:
        """Fallback selection based on heuristics."""
        # Simple heuristic mapping
        type_to_framework = {
            "strategic": "broke",
            "analytical": "cot",
            "creative": "crispe",
            "investigative": "5w1h",
            "technical": "craft",
            "instructional": "risen",
            "persuasive": "bab",
            "operational": "coast",
        }

        fw_id = type_to_framework.get(analysis.prompt_type.value, "craft")
        fw = self._registry.get(fw_id) or self._registry.get("craft")

        return FrameworkSelection(
            primary=FrameworkRecommendation(
                framework_id=fw.id,
                framework_name=fw.name,
                confidence=0.6,
                reasoning="Selected via heuristic fallback based on prompt type",
                is_primary=True,
            ),
            selection_reasoning="Fallback heuristic selection (AI selection failed)",
        )
