"""LLM provider abstraction with DeepSeek integration."""

import hashlib
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """A single message in an LLM conversation."""
    role: str  # system, user, assistant, tool
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: str = "stop"
    latency_ms: float = 0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
            "request_id": self.request_id,
        }


class BaseLLMProvider(ABC):
    """Abstract base for LLM providers (OpenAI, DeepSeek, vLLM, etc.)."""

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Send a chat completion request."""
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs,
    ):
        """Stream a chat completion response."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek API provider (deepseek-chat)."""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = "deepseek-chat"
        self._client = None

    @property
    def provider_name(self) -> str:
        return "deepseek"

    async def _get_client(self):
        if self._client is None:
            try:
                import httpx
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=120.0,
                )
            except ImportError:
                raise RuntimeError("httpx required for DeepSeek provider")
        return self._client

    async def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        import time
        start = time.perf_counter()

        payload = {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        try:
            client = await self._get_client()
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            latency = (time.perf_counter() - start) * 1000

            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", model or self.default_model),
                usage=data.get("usage", {}),
                finish_reason=choice.get("finish_reason", "stop"),
                latency_ms=latency,
            )
        except Exception as e:
            logger.error("DeepSeek API error: %s", e)
            # Fallback: return a simulated response for development
            latency = (time.perf_counter() - start) * 1000
            return LLMResponse(
                content=f"[DEV MODE] Simulated DeepSeek response for: {messages[-1].content[:100] if messages else 'empty'}",
                model=model or self.default_model,
                usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                finish_reason="stop",
                latency_ms=latency,
            )

    async def stream_chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs,
    ):
        payload = {
            "model": model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4096),
            "stream": True,
        }

        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error("DeepSeek stream error: %s", e)
            yield f"[DEV MODE] Stream error: {e}"


class SimulatedProvider(BaseLLMProvider):
    """Simulated LLM provider for development/testing."""

    def __init__(self):
        self.default_model = "simulated-v1"

    @property
    def provider_name(self) -> str:
        return "simulated"

    async def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> LLMResponse:
        import time, random
        start = time.perf_counter()

        # Simulate processing delay
        await __import__('asyncio').sleep(random.uniform(0.1, 0.5))

        last_msg = messages[-1].content if messages else "empty"
        latency = (time.perf_counter() - start) * 1000

        return LLMResponse(
            content=f'{{"analysis": "Simulated analysis of: {last_msg[:80]}...", '
                    f'"confidence": {random.uniform(0.7, 0.99):.2f}, '
                    f'"action": "processed", '
                    f'"timestamp": "{datetime.now(timezone.utc).isoformat()}"}}',
            model=model or self.default_model,
            usage={"prompt_tokens": len(last_msg) // 4, "completion_tokens": 100, "total_tokens": len(last_msg) // 4 + 100},
            finish_reason="stop",
            latency_ms=latency,
        )

    async def stream_chat(self, messages, model=None, **kwargs):
        import asyncio, random
        words = ["Analyzing", "input", "data", "processing", "request", "generating", "response"]
        for word in words:
            yield word + " "
            await asyncio.sleep(random.uniform(0.05, 0.15))


# Global provider factory
_global_provider: Optional[BaseLLMProvider] = None


def get_llm_provider(provider_type: str = None, **kwargs) -> BaseLLMProvider:
    """Get or create an LLM provider instance. Auto-detects DeepSeek if key set."""
    global _global_provider
    if provider_type is None:
        # Auto-detect: use DeepSeek if API key is configured
        import os as _os
        provider_type = "deepseek" if _os.getenv("DEEPSEEK_API_KEY") else "simulated"

    if _global_provider is not None:
        return _global_provider

    if provider_type == "deepseek":
        _global_provider = DeepSeekProvider(
            api_key=kwargs.get("api_key", ""),
            base_url=kwargs.get("base_url", "https://api.deepseek.com/v1"),
        )
    elif provider_type == "simulated":
        _global_provider = SimulatedProvider()
    else:
        _global_provider = SimulatedProvider()

    return _global_provider
