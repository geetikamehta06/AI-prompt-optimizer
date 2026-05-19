"""
OpenAI provider implementation.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ..utils.logging_setup import get_logger
from .base import BaseProvider

logger = get_logger(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI AI provider using langchain-openai."""

    def __init__(self, model: str = "gpt-4o-mini",
                 temperature: float = 0.3, max_tokens: int = 4096,
                 request_timeout: int = 60) -> None:
        super().__init__(model, temperature, max_tokens, request_timeout)
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        """Initialize the LangChain OpenAI LLM."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set — OpenAI provider will fail on calls")
            return

        try:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_key=api_key,
                timeout=self.request_timeout,
            )
            logger.info("OpenAI provider initialized: model=%s", self.model)
        except Exception as e:
            logger.error("Failed to initialize OpenAI provider: %s", e)

    async def generate(self, prompt: str, system: Optional[str] = None,
                       **kwargs: Any) -> str:
        """Generate text using OpenAI."""
        if not self._llm:
            raise RuntimeError("OpenAI provider not initialized. Check OPENAI_API_KEY.")

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        self._call_count += 1
        logger.debug("OpenAI call #%d: prompt=%d chars", self._call_count, len(prompt))

        response = await self._llm.ainvoke(messages)
        return response.content
