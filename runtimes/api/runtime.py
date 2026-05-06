"""ApiRuntime — outbound HTTP/REST calls with domain filtering."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
import structlog

from core.runtime.base import HealthStatus, RuntimeCall, RuntimeResult

log = structlog.get_logger(__name__)


class ApiRuntime:
    runtime_id = "api"
    capabilities = ["http_get", "http_post", "http_request"]

    def __init__(self) -> None:
        self._timeout = 15.0
        self._max_redirects = 3
        self._allowed_domains: list[str] = []   # empty = all allowed

    def configure(self, config: dict) -> None:
        self._timeout = float(config.get("timeout_seconds", self._timeout))
        self._max_redirects = config.get("max_redirects", self._max_redirects)
        self._allowed_domains = config.get("allowed_domains", self._allowed_domains)

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        op = call.operation
        if op in ("http_get", "http_post", "http_request"):
            return self._request(call)
        return RuntimeResult(success=False, error=f"Unknown operation: {op}")

    def health_check(self) -> HealthStatus:
        return HealthStatus.OK

    # ------------------------------------------------------------------

    def _request(self, call: RuntimeCall) -> RuntimeResult:
        url: str = call.params.get("url", "")
        method: str = call.params.get("method", "GET").upper()
        headers: dict = call.params.get("headers", {})
        body = call.params.get("body")
        params = call.params.get("params", {})

        if not url:
            return RuntimeResult(success=False, error="No URL provided")
        if not self._domain_allowed(url):
            return RuntimeResult(success=False, error=f"Domain not in allowed list: {url}")

        log.info("api_runtime.request", method=method, url=url[:80])
        try:
            with httpx.Client(timeout=self._timeout, max_redirects=self._max_redirects) as client:
                response = client.request(method, url, headers=headers, json=body, params=params)
            return RuntimeResult(
                success=response.is_success,
                data={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.text,
                },
                error=None if response.is_success else f"HTTP {response.status_code}",
            )
        except httpx.TimeoutException:
            return RuntimeResult(success=False, error=f"Request timed out after {self._timeout}s")
        except Exception as exc:
            return RuntimeResult(success=False, error=str(exc))

    def _domain_allowed(self, url: str) -> bool:
        if not self._allowed_domains:
            return True
        host = urlparse(url).hostname or ""
        return any(host == d or host.endswith(f".{d}") for d in self._allowed_domains)
