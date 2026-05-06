"""ToolRegistry — central catalogue of all available tools."""

from __future__ import annotations

import jsonschema  # type: ignore[import]
import structlog

from core.tooling.base import ToolCall, ToolDefinition, ToolResult

log = structlog.get_logger(__name__)


class ToolNotFoundError(Exception):
    pass


class ToolInputError(Exception):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, object] = {}  # tool_id -> callable

    def register(self, definition: ToolDefinition, handler) -> None:
        self._tools[definition.id] = definition
        self._handlers[definition.id] = handler
        log.info("tool.registered", id=definition.id, source=definition.source)

    def get(self, tool_id: str) -> ToolDefinition:
        if tool_id not in self._tools:
            raise ToolNotFoundError(f"Tool not registered: {tool_id}")
        return self._tools[tool_id]

    def list_tools(self, source: str | None = None) -> list[ToolDefinition]:
        tools = [t for t in self._tools.values() if t.enabled]
        if source:
            tools = [t for t in tools if t.source == source]
        return tools

    def call(self, call: ToolCall) -> ToolResult:
        defn = self.get(call.tool_id)
        self._validate_inputs(defn, call.inputs)
        handler = self._handlers[call.tool_id]
        try:
            output = handler(call.inputs)
            return ToolResult(tool_id=call.tool_id, call_id=call.call_id, success=True, output=output)
        except Exception as exc:
            log.error("tool.call_failed", tool=call.tool_id, error=str(exc))
            return ToolResult(tool_id=call.tool_id, call_id=call.call_id, success=False, error=str(exc))

    def _validate_inputs(self, defn: ToolDefinition, inputs: dict) -> None:
        try:
            jsonschema.validate(instance=inputs, schema=defn.input_schema)
        except jsonschema.ValidationError as exc:
            raise ToolInputError(f"Invalid inputs for '{defn.id}': {exc.message}") from exc
