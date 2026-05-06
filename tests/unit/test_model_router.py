"""Unit tests for ModelRouter."""

import pytest

from core.model.base import Message, ModelOptions, ModelResponse
from core.model.router import CostTracker, ModelRouter, RoutingRule


class _FakeProvider:
    def __init__(self, name: str, healthy: bool = True):
        self.name = name
        self._healthy = healthy

    def complete(self, messages, options=None):
        return ModelResponse(content=f"reply from {self.name}", model=self.name, provider=self.name)

    def stream(self, messages, options=None):
        yield f"stream from {self.name}"

    def health_check(self):
        return self._healthy


class TestModelRouter:
    def _router(self, providers=None, fallback_chain=None, rules=None):
        if providers is None:
            providers = {"a": _FakeProvider("a"), "b": _FakeProvider("b")}
        if fallback_chain is None:
            fallback_chain = ["a", "b"]
        return ModelRouter(providers=providers, fallback_chain=fallback_chain, rules=rules)

    def test_uses_first_available(self):
        router = self._router()
        resp = router.complete([Message(role="user", content="hi")])
        assert resp.provider == "a"

    def test_skips_unhealthy(self):
        providers = {"a": _FakeProvider("a", healthy=False), "b": _FakeProvider("b")}
        router = self._router(providers=providers, fallback_chain=["a", "b"])
        resp = router.complete([Message(role="user", content="hi")])
        assert resp.provider == "b"

    def test_rule_overrides_fallback(self):
        rules = [RoutingRule(match={"task_type": "code"}, prefer="b")]
        router = self._router(rules=rules)
        resp = router.complete([Message(role="user", content="hi")], context={"task_type": "code"})
        assert resp.provider == "b"

    def test_raises_when_all_unavailable(self):
        providers = {"a": _FakeProvider("a", healthy=False)}
        router = self._router(providers=providers, fallback_chain=["a"])
        with pytest.raises(RuntimeError):
            router.complete([Message(role="user", content="hi")])

    def test_single_provider_fail_fast_without_fallback(self):
        providers = {"gemma4_local": _FakeProvider("gemma4_local", healthy=False)}
        router = self._router(providers=providers, fallback_chain=["gemma4_local"])
        with pytest.raises(RuntimeError):
            router.complete([Message(role="user", content="hi")])

    def test_cost_tracking(self):
        tracker = CostTracker(max_cost_usd=0.0)  # zero budget
        providers = {"a": _FakeProvider("a")}
        router = ModelRouter(providers=providers, fallback_chain=["a"], cost_tracker=tracker)
        tracker.session_cost_usd = 1.0   # simulate over-budget
        with pytest.raises(RuntimeError):
            router.complete([Message(role="user", content="hi")])
