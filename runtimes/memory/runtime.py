"""MemoryRuntime — vector-backed semantic memory with scope isolation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog

from core.memory.base import MemoryEntry, MemoryScope
from core.runtime.base import HealthStatus, RuntimeCall, RuntimeResult

log = structlog.get_logger(__name__)


class MemoryRuntime:
    runtime_id = "memory"
    capabilities = ["memory_read", "memory_write", "memory_forget"]

    def __init__(self) -> None:
        self._backend = "in_memory"
        self._persist_path = "./data/memory"
        self._embedding_model = "nomic-embed-text"
        self._collection = None    # lazy-loaded ChromaDB collection
        self._store: list[MemoryEntry] = []  # fallback in-memory list

    def configure(self, config: dict) -> None:
        self._backend = config.get("backend", self._backend)
        self._persist_path = config.get("persist_path", self._persist_path)
        self._embedding_model = config.get("embedding_model", self._embedding_model)

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        op = call.operation
        if op == "memory_read":
            return self._read(call)
        if op == "memory_write":
            return self._write(call)
        if op == "memory_forget":
            return self._forget(call)
        return RuntimeResult(success=False, error=f"Unknown operation: {op}")

    def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    # ------------------------------------------------------------------

    def _read(self, call: RuntimeCall) -> RuntimeResult:
        query = call.params.get("query", "")
        scope = MemoryScope(call.params.get("scope", "session"))
        top_k = call.params.get("top_k", 5)
        agent_id = call.params.get("agent_id", "")

        if self._backend == "chroma":
            return self._chroma_read(query, scope, agent_id, top_k)

        # In-memory fallback: simple keyword match
        filtered = [e for e in self._store if e.scope == scope and (not agent_id or e.agent_id == agent_id)]
        results = [e for e in filtered if query.lower() in e.content.lower()][:top_k]
        return RuntimeResult(success=True, data={"entries": [vars(e) for e in results]})

    def _write(self, call: RuntimeCall) -> RuntimeResult:
        entry = MemoryEntry(
            content=call.params.get("content", ""),
            scope=MemoryScope(call.params.get("scope", "session")),
            agent_id=call.params.get("agent_id", ""),
            session_id=call.params.get("session_id", ""),
            entry_id=str(uuid.uuid4()),
        )
        self._store.append(entry)
        return RuntimeResult(success=True, data={"entry_id": entry.entry_id})

    def _forget(self, call: RuntimeCall) -> RuntimeResult:
        scope = MemoryScope(call.params.get("scope", "session"))
        agent_id = call.params.get("agent_id", "")
        before = len(self._store)
        self._store = [
            e for e in self._store
            if not (e.scope == scope and (not agent_id or e.agent_id == agent_id))
        ]
        return RuntimeResult(success=True, data={"deleted": before - len(self._store)})

    def _chroma_read(self, query: str, scope: MemoryScope, agent_id: str, top_k: int) -> RuntimeResult:
        try:
            import chromadb  # type: ignore[import]
            client = chromadb.PersistentClient(path=self._persist_path)
            collection = client.get_or_create_collection(f"memory_{scope.value}")
            where = {"agent_id": agent_id} if agent_id else None
            results = collection.query(query_texts=[query], n_results=top_k, where=where)
            docs = results.get("documents", [[]])[0]
            return RuntimeResult(success=True, data={"entries": [{"content": d} for d in docs]})
        except Exception as exc:
            log.error("memory_runtime.chroma_error", error=str(exc))
            return RuntimeResult(success=False, error=str(exc))
