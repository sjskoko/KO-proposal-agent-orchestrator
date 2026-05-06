"""Unit tests for Executor failure propagation."""

import pytest

from core.executor.base import Executor
from core.planner.task_graph import PlanNode, TaskGraph


class _FakeBus:
    def publish(self, event) -> None:
        return None


class _FakeAgentDefinition:
    id = "agent"


class _FakeAgent:
    definition = _FakeAgentDefinition()
    session_id = "sess"
    bus = _FakeBus()


class _FakeRuntimeRegistry:
    def execute(self, call):
        raise RuntimeError("runtime should not be called")


class _FakeToolResult:
    def __init__(self, success: bool, error: str = "") -> None:
        self.success = success
        self.error = error
        self.output = None


class _FailingToolRegistry:
    def call(self, call):
        return _FakeToolResult(False, "boom")


class _OkToolRegistry:
    def call(self, call):
        return _FakeToolResult(True)


def test_executor_raises_when_node_fails() -> None:
    graph = TaskGraph(goal="g")
    graph.add_node(PlanNode(description="t", task_type="tool_call", tool_id="x", inputs={}))
    executor = Executor(runtime_registry=_FakeRuntimeRegistry(), tool_registry=_FailingToolRegistry())

    with pytest.raises(RuntimeError, match="Executor failed"):
        executor.run(graph, agent=_FakeAgent())


def test_executor_raises_on_deadlock() -> None:
    graph = TaskGraph(goal="g")
    graph.add_node(
        PlanNode(description="blocked", task_type="reasoning", depends_on=["missing-node"], inputs={})
    )
    executor = Executor(runtime_registry=_FakeRuntimeRegistry(), tool_registry=_OkToolRegistry())

    with pytest.raises(RuntimeError, match="Executor deadlock"):
        executor.run(graph, agent=_FakeAgent())
