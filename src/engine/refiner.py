"""
Iterative Refiner — multi-pass prompt refinement with self-evaluation.
"""

from __future__ import annotations
from ..models.quality import QualityReport
from ..providers.base import BaseProvider
from ..utils.logging_setup import get_logger
from ..utils.helpers import Timer

logger = get_logger(__name__)

_REFINE_SYSTEM = "You are a world-class prompt engineer performing iterative refinement. Each round must produce a measurably better prompt."

_REFINE_PROMPT = """You are refining a prompt iteratively. This is refinement round {round_num}.

CURRENT PROMPT:
\"\"\"
{current_prompt}
\"\"\"

QUALITY ASSESSMENT:
- Overall Score: {quality_score}/100
- Key Issues: {issues}
- Suggestions: {suggestions}

Your task:
1. Address every identified issue
2. Incorporate every improvement suggestion
3. Maintain all existing strengths
4. Improve clarity, specificity, structure, and constraints
5. Optimize for LLM processing

Output ONLY the refined prompt text — no explanations."""


class IterativeRefiner:
    """Multi-pass prompt refinement with evaluation between rounds."""

    def __init__(self, provider: BaseProvider, evaluator) -> None:
        self._provider = provider
        self._evaluator = evaluator

    async def refine(self, prompt_text: str, initial_quality: QualityReport,
                     max_rounds: int = 2, quality_threshold: float = 80.0) -> tuple[str, list[dict]]:
        """Iteratively refine a prompt.
        
        Returns (best_prompt_text, evolution_history).
        """
        current = prompt_text
        current_quality = initial_quality
        history = [{
            "round": 0, "prompt": current,
            "score": current_quality.overall_score, "action": "initial"
        }]

        for round_num in range(1, max_rounds + 1):
            if current_quality.overall_score >= quality_threshold:
                logger.info("Quality %.1f >= threshold %.1f — stopping refinement", current_quality.overall_score, quality_threshold)
                break

            with Timer() as timer:
                issues_str = "; ".join(i.description for i in current_quality.issues[:5]) or "none"
                suggestions_str = "; ".join(current_quality.improvement_suggestions[:5]) or "none"

                refined = await self._provider.generate(
                    _REFINE_PROMPT.format(
                        round_num=round_num, current_prompt=current,
                        quality_score=current_quality.overall_score,
                        issues=issues_str, suggestions=suggestions_str,
                    ),
                    system=_REFINE_SYSTEM,
                )
                refined = refined.strip()

                # Re-evaluate
                new_quality = await self._evaluator.evaluate(refined)

            improvement = new_quality.overall_score - current_quality.overall_score
            history.append({
                "round": round_num, "prompt": refined,
                "score": new_quality.overall_score,
                "improvement": improvement,
                "duration_ms": timer.duration_ms,
                "action": "refined",
            })

            logger.info("Round %d: %.1f → %.1f (%+.1f) in %.0fms",
                         round_num, current_quality.overall_score, new_quality.overall_score, improvement, timer.duration_ms)

            # Only keep if improved
            if new_quality.overall_score > current_quality.overall_score:
                current = refined
                current_quality = new_quality
            else:
                logger.info("No improvement in round %d — keeping previous version", round_num)
                break

        return current, history
