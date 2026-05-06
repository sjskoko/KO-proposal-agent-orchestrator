"""Integration tests for ApiRuntime (uses httpx mock)."""

import pytest
import respx
import httpx

from core.runtime.base import RuntimeCall
from runtimes.api.runtime import ApiRuntime


@pytest.fixture
def runtime():
    rt = ApiRuntime()
    rt.configure({"timeout_seconds": 5, "allowed_domains": []})
    return rt


class TestApiRuntime:
    @respx.mock
    def test_http_get_success(self, runtime):
        respx.get("https://example.com/api").mock(return_value=httpx.Response(200, text="ok"))
        result = runtime.execute(RuntimeCall("api", "http_get", {"url": "https://example.com/api"}))
        assert result.success
        assert result.data["status_code"] == 200
        assert result.data["body"] == "ok"

    @respx.mock
    def test_http_get_404_returns_failure(self, runtime):
        respx.get("https://example.com/missing").mock(return_value=httpx.Response(404, text="not found"))
        result = runtime.execute(RuntimeCall("api", "http_get", {"url": "https://example.com/missing"}))
        assert not result.success

    def test_domain_filtering(self):
        rt = ApiRuntime()
        rt.configure({"allowed_domains": ["example.com"]})
        result = rt.execute(RuntimeCall("api", "http_get", {"url": "https://other.com/api"}))
        assert not result.success
        assert "allowed" in result.error

    def test_missing_url(self, runtime):
        result = runtime.execute(RuntimeCall("api", "http_get", {}))
        assert not result.success
