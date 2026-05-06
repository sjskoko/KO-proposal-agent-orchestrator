"""FastAPI server — REST endpoint + SSE streaming for agent tasks."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Gemma Agent API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_CONFIG_DIR = Path("config")


class TaskRequest(BaseModel):
    goal: str
    agent_id: str = "main_agent"


class TaskResponse(BaseModel):
    result: str
    session_id: str | None = None


@app.post("/tasks", response_model=TaskResponse)
def create_task(req: TaskRequest):
    """Submit a task and wait for the result (synchronous)."""
    from apps.cli.runner import run_agent
    result = run_agent(goal=req.goal, agent_id=req.agent_id, config_dir=_CONFIG_DIR)
    return TaskResponse(result=str(result))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api_server.main:app", host="0.0.0.0", port=8000, reload=True)
