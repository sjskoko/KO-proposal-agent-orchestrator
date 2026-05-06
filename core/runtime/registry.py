"""RuntimeRegistry — discovers, loads, and routes to runtimes."""

from __future__ import annotations

import importlib

import structlog

from core.runtime.base import HealthStatus, RuntimeCall, RuntimeInterface, RuntimeResult

log = structlog.get_logger(__name__)


class RuntimeNotFoundError(Exception):
    pass


class RuntimeRegistry:
    def __init__(self) -> None:
        self._runtimes: dict[str, RuntimeInterface] = {}

    def register(self, runtime: RuntimeInterface) -> None:
        self._runtimes[runtime.runtime_id] = runtime
        log.info("runtime.registered", id=runtime.runtime_id)

    def load_from_config(self, config: dict) -> None:
        """Instantiate runtimes declared in config/runtimes.yaml."""
        for runtime_id, spec in config.get("runtimes", {}).items():
            if not spec.get("enabled", True):
                log.info("runtime.skipped", id=runtime_id, reason="disabled")
                continue
            module_path, class_name = spec["module"].rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            instance: RuntimeInterface = cls()
            instance.configure(spec.get("config", {}))
            self.register(instance)

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        runtime = self._get(call.runtime_id)
        try:
            log.debug("runtime.execute", runtime=call.runtime_id, op=call.operation)
            return runtime.execute(call)
        except Exception as exc:
            log.error("runtime.error", runtime=call.runtime_id, error=str(exc))
            return RuntimeResult(success=False, error=str(exc))

    def health(self) -> dict[str, HealthStatus]:
        return {rid: r.health_check() for rid, r in self._runtimes.items()}

    def list_ids(self) -> list[str]:
        return list(self._runtimes.keys())

    def _get(self, runtime_id: str) -> RuntimeInterface:
        if runtime_id not in self._runtimes:
            raise RuntimeNotFoundError(f"Runtime not registered: {runtime_id}")
        return self._runtimes[runtime_id]
