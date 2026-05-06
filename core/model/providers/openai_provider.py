"""OpenAI provider (fallback / specialist)."""

from __future__ import annotations

import os
from typing import Iterator

import structlog

from core.model.base import Message, ModelOptions, ModelResponse

log = structlog.get_logger(__name__)


class OpenAIProvider:
    name = "openai_gpt4o"

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def _client(self):
        from openai import OpenAI  # type: ignore[import]
        return OpenAI(api_key=self._api_key)

    def complete(self, messages: list[Message], options: ModelOptions | None = None) -> ModelResponse:
        opts = options or ModelOptions()
        oai_msgs = [{"role": m.role, "content": m.content} for m in messages]

        response = self._client().chat.completions.create(
            model=self.model,
            messages=oai_msgs,  # type: ignore[arg-type]
            temperature=opts.temperature,
            max_tokens=opts.max_tokens,
        )
        choice = response.choices[0]
        usage = response.usage
        return ModelResponse(
            content=choice.message.content or "",
            model=self.model,
            provider=self.name,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            finish_reason=choice.finish_reason or "stop",
        )

    def stream(self, messages: list[Message], options: ModelOptions | None = None) -> Iterator[str]:
        opts = options or ModelOptions()
        oai_msgs = [{"role": m.role, "content": m.content} for m in messages]

        for chunk in self._client().chat.completions.create(
            model=self.model,
            messages=oai_msgs,  # type: ignore[arg-type]
            temperature=opts.temperature,
            stream=True,
        ):
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def health_check(self) -> bool:
        return bool(self._api_key)
