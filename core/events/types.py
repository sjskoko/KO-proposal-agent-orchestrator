"""Typed event definitions for the agent event bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Union
import uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid.uuid4())


@dataclass
class BaseEvent:
    event_id: str = field(default_factory=_uid)
    timestamp: datetime = field(default_factory=_now)
    agent_id: str = ""
    session_id: str = ""


@dataclass
class AgentStartedEvent(BaseEvent):
    goal: str = ""


@dataclass
class AgentDoneEvent(BaseEvent):
    success: bool = True
    summary: str = ""


@dataclass
class TaskDispatchedEvent(BaseEvent):
    task_id: str = ""
    task_type: str = ""
    runtime_id: str = ""


@dataclass
class ToolCalledEvent(BaseEvent):
    tool_id: str = ""
    inputs: dict = field(default_factory=dict)
    outputs: Any = None
    latency_ms: float = 0.0
    success: bool = True


@dataclass
class ModelQueriedEvent(BaseEvent):
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


@dataclass
class StepFailedEvent(BaseEvent):
    task_id: str = ""
    error_type: str = ""
    error_message: str = ""
    retriable: bool = True


@dataclass
class PermissionDeniedEvent(BaseEvent):
    capability: str = ""
    requested_by: str = ""


Event = Union[
    AgentStartedEvent,
    AgentDoneEvent,
    TaskDispatchedEvent,
    ToolCalledEvent,
    ModelQueriedEvent,
    StepFailedEvent,
    PermissionDeniedEvent,
]
