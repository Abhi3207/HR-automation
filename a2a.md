# A2A Communication — Implementation Plan

> **Goal:** Replace the shared `HRState` TypedDict coupling between agents with the **Google A2A (Agent-to-Agent) Protocol**, making each agent an independent, discoverable service that communicates via JSON-RPC 2.0.

---

## 1. Why A2A?

| Current (Shared State) | Target (A2A Protocol) |
|---|---|
| All 6 agents + supervisor share a single `HRState` TypedDict | Each agent is a standalone HTTP microservice |
| Agents are tightly coupled — every field change affects all agents | Agents are decoupled — communicate only through typed messages |
| No discoverability — agents are hard-wired in `pipeline.py` | Agent Cards at `/.well-known/agent.json` enable runtime discovery |
| Single process, single failure domain | Each agent can be deployed, scaled, and tested independently |
| Data passes through in-memory Python dicts | Data passes through JSON-RPC 2.0 `message/send` tasks |

---

## 2. A2A Protocol Key Concepts

```
┌───────────────────────────────────────────────────────────────────┐
│                        A2A Protocol                               │
│                                                                   │
│  Agent Card (.well-known/agent.json)                              │
│  ├── name, description, url                                       │
│  ├── capabilities: { streaming, pushNotifications }               │
│  └── skills: [{ id, name, description, inputModes, outputModes }]│
│                                                                   │
│  JSON-RPC 2.0 Methods:                                            │
│  ├── message/send    →  Send task, wait for result                │
│  ├── message/stream  →  Send task, receive SSE updates            │
│  ├── tasks/get       →  Poll task status by ID                    │
│  └── tasks/cancel    →  Cancel a running task                     │
│                                                                   │
│  Task Lifecycle:                                                  │
│  submitted → working → completed | failed | canceled              │
│                                                                   │
│  Message Parts (artifacts):                                       │
│  └── { type: "text"|"data", text?, data?, mimeType? }            │
└───────────────────────────────────────────────────────────────────┘
```

---

## 3. Target Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        SUPERVISOR (A2A Client)                          │
│                                                                          │
│  Discovers agents via Agent Cards → sends message/send tasks             │
│  Manages pipeline state internally (not shared with agents)              │
│  Receives structured results from each agent                             │
│  Implements retry/skip logic on task failure                             │
│                                                                          │
│  Pipeline:                                                               │
│  ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐│
│  │ Job   │──▶│Resume │──▶│IntSch │──▶│Feedbk │──▶│Rank   │──▶│Final  ││
│  │Posting│   │Select │   │eduling│   │Collect│   │  ing  │   │Select ││
│  └───┬───┘   └───┬───┘   └───┬───┘   └───┬───┘   └───┬───┘   └───┬───┘│
│      │           │           │           │           │           │      │
│   message/    message/    message/    message/    message/    message/  │
│    send        send        send        send        send        send    │
└──────┼───────────┼───────────┼───────────┼───────────┼───────────┼──────┘
       │           │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
│ Server 1 │ │ Server 2 │ │ Server 3 │ │ Server 4 │ │ Server 5 │ │ Server 6 │
│ :5001    │ │ :5002    │ │ :5003    │ │ :5004    │ │ :5005    │ │ :5006    │
│          │ │          │ │          │ │          │ │          │ │          │
│ Agent    │ │ Agent    │ │ Agent    │ │ Agent    │ │ Agent    │ │ Agent    │
│ Card ✓   │ │ Card ✓   │ │ Card ✓   │ │ Card ✓   │ │ Card ✓   │ │ Card ✓   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
       │           │           │           │           │           │
       └───────────┴───────────┴───────────┴───────────┴───────────┘
                                   │
                                   ▼
                          ┌────────────────┐
                          │   SQLite DB    │
                          │  (shared via   │
                          │  filesystem)   │
                          └────────────────┘
```

> [!IMPORTANT]
> The database remains shared. Agents still perform DB operations through their existing tools. The A2A layer replaces the *LangGraph shared state* communication — not the DB. This keeps the migration minimal and focused.

---

## 4. Data Flow — Before vs. After

### Before (Shared State)

```
Supervisor sets next_agent in HRState
    → LangGraph routes to agent node
    → Agent reads all fields from HRState (messages, candidates, etc.)
    → Agent writes results back into HRState
    → LangGraph returns to Supervisor
