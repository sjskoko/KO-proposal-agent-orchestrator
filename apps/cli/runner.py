"""Shared agent bootstrap used by CLI and API server."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
import structlog

log = structlog.get_logger(__name__)


def build_system(config_dir: Path):
    """Construct the full agent system from config files."""
    from dotenv import load_dotenv
    load_dotenv()

    with open(config_dir / "models.yaml") as f:
        models_cfg = yaml.safe_load(f)
    with open(config_dir / "runtimes.yaml") as f:
        runtimes_cfg = yaml.safe_load(f)

    # Model providers
    from core.model.providers import GemmaLocalProvider, OpenAIProvider, AnthropicProvider
    from core.model.router import ModelRouter, RoutingRule

    providers = {
        "gemma4_local": GemmaLocalProvider(
            model=models_cfg["providers"]["gemma4_local"]["model"],
            base_url=models_cfg["providers"]["gemma4_local"]["base_url"],
        ),
        "openai_gpt4o": OpenAIProvider(),
        "anthropic_sonnet": AnthropicProvider(),
    }
    fallback_chain = models_cfg["routing"]["fallback_chain"]
    router = ModelRouter(providers=providers, fallback_chain=fallback_chain)

    # Runtimes
    from core.runtime.registry import RuntimeRegistry
    registry = RuntimeRegistry()
    registry.load_from_config(runtimes_cfg)

    # Inject model into reasoning runtime if present
    if "reasoning" in registry.list_ids():
        reasoning = registry._runtimes["reasoning"]
        reasoning.set_model(router)  # type: ignore[attr-defined]

    # Event bus + trace writer
    from core.events.bus import EventBus
    from core.events.trace import TraceWriter
    import uuid
    session_id = str(uuid.uuid4())[:8]
    bus = EventBus()
    trace = TraceWriter(session_id=session_id)
    bus.subscribe_all(trace)

    # Tool registry
    from core.tooling.registry import ToolRegistry
    tools = ToolRegistry()

    # Planner + executor
    from core.planner.sequential import SequentialPlanner
    from core.executor.base import Executor
    planner = SequentialPlanner(model=router)
    executor = Executor(runtime_registry=registry, tool_registry=tools)

    return {
        "router": router,
        "runtimes": registry,
        "tools": tools,
        "bus": bus,
        "planner": planner,
        "executor": executor,
    }


def run_agent(goal: str, agent_id: str, config_dir: Path) -> Any:
    system = build_system(config_dir)
    agent_path = Path("agents") / f"{agent_id}.yaml"
    if not agent_path.exists():
        agent_path = Path("agents") / "sub_agents" / f"{agent_id}.yaml"

    from core.agent.definition import AgentDefinition
    from core.agent.base import Agent

    definition = AgentDefinition.from_yaml(agent_path)
    agent = Agent(
        definition=definition,
        event_bus=system["bus"],
        planner=system["planner"],
        executor=system["executor"],
    )
    return agent.run(goal)
