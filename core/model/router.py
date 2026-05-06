"""ModelRouter — selects a provider based on rules in config/models.yaml."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

from core.model.base import Message, ModelOptions, ModelProvider, ModelResponse

log = structlog.get_logger(__name__)


@dataclass
class RoutingRule:
    match: dict          # e.g. {"task_type": "code_generation"}
    prefer: str          # provider name


@dataclass
class CostTracker:
    session_cost_usd: float = 0.0
    max_cost_usd: float | None = None

    def record(self, cost: float) -> None:
        self.session_cost_usd += cost

    def over_budget(self) -> bool:
        if self.max_cost_usd is None:
            return False
        return self.session_cost_usd >= self.max_cost_usd


class ModelRouter:
    """
    Resolves which provider handles a given request.

    Resolution order:
    1. Check routing rules for a match → use preferred provider
    2. Walk fallback_chain, skipping unhealthy or over-budget providers
    3. Raise if no provider is available
    """

    def __init__(
        self,
        providers: dict[str, ModelProvider],
        fallback_chain: list[str],
        rules: list[RoutingRule] | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self._providers = providers
        self._fallback_chain = fallback_chain
        self._rules = rules or []
        self._cost = cost_tracker or CostTracker()
        self._health_cache: dict[str, tuple[bool, float]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete(
        self,
        messages: list[Message],
        options: ModelOptions | None = None,
        context: dict | None = None,
    ) -> ModelResponse:
        provider = self._resolve(context or {})
        log.info("model_router.dispatch", provider=provider.name)
        response = provider.complete(messages, options)
        self._cost.record(self._estimate_cost(response))
        return response

    def get_provider(self, name: str) -> ModelProvider:
        if name not in self._providers:
            raise KeyError(f"Unknown provider: {name}")
        return self._providers[name]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, context: dict) -> ModelProvider:
        # 1. rule-based selection
        for rule in self._rules:
            if self._rule_matches(rule, context):
                provider_name = rule.prefer
                if self._is_available(provider_name):
                    return self._providers[provider_name]

        # 2. fallback chain
        for name in self._fallback_chain:
            if self._is_available(name):
                return self._providers[name]

        raise RuntimeError("No available model provider in fallback chain")

    def _rule_matches(self, rule: RoutingRule, context: dict) -> bool:
        for k, v in rule.match.items():
            if context.get(k) != v:
                return False
        return True

    def _is_available(self, name: str) -> bool:
        if name not in self._providers:
            return False
        if self._cost.over_budget():
            return False
        return self._check_health(name)

    def _check_health(self, name: str) -> bool:
        cached_result, cached_at = self._health_cache.get(name, (True, 0.0))
        if time.monotonic() - cached_at < 30:   # 30-second TTL
            return cached_result
        result = self._providers[name].health_check()
        self._health_cache[name] = (result, time.monotonic())
        return result

    @staticmethod
    def _estimate_cost(response: ModelResponse) -> float:
        # Rough estimate — providers should override with real pricing
        return (response.input_tokens / 1_000_000) * 0.50 + (response.output_tokens / 1_000_000) * 1.50
