"""SequentialPlanner — uses the model to decompose a goal into ordered steps."""

from __future__ import annotations

import json

import structlog

from core.model.base import Message, ModelOptions, ModelProvider
from core.planner.task_graph import NodeStatus, PlanNode, TaskGraph

log = structlog.get_logger(__name__)

_SYSTEM_PROMPT = """You are a task planner. Given a goal, break it into a numbered list of
concrete steps. Each step must specify:
- description: what to do
- task_type: one of [reasoning, tool_call, file_op, memory_op, api_call, delegate]
- tool_id: (optional) specific tool or skill to use
- inputs: (optional) dict of inputs for this step

Respond ONLY with a valid JSON array of step objects. Example:
[
  {"description": "Search for X", "task_type": "tool_call", "tool_id": "web_search", "inputs": {"query": "X"}},
  {"description": "Summarize results", "task_type": "reasoning", "inputs": {}}
]"""


class SequentialPlanner:
    def __init__(self, model: ModelProvider) -> None:
        self._model = model

    def plan(self, goal: str, inputs: dict, context: dict | None = None) -> TaskGraph:
        log.info("planner.planning", goal=goal[:80])
        messages = [
            Message(role="system", content=_SYSTEM_PROMPT),
            Message(role="user", content=f"Goal: {goal}\nInputs: {json.dumps(inputs)}"),
        ]
        response = self._model.complete(messages, ModelOptions(temperature=0.2, max_tokens=2048))
        steps = self._parse(response.content)

        graph = TaskGraph(goal=goal)
        prev_id: str | None = None
        for step in steps:
            node = PlanNode(
                description=step.get("description", ""),
                task_type=step.get("task_type", "generic"),
                tool_id=step.get("tool_id"),
                inputs={**inputs, **step.get("inputs", {})},
                depends_on=[prev_id] if prev_id else [],
            )
            graph.add_node(node)
            prev_id = node.node_id

        log.info("planner.done", steps=len(graph.nodes))
        return graph

    def _parse(self, content: str) -> list[dict]:
        # Strip markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            content = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            log.warning("planner.parse_failed", raw=content[:200])
            return [{"description": content, "task_type": "reasoning"}]
