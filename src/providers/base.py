"""
Base AI provider — abstract interface for all AI providers.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Optional, Type

from pydantic import BaseModel

from ..utils.logging_setup import get_logger

logger = get_logger(__name__)


class BaseProvider(ABC):
    """Abstract base class for AI providers.
    
    All providers must implement generate() and generate_structured().
    This ensures any AI provider can be swapped in without changing
    business logic.
    """

    def __init__(self, model: str, temperature: float = 0.3,
                 max_tokens: int = 8192, request_timeout: int = 60) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        self._call_count = 0

    @abstractmethod
    async def generate(self, prompt: str, system: Optional[str] = None,
                       **kwargs: Any) -> str:
        """Generate a text response from the AI provider.
        
        Args:
            prompt: The user prompt text.
            system: Optional system/instruction prompt.
            **kwargs: Provider-specific options.
            
        Returns:
            Generated text response.
        """
        ...

    async def generate_structured(self, prompt: str,
                                  schema: Type[BaseModel],
                                  system: Optional[str] = None,
                                  **kwargs: Any) -> BaseModel:
        """Generate a structured response conforming to a Pydantic schema.
        
        Default implementation: generate text, then parse as JSON into schema.
        Providers may override with native structured output support.
        """
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        structured_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: Respond ONLY with valid JSON matching this schema exactly. "
            f"Do not include any markdown formatting, code fences, or explanatory text.\n\n"
            f"JSON Schema:\n{schema_json}"
        )

        raw = await self.generate(structured_prompt, system=system, **kwargs)
        # Clean up common AI response artifacts
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
            return schema(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Structured output parse failed: %s — retrying with stricter prompt", e)
            # Retry once with emphasis
            retry_prompt = (
                f"{prompt}\n\n"
                f"You MUST respond with ONLY valid JSON. No other text. "
                f"Schema:\n{schema_json}"
            )
            raw2 = await self.generate(retry_prompt, system=system, **kwargs)
            cleaned2 = raw2.strip()
            if cleaned2.startswith("```json"):
                cleaned2 = cleaned2[7:]
            if cleaned2.startswith("```"):
                cleaned2 = cleaned2[3:]
            if cleaned2.endswith("```"):
                cleaned2 = cleaned2[:-3]
            cleaned2 = cleaned2.strip()
            data2 = json.loads(cleaned2)
            return schema(**data2)

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model configuration."""
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "call_count": self._call_count,
        }
