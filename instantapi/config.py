"""Configuration management for InstantAPI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

APP_DIR = Path.home() / ".instantapi"
CONFIG_FILE = APP_DIR / "config.json"
DB_FILE = APP_DIR / "instantapi.db"
CACHE_DIR = APP_DIR / "cache"


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    GROQ = "groq"
    TOGETHER = "together_ai"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"  # Any LiteLLM-compatible model string


# LiteLLM model mapping per provider (defaults)
PROVIDER_MODELS: dict[str, str] = {
    LLMProvider.OLLAMA: "ollama/llama3.1",
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    LLMProvider.GEMINI: "gemini/gemini-2.0-flash",
    LLMProvider.GROQ: "groq/llama-3.1-70b-versatile",
    LLMProvider.TOGETHER: "together_ai/meta-llama/Llama-3.1-70B-Instruct-Turbo",
    LLMProvider.DEEPSEEK: "deepseek/deepseek-chat",
    LLMProvider.CUSTOM: "",  # User must provide model string
}

PROVIDER_ENV_KEYS: dict[str, str | None] = {
    LLMProvider.OLLAMA: None,  # No API key needed
    LLMProvider.OPENAI: "OPENAI_API_KEY",
    LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
    LLMProvider.GEMINI: "GEMINI_API_KEY",
    LLMProvider.GROQ: "GROQ_API_KEY",
    LLMProvider.TOGETHER: "TOGETHER_API_KEY",
    LLMProvider.DEEPSEEK: "DEEPSEEK_API_KEY",
    LLMProvider.CUSTOM: None,  # User sets env vars manually
}


@dataclass
class Config:
    provider: LLMProvider = LLMProvider.OLLAMA
    model: str = ""
    api_key: str = ""
    api_base: str = ""  # Custom API base URL (for self-hosted / custom providers)
    api_port: int = 3000
    max_pages: int = 10
    timeout: int = 30
    cache_ttl: int = 3600  # 1 hour
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.model:
            self.model = PROVIDER_MODELS.get(self.provider, "ollama/llama3.1")

    @property
    def litellm_model(self) -> str:
        """Return the model string LiteLLM expects.

        For custom providers, the model string is passed directly to LiteLLM.
        This means users can use ANY model format LiteLLM supports, e.g.:
          - "openai/my-model" for OpenAI-compatible endpoints
          - "huggingface/bigscience/bloom"
          - "vllm/facebook/opt-6.7b"
          - Any custom string with api_base set
        """
        if self.provider == LLMProvider.CUSTOM:
            return self.model
        if self.provider == LLMProvider.OLLAMA and "/" not in self.model:
            return f"ollama/{self.model}"
        return self.model

    def save(self) -> None:
        """Persist config to disk."""
        APP_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "provider": self.provider.value,
            "model": self.model,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "api_port": self.api_port,
            "max_pages": self.max_pages,
            "timeout": self.timeout,
            "cache_ttl": self.cache_ttl,
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> Config:
        """Load config from disk, or return defaults."""
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            provider_str = data.get("provider", "ollama")
            try:
                provider = LLMProvider(provider_str)
            except ValueError:
                # Unknown provider string -> treat as custom
                provider = LLMProvider.CUSTOM
            return cls(
                provider=provider,
                model=data.get("model", ""),
                api_key=data.get("api_key", ""),
                api_base=data.get("api_base", ""),
                api_port=data.get("api_port", 3000),
                max_pages=data.get("max_pages", 10),
                timeout=data.get("timeout", 30),
                cache_ttl=data.get("cache_ttl", 3600),
            )
        except (json.JSONDecodeError, ValueError):
            return cls()
