"""Sub-agent delegation interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class DelegatedTask:
    task_id: str
    agent_id: str           # target sub-agent
    goal: str
    inputs: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float | None = None


@dataclass
class DelegationResult:
    task_id: str
    agent_id: str
    success: bool
    output: Any = None
    error: str | None = None
    steps_taken: int = 0


@runtime_checkable
class TaskDelegationInterface(Protocol):
    def delegate(self, task: DelegatedTask) -> DelegationResult: ...
    def list_available_agents(self) -> list[str]: ...
