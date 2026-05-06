"""
Agent bootstrap — separates long-lived shared system from per-session state.

Architecture:
  Shared (built once at startup, reused across all requests):
    ModelRouter, RuntimeRegistry, ToolRegistry, SequentialPlanner, Executor

  Per-session (created cheaply for each agent run):
    EventBus, TraceWriter, session_id

This prevents the 26B model from being reloaded on every API request, and
ensures event streams from concurrent runs never cross-contaminate.
"""

from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any

import yaml
import structlog

log = structlog.get_logger(__name__)

_SHARED_SYSTEM: dict | None = None
_SYSTEM_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Shared system (expensive, built once)
# ---------------------------------------------------------------------------

def _build_shared(config_dir: Path) -> dict:
    from dotenv import load_dotenv
    load_dotenv()

    with open(config_dir / "models.yaml") as f:
        models_cfg = yaml.safe_load(f)
    with open(config_dir / "runtimes.yaml") as f:
        runtimes_cfg = yaml.safe_load(f)

    from core.model.providers import GemmaLocalProvider
    from core.model.router import ModelRouter

    gemma_model = os.getenv("GEMMA_MODEL_PATH", models_cfg["providers"]["gemma4_local"]["model"])

    providers = {
        "gemma4_local": GemmaLocalProvider.get_or_create(model=gemma_model, base_url=""),
    }
    fallback_chain = models_cfg["routing"]["fallback_chain"]
    router = ModelRouter(providers=providers, fallback_chain=fallback_chain)

    from core.runtime.registry import RuntimeRegistry
    registry = RuntimeRegistry()
    registry.load_from_config(runtimes_cfg)

    if "reasoning" in registry.list_ids():
        registry._runtimes["reasoning"].set_model(router)  # type: ignore[attr-defined]

    from core.tooling.registry import ToolRegistry
    tools = ToolRegistry()

    from core.planner.sequential import SequentialPlanner
    from core.executor.base import Executor
    planner = SequentialPlanner(model=router)
    executor = Executor(runtime_registry=registry, tool_registry=tools)

    log.info("system.built", providers=list(providers), runtimes=registry.list_ids())
    return {
        "router": router,
        "runtimes": registry,
        "tools": tools,
        "planner": planner,
        "executor": executor,
    }


def get_shared_system(config_dir: Path) -> dict:
    """Return the shared system, initialising it on first call (thread-safe)."""
    global _SHARED_SYSTEM
    if _SHARED_SYSTEM is None:
        with _SYSTEM_LOCK:
            if _SHARED_SYSTEM is None:  # double-checked locking
                _SHARED_SYSTEM = _build_shared(config_dir)
    return _SHARED_SYSTEM


# ---------------------------------------------------------------------------
# Per-session components (cheap, created per request)
# ---------------------------------------------------------------------------

def make_session(config_dir: Path) -> dict:
    """Attach a fresh EventBus + TraceWriter to the shared system."""
    from core.events.bus import EventBus
    from core.events.trace import TraceWriter

    session_id = uuid.uuid4().hex[:8]
    bus = EventBus()
    trace = TraceWriter(session_id=session_id)
    bus.subscribe_all(trace)

    return {
        **get_shared_system(config_dir),
        "bus": bus,
        "session_id": session_id,
    }


# ---------------------------------------------------------------------------
# Backward-compat alias (CLI + old imports still call build_system)
# ---------------------------------------------------------------------------

def build_system(config_dir: Path) -> dict:
    return make_session(config_dir)


# ---------------------------------------------------------------------------
# Synchronous entry point (CLI)
# ---------------------------------------------------------------------------

def run_agent(goal: str, agent_id: str, config_dir: Path) -> Any:
    system = make_session(config_dir)

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
