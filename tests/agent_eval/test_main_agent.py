"""Agent eval — end-to-end scenarios against a stubbed model."""

from __future__ import annotations

import pytest

from core.agent.base import Agent
from core.agent.definition import AgentDefinition, ModelPolicy
from core.events.bus import EventBus
from core.events.types import AgentDoneEvent, AgentStartedEvent
from core.memory.base import MemoryScope
from core.permissions.base import PermissionSet


class _StubModel:
    name = "stub"

    def complete(self, messages, options=None):
        from core.model.base import ModelResponse
        return ModelResponse(content='[{"description":"do thing","task_type":"reasoning"}]', model="stub", provider="stub")

    def stream(self, messages, options=None):
        yield "stub"

    def health_check(self):
        return True


def _make_agent(event_bus) -> Agent:
    defn = AgentDefinition(
        id="test_agent",
        role="tester",
        goal="run tests",
        model_policy=ModelPolicy(preferred="stub"),
        memory_scope=MemoryScope.SESSION,
        permissions=PermissionSet.unrestricted(),
    )
    from core.planner.sequential import SequentialPlanner
    planner = SequentialPlanner(model=_StubModel())
    return Agent(definition=defn, event_bus=event_bus, planner=planner)


class TestMainAgent:
    def test_agent_emits_started_and_done_events(self):
        bus = EventBus()
        events = []
        bus.subscribe_all(events.append)

        agent = _make_agent(bus)
        agent.run("do something")

        types = [type(e).__name__ for e in events]
        assert "AgentStartedEvent" in types
        assert "AgentDoneEvent" in types

    def test_agent_done_event_is_success(self):
        bus = EventBus()
        done_events = []
        bus.subscribe(AgentDoneEvent, done_events.append)

        agent = _make_agent(bus)
        agent.run("simple task")

        assert done_events
        assert done_events[0].success

    def test_agent_state_transitions_to_done(self):
        bus = EventBus()
        agent = _make_agent(bus)
        agent.run("task")
        from core.agent.state import AgentStatus
        assert agent.state.status == AgentStatus.DONE
