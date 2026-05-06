"""AgentDefinition — the declarative spec loaded from agents/*.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.memory.base import MemoryScope
from core.permissions.base import PermissionSet


@dataclass
class ModelPolicy:
    preferred: str = "gemma4_local"
    fallback: str | None = None
    max_cost_usd: float | None = None


@dataclass
class AgentDefinition:
    id: str
    role: str
    goal: str
    model_policy: ModelPolicy = field(default_factory=ModelPolicy)
    memory_scope: MemoryScope = MemoryScope.SESSION
    runtime_access: list[str] = field(default_factory=list)
    permissions: PermissionSet = field(default_factory=PermissionSet)
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    sub_agents: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AgentDefinition":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Resolve model_policy
        mp_data = data.get("model_policy", {})
        model_policy = ModelPolicy(
            preferred=mp_data.get("preferred", "gemma4_local"),
            fallback=mp_data.get("fallback"),
            max_cost_usd=mp_data.get("max_cost_usd"),
        )

        # Resolve permissions
        perm_name = data.get("permissions", "")
        if isinstance(perm_name, str):
            perm_map = {
                "unrestricted": PermissionSet.unrestricted(),
                "read_only": PermissionSet.read_only(),
                "worker": PermissionSet(
                    file_read=True, file_write=True,
                    network_access=False, shell_exec=False,
                    mcp_call=True, api_call=False,
                    memory_read=True, memory_write=True,
                    sub_agent_delegate=True,
                ),
            }
            permissions = perm_map.get(perm_name, PermissionSet())
        else:
            permissions = PermissionSet.from_dict(perm_name)

        return cls(
            id=data["id"],
            role=data["role"],
            goal=data["goal"],
            model_policy=model_policy,
            memory_scope=MemoryScope(data.get("memory_scope", "session")),
            runtime_access=data.get("runtime_access", []),
            permissions=permissions,
            tools=data.get("tools", []),
            skills=data.get("skills", []),
            sub_agents=data.get("sub_agents", []),
        )
