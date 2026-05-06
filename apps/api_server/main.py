"""FastAPI server — REST endpoints + SSE streaming for agent tasks."""

from __future__ import annotations

import dataclasses
import json
import queue
import threading
from datetime import datetime
from pathlib import Path
from typing import Generator

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Agent Orchestrator API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_CONFIG_DIR = Path("config")
_AGENTS_DIR = Path("agents")


class TaskRequest(BaseModel):
    goal: str
    agent_id: str = "main_agent"


class TaskResponse(BaseModel):
    result: str
    session_id: str | None = None


def _serialize_event(event) -> dict:
    """Convert a dataclass event to a JSON-serializable dict."""
    result: dict = {"type": type(event).__name__}
    for f in dataclasses.fields(event):
        value = getattr(event, f.name)
        if isinstance(value, datetime):
            result[f.name] = value.isoformat()
        elif isinstance(value, dict):
            result[f.name] = str(value)
        else:
            result[f.name] = value
    return result


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@app.get("/agents")
def list_agents():
    """Return all agent definitions from the agents/ directory."""
    agents = []
    for yaml_file in sorted(_AGENTS_DIR.rglob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        agents.append({
            "id": data.get("id"),
            "role": data.get("role"),
            "goal": data.get("goal", ""),
            "tools": data.get("tools", []),
            "sub_agents": data.get("sub_agents", []),
            "runtime_access": data.get("runtime_access", []),
            "permissions": data.get("permissions"),
            "path": str(yaml_file.relative_to(_AGENTS_DIR)),
        })
    return agents


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@app.get("/models")
def list_models():
    """Return the full models.yaml config."""
    with open(_CONFIG_DIR / "models.yaml") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.post("/tasks", response_model=TaskResponse)
def create_task(req: TaskRequest):
    """Submit a task synchronously (blocks until done)."""
    from apps.cli.runner import run_agent
    result = run_agent(goal=req.goal, agent_id=req.agent_id, config_dir=_CONFIG_DIR)
    return TaskResponse(result=str(result))


@app.get("/tasks/stream")
def stream_task(goal: str, agent_id: str = "main_agent"):
    """
    Run an agent and stream its events via Server-Sent Events (SSE).

    The browser opens a persistent HTTP connection. The server pushes
    one JSON line per event until the agent finishes or errors.

    Event shapes:
      { "type": "AgentStartedEvent", "goal": "...", ... }
      { "type": "ModelQueriedEvent", "provider": "...", ... }
      { "type": "done", "result": "..." }
      { "type": "error", "message": "..." }
    """

    def event_generator() -> Generator[str, None, None]:
        event_queue: queue.Queue = queue.Queue()

        def on_event(event) -> None:
            event_queue.put(event)

        def run_in_thread() -> None:
            try:
                from apps.cli.runner import build_system
                from core.agent.base import Agent
                from core.agent.definition import AgentDefinition

                system = build_system(_CONFIG_DIR)
                system["bus"].subscribe_all(on_event)

                agent_path = _AGENTS_DIR / f"{agent_id}.yaml"
                if not agent_path.exists():
                    agent_path = _AGENTS_DIR / "sub_agents" / f"{agent_id}.yaml"

                definition = AgentDefinition.from_yaml(agent_path)
                agent = Agent(
                    definition=definition,
                    event_bus=system["bus"],
                    planner=system["planner"],
                    executor=system["executor"],
                )
                result = agent.run(goal)
                event_queue.put({"__done__": True, "result": str(result)})
            except Exception as exc:
                event_queue.put({"__error__": str(exc)})

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

        while True:
            try:
                item = event_queue.get(timeout=120)
            except queue.Empty:
                yield "data: " + json.dumps({"type": "timeout"}) + "\n\n"
                break

            if isinstance(item, dict) and "__done__" in item:
                yield "data: " + json.dumps({"type": "done", "result": item["result"]}) + "\n\n"
                break
            elif isinstance(item, dict) and "__error__" in item:
                yield "data: " + json.dumps({"type": "error", "message": item["__error__"]}) + "\n\n"
                break
            else:
                payload = _serialize_event(item)
                yield "data: " + json.dumps(payload) + "\n\n"

        thread.join(timeout=5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )


# ---------------------------------------------------------------------------
# Serve built React app (production only)
# ---------------------------------------------------------------------------

_UI_DIST = Path("apps/ui/dist")
if _UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api_server.main:app", host="0.0.0.0", port=8000, reload=True)
