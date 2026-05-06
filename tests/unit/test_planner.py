"""Unit tests for SequentialPlanner guards."""

from core.model.base import ModelResponse
from core.planner.sequential import SequentialPlanner


class _StubModel:
    name = "stub"

    def __init__(self, content: str) -> None:
        self._content = content

    def complete(self, messages, options=None):
        return ModelResponse(content=self._content, model="stub", provider="stub")

    def stream(self, messages, options=None):
        yield self._content

    def health_check(self):
        return True


class _StubAgent:
    tools = ["read_file", "write_file"]


def test_planner_sanitizes_unknown_tool_id() -> None:
    planner = SequentialPlanner(
        model=_StubModel(
            '[{"description":"x","task_type":"tool_call","tool_id":"unit_test_framework","inputs":{}}]'
        )
    )

    graph = planner.plan("goal", {}, context={"agent": _StubAgent()})
    assert len(graph.nodes) == 1
    assert graph.nodes[0].tool_id is None
    assert graph.nodes[0].task_type == "reasoning"


def test_planner_keeps_allowed_tool_id() -> None:
    planner = SequentialPlanner(
        model=_StubModel(
            '[{"description":"x","task_type":"tool_call","tool_id":"read_file","inputs":{"path":"a"}}]'
        )
    )

    graph = planner.plan("goal", {}, context={"agent": _StubAgent()})
    assert graph.nodes[0].tool_id == "read_file"
    assert graph.nodes[0].task_type == "tool_call"
