"""The LLM boundary. PLAN.md D10.

Two implementations from day one - the real one and a fake - so no test spends
money or needs a network, and so the deterministic fallbacks (D12) can be
exercised by simply making the fake fail.
"""

from __future__ import annotations

import json
import os
from typing import Protocol, TypeVar

from pydantic import BaseModel

from app.core.errors import AppError

T = TypeVar("T", bound=BaseModel)

# Sec 21.5 - a request that hangs is worse than one that fails.
REQUEST_TIMEOUT_SECONDS = 20.0
MAX_OUTPUT_TOKENS = 4096


class LLMUnavailable(AppError):
    status_code = 503
    code = "ai_unavailable"


class LLMClient(Protocol):
    def structured(self, *, system: str, user: str, schema: type[T]) -> T: ...
    def prose(self, *, system: str, user: str) -> str: ...
    @property
    def available(self) -> bool: ...


class AnthropicClient:
    """Claude, with structured outputs and adaptive thinking.

    Plan generation and progress analysis are the two places this product is
    either good or embarrassing, and both are reasoning tasks over a
    constrained candidate set - so the default is the most capable model, and
    trading that for cost is a decision for the user rather than a default
    buried here.
    """

    MODEL = "claude-opus-5"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model or os.environ.get("GEEKTRAINER_AI_MODEL") or self.MODEL
        self._client = None

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def _sdk(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(
                api_key=self._api_key, timeout=REQUEST_TIMEOUT_SECONDS
            )
        return self._client

    def structured(self, *, system: str, user: str, schema: type[T]) -> T:
        if not self.available:
            raise LLMUnavailable("No AI provider is configured.")
        import anthropic

        try:
            response = self._sdk().messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                thinking={"type": "adaptive"},
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": schema.model_json_schema(),
                    }
                },
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise LLMUnavailable(f"The AI service failed: {exc}") from exc

        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        try:
            return schema.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMUnavailable("The AI returned something unusable.") from exc

    def prose(self, *, system: str, user: str) -> str:
        if not self.available:
            raise LLMUnavailable("No AI provider is configured.")
        import anthropic

        try:
            response = self._sdk().messages.create(
                model=self.model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system,
                thinking={"type": "adaptive"},
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:
            raise LLMUnavailable(f"The AI service failed: {exc}") from exc
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )


class FakeLLMClient:
    """Scripted responses for tests. Set `fail=True` to exercise the
    deterministic fallbacks (D12)."""

    def __init__(self, responses: list[BaseModel | str] | None = None, *, fail: bool = False):
        self.responses = list(responses or [])
        self.fail = fail
        self.calls: list[dict] = []

    @property
    def available(self) -> bool:
        return not self.fail

    def _next(self, system: str, user: str):
        self.calls.append({"system": system, "user": user})
        if self.fail:
            raise LLMUnavailable("The AI service is unavailable.")
        if not self.responses:
            raise LLMUnavailable("The fake client has no scripted response left.")
        return self.responses.pop(0)

    def structured(self, *, system: str, user: str, schema: type[T]) -> T:
        result = self._next(system, user)
        if isinstance(result, schema):
            return result
        return schema.model_validate(result)

    def prose(self, *, system: str, user: str) -> str:
        return str(self._next(system, user))


_client: LLMClient | None = None


def get_client() -> LLMClient:
    global _client
    if _client is None:
        _client = AnthropicClient()
    return _client


def set_client(client: LLMClient | None) -> None:
    global _client
    _client = client
