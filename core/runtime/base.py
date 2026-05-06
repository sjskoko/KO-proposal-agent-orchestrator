"""Runtime interface — all runtimes must implement this contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class RuntimeCall:
    runtime_id: str
    operation: str
    params: dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""
    session_id: str = ""
    timeout_seconds: float | None = None


@dataclass
class RuntimeResult:
    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class RuntimeInterface(Protocol):
    runtime_id: str
    capabilities: list[str]

    def execute(self, call: RuntimeCall) -> RuntimeResult: ...
    def health_check(self) -> HealthStatus: ...
    def configure(self, config: dict) -> None: ...
