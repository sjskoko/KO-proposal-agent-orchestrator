"""TaskGraph — DAG representation of a decomposed goal."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import uuid


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    task_type: str = "generic"
    runtime_id: str = ""
    tool_id: str | None = None
    skill_id: str | None = None
    sub_agent_id: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)   # node_ids
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: str | None = None


@dataclass
class TaskGraph:
    goal: str
    nodes: list[PlanNode] = field(default_factory=list)

    def add_node(self, node: PlanNode) -> PlanNode:
        self.nodes.append(node)
        return node

    def ready_nodes(self) -> list[PlanNode]:
        """Return nodes whose dependencies are all DONE."""
        done_ids = {n.node_id for n in self.nodes if n.status == NodeStatus.DONE}
        return [
            n for n in self.nodes
            if n.status == NodeStatus.PENDING and all(d in done_ids for d in n.depends_on)
        ]

    def is_complete(self) -> bool:
        return all(n.status in (NodeStatus.DONE, NodeStatus.SKIPPED) for n in self.nodes)

    def has_failures(self) -> bool:
        return any(n.status == NodeStatus.FAILED for n in self.nodes)

    def summary(self) -> str:
        counts = {s: 0 for s in NodeStatus}
        for n in self.nodes:
            counts[n.status] += 1
        return " | ".join(f"{s.value}={c}" for s, c in counts.items() if c > 0)
