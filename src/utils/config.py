"""
Configuration loader — loads and validates YAML config with Pydantic models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


# ── Pydantic Config Models ─────────────────────────────────

class ProviderConfig(BaseModel):
    """Configuration for a single AI provider."""
    model: str = "gemini-2.5-flash"
    temperature: float = 0.3
    max_tokens: int = 8192
    request_timeout: int = 60


class ProvidersConfig(BaseModel):
    """All AI provider configurations."""
    default: str = "gemini"
    gemini: ProviderConfig = Field(default_factory=lambda: ProviderConfig())
    openai: ProviderConfig = Field(default_factory=lambda: ProviderConfig(
        model="gpt-4o-mini", max_tokens=4096
    ))


class PipelineConfig(BaseModel):
    """Enhancement pipeline configuration."""
    refinement_rounds: int = 2
    quality_threshold: int = 80
    enable_evaluation: bool = True
    enable_refinement: bool = True
    enable_chaining: bool = True
    max_chain_depth: int = 3


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    enabled: bool = True
    requests_per_minute: int = 15
    burst_size: int = 5
    backoff_base: int = 2


class StorageConfig(BaseModel):
    """Storage configuration."""
    database_path: str = "data/enterprise_prompt.db"
    max_history_items: int = 1000


class SecurityConfig(BaseModel):
    """Security configuration."""
    max_prompt_length: int = 50000
    sanitize_inputs: bool = True
    log_prompts: bool = False


class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class AppConfig(BaseModel):
    """Root application configuration."""
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    rate_limiting: RateLimitConfig = Field(default_factory=RateLimitConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)


# ── Loader ──────────────────────────────────────────────────

_config_instance: Optional[AppConfig] = None


def load_config(config_path: str = "config/app_config.yaml") -> AppConfig:
    """Load and validate configuration from YAML file."""
    global _config_instance

    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        # Remove the top-level 'app' key if present (metadata only)
        raw.pop("app", None)
        _config_instance = AppConfig(**raw)
    else:
        _config_instance = AppConfig()

    return _config_instance


def get_config() -> AppConfig:
    """Get the current config instance (loads default if needed)."""
    global _config_instance
    if _config_instance is None:
        return load_config()
    return _config_instance
