"""MCPAdapter — wraps an MCP server and exposes its tools to the ToolRegistry."""

from __future__ import annotations

import subprocess
from typing import Any

import structlog

log = structlog.get_logger(__name__)


class MCPAdapter:
    """
    Launches an MCP server as a subprocess (stdio transport) and
    proxies tool calls through the MCP protocol.
    """

    def __init__(self, server_id: str, config: dict) -> None:
        self.server_id = server_id
        self._config = config
        self._process: subprocess.Popen | None = None
        self._tools_cache: list[dict] = []

    def start(self) -> None:
        command = [self._config["command"]] + self._config.get("args", [])
        log.info("mcp_adapter.start", server=self.server_id, command=command)
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._initialize()

    def _initialize(self) -> None:
        """Send MCP initialize request and cache available tools."""
        # Real implementation uses the `mcp` SDK client over stdio.
        # Stub for now — replace with: mcp.ClientSession(stdio_transport).initialize()
        log.info("mcp_adapter.initialized", server=self.server_id)
        self._tools_cache = []

    def list_tools(self) -> list[dict]:
        return self._tools_cache

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        if self._process is None:
            raise RuntimeError(f"MCP server '{self.server_id}' is not started")
        log.debug("mcp_adapter.call_tool", server=self.server_id, tool=tool_name)
        # Real implementation: session.call_tool(tool_name, arguments)
        raise NotImplementedError("Wire up mcp.ClientSession here")

    def health_check(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def shutdown(self) -> None:
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            log.info("mcp_adapter.shutdown", server=self.server_id)

    @classmethod
    def from_config_file(cls, path: str) -> "MCPAdapter":
        import yaml
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return cls(server_id=config["id"], config=config)
