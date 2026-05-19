"""
Common helper utilities.
"""

import time
from typing import Callable, Any


class Timer:
    """Simple context-manager timer for measuring execution duration."""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self.duration_ms: float = 0.0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000


def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def word_count(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def char_count(text: str) -> int:
    """Count characters in text."""
    return len(text)