```

### After (A2A)

```
Supervisor builds a JSON task message with ONLY the data the agent needs
    → HTTP POST to agent's /a2a endpoint (JSON-RPC message/send)
    → Agent receives task, does its work (LLM + tools + DB)
    → Agent returns a completed task with structured result artifacts
    → Supervisor parses result, decides next step
```

**Key difference:** Each agent receives a targeted *task payload* instead of the entire pipeline state. The supervisor is the only component that tracks pipeline-wide context.

---

## 5. Agent Card Definitions

Each agent will serve an Agent Card at `/.well-known/agent.json`. Example for the Job Posting Agent:

```json
{
  "protocolVersion": "0.2.1",
  "name": "Job Posting Agent",
  "description": "Creates professional, detailed job postings based on hiring requirements and saves them to the HR database.",
  "url": "http://localhost:5001",
  "version": "2.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "create_job_posting",
      "name": "Create Job Posting",
      "description": "Generates a comprehensive job description with title, requirements, qualifications, salary range, and location. Saves to database.",
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    }
  ]
}
```

### All 6 Agent Cards Summary

| Agent | Port | Skill ID | Input | Output |
|---|---|---|---|---|
| Job Posting | 5001 | `create_job_posting` | `{ job_title, department, requirements, salary_range, location }` | `{ job_posting_id, job_posting }` |
| Resume Selection | 5002 | `screen_resumes` | `{ job_posting_id, candidates[] }` | `{ shortlisted_candidates[], screening_scores[] }` |
| Interview Scheduling | 5003 | `schedule_interviews` | `{ job_posting_id, shortlisted_candidate_ids[] }` | `{ scheduled_interviews[] }` |
| Feedback Collection | 5004 | `collect_feedback` | `{ job_posting_id, interview_ids[] }` | `{ feedback_entries[] }` |
| Candidate Ranking | 5005 | `rank_candidates` | `{ job_posting_id, application_ids[] }` | `{ rankings[] }` |
| Final Selection | 5006 | `make_decisions` | `{ job_posting_id, ranking_ids[] }` | `{ decisions[] }` |

---

## 6. Task Message Format

### Request (Supervisor → Agent)

```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": "task-uuid-1234",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {
          "type": "text",
          "text": "Create a job posting for Senior Software Engineer..."
        },
        {
          "type": "data",
          "mimeType": "application/json",
          "data": {
            "job_title": "Senior Software Engineer",
            "department": "Engineering",
            "requirements": "5+ years Python...",
            "salary_range": "$130,000 - $180,000",
            "location": "Remote (US)"
          }
        }
      ]
    }
  }
}
```

### Response (Agent → Supervisor)

```json
{
  "jsonrpc": "2.0",
  "id": "task-uuid-1234",
  "result": {
    "id": "task-uuid-1234",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "name": "job_posting_result",
        "parts": [
          {
            "type": "text",
            "text": "Successfully created job posting #1 for Senior Software Engineer."
          },
          {
            "type": "data",
            "mimeType": "application/json",
            "data": {
              "job_posting_id": 1,
              "job_posting": {
                "title": "Senior Software Engineer",
                "department": "Engineering",
                "status": "open"
              }
            }
          }
        ]
      }
    ]
  }
}
```

---

## 7. Proposed Changes — File-by-File

### New Dependencies

#### [MODIFY] [requirements.txt](file:///c:/Users/abhin/OneDrive/Documents/my_projects/hr-multi-agent-system/requirements.txt)

Add the `a2a-python` SDK:

```diff
 langgraph>=0.4.0
 langchain>=0.3.0
 langchain-openai>=0.3.0
 langchain-core>=0.3.0
 fastapi>=0.115.0
 uvicorn>=0.34.0
 streamlit>=1.45.0
 sqlalchemy>=2.0.0
 python-dotenv>=1.0.0
 pydantic>=2.0.0
 httpx>=0.27.0
 pandas
 numpy
+a2a-python>=0.2.0
```

---

### New Module: `a2a/` — A2A Communication Layer

#### [NEW] `a2a/__init__.py`

Empty init file.

#### [NEW] `a2a/agent_card.py`

Factory function to build Agent Card dicts for each of the 6 agents. Parametrized by agent name, description, port, and skills list.

```python
def build_agent_card(name, description, url, skills) -> dict:
    """Build a standard A2A Agent Card."""
    return {
        "protocolVersion": "0.2.1",
        "name": name,
        "description": description,
        "url": url,
        "version": "2.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "skills": skills,
    }
