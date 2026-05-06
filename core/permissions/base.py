"""Permission model — capabilities and permission sets."""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field


class Capability(str, Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    SHELL_EXEC = "shell_exec"
    NETWORK_ACCESS = "network_access"
    MCP_CALL = "mcp_call"
    API_CALL = "api_call"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    SUB_AGENT_DELEGATE = "sub_agent_delegate"


@dataclass
class PermissionSet:
    file_read: bool = False
    file_write: bool = False
    shell_exec: bool = False
    network_access: bool = False
    mcp_call: bool = False
    api_call: bool = False
    memory_read: bool = True
    memory_write: bool = True
    sub_agent_delegate: bool = False

    def has(self, cap: Capability) -> bool:
        return bool(getattr(self, cap.value, False))

    @classmethod
    def from_dict(cls, data: dict) -> "PermissionSet":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def unrestricted(cls) -> "PermissionSet":
        return cls(
            file_read=True, file_write=True, shell_exec=True,
            network_access=True, mcp_call=True, api_call=True,
            memory_read=True, memory_write=True, sub_agent_delegate=True,
        )

    @classmethod
    def read_only(cls) -> "PermissionSet":
        return cls(file_read=True, memory_read=True)
