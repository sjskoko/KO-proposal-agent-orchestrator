"""TraceWriter — serializes all events to a JSONL file for replay/debug."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from core.events.types import BaseEvent


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


class TraceWriter:
    def __init__(self, trace_dir: str | Path = "data/traces", session_id: str = "default") -> None:
        self._path = Path(trace_dir) / f"{session_id}.jsonl"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self._path.open("a", encoding="utf-8")

    def __call__(self, event: BaseEvent) -> None:
        """Compatible with EventBus.subscribe_all."""
        record = {"_type": type(event).__name__, **asdict(event)}
        self._file.write(json.dumps(record, default=_json_default) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    @staticmethod
    def replay(trace_path: str | Path) -> list[dict]:
        """Load a trace file and return events as dicts."""
        records = []
        with open(trace_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
