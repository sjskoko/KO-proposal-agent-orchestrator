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

Important constraints:
- Do NOT invent tool IDs.
- Only set tool_id when you are fully certain it exists in the provided allowed_tools list.
- If unsure, omit tool_id and use task_type=reasoning.

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
        allowed_tools = self._extract_allowed_tools(context or {})
        messages = [
            Message(role="system", content=_SYSTEM_PROMPT),
            Message(
                role="user",
                content=(
                    f"Goal: {goal}\n"
                    f"Inputs: {json.dumps(inputs)}\n"
                    f"allowed_tools: {json.dumps(allowed_tools)}"
                ),
            ),
        ]
        response = self._model.complete(messages, ModelOptions(temperature=0.2, max_tokens=512))
        steps = self._parse(response.content)
        steps = self._sanitize_steps(steps, allowed_tools)

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

    @staticmethod
    def _extract_allowed_tools(context: dict) -> list[str]:
        agent = context.get("agent")
        if agent is None:
            return []
        tool_ids = getattr(agent, "tools", [])
        if not isinstance(tool_ids, list):
            return []
        return [str(t) for t in tool_ids]

    @staticmethod
    def _sanitize_steps(steps: list[dict], allowed_tools: list[str]) -> list[dict]:
        allowed_set = set(allowed_tools)
        sanitized: list[dict] = []
        for step in steps:
            current = dict(step)
            tool_id = current.get("tool_id")
            if tool_id and tool_id not in allowed_set:
                log.warning("planner.unknown_tool_id", tool_id=tool_id)
                current.pop("tool_id", None)
                current["task_type"] = "reasoning"
            sanitized.append(current)
        return sanitized

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
