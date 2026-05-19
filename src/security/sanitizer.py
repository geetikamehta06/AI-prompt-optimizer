"""
Prompt Sanitizer — input sanitization and validation.
"""

from __future__ import annotations
import re
from ..utils.config import get_config
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


class PromptSanitizer:
    """Sanitizes and validates user prompt input."""

    def __init__(self) -> None:
        config = get_config()
        self._max_length = config.security.max_prompt_length
        self._enabled = config.security.sanitize_inputs

    def sanitize(self, text: str) -> str:
        """Sanitize a prompt string."""
        if not self._enabled:
            return text.strip()

        result = text.strip()

        # Truncate if too long
        if len(result) > self._max_length:
            result = result[:self._max_length]
            logger.warning("Prompt truncated from %d to %d chars", len(text), self._max_length)

        # Remove null bytes
        result = result.replace("\x00", "")

        # Normalize excessive whitespace
        result = re.sub(r'\n{4,}', '\n\n\n', result)
        result = re.sub(r' {4,}', '   ', result)

        return result

    def validate(self, text: str) -> tuple[bool, str]:
        """Validate prompt input. Returns (is_valid, error_message)."""
        if not text or not text.strip():
            return False, "Prompt cannot be empty"
        if len(text) > self._max_length:
            return False, f"Prompt exceeds maximum length of {self._max_length} characters"
        if len(text.strip()) < 3:
            return False, "Prompt is too short — provide at least a few words"
        return True, ""
