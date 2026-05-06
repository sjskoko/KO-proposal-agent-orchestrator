"""Unit tests for the ToolRegistry."""

import pytest

from core.tooling.base import ToolCall, ToolDefinition
from core.tooling.registry import ToolNotFoundError, ToolRegistry


def _make_tool(tool_id: str = "echo") -> ToolDefinition:
    return ToolDefinition(
        id=tool_id,
        name="Echo",
        description="Returns the input message",
        input_schema={
            "type": "object",
            "required": ["message"],
            "properties": {"message": {"type": "string"}},
        },
        output_schema={"type": "object"},
        runtime_id="builtin",
    )


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        defn = _make_tool()
        reg.register(defn, handler=lambda inputs: inputs["message"])
        assert reg.get("echo").id == "echo"

    def test_get_unknown_raises(self):
        reg = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            reg.get("nonexistent")

    def test_call_success(self):
        reg = ToolRegistry()
        reg.register(_make_tool(), handler=lambda inputs: {"echo": inputs["message"]})
        result = reg.call(ToolCall(tool_id="echo", inputs={"message": "hello"}))
        assert result.success
        assert result.output == {"echo": "hello"}

    def test_call_invalid_inputs_fails(self):
        reg = ToolRegistry()
        reg.register(_make_tool(), handler=lambda inputs: inputs)
        result = reg.call(ToolCall(tool_id="echo", inputs={}))   # missing "message"
        assert not result.success

    def test_list_tools(self):
        reg = ToolRegistry()
        reg.register(_make_tool("t1"), handler=lambda i: i)
        reg.register(_make_tool("t2"), handler=lambda i: i)
        assert len(reg.list_tools()) == 2