```

#### [NEW] `a2a/task_manager.py`

In-memory task store that tracks A2A task lifecycle (`submitted → working → completed/failed`). Each agent server uses this to manage its tasks.

- `create_task(task_id) → Task`
- `update_task(task_id, status, artifacts) → Task`
- `get_task(task_id) → Task`
- `cancel_task(task_id) → Task`

#### [NEW] `a2a/message_handler.py`

Abstract base class that each agent implements. Receives an A2A message, extracts the structured data payload, runs the agent's LangGraph sub-graph, and returns structured artifacts.

```python
class A2AMessageHandler(ABC):
    @abstractmethod
    async def handle_message(self, message: dict) -> dict:
        """Process an A2A message and return result artifacts."""
        ...
```

#### [NEW] `a2a/server_factory.py`

Creates a FastAPI app for any agent with:
- `GET /.well-known/agent.json` — Agent Card endpoint
- `POST /a2a` — JSON-RPC 2.0 dispatcher (`message/send`, `tasks/get`, `tasks/cancel`)

This is a **generic factory** — each agent just plugs in its Agent Card + message handler.

```python
def create_agent_server(agent_card: dict, handler: A2AMessageHandler) -> FastAPI:
    """Create an A2A-compliant FastAPI app for an agent."""
    app = FastAPI(title=agent_card["name"])

    @app.get("/.well-known/agent.json")
    async def get_agent_card():
        return agent_card

    @app.post("/a2a")
    async def handle_jsonrpc(request: dict):
        # Dispatch based on request["method"]
        ...

    return app
```

#### [NEW] `a2a/client.py`

A2A client used by the Supervisor to:
1. **Discover** agents by fetching their Agent Cards
2. **Send tasks** via `message/send`
3. **Poll status** via `tasks/get`
4. **Cancel** via `tasks/cancel`

```python
class A2AClient:
    def __init__(self, agent_url: str):
        self.agent_url = agent_url
        self.agent_card = None

    async def discover(self) -> dict:
        """Fetch the agent's Agent Card."""
        ...

    async def send_message(self, task_id: str, message: dict) -> dict:
        """Send a message/send JSON-RPC request."""
        ...

    async def get_task(self, task_id: str) -> dict:
        """Poll task status."""
        ...
```

---

### Agent Servers — Wrapping Each Existing Agent

Each agent gets a new `_server.py` file that wraps its existing LangGraph sub-graph into an A2A-compliant server.

#### [NEW] `agents/job_posting_server.py`

```python
# 1. Import the existing build function
from agents.job_posting_agent import build_job_posting_agent
from a2a.server_factory import create_agent_server
from a2a.message_handler import A2AMessageHandler

class JobPostingHandler(A2AMessageHandler):
    async def handle_message(self, message):
        # Extract job requirements from message parts
        # Build minimal LangGraph state
        # Run the existing sub-graph
        # Return structured result as A2A artifacts
        ...

