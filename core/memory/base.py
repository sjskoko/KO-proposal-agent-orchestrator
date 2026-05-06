"""Memory interface — scoped read/write/forget."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class MemoryScope(str, Enum):
    SESSION = "session"
    AGENT = "agent"
    GLOBAL = "global"


@dataclass
class MemoryEntry:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    scope: MemoryScope = MemoryScope.SESSION
    agent_id: str = ""
    session_id: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    entry_id: str = ""


@runtime_checkable
class MemoryStore(Protocol):
    def read(
        self,
        query: str,
        scope: MemoryScope,
        agent_id: str = "",
        session_id: str = "",
        top_k: int = 5,
    ) -> list[MemoryEntry]: ...

    def write(self, entry: MemoryEntry) -> str: ...  # returns entry_id

    def forget(
        self,
        scope: MemoryScope,
        agent_id: str = "",
        session_id: str = "",
        filter: dict | None = None,
    ) -> int: ...  # returns number of deleted entries
