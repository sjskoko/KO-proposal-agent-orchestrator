"""Unit tests for the permissions system."""

import pytest

from core.permissions.base import Capability, PermissionSet
from core.permissions.checker import PermissionChecker, PermissionDeniedError


class TestPermissionSet:
    def test_unrestricted_has_all(self):
        ps = PermissionSet.unrestricted()
        for cap in Capability:
            assert ps.has(cap)

    def test_read_only_denies_write(self):
        ps = PermissionSet.read_only()
        assert ps.has(Capability.FILE_READ)
        assert not ps.has(Capability.FILE_WRITE)
        assert not ps.has(Capability.SHELL_EXEC)

    def test_from_dict(self):
        ps = PermissionSet.from_dict({"file_read": True, "file_write": False})
        assert ps.has(Capability.FILE_READ)
        assert not ps.has(Capability.FILE_WRITE)


class TestPermissionChecker:
    def test_require_granted(self):
        checker = PermissionChecker("agent1", PermissionSet.unrestricted())
        checker.require(Capability.SHELL_EXEC)   # should not raise

    def test_require_denied(self):
        checker = PermissionChecker("agent1", PermissionSet.read_only())
        with pytest.raises(PermissionDeniedError) as exc_info:
            checker.require(Capability.SHELL_EXEC)
        assert exc_info.value.agent_id == "agent1"
        assert exc_info.value.capability == Capability.SHELL_EXEC

    def test_check_returns_bool(self):
        checker = PermissionChecker("a", PermissionSet())
        assert checker.check(Capability.MEMORY_READ) is True
        assert checker.check(Capability.SHELL_EXEC) is False
