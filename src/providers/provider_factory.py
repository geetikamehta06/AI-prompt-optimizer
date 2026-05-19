"""
Provider factory — creates AI provider instances by name.

Uses a registry pattern so adding a new provider only requires:
1. Create a new provider class extending BaseProvider
2. Register it here
"""

from __future__ import annotations

from typing import Optional

from ..utils.config import ProviderConfig, get_config
from ..utils.logging_setup import get_logger
from .base import BaseProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

logger = get_logger(__name__)

# ── Provider Registry ───────────────────────────────────────
# To add a new provider: import it and add an entry here.
_PROVIDER_REGISTRY: dict[str, type[BaseProvider]] = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}


def create_provider(name: Optional[str] = None,
                    config: Optional[ProviderConfig] = None) -> BaseProvider:
    """Create an AI provider by name.
    
    Args:
        name: Provider name (e.g., 'gemini', 'openai'). 
              Defaults to config default.
        config: Provider-specific config. Defaults to app config.
    """
    app_config = get_config()

    if name is None:
        name = app_config.providers.default

    if name not in _PROVIDER_REGISTRY:
        available = ", ".join(_PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown provider '{name}'. Available: {available}")

    if config is None:
        config = getattr(app_config.providers, name, ProviderConfig())

    provider_class = _PROVIDER_REGISTRY[name]
    provider = provider_class(
        model=config.model,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        request_timeout=config.request_timeout,
    )

    logger.info("Created provider: %s (model=%s)", name, config.model)
    return provider


def list_providers() -> list[str]:
    """List all registered provider names."""
    return list(_PROVIDER_REGISTRY.keys())


def register_provider(name: str, provider_class: type[BaseProvider]) -> None:
    """Register a new provider type."""
    _PROVIDER_REGISTRY[name] = provider_class
    logger.info("Registered provider: %s", name)
