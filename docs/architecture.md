# Architecture

## System overview

```
User / App
    │
    ▼
[apps/cli | apps/api_server]
    │
    ▼
[core/agent]  ← AgentDefinition (YAML)
    │
    ├── [core/planner]  ← SequentialPlanner → TaskGraph
    │
    ├── [core/executor] ← walks TaskGraph, dispatches nodes
    │       │
    │       ├── [core/permissions]  ← enforced before every call
    │       ├── [core/runtime/registry] ─▶ [runtimes/*]
    │       ├── [core/tooling/registry] ─▶ skill handlers / MCP adapters
    │       └── sub-agent delegation ─▶ child Agent instances
    │
    ├── [core/model/router] ← ModelRouter → local Gemma 4 or API
    └── [core/events/bus]   ← TraceWriter (JSONL replay log)
```

## Key design decisions

### Config-first
No model names, runtime IDs, tool names, or API keys appear in `core/`.
Everything is driven from `config/*.yaml` and `agents/*.yaml`.

### Protocol-based interfaces
All cross-module contracts are Python `Protocol` classes (`runtime_checkable`).
This enables swapping implementations without changing callers.

### Permission enforcement
`PermissionChecker.require(Capability)` is called in the executor before every
runtime dispatch and MCP call. A `PermissionDeniedError` stops the step.

### Runtime isolation
Each runtime is an independent class loaded lazily by `RuntimeRegistry`.
A crash in `BrowserRuntime` does not affect `FileRuntime` or `MemoryRuntime`.

### Trace replay
Every event is serialized to a `.jsonl` file in `data/traces/`.
`TraceWriter.replay(path)` loads the file for inspection or diff.

## Adding a new runtime

1. Create `runtimes/myruntime/runtime.py` implementing `RuntimeInterface`
2. Add an entry to `config/runtimes.yaml`
3. Write isolated tests in `tests/integration/test_runtime_myruntime.py`

## Adding a new skill

1. Create `skills/myskill/skill.yaml`, `handler.py`, `instructions.md`
2. The skill loader auto-discovers it on startup
3. Add test cases to `skills/myskill/tests/` and `tests/skill_eval/`

## Adding a new agent

1. Create `agents/sub_agents/myagent.yaml`
2. Reference its `id` in a parent agent's `sub_agents` list
3. The delegation interface handles the rest
