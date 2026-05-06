"""Tool definitions and call/result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ToolDefinition:
    id: str
    name: str
    description: str
    input_schema: dict          # JSON Schema
    output_schema: dict         # JSON Schema
    runtime_id: str
    permissions_required: list[str] = field(default_factory=list)
    source: Literal["builtin", "skill", "mcp"] = "builtin"
    enabled: bool = True


@dataclass
class ToolCall:
    tool_id: str
    inputs: dict[str, Any]
    call_id: str = ""
    agent_id: str = ""


@dataclass
class ToolResult:
    tool_id: str
    call_id: str
    success: bool
    output: Any = None
    error: str | None = None
