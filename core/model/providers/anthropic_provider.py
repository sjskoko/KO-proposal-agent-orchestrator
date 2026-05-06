"""Anthropic provider (fallback / specialist)."""

from __future__ import annotations

import os
from typing import Iterator

import structlog

from core.model.base import Message, ModelOptions, ModelResponse

log = structlog.get_logger(__name__)

_SYSTEM_ROLE = "system"


class AnthropicProvider:
    name = "anthropic_sonnet"

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")

    def _client(self):
        import anthropic  # type: ignore[import]
        return anthropic.Anthropic(api_key=self._api_key)

    def complete(self, messages: list[Message], options: ModelOptions | None = None) -> ModelResponse:
        opts = options or ModelOptions()
        system_prompt = next((m.content for m in messages if m.role == _SYSTEM_ROLE), "")
        user_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != _SYSTEM_ROLE]

        response = self._client().messages.create(
            model=self.model,
            max_tokens=opts.max_tokens,
            system=system_prompt,
            messages=user_msgs,  # type: ignore[arg-type]
        )
        content = response.content[0].text if response.content else ""
        return ModelResponse(
            content=content,
            model=self.model,
            provider=self.name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            finish_reason=response.stop_reason or "stop",
        )

    def stream(self, messages: list[Message], options: ModelOptions | None = None) -> Iterator[str]:
        opts = options or ModelOptions()
        system_prompt = next((m.content for m in messages if m.role == _SYSTEM_ROLE), "")
        user_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != _SYSTEM_ROLE]

        with self._client().messages.stream(
            model=self.model,
            max_tokens=opts.max_tokens,
            system=system_prompt,
            messages=user_msgs,  # type: ignore[arg-type]
        ) as stream:
            yield from stream.text_stream

    def health_check(self) -> bool:
        return bool(self._api_key)
