"""Agent state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    WAITING = "waiting"       # waiting for sub-agent
    DONE = "done"
    FAILED = "failed"


@dataclass
class AgentState:
    agent_id: str
    session_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_goal: str = ""
    step_index: int = 0
    total_steps: int = 0
    last_result: Any = None
    errors: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def transition(self, new_status: AgentStatus) -> None:
        if new_status == AgentStatus.EXECUTING and self.started_at is None:
            self.started_at = datetime.now(timezone.utc)
        if new_status in (AgentStatus.DONE, AgentStatus.FAILED):
            self.finished_at = datetime.now(timezone.utc)
        self.status = new_status

    def is_terminal(self) -> bool:
        return self.status in (AgentStatus.DONE, AgentStatus.FAILED)
