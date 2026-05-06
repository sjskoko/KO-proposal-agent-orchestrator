"""BrowserRuntime — Playwright-based browser automation (opt-in)."""

from __future__ import annotations

import structlog

from core.runtime.base import HealthStatus, RuntimeCall, RuntimeResult

log = structlog.get_logger(__name__)


class BrowserRuntime:
    runtime_id = "browser"
    capabilities = ["navigate", "screenshot", "extract_text", "click", "fill_form"]

    def __init__(self) -> None:
        self._headless = True
        self._browser_type = "chromium"
        self._timeout_ms = 60_000
        self._playwright = None
        self._browser = None

    def configure(self, config: dict) -> None:
        self._headless = config.get("headless", self._headless)
        self._browser_type = config.get("browser", self._browser_type)
        self._timeout_ms = config.get("timeout_seconds", 60) * 1000

    def _ensure_started(self) -> None:
        if self._browser is not None:
            return
        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import]
            self._playwright = sync_playwright().start()
            launcher = getattr(self._playwright, self._browser_type)
            self._browser = launcher.launch(headless=self._headless)
            log.info("browser_runtime.started", browser=self._browser_type)
        except ImportError:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install")

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        try:
            self._ensure_started()
        except RuntimeError as exc:
            return RuntimeResult(success=False, error=str(exc))

        op = call.operation
        if op == "navigate":
            return self._navigate(call)
        if op == "screenshot":
            return self._screenshot(call)
        if op == "extract_text":
            return self._extract_text(call)
        return RuntimeResult(success=False, error=f"Unknown operation: {op}")

    def health_check(self) -> HealthStatus:
        try:
            import playwright  # type: ignore[import] # noqa: F401
            return HealthStatus.OK
        except ImportError:
            return HealthStatus.UNAVAILABLE

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    # ------------------------------------------------------------------

    def _navigate(self, call: RuntimeCall) -> RuntimeResult:
        url = call.params.get("url", "")
        page = self._browser.new_page()
        try:
            response = page.goto(url, timeout=self._timeout_ms)
            return RuntimeResult(
                success=True,
                data={"url": page.url, "title": page.title(), "status": response.status if response else None},
            )
        finally:
            page.close()

    def _extract_text(self, call: RuntimeCall) -> RuntimeResult:
        url = call.params.get("url", "")
        selector = call.params.get("selector", "body")
        page = self._browser.new_page()
        try:
            page.goto(url, timeout=self._timeout_ms)
            text = page.inner_text(selector)
            return RuntimeResult(success=True, data={"text": text, "url": page.url})
        finally:
            page.close()

    def _screenshot(self, call: RuntimeCall) -> RuntimeResult:
        url = call.params.get("url", "")
        output_path = call.params.get("output_path", "/tmp/screenshot.png")
        page = self._browser.new_page()
        try:
            page.goto(url, timeout=self._timeout_ms)
            page.screenshot(path=output_path)
            return RuntimeResult(success=True, data={"path": output_path})
        finally:
            page.close()