# Build the server
handler = JobPostingHandler()
agent_card = build_agent_card(...)
app = create_agent_server(agent_card, handler)
```

**Same pattern repeated for all 6 agents:**

| File | Agent | Port |
|---|---|---|
| [NEW] `agents/job_posting_server.py` | Job Posting | 5001 |
| [NEW] `agents/resume_selection_server.py` | Resume Selection | 5002 |
| [NEW] `agents/interview_scheduling_server.py` | Interview Scheduling | 5003 |
| [NEW] `agents/feedback_server.py` | Feedback Collection | 5004 |
| [NEW] `agents/ranking_server.py` | Candidate Ranking | 5005 |
| [NEW] `agents/final_selection_server.py` | Final Selection | 5006 |

> [!NOTE]
> The existing agent files (`job_posting_agent.py`, etc.) remain **untouched**. The new `*_server.py` files wrap them. The LangGraph sub-graphs inside each agent continue to work as they do today — we just change how they receive input and return output.

---

### Supervisor Refactor

#### [MODIFY] [supervisor.py](file:///c:/Users/abhin/OneDrive/Documents/my_projects/hr-multi-agent-system/graph/supervisor.py)

The supervisor transforms from a LangGraph node into an **A2A orchestrator client**:

**Current:** Reads `HRState`, uses structured output LLM to pick `next_agent`, sets `next_agent` in state.

**New:** Maintains an internal pipeline context dict, sequentially sends tasks to each agent via A2A, collects results, handles retries.

```python
class A2ASupervisor:
    """Orchestrates the HR pipeline by sending A2A tasks to agent services."""

    def __init__(self, agent_urls: dict[str, str]):
        self.clients = {
            name: A2AClient(url)
            for name, url in agent_urls.items()
        }
        self.pipeline_context = {}  # Internal state, NOT shared

    async def run_pipeline(self, job_request: dict) -> dict:
        """Execute the full pipeline via A2A communication."""

        # Step 1: Job Posting
        result = await self._send_task("job_posting", {
            "job_title": job_request["job_title"],
            "department": job_request["department"],
            ...
        })
        self.pipeline_context["job_posting_id"] = result["job_posting_id"]

        # Step 2: Resume Selection
        result = await self._send_task("resume_selection", {
            "job_posting_id": self.pipeline_context["job_posting_id"],
            "candidates": job_request["candidates"],
        })
        self.pipeline_context["shortlisted_ids"] = result["shortlisted_ids"]

        # ... Steps 3-6 ...

    async def _send_task(self, agent_name, payload, max_retries=2):
        """Send a task with retry logic."""
        for attempt in range(max_retries + 1):
            try:
                result = await self.clients[agent_name].send_message(
                    task_id=str(uuid.uuid4()),
                    message=self._build_message(payload)
                )
                if result["status"]["state"] == "completed":
                    return self._extract_data(result)
            except Exception as e:
                if attempt == max_retries:
                    raise
        ...
```

#### [MODIFY] [pipeline.py](file:///c:/Users/abhin/OneDrive/Documents/my_projects/hr-multi-agent-system/graph/pipeline.py)

The `build_pipeline()` function is replaced by an `A2ASupervisor` instantiation. The LangGraph `StateGraph` is no longer needed for top-level orchestration (though each agent internally still uses its own LangGraph sub-graph).

```python
def build_a2a_pipeline(agent_urls: dict = None):
    """Build the pipeline using A2A protocol communication."""
    if agent_urls is None:
        agent_urls = {
            "job_posting": "http://localhost:5001",
            "resume_selection": "http://localhost:5002",
            "interview_scheduling": "http://localhost:5003",
            "feedback_collection": "http://localhost:5004",
            "candidate_ranking": "http://localhost:5005",
            "final_selection": "http://localhost:5006",
        }
    return A2ASupervisor(agent_urls)
```

---

### State Changes

#### [MODIFY] [hr_state.py](file:///c:/Users/abhin/OneDrive/Documents/my_projects/hr-multi-agent-system/state/hr_state.py)

The `HRState` TypedDict is **kept but reduced**. It's still used *internally* within each agent's sub-graph (since agents still use LangGraph ReAct loops for LLM ↔ tool interaction). However, we add a lightweight `AgentTaskInput` and `AgentTaskOutput` schema for A2A message payloads:

```python
# Existing HRState stays for internal agent use (unchanged)

# NEW: Pydantic models for A2A message data payloads
class AgentTaskInput(BaseModel):
    """Base input schema for A2A task messages."""
    task_description: str
    data: dict  # Agent-specific payload

class AgentTaskOutput(BaseModel):
    """Base output schema for A2A task results."""
    status: str  # "success" | "error"
    data: dict  # Agent-specific result
    error: Optional[str] = None
