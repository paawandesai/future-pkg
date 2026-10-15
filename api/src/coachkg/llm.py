"""Thin wrapper over the Anthropic SDK: structured output only, no free text reaches the UI.

The key is read from ANTHROPIC_FUTURE_API_KEY and never logged. Prompts and outputs are never
logged either; only model id, latency and token counts are kept for the trace.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

import anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
Effort = Literal["low", "medium", "high"]

# Models that accept the server-side refusal fallback (`fallbacks: "default"`).
_FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LLMError(RuntimeError):
    """The model call failed or returned nothing usable. Callers fail closed."""


@dataclass(frozen=True)
class CallStats:
    purpose: str
    model: str
    served_by: str
    ms: int
    input_tokens: int
    output_tokens: int


class LLM:
    def __init__(self, client: anthropic.AsyncAnthropic | None = None, timeout_s: float = 30.0) -> None:
        if client is None:
            key = os.environ.get("ANTHROPIC_FUTURE_API_KEY")
            if not key:
                raise LLMError("ANTHROPIC_FUTURE_API_KEY is not set")
            client = anthropic.AsyncAnthropic(api_key=key, timeout=timeout_s, max_retries=1)
        self.client = client

    async def parse(
        self,
        *,
        purpose: str,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        effort: Effort = "low",
        max_tokens: int = 4000,
    ) -> tuple[T, CallStats]:
        t0 = time.perf_counter()
        try:
            if model in _FALLBACK_MODELS:
                resp = await self.client.beta.messages.parse(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_format=schema,
                    output_config={"effort": effort},
                    betas=[_FALLBACK_BETA],
                    fallbacks="default",
                )
            else:
                resp = await self.client.messages.parse(  # type: ignore[assignment]
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_format=schema,
                    output_config={"effort": effort},
                )
        except anthropic.APIError as exc:
            raise LLMError(f"{purpose}: {type(exc).__name__}") from exc
        ms = int((time.perf_counter() - t0) * 1000)
        if resp.stop_reason == "refusal":
            raise LLMError(f"{purpose}: model declined")
        if resp.stop_reason == "max_tokens" or resp.parsed_output is None:
            raise LLMError(f"{purpose}: no structured output")
        stats = CallStats(purpose, model, resp.model, ms, resp.usage.input_tokens, resp.usage.output_tokens)
        return resp.parsed_output, stats

    async def create(
        self,
        *,
        model: str,
        system: str,
        messages: list[Any],
        tools: list[dict[str, Any]],
        effort: Effort = "low",
        max_tokens: int = 4000,
    ) -> tuple[Any, int]:
        """One turn of a tool-use loop. Returns the raw response and its latency in ms."""
        t0 = time.perf_counter()
        kw: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": messages,
            "tools": tools,
            "output_config": {"effort": effort},
        }
        try:
            if model in _FALLBACK_MODELS:
                resp: Any = await self.client.beta.messages.create(
                    **kw, betas=[_FALLBACK_BETA], fallbacks="default"
                )
            else:
                resp = await self.client.messages.create(**kw)
        except anthropic.APIError as exc:
            raise LLMError(f"copilot: {type(exc).__name__}") from exc
        return resp, int((time.perf_counter() - t0) * 1000)
