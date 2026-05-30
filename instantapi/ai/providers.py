"""Multi-provider LLM integration via LiteLLM."""

from __future__ import annotations

import json
import os
from typing import Any

import litellm
from pydantic import BaseModel

from instantapi.config import Config, LLMProvider, PROVIDER_ENV_KEYS

# Suppress LiteLLM verbose logging
litellm.suppress_debug_info = True
litellm.set_verbose = False


class LLMResponse(BaseModel):
    """Structured response from LLM."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] = {}


def _setup_env(config: Config) -> None:
    """Set environment variables for the chosen provider."""
    env_key = PROVIDER_ENV_KEYS.get(config.provider)
    if env_key and config.api_key:
        os.environ[env_key] = config.api_key

    # Ollama needs base URL
    if config.provider == LLMProvider.OLLAMA:
        os.environ.setdefault("OLLAMA_API_BASE", "http://localhost:11434")

    # Custom provider: user may set api_base for OpenAI-compatible endpoints
    # (e.g., LM Studio, vLLM, LocalAI, Oobabooga, etc.)
    if config.api_base:
        os.environ["OPENAI_API_BASE"] = config.api_base

    # If custom provider has an api_key, set it as generic key
    if config.provider == LLMProvider.CUSTOM and config.api_key:
        os.environ["OPENAI_API_KEY"] = config.api_key


async def ask_llm(
    prompt: str,
    config: Config,
    system: str = "You are a helpful assistant that extracts structured data from HTML.",
    temperature: float = 0.1,
    max_tokens: int = 4096,
    response_format: dict[str, Any] | None = None,
) -> LLMResponse:
    """Send a prompt to the configured LLM provider.

    Args:
        prompt: User prompt to send.
        config: InstantAPI config with provider details.
        system: System message for the LLM.
        temperature: Sampling temperature (lower = more deterministic).
        max_tokens: Maximum tokens in response.
        response_format: Optional JSON response format hint.

    Returns:
        LLMResponse with content and metadata.
    """
    _setup_env(config)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    kwargs: dict[str, Any] = {
        "model": config.litellm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Pass custom api_base directly to LiteLLM
    if config.api_base:
        kwargs["api_base"] = config.api_base

    # JSON mode where supported
    if response_format:
        kwargs["response_format"] = response_format

    response = await litellm.acompletion(**kwargs)

    return LLMResponse(
        content=response.choices[0].message.content or "",
        model=config.litellm_model,
        provider=config.provider.value,
        usage={
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        },
    )


_JSON_MODE_PROVIDERS = {LLMProvider.OPENAI, LLMProvider.ANTHROPIC}


async def ask_llm_json(
    prompt: str,
    config: Config,
    system: str = "You are a helpful assistant. Always respond with valid JSON.",
    temperature: float = 0.0,
) -> dict | list:
    """Send a prompt and parse the response as JSON.

    Falls back to extracting JSON from markdown code blocks if needed.
    Only enables JSON mode (response_format) for providers that support it.
    """
    use_json_mode = config.provider in _JSON_MODE_PROVIDERS
    response = await ask_llm(
        prompt=prompt,
        config=config,
        system=system,
        temperature=temperature,
        response_format={"type": "json_object"} if use_json_mode else None,
    )

    text = response.content.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` blocks
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    raise ValueError(f"LLM response is not valid JSON:\n{text[:500]}")