```

---

### Settings Update

#### [MODIFY] [settings.py](file:///c:/Users/abhin/OneDrive/Documents/my_projects/hr-multi-agent-system/config/settings.py)

Add agent service URLs and ports:

```python
# A2A Agent Service Configuration
self.AGENT_PORTS: dict = {
    "job_posting": self._parse_int("AGENT_PORT_JOB_POSTING", 5001),
    "resume_selection": self._parse_int("AGENT_PORT_RESUME_SELECTION", 5002),
    "interview_scheduling": self._parse_int("AGENT_PORT_INTERVIEW_SCHEDULING", 5003),
    "feedback_collection": self._parse_int("AGENT_PORT_FEEDBACK_COLLECTION", 5004),
    "candidate_ranking": self._parse_int("AGENT_PORT_CANDIDATE_RANKING", 5005),
    "final_selection": self._parse_int("AGENT_PORT_FINAL_SELECTION", 5006),
}
self.AGENT_HOST: str = os.getenv("AGENT_HOST", "localhost")
```

---

### Main Entry Point

#### [MODIFY] [main.py](file:///c:/Users/abhin/OneDrive/Documents/my_projects/hr-multi-agent-system/main.py)

Add new commands for the A2A workflow:

```python
# New commands:
"agents"  →  Start all 6 agent servers (as subprocesses or concurrent tasks)
"a2a-run" →  Run the pipeline using A2A communication (supervisor sends tasks)
```

The existing `run` command is kept as a legacy/fallback (shared-state mode), so migration is non-breaking.

---

### API Layer Integration

#### [MODIFY] [server.py](file:///c:/Users/abhin/OneDrive/Documents/my_projects/hr-multi-agent-system/api/server.py)

The `/pipeline/start` endpoint switches to use `A2ASupervisor.run_pipeline()` instead of `pipeline.invoke()`:

```python
async def _run_pipeline_background(run_id, request):
    supervisor = A2ASupervisor(agent_urls=settings.get_agent_urls())
    result = await supervisor.run_pipeline({
        "job_title": request.job_title,
        "department": request.department,
        "requirements": request.requirements,
        "candidates": request.candidates,
    })
    # Update _pipeline_runs[run_id] with result
```

New endpoints for agent management:

```python
GET  /agents          → List registered agents and their Agent Card info
GET  /agents/{name}   → Get specific agent's Agent Card
GET  /agents/health   → Check health of all agent services
```

---

### Process Manager

#### [NEW] `a2a/process_manager.py`

Manages starting/stopping all 6 agent servers for local development:

```python
class AgentProcessManager:
    """Starts all agent servers as subprocesses."""

    def start_all(self):
        """Start all 6 agent servers."""
        for name, port in settings.AGENT_PORTS.items():
            subprocess.Popen([
                sys.executable, "-m", "uvicorn",
                f"agents.{name}_server:app",
                "--host", "0.0.0.0", "--port", str(port),
            ])

    def stop_all(self): ...
    def health_check(self) -> dict: ...
