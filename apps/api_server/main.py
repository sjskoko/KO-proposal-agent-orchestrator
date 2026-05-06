"""
FastAPI server — REST endpoints + SSE streaming for agent tasks.

Architecture notes
------------------
- The shared system (model, runtimes, planner, executor) is initialised once
  at startup via FastAPI lifespan, not rebuilt per request.
- Each task gets an isolated EventBus so concurrent runs never mix events.
- Completed task events are stored in _TASK_STORE (in-memory) so clients
  can reconnect and replay the full history.
- SSE uses periodic heartbeat comments (': heartbeat') to keep TCP connections
  alive through proxies; hard deadline is 10 minutes.
"""

from __future__ import annotations

import dataclasses
import json
import queue
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Generator

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

_CONFIG_DIR = Path("config")
_AGENTS_DIR = Path("agents")

app = FastAPI(title="Agent Orchestrator API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# In-memory task store  {session_id → task record}
#
# Stores the event history so clients can replay after reconnect.
# Resets when the server restarts — acceptable for V1.
# ---------------------------------------------------------------------------

_TASK_STORE: dict[str, dict] = {}
_TASK_LOCK = threading.Lock()


def _task_create(session_id: str, goal: str, agent_id: str) -> None:
    with _TASK_LOCK:
        _TASK_STORE[session_id] = {
            "session_id": session_id,
            "goal": goal,
            "agent_id": agent_id,
            "status": "running",
            "events": [],
            "result": None,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None,
        }


def _task_append_event(session_id: str, event_dict: dict) -> None:
    with _TASK_LOCK:
        if session_id in _TASK_STORE:
            _TASK_STORE[session_id]["events"].append(event_dict)


def _task_finish(session_id: str, *, result: str | None = None, error: str | None = None) -> None:
    with _TASK_LOCK:
        if session_id in _TASK_STORE:
            task = _TASK_STORE[session_id]
            task["status"] = "error" if error else "done"
            task["result"] = result
            task["error"] = error
            task["finished_at"] = datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_event(event) -> dict:
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


class TaskRequest(BaseModel):
    goal: str
    agent_id: str = "main_agent"


class TaskResponse(BaseModel):
    result: str
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/agents")
def list_agents():
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


@app.get("/models")
def list_models():
    with open(_CONFIG_DIR / "models.yaml") as f:
        return yaml.safe_load(f)


# --- Task history ---

@app.get("/tasks")
def list_tasks():
    """Return recent tasks (newest first, max 50)."""
    with _TASK_LOCK:
        tasks = sorted(_TASK_STORE.values(), key=lambda t: t["started_at"], reverse=True)
    return tasks[:50]


@app.get("/tasks/stream")
def stream_task(goal: str, agent_id: str = "main_agent"):
    """
    Run an agent and stream its events via Server-Sent Events.

    Protocol:
      Each message is a JSON object on a `data:` line.
      Heartbeat comments (': heartbeat') are sent every 15 s to keep
      the connection alive through proxies — browsers ignore them.

    Event shapes:
      { "type": "AgentStartedEvent", ... }   ← domain events from EventBus
      { "type": "done",   "result": "...", "session_id": "..." }
      { "type": "error",  "message": "..." }
      { "type": "timeout" }
    """

    def event_generator() -> Generator[str, None, None]:
        from apps.cli.runner import make_session
        from core.agent.base import Agent
        from core.agent.definition import AgentDefinition

        session = make_session(_CONFIG_DIR)
        session_id = session["session_id"]
        _task_create(session_id, goal=goal, agent_id=agent_id)

        event_queue: queue.Queue = queue.Queue()

        def on_event(event) -> None:
            payload = _serialize_event(event)
            _task_append_event(session_id, payload)
            event_queue.put(payload)

        session["bus"].subscribe_all(on_event)

        def run_in_thread() -> None:
            try:
                agent_path = _AGENTS_DIR / f"{agent_id}.yaml"
                if not agent_path.exists():
                    agent_path = _AGENTS_DIR / "sub_agents" / f"{agent_id}.yaml"

                definition = AgentDefinition.from_yaml(agent_path)
                agent = Agent(
                    definition=definition,
                    event_bus=session["bus"],
                    planner=session["planner"],
                    executor=session["executor"],
                )
                result = agent.run(goal)
                event_queue.put({"__done__": True, "result": str(result), "session_id": session_id})
            except Exception as exc:
                event_queue.put({"__error__": str(exc)})

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

        deadline = time.monotonic() + 600  # 10-minute hard cap

        # Emit session_id immediately so the client can store it for replay
        yield "data: " + json.dumps({"type": "session_started", "session_id": session_id}) + "\n\n"

        while True:
            try:
                item = event_queue.get(timeout=15)
            except queue.Empty:
                if time.monotonic() > deadline:
                    _task_finish(session_id, error="timeout")
                    yield "data: " + json.dumps({"type": "timeout"}) + "\n\n"
                    break
                if not thread.is_alive():
                    _task_finish(session_id, error="agent thread stopped unexpectedly")
                    yield "data: " + json.dumps({"type": "error", "message": "Agent stopped unexpectedly"}) + "\n\n"
                    break
                yield ": heartbeat\n\n"
                continue

            if "__done__" in item:
                _task_finish(session_id, result=item["result"])
                yield "data: " + json.dumps({"type": "done", "result": item["result"], "session_id": session_id}) + "\n\n"
                break
            elif "__error__" in item:
                _task_finish(session_id, error=item["__error__"])
                yield "data: " + json.dumps({"type": "error", "message": item["__error__"]}) + "\n\n"
                break
            else:
                yield "data: " + json.dumps(item) + "\n\n"

        thread.join(timeout=5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# --- Task detail & sync execution (after /tasks/stream to avoid route shadowing) ---

@app.get("/tasks/{session_id}")
def get_task(session_id: str):
    """Return a task record including full event history (allows SSE reconnect)."""
    with _TASK_LOCK:
        task = _TASK_STORE.get(session_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", response_model=TaskResponse)
def create_task(req: TaskRequest):
    """Submit a task synchronously (blocks until done). For CLI/script use."""
    from apps.cli.runner import run_agent
    result = run_agent(goal=req.goal, agent_id=req.agent_id, config_dir=_CONFIG_DIR)
    return TaskResponse(result=str(result))


# ---------------------------------------------------------------------------
# Serve built React app (production only)
# ---------------------------------------------------------------------------

_UI_DIST = Path("apps/ui/dist")
if _UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIST), html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api_server.main:app", host="0.0.0.0", port=8000, reload=True)
