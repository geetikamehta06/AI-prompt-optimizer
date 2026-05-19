"""
Prompt Enhancer — applies selected frameworks to restructure and improve prompts.

This is the core enhancement engine. It takes a raw prompt, a framework selection,
and produces an enhanced, optimized prompt.
"""

from __future__ import annotations

from ..frameworks.registry import FrameworkRegistry
from ..models.framework import FrameworkSelection
from ..models.prompt import EnhancedPrompt, PromptAnalysis
from ..providers.base import BaseProvider
from ..utils.logging_setup import get_logger
from ..utils.helpers import Timer

logger = get_logger(__name__)


_ENHANCE_SYSTEM_PROMPT = """You are a world-class prompt engineer. Your task is to take a raw, unstructured prompt and transform it into a highly optimized, well-structured prompt that will produce significantly better results from any LLM.

Your enhanced prompts should be:
- Clear and unambiguous
- Well-structured with logical flow
- Specific with concrete requirements
- Formatted for optimal LLM processing
- Include all necessary context and constraints

Output ONLY the enhanced prompt text. Do not include explanations, headers, or meta-commentary — just the improved prompt itself."""


_CHAIN_MERGE_PROMPT = """You are an expert prompt engineer. You have been given a prompt that was enhanced using multiple frameworks sequentially. Your job is to merge and harmonize the results into a single, cohesive, optimized prompt.

The frameworks used were: {frameworks}

Here are the intermediate versions:

{versions}

---

Create a final unified prompt that:
1. Combines the best elements from each framework's enhancement
2. Removes redundancy and overlap
3. Maintains a natural, clear flow
4. Is optimized for LLM processing
5. Represents the highest quality version possible

Output ONLY the final merged prompt text."""


class PromptEnhancer:
    """Applies prompt engineering frameworks to enhance raw prompts.
    
    Supports single-framework enhancement and multi-framework chaining.
    """

    def __init__(self, provider: BaseProvider, registry: FrameworkRegistry) -> None:
        self._provider = provider
        self._registry = registry

    async def enhance(
        self,
        raw_prompt: str,
        selection: FrameworkSelection,
        analysis: PromptAnalysis | None = None,
    ) -> EnhancedPrompt:
        """Enhance a prompt using the selected framework(s).
        
        If chaining is recommended, applies multiple frameworks sequentially
        and merges the results.
        """
        with Timer() as timer:
            if selection.should_chain and selection.suggested_chain:
                enhanced_text, frameworks_used, details = await self._chain_enhance(
                    raw_prompt, selection, analysis
                )
            else:
                enhanced_text, frameworks_used, details = await self._single_enhance(
                    raw_prompt, selection.primary.framework_id, analysis
                )

        # Build improvement summary
        improvement_summary = self._build_improvement_summary(
            raw_prompt, enhanced_text, frameworks_used
        )

        result = EnhancedPrompt(
            original_prompt=raw_prompt,
            enhanced_prompt=enhanced_text,
            frameworks_used=frameworks_used,
            framework_details=details,
            reasoning=selection.selection_reasoning,
            improvement_summary=improvement_summary,
            analysis=analysis,
            provider_used=self._provider.__class__.__name__,
            model_used=self._provider.model,
            processing_time_ms=timer.duration_ms,
        )

        logger.info("Prompt enhanced in %.0fms using %s",
                     timer.duration_ms, ", ".join(frameworks_used))
        return result

    async def _single_enhance(
        self, raw_prompt: str, framework_id: str,
        analysis: PromptAnalysis | None
    ) -> tuple[str, list[str], dict]:
        """Enhance using a single framework."""
        # Render the framework template
        context_vars = {"raw_prompt": raw_prompt}
        if analysis:
            context_vars["context"] = analysis.summary

        rendered = self._registry.render_template(framework_id, **context_vars)

        if rendered:
            enhanced = await self._provider.generate(rendered, system=_ENHANCE_SYSTEM_PROMPT)
        else:
            # Fallback: use the framework summary as guidance
            fw_summary = self._registry.get_framework_summary(framework_id)
            fallback_prompt = (
                f"Using the {framework_id.upper()} framework ({fw_summary}), "
                f"enhance this prompt:\n\n{raw_prompt}"
            )
            enhanced = await self._provider.generate(fallback_prompt, system=_ENHANCE_SYSTEM_PROMPT)

        fw = self._registry.get(framework_id)
        details = {
            framework_id: {
                "name": fw.name if fw else framework_id,
                "acronym": fw.acronym if fw else "",
            }
        }

        return enhanced.strip(), [framework_id], details

    async def _chain_enhance(
        self, raw_prompt: str, selection: FrameworkSelection,
        analysis: PromptAnalysis | None
    ) -> tuple[str, list[str], dict]:
        """Enhance using multiple frameworks in sequence, then merge."""
        chain = selection.suggested_chain
        if not chain:
            return await self._single_enhance(
                raw_prompt, selection.primary.framework_id, analysis
            )

        versions = []
        details = {}

        for fw_id in chain.frameworks:
            context_vars = {"raw_prompt": raw_prompt}
            if analysis:
                context_vars["context"] = analysis.summary

            rendered = self._registry.render_template(fw_id, **context_vars)
            if rendered:
                enhanced = await self._provider.generate(rendered, system=_ENHANCE_SYSTEM_PROMPT)
            else:
                fw_summary = self._registry.get_framework_summary(fw_id)
                fallback = f"Using {fw_id.upper()} ({fw_summary}), enhance:\n\n{raw_prompt}"
                enhanced = await self._provider.generate(fallback, system=_ENHANCE_SYSTEM_PROMPT)

            versions.append((fw_id, enhanced.strip()))

            fw = self._registry.get(fw_id)
            details[fw_id] = {
                "name": fw.name if fw else fw_id,
                "acronym": fw.acronym if fw else "",
            }

        # Merge all versions into one cohesive prompt
        versions_text = "\n\n---\n\n".join(
            f"[{fw_id.upper()} version]:\n{text}" for fw_id, text in versions
        )
        frameworks_str = ", ".join(fw_id.upper() for fw_id, _ in versions)

        merge_prompt = _CHAIN_MERGE_PROMPT.format(
            frameworks=frameworks_str,
            versions=versions_text,
        )
        merged = await self._provider.generate(merge_prompt)

        return merged.strip(), [fw_id for fw_id, _ in versions], details

    def _build_improvement_summary(
        self, original: str, enhanced: str, frameworks: list[str]
    ) -> str:
        """Build a brief summary of improvements made."""
        orig_words = len(original.split())
        enhanced_words = len(enhanced.split())
        word_change = enhanced_words - orig_words

        parts = [
            f"Enhanced using {', '.join(f.upper() for f in frameworks)}.",
            f"Word count: {orig_words} → {enhanced_words} ({'+' if word_change > 0 else ''}{word_change}).",
        ]

        if enhanced_words > orig_words * 1.5:
            parts.append("Significant expansion with added context and structure.")
        elif enhanced_words < orig_words * 0.8:
            parts.append("Condensed for clarity and focus.")
        else:
            parts.append("Restructured with improved clarity and specificity.")

        return " ".join(parts)
