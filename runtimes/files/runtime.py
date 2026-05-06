"""FileRuntime — sandboxed file system operations with allowed_roots enforcement."""

from __future__ import annotations

from pathlib import Path

import structlog

from core.runtime.base import HealthStatus, RuntimeCall, RuntimeResult

log = structlog.get_logger(__name__)


class FileAccessError(Exception):
    pass


class FileRuntime:
    runtime_id = "files"
    capabilities = ["file_read", "file_write", "file_list", "file_delete"]

    def __init__(self) -> None:
        self._allowed_roots: list[Path] = [Path("./workspace")]
        self._max_bytes = 50 * 1024 * 1024  # 50 MB

    def configure(self, config: dict) -> None:
        roots = config.get("allowed_roots", ["./workspace"])
        self._allowed_roots = [Path(r).resolve() for r in roots]
        self._max_bytes = config.get("max_file_size_mb", 50) * 1024 * 1024

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        op = call.operation
        dispatch = {
            "file_read": self._read,
            "file_write": self._write,
            "file_list": self._list,
            "file_delete": self._delete,
        }
        handler = dispatch.get(op)
        if handler is None:
            return RuntimeResult(success=False, error=f"Unknown operation: {op}")
        try:
            return handler(call)
        except FileAccessError as exc:
            return RuntimeResult(success=False, error=str(exc))

    def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    # ------------------------------------------------------------------

    def _guard(self, path_str: str) -> Path:
        path = Path(path_str).resolve()
        if not any(str(path).startswith(str(root)) for root in self._allowed_roots):
            raise FileAccessError(f"Path outside allowed roots: {path}")
        return path

    def _read(self, call: RuntimeCall) -> RuntimeResult:
        path = self._guard(call.params["path"])
        if not path.exists():
            return RuntimeResult(success=False, error=f"File not found: {path}")
        if path.stat().st_size > self._max_bytes:
            return RuntimeResult(success=False, error="File exceeds max_file_size limit")
        return RuntimeResult(success=True, data={"content": path.read_text(encoding="utf-8"), "path": str(path)})

    def _write(self, call: RuntimeCall) -> RuntimeResult:
        path = self._guard(call.params["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(call.params.get("content", ""), encoding="utf-8")
        return RuntimeResult(success=True, data={"path": str(path)})

    def _list(self, call: RuntimeCall) -> RuntimeResult:
        path = self._guard(call.params.get("path", str(self._allowed_roots[0])))
        if not path.is_dir():
            return RuntimeResult(success=False, error=f"Not a directory: {path}")
        entries = [{"name": e.name, "type": "dir" if e.is_dir() else "file"} for e in sorted(path.iterdir())]
        return RuntimeResult(success=True, data={"entries": entries})

    def _delete(self, call: RuntimeCall) -> RuntimeResult:
        path = self._guard(call.params["path"])
        if not path.exists():
            return RuntimeResult(success=False, error=f"File not found: {path}")
        path.unlink()
        return RuntimeResult(success=True, data={"deleted": str(path)})
