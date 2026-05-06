"""Planner protocol — any planning strategy must satisfy this."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.planner.task_graph import TaskGraph


@runtime_checkable
class Planner(Protocol):
    def plan(self, goal: str, inputs: dict, context: dict | None = None) -> TaskGraph: ...
