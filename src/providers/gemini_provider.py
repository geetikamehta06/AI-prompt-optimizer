"""
Google Gemini AI provider implementation.
"""

from __future__ import annotations

import os
from typing import Any, Optional

from ..utils.logging_setup import get_logger
from .base import BaseProvider

logger = get_logger(__name__)


class GeminiProvider(BaseProvider):
    """Google Gemini AI provider using langchain-google-genai."""

    def __init__(self, model: str = "gemini-2.5-flash",
                 temperature: float = 0.3, max_tokens: int = 8192,
                 request_timeout: int = 60) -> None:
        super().__init__(model, temperature, max_tokens, request_timeout)
        self._llm = None
        self._init_llm()

    def _init_llm(self) -> None:
        """Initialize the LangChain Gemini LLM."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set — Gemini provider will fail on calls")
            return

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._llm = ChatGoogleGenerativeAI(
                model=self.model,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                google_api_key=api_key,
                timeout=self.request_timeout,
            )
            logger.info("Gemini provider initialized: model=%s", self.model)
        except Exception as e:
            logger.error("Failed to initialize Gemini provider: %s", e)

    async def generate(self, prompt: str, system: Optional[str] = None,
                       **kwargs: Any) -> str:
        """Generate text using Google Gemini."""
        if not self._llm:
            raise RuntimeError("Gemini provider not initialized. Check GOOGLE_API_KEY.")

        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))

        self._call_count += 1
        logger.debug("Gemini call #%d: prompt=%d chars", self._call_count, len(prompt))

        response = await self._llm.ainvoke(messages)
        return response.content
