"""
adapters/llm_adapters.py — Normalized LLM provider wrappers.
All adapters expose the same interface: generate(system, user, max_tokens) -> str
This lets agents swap providers without changing their logic.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

import anthropic
import httpx

logger = logging.getLogger(__name__)


class BaseLLMAdapter(ABC):
    """Normalized interface for any LLM provider."""

    provider: str = "base"

    @abstractmethod
    def generate(
        self,
        system: str,
        user: str,
        max_tokens: int = 2000,
        model: Optional[str] = None,
    ) -> str:
        ...

    def generate_json(self, system: str, user: str, max_tokens: int = 2000) -> str:
        """Generate and strip markdown code fences if present."""
        raw = self.generate(system, user, max_tokens)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return raw


class ClaudeAdapter(BaseLLMAdapter):
    """
    Anthropic Claude adapter.
    Best for: code, architecture, debate, orchestration.
    """
    provider = "claude"

    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY", ""))
        self.default_model = "claude-sonnet-4-5"

    def generate(self, system: str, user: str, max_tokens: int = 2000, model: Optional[str] = None) -> str:
        try:
            response = self.client.messages.create(
                model=model or self.default_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise


class DeepSeekAdapter(BaseLLMAdapter):
    """
    DeepSeek adapter (OpenAI-compatible API).
    Best for: research, long-context analysis, fact extraction.
    """
    provider = "deepseek"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = "https://api.deepseek.com/v1"
        self.default_model = "deepseek-chat"

    def generate(self, system: str, user: str, max_tokens: int = 2000, model: Optional[str] = None) -> str:
        if not self.api_key:
            logger.warning("DeepSeek API key not set — falling back to Claude")
            return ClaudeAdapter().generate(system, user, max_tokens)

        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": model or self.default_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise


class GeminiAdapter(BaseLLMAdapter):
    """
    Google Gemini adapter via REST API.
    Best for: multimodal content, creative tasks, audio/video generation prompts.
    """
    provider = "gemini"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.default_model = "gemini-1.5-flash"

    def generate(self, system: str, user: str, max_tokens: int = 2000, model: Optional[str] = None) -> str:
        if not self.api_key:
            logger.warning("Gemini API key not set — falling back to Claude")
            return ClaudeAdapter().generate(system, user, max_tokens)

        try:
            m = model or self.default_model
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    f"{self.base_url}/models/{m}:generateContent?key={self.api_key}",
                    json={
                        "contents": [
                            {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}
                        ],
                        "generationConfig": {
                            "maxOutputTokens": max_tokens,
                            "temperature": 0.4,
                        },
                    },
                )
                response.raise_for_status()
                return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI adapter — optional fallback."""
    provider = "openai"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = "https://api.openai.com/v1"
        self.default_model = "gpt-4o"

    def generate(self, system: str, user: str, max_tokens: int = 2000, model: Optional[str] = None) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key not set")
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": model or self.default_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]


# ── Factory ────────────────────────────────────────────────────────────────────

def get_adapter(provider: str = "claude") -> BaseLLMAdapter:
    """Return the appropriate adapter for a given provider string."""
    adapters = {
        "claude":   ClaudeAdapter,
        "deepseek": DeepSeekAdapter,
        "gemini":   GeminiAdapter,
        "openai":   OpenAIAdapter,
    }
    cls = adapters.get(provider.lower(), ClaudeAdapter)
    return cls()
