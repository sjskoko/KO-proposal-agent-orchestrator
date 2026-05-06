"""Agent — lifecycle orchestration gluing all core components together."""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from core.agent.definition import AgentDefinition
from core.agent.state import AgentState, AgentStatus
from core.events.bus import EventBus
from core.events.types import AgentDoneEvent, AgentStartedEvent
from core.permissions.checker import PermissionChecker

log = structlog.get_logger(__name__)


class Agent:
    def __init__(
        self,
        definition: AgentDefinition,
        event_bus: EventBus,
        planner=None,
        executor=None,
    ) -> None:
        self.definition = definition
        self.session_id = str(uuid.uuid4())
        self.state = AgentState(
            agent_id=definition.id,
            session_id=self.session_id,
        )
        self.bus = event_bus
        self.planner = planner
        self.executor = executor
        self.permissions = PermissionChecker(definition.id, definition.permissions)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, goal: str, inputs: dict | None = None) -> Any:
        """Synchronous entry point — plan then execute."""
        self._start(goal)
        try:
            plan = self._plan(goal, inputs or {})
            result = self._execute(plan)
            self._finish(success=True, summary=str(result))
            return result
        except Exception as exc:
            self.state.errors.append(str(exc))
            self._finish(success=False, summary=str(exc))
            raise

    # ------------------------------------------------------------------
    # Internal lifecycle
    # ------------------------------------------------------------------

    def _start(self, goal: str) -> None:
        self.state.current_goal = goal
        self.state.transition(AgentStatus.PLANNING)
        self.bus.publish(AgentStartedEvent(
            agent_id=self.definition.id,
            session_id=self.session_id,
            goal=goal,
        ))
        log.info("agent.started", agent=self.definition.id, goal=goal[:80])

    def _plan(self, goal: str, inputs: dict) -> Any:
        if self.planner is None:
            return [{"goal": goal, "inputs": inputs}]
        return self.planner.plan(goal, inputs, context={"agent": self.definition})

    def _execute(self, plan: Any) -> Any:
        self.state.transition(AgentStatus.EXECUTING)
        if self.executor is None:
            return plan
        return self.executor.run(plan, agent=self)

    def _finish(self, success: bool, summary: str) -> None:
        self.state.transition(AgentStatus.DONE if success else AgentStatus.FAILED)
        self.bus.publish(AgentDoneEvent(
            agent_id=self.definition.id,
            session_id=self.session_id,
            success=success,
            summary=summary,
        ))
        log.info("agent.finished", agent=self.definition.id, success=success)
