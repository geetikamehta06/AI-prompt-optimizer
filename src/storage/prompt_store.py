"""
Prompt Store — CRUD operations for prompts with versioning.
"""

from __future__ import annotations
import json
from typing import Optional
from ..models.prompt import EnhancedPrompt, PromptVersion
from ..utils.logging_setup import get_logger
from .database import DatabaseManager

logger = get_logger(__name__)


class PromptStore:
    """Persistent storage for prompts with versioning support."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def save(self, enhanced: EnhancedPrompt) -> str:
        """Save an enhanced prompt and create version 1."""
        async with self._db.get_connection() as conn:
            await conn.execute(
                """INSERT INTO prompts (id, original_text, enhanced_text, frameworks_used,
                   analysis_json, quality_before, quality_after, provider, model,
                   processing_time_ms, improvement_summary, reasoning)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (enhanced.id, enhanced.original_prompt, enhanced.enhanced_prompt,
                 json.dumps(enhanced.frameworks_used),
                 enhanced.analysis.model_dump_json() if enhanced.analysis else "{}",
                 enhanced.quality_before, enhanced.quality_after,
                 enhanced.provider_used, enhanced.model_used,
                 enhanced.processing_time_ms, enhanced.improvement_summary, enhanced.reasoning)
            )
            await conn.execute(
                """INSERT INTO prompt_versions (prompt_id, version, prompt_text, frameworks_used, quality_score)
                   VALUES (?, 1, ?, ?, ?)""",
                (enhanced.id, enhanced.enhanced_prompt,
                 json.dumps(enhanced.frameworks_used), enhanced.quality_after)
            )
            # Track framework usage
            for fw_id in enhanced.frameworks_used:
                await conn.execute(
                    "INSERT INTO framework_usage (framework_id, prompt_id) VALUES (?, ?)",
                    (fw_id, enhanced.id)
                )
            await conn.commit()
        logger.info("Saved prompt %s with %d frameworks", enhanced.id, len(enhanced.frameworks_used))
        return enhanced.id

    async def get(self, prompt_id: str) -> Optional[dict]:
        """Get a prompt by ID."""
        async with self._db.get_connection() as conn:
            cursor = await conn.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
        return None

    async def get_versions(self, prompt_id: str) -> list[dict]:
        """Get all versions of a prompt."""
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM prompt_versions WHERE prompt_id = ? ORDER BY version",
                (prompt_id,)
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def get_history(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get prompt history, most recent first."""
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM prompts ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in await cursor.fetchall()]

    async def delete(self, prompt_id: str) -> bool:
        """Delete a prompt and its versions."""
        async with self._db.get_connection() as conn:
            await conn.execute("DELETE FROM prompt_versions WHERE prompt_id = ?", (prompt_id,))
            await conn.execute("DELETE FROM framework_usage WHERE prompt_id = ?", (prompt_id,))
            cursor = await conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
            await conn.commit()
            return cursor.rowcount > 0

    async def get_analytics(self) -> dict:
        """Get dashboard analytics data."""
        async with self._db.get_connection() as conn:
            total = (await (await conn.execute("SELECT COUNT(*) FROM prompts")).fetchone())[0]
            avg_improvement = await (await conn.execute(
                "SELECT AVG(quality_after - quality_before) FROM prompts WHERE quality_before IS NOT NULL AND quality_after IS NOT NULL"
            )).fetchone()
            top_fw = await (await conn.execute(
                "SELECT framework_id, COUNT(*) as cnt FROM framework_usage GROUP BY framework_id ORDER BY cnt DESC LIMIT 5"
            )).fetchall()
            recent = await (await conn.execute(
                "SELECT COUNT(*) FROM prompts WHERE created_at >= datetime('now', '-1 day')"
            )).fetchone()

            return {
                "total_prompts": total,
                "avg_quality_improvement": round(avg_improvement[0] or 0, 1),
                "prompts_today": recent[0],
                "top_frameworks": [{"id": r[0], "count": r[1]} for r in top_fw],
            }