```

---

## 8. Implementation Phases

### Phase 1: A2A Infrastructure (New files, no breaking changes)

- [ ] Create `a2a/` module (`__init__.py`, `agent_card.py`, `task_manager.py`, `message_handler.py`, `server_factory.py`, `client.py`)
- [ ] Add `a2a-python` to `requirements.txt`
- [ ] Add A2A port/host settings to `config/settings.py`
- [ ] Add `AgentTaskInput`/`AgentTaskOutput` schemas to `state/hr_state.py`

### Phase 2: Agent Servers (New files, existing agents untouched)

- [ ] Create `agents/job_posting_server.py`
- [ ] Create `agents/resume_selection_server.py`
- [ ] Create `agents/interview_scheduling_server.py`
- [ ] Create `agents/feedback_server.py`
- [ ] Create `agents/ranking_server.py`
- [ ] Create `agents/final_selection_server.py`
- [ ] Test each agent server independently with curl/httpx

### Phase 3: Supervisor & Pipeline Migration

- [ ] Build `A2ASupervisor` class in `graph/supervisor.py` (add, don't replace)
- [ ] Build `build_a2a_pipeline()` in `graph/pipeline.py` (add, don't replace)
- [ ] Wire retry logic into `A2ASupervisor._send_task()`
- [ ] Integrate `StageTimer` metrics into A2A task flow

### Phase 4: Integration & Entry Points

- [ ] Add `agents` and `a2a-run` commands to `main.py`
- [ ] Create `a2a/process_manager.py` for starting/stopping agents
- [ ] Update `api/server.py` `/pipeline/start` to use A2A supervisor
- [ ] Add `/agents` endpoints to `api/server.py`
- [ ] Update `.env.example` with new A2A settings
- [ ] Update `README.md` with A2A usage instructions

### Phase 5: Polish & Testing

- [ ] End-to-end test: start all agents → run pipeline via A2A → verify DB results
- [ ] Update `ui/dashboard.py` to show agent status (optional)
- [ ] Update `architecture.md` with new A2A architecture
- [ ] Clean up and document

---

## 9. What Stays the Same

These components are **NOT changed** by this migration:

| Component | Why |
|---|---|
| `database/models.py` | DB schema is unchanged — agents still CRUD the same tables |
| `database/db.py` | Session management is unchanged |
| `tools/*.py` | All tool functions are unchanged — agents still use them internally |
| `agents/*_agent.py` | The LangGraph sub-graphs are unchanged — servers wrap them |
| `config/metrics.py` | `StageTimer` is reused in the A2A flow |
| `config/logging_config.py` | Logging is unchanged |
| `api/schemas.py` | API request/response schemas are unchanged |
| `ui/dashboard.py` | Dashboard reads from DB — unaffected |

---

## 10. Updated Directory Structure

```
hr-multi-agent-system/
│
├── a2a/                                 # 🆕 A2A Communication Layer
│   ├── __init__.py
│   ├── agent_card.py                    # Agent Card builder
│   ├── task_manager.py                  # Task lifecycle management
│   ├── message_handler.py              # Abstract message handler base
│   ├── server_factory.py               # Generic A2A server factory
│   ├── client.py                        # A2A client for supervisor
│   └── process_manager.py              # Multi-agent process manager
│
├── agents/                              # 🤖 AI Agents
│   ├── job_posting_agent.py             # (unchanged) LangGraph sub-graph
│   ├── job_posting_server.py            # 🆕 A2A server wrapper
│   ├── resume_selection_agent.py        # (unchanged)
│   ├── resume_selection_server.py       # 🆕
│   ├── interview_scheduling_agent.py    # (unchanged)
│   ├── interview_scheduling_server.py   # 🆕
│   ├── feedback_agent.py               # (unchanged)
│   ├── feedback_server.py              # 🆕
│   ├── ranking_agent.py                 # (unchanged)
│   ├── ranking_server.py               # 🆕
│   ├── final_selection_agent.py         # (unchanged)
│   └── final_selection_server.py        # 🆕
│
├── graph/
│   ├── pipeline.py                      # (modified) adds build_a2a_pipeline()
│   └── supervisor.py                    # (modified) adds A2ASupervisor class
│
├── state/
│   └── hr_state.py                      # (modified) adds A2A payload schemas
│
├── config/
│   └── settings.py                      # (modified) adds agent port settings
│
├── main.py                              # (modified) adds 'agents' and 'a2a-run' commands
│
└── ... (all other files unchanged)
```

---

## 11. Open Questions

> [!IMPORTANT]
> **1. Single-process vs. Multi-process for local dev?**
> Should the `agents` command start all 6 agent servers as **separate OS processes** (true microservices), or run them all in a **single process** using different FastAPI routers on different ports? Separate processes is more realistic but heavier for local dev.

> [!IMPORTANT]
> **2. Use the `a2a-python` SDK or implement A2A from scratch?**
> The `a2a-python` PyPI package provides ready-made server/client utilities. We can either:
> - **(A)** Use `a2a-python` for full spec compliance (less code, potential dependency issues)
> - **(B)** Implement a lightweight A2A-compatible layer ourselves using plain FastAPI + httpx (more control, simpler dependencies)
>
> I recommend **(B)** — building it ourselves with FastAPI + httpx — since we already use both, and it avoids pulling in an immature external SDK. We'd still follow the A2A spec (Agent Cards, JSON-RPC 2.0, task lifecycle) but own the implementation.

> [!IMPORTANT]
> **3. Keep the legacy shared-state pipeline?**
> Should the old `build_pipeline()` + `HRState` flow remain as a fallback (selectable via `python main.py run`), or should we fully replace it? I recommend keeping it during development for comparison and fallback.

---

## 12. Verification Plan

### Automated Tests

```bash
# 1. Start all agent servers
python main.py agents

# 2. Test agent discovery
curl http://localhost:5001/.well-known/agent.json
curl http://localhost:5002/.well-known/agent.json
# ... all 6

# 3. Test individual agent task (Job Posting)
curl -X POST http://localhost:5001/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":"test-1","params":{...}}'

# 4. Run full pipeline via A2A
python main.py a2a-run

# 5. Compare DB results with legacy pipeline
python main.py reset && python main.py run      # Legacy
python main.py reset && python main.py a2a-run   # A2A
# Both should produce equivalent job postings, screenings, interviews, etc.
```

### Manual Verification

- [ ] Each agent's `/.well-known/agent.json` returns valid Agent Card
- [ ] JSON-RPC `message/send` to each agent returns correct task lifecycle
- [ ] Supervisor retry logic works when an agent is temporarily unavailable
- [ ] Pipeline completes end-to-end with same DB results as legacy mode
- [ ] API `/pipeline/start` works with A2A backend
- [ ] Streamlit dashboard shows same data after A2A pipeline run
