"""PermissionChecker — enforces capability boundaries before dispatch."""

from __future__ import annotations

import structlog

from core.permissions.base import Capability, PermissionSet

log = structlog.get_logger(__name__)


class PermissionDeniedError(Exception):
    def __init__(self, agent_id: str, capability: Capability) -> None:
        self.agent_id = agent_id
        self.capability = capability
        super().__init__(f"Agent '{agent_id}' lacks capability: {capability.value}")


class PermissionChecker:
    def __init__(self, agent_id: str, permissions: PermissionSet) -> None:
        self._agent_id = agent_id
        self._permissions = permissions

    def require(self, capability: Capability) -> None:
        """Raise PermissionDeniedError if the agent lacks the given capability."""
        if not self._permissions.has(capability):
            log.warning(
                "permission.denied",
                agent=self._agent_id,
                capability=capability.value,
            )
            raise PermissionDeniedError(self._agent_id, capability)
        log.debug("permission.granted", agent=self._agent_id, capability=capability.value)

    def check(self, capability: Capability) -> bool:
        return self._permissions.has(capability)
