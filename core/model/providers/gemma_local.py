"""Gemma 4 provider via Ollama (default local backend)."""

from __future__ import annotations

from typing import Iterator

import structlog

from core.model.base import Message, ModelOptions, ModelResponse

log = structlog.get_logger(__name__)


class GemmaLocalProvider:
    """Talks to a locally running Ollama instance."""

    name = "gemma4_local"

    def __init__(self, model: str = "gemma4:27b", base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url
        self._client = None  # lazy init

    # ------------------------------------------------------------------

    def complete(self, messages: list[Message], options: ModelOptions | None = None) -> ModelResponse:
        import ollama  # type: ignore[import]

        opts = options or ModelOptions()
        ollama_msgs = [{"role": m.role, "content": m.content} for m in messages]

        log.debug("gemma_local.complete", model=self.model, n_messages=len(messages))
        response = ollama.chat(
            model=self.model,
            messages=ollama_msgs,
            options={"temperature": opts.temperature, "num_predict": opts.max_tokens},
        )
        msg = response["message"]
        return ModelResponse(
            content=msg["content"],
            model=self.model,
            provider=self.name,
            raw=response,
        )

    def stream(self, messages: list[Message], options: ModelOptions | None = None) -> Iterator[str]:
        import ollama  # type: ignore[import]

        opts = options or ModelOptions()
        ollama_msgs = [{"role": m.role, "content": m.content} for m in messages]

        for chunk in ollama.chat(
            model=self.model,
            messages=ollama_msgs,
            stream=True,
            options={"temperature": opts.temperature},
        ):
            yield chunk["message"]["content"]

    def health_check(self) -> bool:
        try:
            import ollama  # type: ignore[import]

            models = ollama.list()
            names = [m["name"] for m in models.get("models", [])]
            return any(self.model in n for n in names)
        except Exception as exc:
            log.warning("gemma_local.health_check_failed", error=str(exc))
            return False
