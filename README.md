# Gemma Agent Orchestrator

Gemma 4 기반 로컬 에이전트 오케스트레이터입니다.
로컬 LLM을 기본으로 사용하고, 외부 API는 선택적 폴백으로만 활용합니다.
런타임, 스킬, MCP 서버, 에이전트 모두 YAML 설정으로 조립합니다.

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [전체 아키텍처](#2-전체-아키텍처)
3. [디렉토리 구조](#3-디렉토리-구조)
4. [설치 및 환경 설정](#4-설치-및-환경-설정)
5. [빠른 시작](#5-빠른-시작)
6. [CLI 사용법](#6-cli-사용법)
7. [API 서버 사용법](#7-api-서버-사용법)
8. [에이전트 설정](#8-에이전트-설정)
9. [런타임 설정](#9-런타임-설정)
10. [모델 설정 및 라우팅](#10-모델-설정-및-라우팅)
11. [스킬 개발](#11-스킬-개발)
12. [MCP 서버 연결](#12-mcp-서버-연결)
13. [권한 시스템](#13-권한-시스템)
14. [이벤트 & 트레이스 로그](#14-이벤트--트레이스-로그)
15. [테스트 실행](#15-테스트-실행)
16. [주요 인터페이스 레퍼런스](#16-주요-인터페이스-레퍼런스)

---

## 1. 시스템 개요

| 항목 | 내용 |
|---|---|
| 기본 모델 | Gemma 4 (로컬 체크포인트 실행) |
| API 폴백 | 없음 (1차 버전: Gemma 실패 시 즉시 종료) |
| 런타임 | reasoning / tools / files / browser / memory / api |
| 에이전트 패턴 | planner-worker, supervisor-specialist, tool-executor |
| 스킬 형식 | YAML 명세 + Python 핸들러 |
| MCP 지원 | stdio 트랜스포트, 설정 파일 기반 자동 등록 |
| 설정 방식 | 전부 YAML — 코드에 모델명·툴명 하드코딩 없음 |

---

## 2. 전체 아키텍처

```
사용자 입력 (CLI / API)
        │
        ▼
  ┌─────────────────────────────┐
  │       apps/cli  or  apps/api_server        │
  └──────────────┬──────────────┘
                 │ goal (문자열)
                 ▼
  ┌──────────────────────────────────────────┐
  │              core/agent (Agent)           │
  │  - AgentDefinition 로드 (YAML)            │
  │  - PermissionChecker 생성                 │
  │  - 상태머신: idle→planning→executing→done │
  └───────┬────────────────────┬─────────────┘
          │                    │
          ▼                    ▼
  ┌───────────────┐   ┌─────────────────────┐
  │ core/planner  │   │  core/events (Bus)   │
  │ SequentialPlan│   │  TraceWriter → JSONL │
  │ → TaskGraph   │   └─────────────────────┘
  └───────┬───────┘
          │ TaskGraph (DAG)
          ▼
  ┌────────────────────────────────────────────────┐
  │                core/executor                    │
  │  - TaskGraph 노드 순서대로 실행                  │
  │  - 노드마다 permissions.require() 검사           │
  │  - 실패 시 RetryPolicy(지수 백오프) 재시도        │
  └──────┬──────────────┬───────────────┬──────────┘
         │              │               │
         ▼              ▼               ▼
  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐
  │ runtime  │  │  tooling     │  │  sub-agent       │
  │ registry │  │  registry    │  │  delegation      │
  └──────┬───┘  └──────┬───────┘  └────────┬─────────┘
         │             │                    │
    ┌────┴────┐   ┌────┴──────┐        ┌───┴──────┐
    │runtimes/│   │skills/    │        │child     │
    │reasoning│   │handler.py │        │Agent     │
    │tools    │   │           │        │(동일 흐름)│
    │files    │   │mcp/       │        └──────────┘
    │browser  │   │adapters/  │
    │memory   │   └───────────┘
    │api      │
    └─────────┘
         │
         ▼
  ┌────────────────────────┐
  │  core/model (Router)   │
  │  1순위: Gemma 4 로컬    │
  │  2순위: OpenAI / Claude │
  └────────────────────────┘
```

### 데이터 흐름 요약

1. 사용자가 `goal` 문자열을 입력
2. `Agent`가 `Planner`를 호출 → 모델이 JSON 형식으로 단계 목록 반환
3. `Planner`가 `TaskGraph` (DAG) 생성
4. `Executor`가 의존성 순서대로 노드 실행
5. 각 노드는 **런타임 호출**, **툴 호출**, **스킬 실행**, **서브에이전트 위임** 중 하나
6. 모든 단계의 입출력이 `EventBus`를 통해 JSONL 트레이스 파일에 기록
7. 최종 결과를 앱 레이어로 반환

---

## 3. 디렉토리 구조

```
gemma-agent/
├── apps/
│   ├── cli/              # Typer CLI (run / repl / replay)
│   ├── ui/               # 선택적 데스크탑·웹 UI (미구현 플레이스홀더)
│   └── api_server/       # FastAPI REST 서버
│
├── core/                 # 에이전트 핵심 로직 (런타임·모델 독립적)
│   ├── agent/            # Agent, AgentDefinition, 상태머신, 위임
│   ├── planner/          # TaskGraph, SequentialPlanner
│   ├── executor/         # Executor, RetryPolicy
│   ├── runtime/          # RuntimeInterface, RuntimeRegistry
│   ├── memory/           # MemoryStore Protocol, MemoryScope
│   ├── model/            # ModelProvider Protocol, ModelRouter, 3개 공급자
│   ├── tooling/          # ToolDefinition, ToolRegistry
│   ├── events/           # EventBus, TraceWriter, 이벤트 타입 정의
│   └── permissions/      # Capability, PermissionSet, PermissionChecker
│
├── runtimes/             # 런타임 구현체 (각각 독립 교체 가능)
│   ├── reasoning/        # Chain-of-Thought, 반성(reflection)
│   ├── tools/            # 샌드박스 셸 실행
│   ├── files/            # allowed_roots 내 파일 I/O
│   ├── browser/          # Playwright 브라우저 자동화 (opt-in)
│   ├── memory/           # 벡터 메모리 (Chroma / 인메모리)
│   └── api/              # 외부 HTTP 호출 (도메인 필터링)
│
├── skills/               # 스킬 패키지 (YAML + 핸들러)
│   └── example_skill/    # web_research 예제
│
├── mcp/                  # MCP 서버 관리
│   ├── servers/          # 커스텀 서버 구현체 위치
│   ├── configs/          # 서버별 YAML 설정
│   └── adapters/         # MCP → ToolRegistry 브리지
│
├── agents/               # 에이전트 정의 YAML
│   ├── main_agent.yaml
│   └── sub_agents/
│
├── config/               # 전역 설정
│   ├── default.yaml
│   ├── models.yaml       # 모델 공급자, 라우팅, 비용 제어
│   ├── runtimes.yaml     # 런타임 활성화·설정
│   ├── tools.yaml        # 내장 툴 등록
│   ├── permissions.yaml  # 권한 세트 정의
│   └── env.example       # 환경 변수 템플릿
│
├── tests/
│   ├── unit/             # 코어 컴포넌트 단위 테스트
│   ├── integration/      # 런타임 통합 테스트
│   ├── agent_eval/       # 에이전트 시나리오 테스트
│   └── skill_eval/       # 스킬 단위 테스트
│
├── docs/                 # 추가 문서
├── html/                 # HTML 형식 문서 (브라우저에서 열기)
├── data/
│   ├── memory/           # 벡터 메모리 퍼시스턴트 저장소
│   └── traces/           # JSONL 실행 트레이스
├── workspace/            # 에이전트 파일 작업 루트
├── scripts/
│   ├── setup_local.sh
│   ├── run_agent.sh
│   └── run_tests.sh
└── pyproject.toml
```

---

## 4. 설치 및 환경 설정

### 4-1. 사전 조건

| 항목 | 버전 | 용도 |
|---|---|---|
| Python | 3.11 이상 | 프로젝트 런타임 |
| Gemma4 체크포인트 | 로컬 경로 | `/workspace/playground/Gemma4/ckpts` 등 |
| Node.js | 18 이상 | MCP 서버 (npx) |
| Git | - | 레포 관리 |

### 4-2. Gemma4 체크포인트 준비

```bash
# 예시 경로
ls /workspace/playground/Gemma4/ckpts
```

### 4-3. 프로젝트 설치

```bash
git clone <repo-url>
cd gemma-agent

# 자동 설치 (venv 생성 + 패키지 설치 + .env 복사 포함)
bash scripts/setup_local.sh

# 또는 수동 설치
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp config/env.example .env
```

### 4-4. 환경 변수 설정

`.env` 파일을 열고 필요한 값을 채웁니다.

```dotenv
# 로컬 Gemma4 체크포인트 경로
GEMMA_MODEL_PATH=/workspace/playground/Gemma4/ckpts

# MCP Brave Search (선택)
BRAVE_API_KEY=...
```

> 1차 버전 정책: Gemma4 로드/호출 실패 시 즉시 종료하며, 외부 API로 폴백하지 않습니다.

---

## 5. 빠른 시작

```bash
source .venv/bin/activate

# 단일 목표 실행
agent run "workspace 폴더의 파일 목록을 정리해서 요약해줘"

# 인터랙티브 REPL
agent repl

# API 서버 실행 (포트 8000)
uvicorn apps.api_server.main:app --reload
```

---

## 6. CLI 사용법

### 6-1. `agent run` — 단일 목표 실행

```bash
agent run "<목표>" [옵션]

# 옵션
--agent, -a    사용할 에이전트 ID (기본값: main_agent)
--config, -c   설정 디렉토리 경로 (기본값: config/)

# 예시
agent run "Python으로 피보나치 함수 작성해줘"
agent run "workspace/report.txt 파일 요약해줘" --agent file_worker
agent run "최신 AI 논문 3개 검색해줘" --agent researcher
```

### 6-2. `agent repl` — 인터랙티브 세션

```bash
agent repl [옵션]
--agent, -a    사용할 에이전트 ID (기본값: main_agent)

# REPL 내부 명령
> 안녕, 오늘 할 일 목록 작성해줘   ← 자연어 입력
> /quit                            ← 종료
```

### 6-3. `agent replay` — 트레이스 재생

```bash
# 특정 세션의 실행 기록 조회
agent replay data/traces/abc12345.jsonl

# 출력 예시
001 AgentStartedEvent     agent_id=main_agent goal=workspace 파일 요약...
002 TaskDispatchedEvent   task_id=a1b2 runtime_id=files
003 ToolCalledEvent       tool_id=read_file latency_ms=12.4
004 ModelQueriedEvent     provider=gemma4_local input_tokens=512
005 AgentDoneEvent        success=True
```

---

## 7. API 서버 사용법

### 7-1. 서버 시작

```bash
# 개발 모드 (자동 리로드)
uvicorn apps.api_server.main:app --host 0.0.0.0 --port 8000 --reload

# 프로덕션
uvicorn apps.api_server.main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 7-2. 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/tasks` | 작업 제출 (동기 응답) |
| `GET` | `/health` | 서버 상태 확인 |

### 7-3. 작업 제출 예시

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Python 버블정렬 코드 작성해줘",
    "agent_id": "coder"
  }'
```

응답:
```json
{
  "result": "def bubble_sort(arr): ...",
  "session_id": "a1b2c3d4"
}
```

### 7-4. Swagger UI

서버 실행 후 브라우저에서 확인:
```
http://localhost:8000/docs
```

---

## 8. 에이전트 설정

에이전트는 `agents/` 디렉토리의 YAML 파일로 정의합니다.

### 8-1. 에이전트 YAML 구조

```yaml
# agents/sub_agents/my_agent.yaml

id: my_agent                     # 고유 ID (CLI/API에서 --agent 옵션으로 참조)
role: specialist                  # 역할 설명 (프롬프트에 포함)
goal: "이 에이전트가 하는 일 설명"

model_policy:
  preferred: gemma4_local         # 1순위 모델 공급자
  fallback: openai_gpt4o          # 실패 시 폴백
  max_cost_usd: 0.10              # 세션당 최대 API 비용 (선택)

memory_scope: agent               # session | agent | global
runtime_access:                   # 이 에이전트가 사용할 수 있는 런타임
  - reasoning
  - files
  - memory

permissions: worker               # 권한 세트 이름 (config/permissions.yaml 참조)
                                  # 또는 인라인으로 직접 지정 가능:
# permissions:
#   file_read: true
#   file_write: true
#   shell_exec: false

tools:                            # 사용 가능한 툴 ID 목록
  - read_file
  - write_file

skills:                           # 사용 가능한 스킬 ID 목록
  - web_research

sub_agents:                       # 위임 가능한 서브에이전트 ID 목록
  - researcher
```

### 8-2. 내장 에이전트 목록

| ID | 역할 | 주요 권한 |
|---|---|---|
| `main_agent` | 오케스트레이터 | 서브에이전트 위임, 메모리 읽기/쓰기 |
| `researcher` | 웹 리서치 | 네트워크, 브라우저, API |
| `coder` | 코드 생성·리뷰 | 파일 읽기/쓰기, MCP |
| `file_worker` | 파일 작업 | 파일 읽기/쓰기만 |
| `tool_operator` | 셸 실행 | 셸 실행 (유일하게 허용) |

### 8-3. 새 에이전트 추가

```bash
# 1. YAML 파일 생성
cp agents/sub_agents/researcher.yaml agents/sub_agents/my_analyst.yaml

# 2. id, role, goal, permissions 수정
# 3. main_agent.yaml의 sub_agents 목록에 추가
#    sub_agents:
#      - my_analyst

# 4. 바로 사용 가능
agent run "주어진 데이터 분석해줘" --agent my_analyst
```

---

## 9. 런타임 설정

런타임은 `config/runtimes.yaml`에서 관리합니다.

### 9-1. 런타임 활성화·비활성화

```yaml
# config/runtimes.yaml
runtimes:
  browser:
    enabled: false   # ← true로 변경하면 활성화
    module: runtimes.browser.BrowserRuntime
    config:
      headless: true
      browser: chromium
      timeout_seconds: 60
```

### 9-2. 런타임별 주요 설정

**files 런타임 — 허용 경로 설정**
```yaml
files:
  enabled: true
  config:
    allowed_roots:
      - ./workspace          # 에이전트가 접근 가능한 루트 디렉토리
      - /tmp/agent_workspace
    max_file_size_mb: 50
```

**api 런타임 — 도메인 필터링**
```yaml
api:
  enabled: true
  config:
    timeout_seconds: 15
    allowed_domains:          # 빈 리스트 = 모든 도메인 허용
      - api.openai.com        # 특정 도메인만 허용하려면 여기에 추가
      - api.anthropic.com
```

**memory 런타임 — 벡터 DB 전환**
```yaml
memory:
  enabled: true
  config:
    backend: chroma           # in_memory → chroma (영구 저장)
    persist_path: ./data/memory
    embedding_model: nomic-embed-text
```

### 9-3. 새 런타임 추가

```python
# runtimes/myruntime/runtime.py

from core.runtime.base import HealthStatus, RuntimeCall, RuntimeResult

class MyRuntime:
    runtime_id = "myruntime"
    capabilities = ["my_op"]

    def configure(self, config: dict) -> None:
        self._setting = config.get("setting", "default")

    def execute(self, call: RuntimeCall) -> RuntimeResult:
        if call.operation == "my_op":
            return RuntimeResult(success=True, data={"result": "..."})
        return RuntimeResult(success=False, error=f"Unknown: {call.operation}")

    def health_check(self) -> HealthStatus:
        return HealthStatus.OK
```

```yaml
# config/runtimes.yaml에 추가
runtimes:
  myruntime:
    enabled: true
    module: runtimes.myruntime.MyRuntime
    config:
      setting: custom_value
```

---

## 10. 모델 설정 및 라우팅

`config/models.yaml`에서 모델 공급자와 라우팅 규칙을 설정합니다.

### 10-1. 공급자 설정

```yaml
providers:
  gemma4_local:
    type: local
    backend: transformers_local
    model: /workspace/playground/Gemma4/ckpts
    base_url: ""
    priority: 1                # 낮을수록 먼저 시도
```

### 10-2. 라우팅 규칙

특정 작업 유형에 특정 모델을 우선 사용하도록 설정:

```yaml
routing:
  rules:
    # 코드 생성은 로컬 모델로
    - match: { task_type: code_generation }
      prefer: gemma4_local

    # 긴 문서는 컨텍스트 큰 로컬 모델로
    - match: { context_tokens: ">100000" }
      prefer: gemma4_local

  # 규칙 미매칭 시 순서대로 시도
  fallback_chain:
    - gemma4_local
```

### 10-3. 비용 제어

```yaml
providers:
  openai_gpt4o:
    cost_control:
      max_cost_per_session_usd: 1.00   # 세션당 $1 초과 시 다음 공급자로

retry:
  max_attempts: 3
  backoff: exponential      # exponential | linear | none
  backoff_base_ms: 500
  max_backoff_ms: 10000
```

---

## 11. 스킬 개발

스킬은 `skills/<skill_id>/` 디렉토리에 4개 파일로 구성됩니다.

### 11-1. 파일 구조

```
skills/
└── my_skill/
    ├── skill.yaml       ← 메타데이터, 입출력 스키마
    ├── instructions.md  ← 에이전트에게 보여줄 사용 설명
    ├── handler.py       ← 실제 실행 로직
    └── tests/
        └── test_handler.py
```

### 11-2. `skill.yaml` 작성

```yaml
id: my_skill
version: "1.0.0"
name: 내 스킬 이름
description: "이 스킬이 하는 일"

runtime_required:
  - api           # 필요한 런타임 목록

permissions_required:
  - network_access

inputs:
  - name: query
    type: string
    required: true
  - name: max_results
    type: integer
    default: 10

outputs:
  - name: results
    type: array

timeout_seconds: 30
enabled: true
```

### 11-3. `handler.py` 작성

```python
# skills/my_skill/handler.py

def run(inputs: dict, context=None) -> dict:
    """
    inputs: skill.yaml의 inputs 스키마에 맞게 검증된 딕셔너리
    context: AgentContext (런타임, 모델 접근 가능)
    반환값: skill.yaml의 outputs 스키마와 일치해야 함
    """
    query = inputs["query"]

    # 런타임 사용 예시
    if context:
        api = context.get_runtime("api")
        from core.runtime.base import RuntimeCall
        result = api.execute(RuntimeCall("api", "http_get", {"url": f"https://...?q={query}"}))

    return {"results": [...]}

def validate_inputs(inputs: dict) -> list[str]:
    """검증 오류 목록 반환 (빈 리스트 = 유효)"""
    errors = []
    if not inputs.get("query"):
        errors.append("query는 필수입니다")
    return errors
```

### 11-4. 스킬 테스트

```bash
# 스킬 단독 테스트
pytest tests/skill_eval/ -v

# 특정 스킬만
pytest tests/skill_eval/test_my_skill.py -v
```

---

## 12. MCP 서버 연결

### 12-1. 기존 MCP 서버 활성화

```yaml
# mcp/configs/filesystem_server.yaml
id: mcp_filesystem
transport: stdio
command: npx
args: ["-y", "@modelcontextprotocol/server-filesystem", "./workspace"]
enabled: true    # ← false에서 true로 변경
```

### 12-2. Brave Search MCP 서버 활성화

```bash
# .env에 API 키 설정
BRAVE_API_KEY=BSA...

# mcp/configs/brave_search.yaml
# enabled: true 로 변경
```

### 12-3. 커스텀 MCP 서버 추가

```yaml
# mcp/configs/my_server.yaml
id: mcp_my_server
transport: stdio
command: python
args: ["-m", "mcp.servers.my_server"]
capabilities:
  - my_tool_1
  - my_tool_2
permissions_required:
  - api_call
enabled: true
```

```python
# mcp/servers/my_server/server.py
# mcp SDK를 사용해 서버 구현
from mcp.server import Server
app = Server("my_server")

@app.tool()
def my_tool_1(param: str) -> str:
    return f"결과: {param}"
```

### 12-4. MCP 도구 에이전트에서 사용

MCP 서버가 활성화되면 해당 도구들은 자동으로 `ToolRegistry`에 등록됩니다.
에이전트 YAML의 `tools` 목록에 `mcp_<서버ID>__<툴이름>` 형식으로 추가하면 됩니다.

```yaml
# agents/sub_agents/my_agent.yaml
tools:
  - mcp_filesystem__read_file
  - mcp_brave_search__web_search
```

---

## 13. 권한 시스템

### 13-1. 권한 세트

`config/permissions.yaml`에 정의된 세트를 에이전트 YAML에서 이름으로 참조합니다.

| 세트명 | 설명 | 주요 허용 권한 |
|---|---|---|
| `unrestricted` | 모든 권한 | 전부 |
| `worker` | 일반 작업자 | 파일 읽기/쓰기, MCP, 메모리 |
| `read_only` | 읽기 전용 | 파일 읽기, 메모리 읽기 |
| `network_worker` | 네트워크 작업자 | 네트워크, API, MCP |

### 13-2. 커스텀 권한 인라인 설정

```yaml
# agents/sub_agents/my_agent.yaml
permissions:
  file_read: true
  file_write: true
  shell_exec: false     # 셸 실행 불가
  network_access: true
  mcp_call: true
  api_call: false
  memory_read: true
  memory_write: true
  sub_agent_delegate: false
```

### 13-3. 권한 검사 동작

에이전트가 허용되지 않은 작업을 시도하면:

```
core.permissions.checker.PermissionDeniedError:
  Agent 'researcher' lacks capability: shell_exec
```

해당 스텝이 실패(`NodeStatus.FAILED`)로 표시되고,
`PermissionDeniedEvent`가 트레이스 로그에 기록됩니다.
다른 스텝은 계속 실행됩니다.

---

## 14. 이벤트 & 트레이스 로그

### 14-1. 트레이스 파일 위치

```
data/traces/<session_id>.jsonl
```

각 세션마다 별도 파일이 생성됩니다.

### 14-2. 트레이스 파일 형식

```jsonl
{"_type": "AgentStartedEvent", "agent_id": "main_agent", "goal": "파일 요약", "timestamp": "2026-05-06T10:00:00Z"}
{"_type": "TaskDispatchedEvent", "task_id": "a1b2", "runtime_id": "files", "timestamp": "..."}
{"_type": "ToolCalledEvent", "tool_id": "read_file", "latency_ms": 12.4, "success": true, ...}
{"_type": "ModelQueriedEvent", "provider": "gemma4_local", "input_tokens": 512, "output_tokens": 128, ...}
{"_type": "AgentDoneEvent", "success": true, "summary": "요약 완료", ...}
```

### 14-3. CLI로 트레이스 조회

```bash
agent replay data/traces/abc12345.jsonl
```

### 14-4. Python에서 트레이스 로드

```python
from core.events.trace import TraceWriter

records = TraceWriter.replay("data/traces/abc12345.jsonl")
for r in records:
    print(r["_type"], r.get("tool_id", ""), r.get("latency_ms", ""))
```

---

## 15. 테스트 실행

```bash
# 전체 테스트
bash scripts/run_tests.sh all

# 단위 테스트만
bash scripts/run_tests.sh unit

# 통합 테스트 (런타임)
bash scripts/run_tests.sh integration

# 에이전트 시나리오 테스트
bash scripts/run_tests.sh agent

# 스킬 테스트
bash scripts/run_tests.sh skill

# 커버리지 포함
pytest tests/ --cov=core --cov=runtimes --cov-report=html
open htmlcov/index.html
```

### 테스트 계층 구조

| 계층 | 위치 | Gemma 체크포인트 필요 | 설명 |
|---|---|---|---|
| 단위 | `tests/unit/` | 불필요 | 인터페이스·로직 검증 |
| 통합 | `tests/integration/` | 불필요 | 런타임 실제 동작 |
| 에이전트 평가 | `tests/agent_eval/` | 불필요 (Stub 모델) | 전체 흐름 시나리오 |
| 스킬 평가 | `tests/skill_eval/` | 불필요 | 스킬 핸들러 단독 |

---

## 16. 주요 인터페이스 레퍼런스

### ModelProvider

```python
class ModelProvider(Protocol):
    name: str
    def complete(self, messages: list[Message], options: ModelOptions | None) -> ModelResponse: ...
    def stream(self, messages: list[Message], options: ModelOptions | None) -> Iterator[str]: ...
    def health_check(self) -> bool: ...
```

### RuntimeInterface

```python
class RuntimeInterface(Protocol):
    runtime_id: str
    capabilities: list[str]
    def execute(self, call: RuntimeCall) -> RuntimeResult: ...
    def health_check(self) -> HealthStatus: ...
    def configure(self, config: dict) -> None: ...
```

### SkillHandler

```python
def run(inputs: dict[str, Any], context: AgentContext | None) -> dict[str, Any]: ...
def validate_inputs(inputs: dict) -> list[str]: ...
```

### AgentDefinition (YAML → Python)

```python
@dataclass
class AgentDefinition:
    id: str
    role: str
    goal: str
    model_policy: ModelPolicy      # preferred, fallback, max_cost_usd
    memory_scope: MemoryScope      # session | agent | global
    runtime_access: list[str]
    permissions: PermissionSet
    tools: list[str]
    skills: list[str]
    sub_agents: list[str]
```

---

## 문서 (HTML)

브라우저에서 보다 편리하게 읽으려면 `html/` 폴더의 문서를 여세요.

```bash
# 브라우저로 열기
open html/index.html          # macOS
xdg-open html/index.html      # Linux
```

---

*한국 정부과제 작성용 — Gemma Agent Orchestrator*
