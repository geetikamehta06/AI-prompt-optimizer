"""
Database Manager — SQLite database initialization and connection management.
"""

from __future__ import annotations
import aiosqlite
from pathlib import Path
from ..utils.config import get_config
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    original_text TEXT NOT NULL,
    enhanced_text TEXT,
    frameworks_used TEXT DEFAULT '[]',
    analysis_json TEXT DEFAULT '{}',
    quality_before REAL,
    quality_after REAL,
    provider TEXT,
    model TEXT,
    processing_time_ms REAL,
    improvement_summary TEXT DEFAULT '',
    reasoning TEXT DEFAULT '',
    team TEXT,
    tags TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    frameworks_used TEXT DEFAULT '[]',
    quality_score REAL,
    changes_summary TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

CREATE TABLE IF NOT EXISTS framework_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    framework_id TEXT NOT NULL,
    prompt_id TEXT,
    used_at TEXT DEFAULT (datetime('now')),
    was_primary INTEGER DEFAULT 1,
    confidence REAL
);

CREATE INDEX IF NOT EXISTS idx_prompts_created ON prompts(created_at);
CREATE INDEX IF NOT EXISTS idx_versions_prompt ON prompt_versions(prompt_id);
CREATE INDEX IF NOT EXISTS idx_framework_usage_fw ON framework_usage(framework_id);
"""

from contextlib import asynccontextmanager

class DatabaseManager:
    """Manages SQLite database connections and schema."""

    def __init__(self) -> None:
        config = get_config()
        self._db_path = config.storage.database_path
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def get_connection(self):
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    async def initialize(self) -> None:
        async with self.get_connection() as conn:
            await conn.executescript(_SCHEMA)
            await conn.commit()
        logger.info("Database initialized: %s", self._db_path)
