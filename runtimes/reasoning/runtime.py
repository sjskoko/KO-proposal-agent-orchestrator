"""ReasoningRuntime — chain-of-thought, reflection, self-critique."""

from __future__ import annotations

import structlog

from core.runtime.base import HealthStatus, RuntimeCall, RuntimeResult

log = structlog.get_logger(__name__)

_COT_TEMPLATE = """Think step-by-step to answer the following.

{prompt}

Reasoning:"""


class ReasoningRuntime:
    runtime_id = "reasoning"
    capabilities = ["chain_of_thought", "reflect", "critique"]

    def __init__(self) -> None:
        self._strategy = "chain_of_thought"
        self._max_reflection_steps = 3
        self._model = None   # injected via configure() or set externally

    def configure(self, config: dict) -> None:
        self._strategy = config.get("strategy", self._strategy)
        self._max_reflection_steps = config.get("max_reflection_steps", self._max_reflection_steps)

    def set_model(self, model) -> None:
        self._model = model

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        op = call.operation
        if op == "chain_of_thought":
            return self._cot(call)
        if op == "reflect":
            return self._reflect(call)
        return RuntimeResult(success=False, error=f"Unknown operation: {op}")

    def health_check(self) -> HealthStatus:
        return HealthStatus.OK if self._model is not None else HealthStatus.DEGRADED

    # ------------------------------------------------------------------

    def _cot(self, call: RuntimeCall) -> RuntimeResult:
        prompt = call.params.get("prompt", "")
        if self._model is None:
            return RuntimeResult(success=False, error="No model attached to ReasoningRuntime")

        from core.model.base import Message, ModelOptions
        messages = [Message(role="user", content=_COT_TEMPLATE.format(prompt=prompt))]
        response = self._model.complete(messages, ModelOptions(temperature=0.3))
        return RuntimeResult(success=True, data={"reasoning": response.content})

    def _reflect(self, call: RuntimeCall) -> RuntimeResult:
        prior = call.params.get("prior_response", "")
        goal = call.params.get("goal", "")
        if self._model is None:
            return RuntimeResult(success=False, error="No model attached to ReasoningRuntime")

        from core.model.base import Message, ModelOptions
        prompt = f"Goal: {goal}\n\nPrior response:\n{prior}\n\nIs this correct and complete? If not, improve it."
        messages = [Message(role="user", content=prompt)]
        response = self._model.complete(messages, ModelOptions(temperature=0.2))
        return RuntimeResult(success=True, data={"reflection": response.content})
