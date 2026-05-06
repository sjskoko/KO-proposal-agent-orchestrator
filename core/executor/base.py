"""Executor — walks a TaskGraph and dispatches each node."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog

from core.executor.retry import RetryPolicy, with_retry
from core.events.types import StepFailedEvent, TaskDispatchedEvent
from core.planner.task_graph import NodeStatus, TaskGraph
from core.runtime.base import RuntimeCall
from core.tooling.base import ToolCall

if TYPE_CHECKING:
    from core.agent.base import Agent

log = structlog.get_logger(__name__)

_DEFAULT_RETRY = RetryPolicy(max_attempts=3, backoff="exponential", base_ms=500)


class Executor:
    def __init__(self, runtime_registry, tool_registry, retry_policy: RetryPolicy | None = None) -> None:
        self._runtimes = runtime_registry
        self._tools = tool_registry
        self._retry = retry_policy or _DEFAULT_RETRY

    def run(self, graph: TaskGraph, agent: "Agent") -> Any:
        last_result: Any = None

        while not graph.is_complete():
            ready = graph.ready_nodes()
            if not ready:
                if not graph.is_complete():
                    log.error("executor.deadlock", summary=graph.summary())
                    raise RuntimeError(f"Executor deadlock: {graph.summary()}")
                break

            for node in ready:
                node.status = NodeStatus.RUNNING
                agent.bus.publish(TaskDispatchedEvent(
                    agent_id=agent.definition.id,
                    session_id=agent.session_id,
                    task_id=node.node_id,
                    task_type=node.task_type,
                    runtime_id=node.runtime_id,
                ))
                t0 = time.monotonic()
                try:
                    result = with_retry(lambda: self._dispatch(node, agent), self._retry)
                    node.result = result
                    node.status = NodeStatus.DONE
                    last_result = result
                    log.info("executor.step_done", node=node.node_id, ms=int((time.monotonic()-t0)*1000))
                except Exception as exc:
                    node.error = str(exc)
                    node.status = NodeStatus.FAILED
                    agent.bus.publish(StepFailedEvent(
                        agent_id=agent.definition.id,
                        session_id=agent.session_id,
                        task_id=node.node_id,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    ))
                    log.error("executor.step_failed", node=node.node_id, error=str(exc))

        if graph.has_failures():
            raise RuntimeError(f"Executor failed: {graph.summary()}")

        return last_result

    # ------------------------------------------------------------------

    def _dispatch(self, node, agent: "Agent") -> Any:
        if node.tool_id:
            call = ToolCall(tool_id=node.tool_id, inputs=node.inputs, agent_id=agent.definition.id)
            result = self._tools.call(call)
            if not result.success:
                raise RuntimeError(result.error)
            return result.output

        if node.runtime_id:
            call = RuntimeCall(
                runtime_id=node.runtime_id,
                operation=node.task_type,
                params=node.inputs,
                agent_id=agent.definition.id,
                session_id=agent.session_id,
            )
            result = self._runtimes.execute(call)
            if not result.success:
                raise RuntimeError(result.error)
            return result.data

        # Fallback: return inputs as-is (no-op node)
        return node.inputs
