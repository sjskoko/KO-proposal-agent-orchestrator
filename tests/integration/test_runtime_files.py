"""Integration tests for FileRuntime."""

import tempfile
from pathlib import Path

import pytest

from core.runtime.base import RuntimeCall
from runtimes.files.runtime import FileRuntime


@pytest.fixture
def runtime(tmp_path):
    rt = FileRuntime()
    rt.configure({"allowed_roots": [str(tmp_path)], "max_file_size_mb": 1})
    return rt, tmp_path


class TestFileRuntime:
    def test_write_and_read(self, runtime):
        rt, root = runtime
        path = str(root / "hello.txt")
        write_result = rt.execute(RuntimeCall("files", "file_write", {"path": path, "content": "hello"}))
        assert write_result.success

        read_result = rt.execute(RuntimeCall("files", "file_read", {"path": path}))
        assert read_result.success
        assert read_result.data["content"] == "hello"

    def test_list_directory(self, runtime):
        rt, root = runtime
        (root / "a.txt").write_text("a")
        (root / "b.txt").write_text("b")
        result = rt.execute(RuntimeCall("files", "file_list", {"path": str(root)}))
        assert result.success
        names = [e["name"] for e in result.data["entries"]]
        assert "a.txt" in names
        assert "b.txt" in names

    def test_access_outside_root_is_denied(self, runtime):
        rt, root = runtime
        result = rt.execute(RuntimeCall("files", "file_read", {"path": "/etc/passwd"}))
        assert not result.success
        assert "outside allowed roots" in result.error

    def test_delete_file(self, runtime):
        rt, root = runtime
        path = root / "del.txt"
        path.write_text("bye")
        result = rt.execute(RuntimeCall("files", "file_delete", {"path": str(path)}))
        assert result.success
        assert not path.exists()
