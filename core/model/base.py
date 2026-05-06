"""Model provider interface — all local and API models share this contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Literal, Protocol, runtime_checkable


@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ModelOptions:
    temperature: float = 0.7
    max_tokens: int = 4096
    stop: list[str] = field(default_factory=list)
    stream: bool = False
    # Passed through to provider if supported
    extra: dict = field(default_factory=dict)


@dataclass
class ModelResponse:
    content: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"
    raw: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@runtime_checkable
class ModelProvider(Protocol):
    """Every model backend — local or API — must satisfy this interface."""

    name: str

    def complete(
        self,
        messages: list[Message],
        options: ModelOptions | None = None,
    ) -> ModelResponse: ...

    def stream(
        self,
        messages: list[Message],
        options: ModelOptions | None = None,
    ) -> Iterator[str]: ...

    def health_check(self) -> bool: ...
