"""ToolRuntime — sandboxed subprocess / shell tool execution."""

from __future__ import annotations

import subprocess
import shlex

import structlog

from core.runtime.base import HealthStatus, RuntimeCall, RuntimeResult

log = structlog.get_logger(__name__)


class ToolRuntime:
    runtime_id = "tools"
    capabilities = ["shell_exec", "subprocess"]

    def __init__(self) -> None:
        self._timeout_seconds = 30
        self._sandbox = True

    def configure(self, config: dict) -> None:
        self._timeout_seconds = config.get("timeout_seconds", self._timeout_seconds)
        self._sandbox = config.get("sandbox", self._sandbox)

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        op = call.operation
        if op == "shell_exec":
            return self._shell_exec(call)
        return RuntimeResult(success=False, error=f"Unknown operation: {op}")

    def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    # ------------------------------------------------------------------

    def _shell_exec(self, call: RuntimeCall) -> RuntimeResult:
        command = call.params.get("command", "")
        if not command:
            return RuntimeResult(success=False, error="No command provided")

        if self._sandbox:
            # Basic sanity — no shell injection vectors in sandbox mode
            forbidden = [";", "&&", "||", "|", "`", "$("]
            for token in forbidden:
                if token in command:
                    return RuntimeResult(success=False, error=f"Forbidden token in sandbox mode: {token}")

        log.info("tool_runtime.shell_exec", command=command[:80], sandbox=self._sandbox)
        try:
            result = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
            return RuntimeResult(
                success=result.returncode == 0,
                data={"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode},
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return RuntimeResult(success=False, error=f"Command timed out after {self._timeout_seconds}s")
        except Exception as exc:
            return RuntimeResult(success=False, error=str(exc))
