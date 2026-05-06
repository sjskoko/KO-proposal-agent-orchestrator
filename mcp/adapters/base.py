"""Base interface every MCP adapter must satisfy."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MCPAdapterBase(Protocol):
    server_id: str

    def list_tools(self) -> list[dict]: ...
    def call_tool(self, tool_name: str, arguments: dict) -> Any: ...
    def health_check(self) -> bool: ...
    def shutdown(self) -> None: ...
