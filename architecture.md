# 🏢 HR Multi-Agent Recruitment System — Architecture Document

> **Version:** 2.0  
> **Last Updated:** 2026-06-20  
> **Author:** Auto-generated from source-code analysis

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Step-by-Step Pipeline Walkthrough](#3-step-by-step-pipeline-walkthrough)
   - [Step 0 — Configuration & Bootstrapping](#step-0--configuration--bootstrapping)
   - [Step 1 — State Initialization](#step-1--state-initialization)
   - [Step 2 — Supervisor Routing](#step-2--supervisor-routing)
   - [Step 3 — Job Posting Agent](#step-3--job-posting-agent)
   - [Step 4 — Resume Selection Agent](#step-4--resume-selection-agent)
   - [Step 5 — Interview Scheduling Agent](#step-5--interview-scheduling-agent)
   - [Step 6 — Feedback Collection Agent](#step-6--feedback-collection-agent)
   - [Step 7 — Candidate Ranking Agent](#step-7--candidate-ranking-agent)
   - [Step 8 — Final Selection Agent](#step-8--final-selection-agent)
   - [Step 9 — Pipeline Completion](#step-9--pipeline-completion)
4. [Agent Sub-Graph Architecture](#4-agent-sub-graph-architecture)
5. [Database Schema (ERD)](#5-database-schema-erd)
6. [API Layer](#6-api-layer)
7. [Dashboard (UI Layer)](#7-dashboard-ui-layer)
8. [Observability & Metrics](#8-observability--metrics)
9. [Resilience & Error Handling](#9-resilience--error-handling)
10. [Complete Tech Stack Summary](#10-complete-tech-stack-summary)
11. [Project Directory Structure](#11-project-directory-structure)
12. [Deployment Guide — GCP](#12-deployment-guide--gcp)
13. [Deployment Guide — AWS](#13-deployment-guide--aws)
14. [Deployment Guide — Azure](#14-deployment-guide--azure)

---

## 1. System Overview

The **HR Multi-Agent Recruitment System** automates the end-to-end hiring pipeline using a **multi-agent architecture** powered by **LangGraph**. Six specialized AI agents — orchestrated by a central Supervisor — collaboratively handle every stage of recruitment, from job posting creation to final hire/reject decisions.

### Core Principles

| Principle | Implementation |
|-----------|----------------|
| **Separation of concerns** | Each pipeline stage is handled by a dedicated agent with its own tools |
| **Shared state** | A single `HRState` TypedDict flows through the entire LangGraph |
| **Resilience** | Supervisor provides automatic retry (configurable, default 2) with skip-on-failure |
| **Observability** | Per-stage wall-clock timing, tool-call counts, and success/error tracking |
| **Multi-interface** | CLI (`main.py`), REST API (FastAPI), and Dashboard (Streamlit) |

---

## 2. High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                            │
│  ┌─────────────────┐   ┌───────────────────┐   ┌────────────────────┐  │
│  │   CLI (main.py) │   │ FastAPI REST API   │   │ Streamlit Dashboard│  │
│  │   argparse       │   │ uvicorn + async    │   │ Interactive UI     │  │
│  └────────┬────────┘   └────────┬──────────┘   └────────┬───────────┘  │
│           │                     │                        │              │
│           └─────────────┬───────┴────────────────────────┘              │
│                         ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     ORCHESTRATION LAYER                          │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐    │   │
│  │  │              LangGraph StateGraph (Pipeline)              │    │   │
│  │  │                                                          │    │   │
│  │  │   START ──► SUPERVISOR ──┬──► Agent 1 ──► SUPERVISOR     │    │   │
│  │  │                         ├──► Agent 2 ──► SUPERVISOR      │    │   │
│  │  │                         ├──► Agent 3 ──► SUPERVISOR      │    │   │
│  │  │                         ├──► Agent 4 ──► SUPERVISOR      │    │   │
│  │  │                         ├──► Agent 5 ──► SUPERVISOR      │    │   │
│  │  │                         ├──► Agent 6 ──► SUPERVISOR      │    │   │
│  │  │                         └──► END (complete)              │    │   │
│  │  └──────────────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        AGENT LAYER                               │   │
│  │                                                                  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐                 │   │
│  │  │ Job Posting │ │  Resume    │ │  Interview   │                 │   │
│  │  │   Agent     │ │ Selection  │ │ Scheduling   │                 │   │
│  │  └────────────┘ └────────────┘ └──────────────┘                 │   │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐                 │   │
│  │  │  Feedback  │ │  Ranking   │ │    Final     │                 │   │
│  │  │ Collection │ │   Agent    │ │  Selection   │                 │   │
│  │  └────────────┘ └────────────┘ └──────────────┘                 │   │
│  │                                                                  │   │
│  │  Each agent = LangGraph sub-graph: agent_node ↔ ToolNode         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      TOOLS LAYER (LangChain @tool)               │   │
│  │                                                                  │   │
│  │  job_tools.py │ resume_tools.py │ scheduling_tools.py            │   │
│  │  feedback_tools.py │ ranking_tools.py │ selection_tools.py       │   │
│  │                                                                  │   │
│  │  Each tool function performs DB CRUD via SQLAlchemy sessions      │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      DATA LAYER                                  │   │
│  │                                                                  │   │
│  │  SQLAlchemy ORM   ──►   SQLite (hr_system.db)                    │   │
│  │  7 tables: job_postings, candidates, applications,               │   │
│  │            interviews, feedback, rankings, offers                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    EXTERNAL SERVICES                             │   │
│  │                                                                  │   │
│  │  OpenAI API (GPT-4o-mini) — LLM inference for all agents        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Step-by-Step Pipeline Walkthrough

### Step 0 — Configuration & Bootstrapping

**What happens:** The system loads environment variables, validates the OpenAI API key, initializes the database, and sets up logging.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `python-dotenv`, `os.getenv()`, Python `logging`, `SQLAlchemy` |
| **Files** | `config/settings.py`, `config/logging_config.py`, `database/db.py` |
| **Data** | `.env` file → `Settings` singleton; `hr_system.db` → SQLAlchemy `engine` |
| **Key Config** | `OPENAI_API_KEY`, `LLM_MODEL` (gpt-4o-mini), `LLM_TEMPERATURE` (0.1), `DATABASE_URL` (sqlite), `AGENT_RECURSION_LIMIT` (25), `AGENT_TIMEOUT_SECONDS` (120), `AGENT_MAX_RETRIES` (2) |

**Flow:**
```
.env  ──►  python-dotenv  ──►  Settings class  ──►  settings.validate()
                                                         │
SQLAlchemy engine ◄── DATABASE_URL ◄─────────────────────┘
        │
        ▼
Base.metadata.create_all()  →  7 tables created in SQLite
```

---

### Step 1 — State Initialization

**What happens:** The shared `HRState` TypedDict is created with the initial hiring request, candidate data, and empty containers for every pipeline stage output.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | Python `TypedDict`, `langchain_core.messages.HumanMessage`, `langgraph.graph.message.add_messages` reducer |
| **Files** | `state/hr_state.py`, `main.py` (lines 138–177) |
| **Data** | Initial `HumanMessage` with job title/requirements/candidates, sample candidate dicts seeded into the DB |

**HRState fields:**

| Category | Fields | Type |
|----------|--------|------|
| **Messages** | `messages` | `Annotated[list[BaseMessage], add_messages]` — append-only conversation history |
| **Pipeline Control** | `current_stage`, `next_agent`, `pipeline_status`, `error_message`, `retry_count`, `max_retries`, `failed_stages` | str, int, list |
| **Job Data** | `job_posting_id`, `job_posting` | Optional[int], Optional[dict] |
| **Candidate Data** | `candidates`, `shortlisted_candidates` | list[dict] |
| **Interview Data** | `scheduled_interviews` | list[dict] |
| **Feedback Data** | `interview_feedback` | list[dict] |
| **Ranking Data** | `candidate_rankings` | list[dict] |
| **Decision Data** | `final_decisions` | list[dict] |
| **Observability** | `stage_metrics` | list[dict] |

---

### Step 2 — Supervisor Routing

**What happens:** The Supervisor agent evaluates the current pipeline state and decides which worker agent should execute next. It uses an LLM with **structured output** (`SupervisorDecision`) to guarantee valid routing.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `langchain_openai.ChatOpenAI` with `.with_structured_output()`, `pydantic.BaseModel`, LangGraph conditional edges |
| **Files** | `graph/supervisor.py`, `graph/pipeline.py` |
| **LLM Model** | GPT-4o-mini (temperature=0 for deterministic routing) |
| **Data** | Reads `current_stage`, `error_message`, `retry_count`, `failed_stages` from `HRState` |
| **Output** | Sets `next_agent` to one of: `job_posting`, `resume_selection`, `interview_scheduling`, `feedback_collection`, `candidate_ranking`, `final_selection`, `complete` |

**Routing Logic:**
```
current_stage = "start"                   → next = "job_posting"
current_stage = "job_posting_complete"    → next = "resume_selection"
current_stage = "resume_selection_complete" → next = "interview_scheduling"
...
current_stage = "final_selection_complete" → next = "complete" (→ END)
```

**Retry Logic:**
```
if error_message AND retry_count < max_retries:
    → Re-route to same agent, bump retry_count
elif error_message AND retries exhausted:
    → Log failure, add to failed_stages, advance to next agent
else:
    → Normal LLM-based routing decision
```

---

### Step 3 — Job Posting Agent

**What happens:** Generates a professional, detailed job posting based on the hiring requirements and saves it to the database.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `langchain_openai.ChatOpenAI` with `.bind_tools()`, `langgraph.prebuilt.ToolNode`, LangGraph sub-graph |
| **Files** | `agents/job_posting_agent.py`, `tools/job_tools.py` |
| **LLM Model** | GPT-4o-mini (temperature=0.1) |
| **Tools Used** | `create_job_posting`, `list_job_postings`, `get_job_posting`, `update_job_posting` |
| **Input Data** | Job title, department, requirements from the initial `HumanMessage` |
| **Output Data** | New row in `job_postings` table; `current_stage` → `"job_posting_complete"` |
| **DB Table** | `job_postings` (id, title, department, description, requirements, preferred_qualifications, salary_range, location, employment_type, status, created_at, updated_at) |

**Agent Sub-Graph Flow:**
```
agent_node (LLM reasoning) ──► should_continue?
    ├── has tool_calls → ToolNode (executes DB tools) → back to agent_node
    └── no tool_calls  → END (done)
```

**Metrics Collected:** `StageTimer` records wall-clock time, tool-call count, success/error status.

---

### Step 4 — Resume Selection Agent

**What happens:** Screens every candidate's resume against the job requirements, assigns a 0–100 score, and automatically shortlists candidates above the threshold (default: 60).

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `langchain_openai.ChatOpenAI`, `langgraph.prebuilt.ToolNode`, LangGraph sub-graph |
| **Files** | `agents/resume_selection_agent.py`, `tools/resume_tools.py` |
| **LLM Model** | GPT-4o-mini (temperature=0.1) |
| **Tools Used** | `get_job_requirements`, `get_candidates_for_job`, `add_candidate`, `create_application`, `score_resume`, `get_shortlisted_candidates` |
| **Input Data** | Job posting ID, candidate resumes from DB |
| **Output Data** | `applications` table rows with screening scores; candidates with score ≥ 60 marked as `is_shortlisted=True`; candidate status → `"shortlisted"` |
| **DB Tables** | `candidates`, `applications` |

**Scoring Criteria (LLM-guided):**
| Weight | Category |
|--------|----------|
| 40% | Skills match |
| 30% | Experience relevance |
| 15% | Education fit |
| 15% | Overall presentation |

---

### Step 5 — Interview Scheduling Agent

**What happens:** Schedules interviews for all shortlisted candidates with appropriate interviewers, types, and time slots.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `langchain_openai.ChatOpenAI`, `langgraph.prebuilt.ToolNode`, LangGraph sub-graph |
| **Files** | `agents/interview_scheduling_agent.py`, `tools/scheduling_tools.py` |
| **LLM Model** | GPT-4o-mini (temperature=0.1) |
| **Tools Used** | `get_available_slots`, `schedule_interview`, `list_interviews`, `update_interview_status` |
| **Input Data** | Shortlisted candidate IDs from the previous stage |
| **Output Data** | `interviews` table rows with scheduled times, interviewer assignments, meeting links |
| **DB Table** | `interviews` (id, candidate_id, interviewer_name, interviewer_email, interview_type, scheduled_time, duration_minutes, meeting_link, status, notes, created_at) |

**Interview Types:**
| Type | Focus |
|------|-------|
| `technical` | Technical skills assessment |
| `behavioral` | Soft skills and behavioral evaluation |
| `culture_fit` | Team and culture fit (optional, top candidates) |

**Scheduling Rules:**
- Minimum 2 interviews per candidate (technical + behavioral)
- Different interviewers for different types
- Slots spaced ≥ 30 minutes apart
- Available slots: 09:00–16:30 (excluding already-booked slots)
- Auto-generates meeting links: `https://meet.example.com/hr-interview-{candidate_id}-{type}`

---

### Step 6 — Feedback Collection Agent

**What happens:** Generates realistic, structured interviewer feedback for all scheduled interviews (simulated in demo mode).

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `langchain_openai.ChatOpenAI`, `langgraph.prebuilt.ToolNode`, LangGraph sub-graph |
| **Files** | `agents/feedback_agent.py`, `tools/feedback_tools.py` |
| **LLM Model** | GPT-4o-mini (**temperature=0.3** — slightly higher for varied feedback) |
| **Tools Used** | `get_pending_feedback`, `submit_feedback`, `get_feedback_for_candidate`, `get_all_feedback_summary` |
| **Input Data** | Scheduled interview records from DB |
| **Output Data** | `feedback` table rows with multi-dimensional ratings; interview status → `"completed"` |
| **DB Table** | `feedback` (id, interview_id, interviewer_name, technical_rating, communication_rating, culture_fit_rating, overall_rating, strengths, weaknesses, recommendation, detailed_notes, submitted_at) |

**Rating Dimensions:**
| Rating | Scale | Focus |
|--------|-------|-------|
| `technical_rating` | 1–10 | Technical competency |
| `communication_rating` | 1–10 | Communication skills |
| `culture_fit_rating` | 1–10 | Cultural alignment |
| `overall_rating` | 1.0–10.0 | Overall impression |

**Recommendation Levels:** `strong_hire`, `hire`, `maybe`, `no_hire`

---

### Step 7 — Candidate Ranking Agent

**What happens:** Calculates composite scores from resume screening + interview performance and produces a ranked list of all candidates.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `langchain_openai.ChatOpenAI`, `langgraph.prebuilt.ToolNode`, LangGraph sub-graph |
| **Files** | `agents/ranking_agent.py`, `tools/ranking_tools.py` |
| **LLM Model** | GPT-4o-mini (temperature=0.1) |
| **Tools Used** | `calculate_composite_score`, `save_ranking`, `get_rankings` |
| **Input Data** | Application screening scores, interview feedback ratings |
| **Output Data** | `rankings` table rows with composite scores, rank positions, LLM-generated analysis |
| **DB Table** | `rankings` (id, application_id, resume_score, interview_score, overall_score, rank, score_breakdown (JSON), analysis, created_at) |

**Composite Scoring Formula:**
```
resume_score_normalized = screening_score / 10.0      (0–10 scale)
interview_score = avg(all_feedback.overall_rating)     (0–10 scale)

composite = (resume_score × 0.30) + (interview_score × 0.70)
```

| Weight | Source |
|--------|--------|
| **30%** | Resume/screening score |
| **70%** | Interview performance (average across all feedback) |

---

### Step 8 — Final Selection Agent

**What happens:** Reviews the complete candidate journey (resume → screening → interviews → rankings) and makes final hire/reject/waitlist decisions with justifications.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | `langchain_openai.ChatOpenAI`, `langgraph.prebuilt.ToolNode`, LangGraph sub-graph |
| **Files** | `agents/final_selection_agent.py`, `tools/selection_tools.py` |
| **LLM Model** | GPT-4o-mini (temperature=0.1) |
| **Tools Used** | `generate_offer_summary`, `make_decision`, `get_all_decisions`, `get_pipeline_summary` |
| **Input Data** | Candidate profiles, screening scores, interview feedback, rankings |
| **Output Data** | `offers` table rows with decisions + justifications; candidate status → `"selected"` or `"rejected"` |
| **DB Table** | `offers` (id, candidate_id, job_posting_id, decision, salary_offered, start_date, justification, offer_letter_summary, created_at) |

**Decision Criteria:**
| Decision | When Applied |
|----------|-------------|
| `offer` | Top-ranked candidates with `strong_hire` / `hire` recommendations |
| `waitlist` | Borderline candidates with mixed feedback |
| `reject` | Low-ranked candidates or those with `no_hire` recommendations |

---

### Step 9 — Pipeline Completion

**What happens:** The Supervisor receives `current_stage = "final_selection_complete"`, routes to `"complete"` which maps to `END` in the LangGraph, terminating execution.

| Aspect | Detail |
|--------|--------|
| **Tech Stack** | LangGraph `StateGraph`, `END` sentinel |
| **Files** | `graph/pipeline.py` (line 60: `"complete": END`) |
| **Data** | Final `HRState` with all accumulated messages, metrics, and results |
| **Output** | Pipeline status → `"completed"`; stage metrics logged |

---

## 4. Agent Sub-Graph Architecture

Every worker agent follows the same **ReAct (Reason + Act)** pattern, implemented as a LangGraph sub-graph:

```
┌─────────────────────────────────────────────────┐
│              Agent Sub-Graph                     │
│                                                  │
│  ┌──────────┐     tool_calls?     ┌──────────┐  │
│  │          │ ─── YES ──────────► │          │  │
│  │  agent   │                     │  tools   │  │
│  │  (LLM)   │ ◄────────────────── │ (ToolNode│  │
│  │          │                     │          │  │
│  └────┬─────┘                     └──────────┘  │
│       │ NO tool_calls                            │
│       ▼                                          │
│      END                                         │
│                                                  │
│  Recursion Limit: 25 (configurable)              │
└─────────────────────────────────────────────────┘
```

**Pattern for every agent:**

```python
# 1. Build LLM with tools bound
llm_with_tools = ChatOpenAI(...).bind_tools(AGENT_TOOLS)

# 2. agent_node: prepend system prompt, invoke LLM
def agent_node(state):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 3. should_continue: check if LLM wants to call tools
def should_continue(state):
    if state["messages"][-1].tool_calls:
        return "tools"
    return "done"

# 4. Assemble sub-graph
workflow = StateGraph(HRState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(AGENT_TOOLS))
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "done": END})
workflow.add_edge("tools", "agent")
compiled = workflow.compile(recursion_limit=25)
```

**Wrapper node** (used in the main pipeline):
```python
def agent_wrapper_node(state):
    with StageTimer("stage_name") as timer:
        result = compiled_sub_graph.invoke(state)
        timer.count_tool_calls(result["messages"])
        timer.mark_success()
    return {
        "messages": result["messages"],
        "current_stage": "stage_name_complete",
        "stage_metrics": [..., timer.to_dict()],
    }
```

---

## 5. Database Schema (ERD)

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   job_postings    │       │    candidates     │       │   applications   │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ id          (PK) │◄──┐   │ id          (PK) │◄──┐   │ id          (PK) │
│ title             │   │   │ name              │   │   │ candidate_id (FK)│──►
│ department        │   │   │ email    (UNIQUE) │   │   │ job_posting_id(FK│──►
│ description       │   │   │ phone             │   │   │ screening_score  │
│ requirements      │   │   │ resume_text       │   │   │ screening_notes  │
│ preferred_quals   │   │   │ skills            │   │   │ is_shortlisted   │
│ salary_range      │   │   │ experience_years  │   │   │ applied_at       │
│ location          │   └───│ education         │   │   └──────────────────┘
│ employment_type   │       │ status            │   │           │
│ status            │       │ created_at        │   │           │
│ created_at        │       └──────────────────┘   │           │
│ updated_at        │                │              │           │
└──────────────────┘                │              │           ▼
        │                           │              │   ┌──────────────────┐
        │                           ▼              │   │    rankings       │
        │                  ┌──────────────────┐    │   ├──────────────────┤
        │                  │   interviews      │    │   │ id          (PK) │
        │                  ├──────────────────┤    │   │ application_id(FK│
        │                  │ id          (PK) │    │   │ resume_score     │
        │                  │ candidate_id (FK)│────┘   │ interview_score  │
        │                  │ interviewer_name  │        │ overall_score    │
        │                  │ interviewer_email │        │ rank             │
        │                  │ interview_type    │        │ score_breakdown  │
        │                  │ scheduled_time    │        │ analysis         │
        │                  │ duration_minutes  │        │ created_at       │
        │                  │ meeting_link      │        └──────────────────┘
        │                  │ status            │
        │                  │ notes             │
        │                  │ created_at        │
        │                  └────────┬─────────┘
        │                           │
        │                           ▼
        │                  ┌──────────────────┐
        │                  │    feedback       │
        │                  ├──────────────────┤
        │                  │ id          (PK) │
        │                  │ interview_id (FK)│ (UNIQUE — 1:1 with interviews)
        │                  │ interviewer_name  │
        │                  │ technical_rating  │
        │                  │ communication_rtg │
        │                  │ culture_fit_rtg   │
        │                  │ overall_rating    │
        │                  │ strengths         │
        │                  │ weaknesses        │
        │                  │ recommendation    │
        │                  │ detailed_notes    │
        │                  │ submitted_at      │
        │                  └──────────────────┘
        │
        ▼
┌──────────────────┐
│     offers        │
├──────────────────┤
│ id          (PK) │
│ candidate_id (FK)│
│ job_posting_id(FK│
│ decision          │
│ salary_offered    │
│ start_date        │
│ justification     │
│ offer_letter_sum  │
│ created_at        │
└──────────────────┘
```

**Table Count:** 7  
**ORM:** SQLAlchemy 2.0+ with `declarative_base()`  
**Database:** SQLite (file: `hr_system.db`) — swappable to PostgreSQL/MySQL via `DATABASE_URL`

---

## 6. API Layer

### Tech Stack
| Component | Technology |
|-----------|-----------|
| Framework | **FastAPI** 0.115+ |
| Server | **Uvicorn** (ASGI, hot-reload in dev) |
| Validation | **Pydantic** v2 BaseModel |
| CORS | `CORSMiddleware` (allow all origins in dev) |
| Background Execution | `FastAPI.BackgroundTasks` + `threading.Lock` for run tracking |
| Pipeline Run Storage | **In-memory** dict `_pipeline_runs` (keyed by `run_id`) |

### Endpoints

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| `GET` | `/health` | Health check | `{"status": "healthy"}` |
| `POST` | `/pipeline/start` | Start async pipeline | `PipelineRunResponse` (run_id) |
| `GET` | `/pipeline/status/{run_id}` | Poll run status | `PipelineStatusResponse` |
| `GET` | `/pipeline/metrics/{run_id}` | Per-stage metrics | stage_metrics array |
| `GET` | `/pipeline/runs` | List all runs | Array of {run_id, status, started_at} |
| `GET` | `/pipeline/summary/{job_id}` | DB-based job summary | Counts at each funnel stage |
| `GET` | `/jobs` | List jobs | Array of JobPosting dicts |
| `GET` | `/jobs/{job_id}` | Get specific job | JobPosting dict |
| `GET` | `/candidates` | List candidates | Array of Candidate dicts |
| `POST` | `/candidates` | Add candidate | Created Candidate dict |
| `GET` | `/interviews` | List interviews | Array of Interview dicts |
| `GET` | `/feedback` | List feedback | Array of Feedback dicts |
| `POST` | `/feedback` | Submit feedback | Created Feedback dict |
| `GET` | `/rankings` | List rankings | Sorted Ranking array |
| `GET` | `/decisions` | List decisions | Array of Offer dicts |

### Request/Response Schemas (Pydantic)

```python
# Request
PipelineStartRequest:  job_title, department, requirements, candidates[]
CandidateInput:        name, email, resume_text, phone, skills, experience_years, education
FeedbackInput:         interview_id, interviewer_name, overall_rating, recommendation, ...

# Response
PipelineRunResponse:   run_id, status, message
PipelineStatusResponse: run_id, status, current_stage, started_at, completed_at, error, total_messages, stage_metrics
```

---

## 7. Dashboard (UI Layer)

### Tech Stack
| Component | Technology |
|-----------|-----------|
| Framework | **Streamlit** 1.45+ |
| Data manipulation | **Pandas** |
| Charts | Streamlit built-in `st.bar_chart()` |
| Layout | `st.columns()`, `st.expander()`, `st.tabs()` |
| Styling | Custom CSS injected via `st.markdown(unsafe_allow_html=True)` |
| Export | CSV download via `st.download_button()` |

### Pages

| Page | Features |
|------|----------|
| 📊 **Dashboard** | KPI metrics (jobs, candidates, interviews, offers, rejections), pipeline stage progress bar, recent activity feed |
| 📋 **Job Postings** | Expandable cards with description, requirements, salary, status |
| 👥 **Candidates** | Summary table + CSV export, detailed per-candidate view |
| 📅 **Interviews** | Table with candidate, interviewer, type, time, status + CSV export |
| 💬 **Feedback** | Per-feedback expandable cards with ratings, strengths, weaknesses |
| 🏆 **Rankings** | Ranked table with medal icons, detailed analysis per candidate |
| ✅ **Decisions** | Summary metrics (offers/rejections/waitlist), per-decision detail, CSV export |
| 📈 **Compare Candidates** | Side-by-side bar chart + top-3 detail cards |
| 🚀 **Run Pipeline** | Form to start a new pipeline with custom job + candidates |

---

## 8. Observability & Metrics

### StageTimer (config/metrics.py)

```python
@dataclass
class StageTimer:
    stage_name: str
    start_time: float       # set on __enter__
    end_time: float         # set on __exit__
    elapsed_seconds: float  # end - start
    status: str             # "running" | "success" | "error"
    error_detail: str       # error message if failed
    tool_call_count: int    # counted from AI messages

    # Context manager: times the agent execution
    # Output: dict with stage, elapsed_seconds, status, error, tool_calls
```

### Metrics Flow

```
Agent wrapper node
    │
    ├── with StageTimer("stage_name") as timer:
    │       result = agent.invoke(state)
    │       timer.count_tool_calls(result["messages"])
    │       timer.mark_success()
    │
    └── state["stage_metrics"].append(timer.to_dict())
```

### Available Metrics per Stage
| Metric | Type | Description |
|--------|------|-------------|
| `stage` | string | Stage name (e.g., "job_posting") |
| `elapsed_seconds` | float | Wall-clock execution time |
| `status` | string | "success" or "error" |
| `error` | string | Error message (if failed) |
| `tool_calls` | int | Number of LangChain tool invocations |

---

## 9. Resilience & Error Handling

### Retry Mechanism

```
┌──────────────────────────────────────────────────────┐
│                  SUPERVISOR NODE                      │
│                                                      │
│  if error_message:                                   │
│    if retry_count < max_retries:                     │
│      → Re-route to SAME agent                        │
│      → retry_count += 1                              │
│      → error_message = None (clean slate)            │
│    else:                                             │
│      → Add to failed_stages[]                        │
│      → Advance to NEXT stage                         │
│      → retry_count = 0                               │
│  else:                                               │
│    → Normal LLM routing                              │
│    → retry_count = 0                                 │
└──────────────────────────────────────────────────────┘
```

### Guardrails

| Guardrail | Default | Purpose |
|-----------|---------|---------|
| `AGENT_RECURSION_LIMIT` | 25 | Max LLM ↔ tool loops per agent sub-graph |
| `AGENT_TIMEOUT_SECONDS` | 120 | Max wall-clock time per agent |
| `AGENT_MAX_RETRIES` | 2 | Retries before skipping a failed stage |

### Error Propagation

```
Agent tool raises exception
  → agent sub-graph catches in wrapper node
  → sets error_message in HRState
  → Supervisor detects error_message on next invocation
  → Retry or skip based on retry_count vs max_retries
```

---

## 10. Complete Tech Stack Summary

### Core Framework

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Agent Orchestration | **LangGraph** | ≥0.4.0 | StateGraph, conditional routing, sub-graphs |
| LLM Framework | **LangChain** | ≥0.3.0 | Tool abstraction, message types, ToolNode |
| LLM Provider | **langchain-openai** | ≥0.3.0 | OpenAI GPT integration |
| LLM Core | **langchain-core** | ≥0.3.0 | BaseMessage, SystemMessage, HumanMessage |

### API & Web

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| REST API | **FastAPI** | ≥0.115.0 | Async REST endpoints, background tasks |
| ASGI Server | **Uvicorn** | ≥0.34.0 | High-performance Python web server |
| Dashboard | **Streamlit** | ≥1.45.0 | Interactive data dashboard |
| HTTP Client | **httpx** | ≥0.27.0 | Async HTTP requests |

### Data & Validation

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| ORM | **SQLAlchemy** | ≥2.0.0 | Database abstraction, models, sessions |
| Database | **SQLite** | Built-in | File-based relational storage |
| Validation | **Pydantic** | ≥2.0.0 | Request/response schemas, structured LLM output |
| Data Analysis | **Pandas** | Latest | DataFrame operations, CSV export |
| Numerical | **NumPy** | Latest | Numerical computations |

### Configuration & Utilities

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Environment | **python-dotenv** | ≥1.0.0 | `.env` file loading |
| Logging | Python `logging` | stdlib | Structured console logging |
| CLI | Python `argparse` | stdlib | Command-line interface |

### External Services

| Service | Usage | Model |
|---------|-------|-------|
| **OpenAI API** | All LLM inference (agents + supervisor) | `gpt-4o-mini` (configurable) |

---

## 11. Project Directory Structure

```
hr-multi-agent-system/
│
├── main.py                          # CLI entry point (run, api, ui, init, reset)
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variable template
├── .gitignore                       # Git ignore rules
├── README.md                        # Project README
├── architecture.md                  # This file
├── hr_system.db                     # SQLite database (auto-generated)
│
├── config/                          # ⚙️ Configuration Layer
│   ├── __init__.py
│   ├── settings.py                  # Environment-based Settings class (singleton)
│   ├── logging_config.py            # Centralized logging setup
│   └── metrics.py                   # StageTimer context manager
│
├── state/                           # 📦 Shared State
│   ├── __init__.py
│   └── hr_state.py                  # HRState TypedDict + stage constants
│
├── graph/                           # 🔀 Pipeline Orchestration
│   ├── __init__.py
│   ├── pipeline.py                  # StateGraph assembly (7 nodes + edges)
│   └── supervisor.py                # Supervisor routing + retry logic
│
├── agents/                          # 🤖 AI Agents (LangGraph sub-graphs)
│   ├── __init__.py
│   ├── job_posting_agent.py         # Stage 1: Job posting creation
│   ├── resume_selection_agent.py    # Stage 2: Resume screening
│   ├── interview_scheduling_agent.py # Stage 3: Interview scheduling
│   ├── feedback_agent.py            # Stage 4: Feedback collection
│   ├── ranking_agent.py             # Stage 5: Candidate ranking
│   └── final_selection_agent.py     # Stage 6: Final decisions
│
├── tools/                           # 🔧 LangChain Tools (DB operations)
│   ├── __init__.py
│   ├── job_tools.py                 # CRUD for job_postings
│   ├── resume_tools.py              # Candidate + application management
│   ├── scheduling_tools.py          # Interview scheduling + calendar
│   ├── feedback_tools.py            # Feedback submission + queries
│   ├── ranking_tools.py             # Score calculation + ranking
│   └── selection_tools.py           # Offer/reject decisions + summaries
│
├── database/                        # 💾 Data Layer
│   ├── __init__.py
│   ├── db.py                        # SQLAlchemy engine, session management
│   └── models.py                    # 7 ORM models (Base declarative)
│
├── api/                             # 🌐 REST API
│   ├── __init__.py
│   ├── server.py                    # FastAPI app + all endpoints
│   └── schemas.py                   # Pydantic request/response models
│
└── ui/                              # 🖥️ Dashboard
    └── dashboard.py                 # Streamlit app (9 pages, 635 lines)
```

---

## 12. Deployment Guide — GCP (Google Cloud Platform)

### Architecture on GCP

```
                    ┌─────────────────┐
                    │  Cloud Load     │
                    │  Balancer       │
                    └────┬────────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │ Cloud Run│ │ Cloud Run│ │ Cloud Run│
     │ (FastAPI)│ │(Streamlit│ │ (Worker) │
     └────┬─────┘ └──────────┘ └────┬─────┘
          │                         │
          └────────┬────────────────┘
                   ▼
          ┌──────────────────┐
          │  Cloud SQL       │
          │  (PostgreSQL)    │
          └──────────────────┘
                   │
          ┌──────────────────┐
          │  Secret Manager  │
          │  (API keys)      │
          └──────────────────┘
```

### Step-by-Step Deployment

#### 1. Prerequisites
```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com
```

#### 2. Create Cloud SQL (PostgreSQL) Instance
```bash
# Create a PostgreSQL instance
gcloud sql instances create hr-system-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YOUR_DB_PASSWORD

# Create the database
gcloud sql databases create hr_system --instance=hr-system-db

# Create a user
gcloud sql users create hr_user \
    --instance=hr-system-db \
    --password=YOUR_USER_PASSWORD
```

#### 3. Store Secrets
```bash
# Store OpenAI API key
echo -n "sk-your-openai-key" | gcloud secrets create OPENAI_API_KEY \
    --data-file=-

# Store database URL
echo -n "postgresql://hr_user:YOUR_USER_PASSWORD@/hr_system?host=/cloudsql/YOUR_PROJECT:us-central1:hr-system-db" \
    | gcloud secrets create DATABASE_URL --data-file=-
```

#### 4. Create Dockerfile
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary gunicorn

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Default to FastAPI server
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### 5. Create Artifact Registry & Push Image
```bash
# Create Docker repository
gcloud artifacts repositories create hr-system \
    --repository-format=docker \
    --location=us-central1

# Build and push
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-api:latest .
```

#### 6. Deploy FastAPI to Cloud Run
```bash
gcloud run deploy hr-api \
    --image=us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-api:latest \
    --platform=managed \
    --region=us-central1 \
    --allow-unauthenticated \
    --port=8080 \
    --memory=1Gi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=5 \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest" \
    --add-cloudsql-instances=YOUR_PROJECT:us-central1:hr-system-db \
    --set-env-vars="LLM_MODEL=gpt-4o-mini,LLM_TEMPERATURE=0.1,AGENT_MAX_RETRIES=2"
```

#### 7. Deploy Streamlit Dashboard to Cloud Run
```dockerfile
# Dockerfile.streamlit
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "ui/dashboard.py", "--server.port=8501", "--server.headless=true", "--server.address=0.0.0.0"]
```

```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-dashboard:latest -f Dockerfile.streamlit .

gcloud run deploy hr-dashboard \
    --image=us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-dashboard:latest \
    --platform=managed \
    --region=us-central1 \
    --allow-unauthenticated \
    --port=8501 \
    --memory=512Mi \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest" \
    --add-cloudsql-instances=YOUR_PROJECT:us-central1:hr-system-db
```

#### 8. Set Up Custom Domain (Optional)
```bash
gcloud run domain-mappings create \
    --service=hr-api \
    --domain=api.yourdomain.com \
    --region=us-central1
```

#### GCP Cost Estimate (Monthly)

| Service | Spec | Est. Cost |
|---------|------|-----------|
| Cloud Run (API) | 1 vCPU, 1GB RAM, ~100 hrs | ~$5–15 |
| Cloud Run (Dashboard) | 1 vCPU, 512MB RAM | ~$3–8 |
| Cloud SQL (PostgreSQL) | db-f1-micro | ~$9 |
| Secret Manager | 3 secrets | ~$0.06 |
| Artifact Registry | <1GB | ~$0.10 |
| **Total** | | **~$17–33/mo** |

---

## 13. Deployment Guide — AWS (Amazon Web Services)

### Architecture on AWS

```
                    ┌─────────────────┐
                    │  Application    │
                    │  Load Balancer  │
                    └────┬────────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  ECS     │ │  ECS     │ │  ECS     │
     │  Fargate │ │  Fargate │ │  Fargate │
     │ (FastAPI)│ │(Streamlit│ │ (Worker) │
     └────┬─────┘ └──────────┘ └────┬─────┘
          │                         │
          └────────┬────────────────┘
                   ▼
          ┌──────────────────┐
          │   RDS            │
          │  (PostgreSQL)    │
          └──────────────────┘
                   │
          ┌──────────────────┐
          │ Secrets Manager  │
          │  (API keys)      │
          └──────────────────┘
```

### Step-by-Step Deployment

#### 1. Prerequisites
```bash
# Install AWS CLI v2
# https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

aws configure
# Set your AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, region
```

#### 2. Create VPC & Networking
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=hr-system-vpc}]'

# Create subnets (at least 2 AZs for RDS)
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create security group
aws ec2 create-security-group --group-name hr-system-sg --description "HR System" --vpc-id vpc-xxx
aws ec2 authorize-security-group-ingress --group-id sg-xxx --protocol tcp --port 5432 --cidr 10.0.0.0/16
aws ec2 authorize-security-group-ingress --group-id sg-xxx --protocol tcp --port 8080 --cidr 0.0.0.0/0
```

#### 3. Create RDS PostgreSQL
```bash
# Create subnet group
aws rds create-db-subnet-group \
    --db-subnet-group-name hr-system-subnets \
    --db-subnet-group-description "HR System subnets" \
    --subnet-ids subnet-xxx1 subnet-xxx2

# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier hr-system-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username hr_admin \
    --master-user-password YOUR_DB_PASSWORD \
    --allocated-storage 20 \
    --db-name hr_system \
    --vpc-security-group-ids sg-xxx \
    --db-subnet-group-name hr-system-subnets \
    --no-publicly-accessible
```

#### 4. Store Secrets in AWS Secrets Manager
```bash
aws secretsmanager create-secret \
    --name hr-system/openai-api-key \
    --secret-string "sk-your-openai-key"

aws secretsmanager create-secret \
    --name hr-system/database-url \
    --secret-string "postgresql://hr_admin:YOUR_DB_PASSWORD@hr-system-db.xxx.us-east-1.rds.amazonaws.com:5432/hr_system"
```

#### 5. Create ECR Repository & Push Image
```bash
# Create ECR repository
aws ecr create-repository --repository-name hr-system-api

# Authenticate Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t hr-system-api .
docker tag hr-system-api:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-api:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-api:latest
```

#### 6. Create ECS Cluster & Service (Fargate)

**Task Definition (`task-definition.json`):**
```json
{
  "family": "hr-system-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "hr-api",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-api:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "LLM_MODEL", "value": "gpt-4o-mini"},
        {"name": "LLM_TEMPERATURE", "value": "0.1"},
        {"name": "AGENT_MAX_RETRIES", "value": "2"}
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:hr-system/openai-api-key"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:hr-system/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/hr-system-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create cluster
aws ecs create-cluster --cluster-name hr-system-cluster

# Create service
aws ecs create-service \
    --cluster hr-system-cluster \
    --service-name hr-api-service \
    --task-definition hr-system-api:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx1,subnet-xxx2],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### 7. Create Application Load Balancer
```bash
# Create ALB
aws elbv2 create-load-balancer \
    --name hr-system-alb \
    --subnets subnet-xxx1 subnet-xxx2 \
    --security-groups sg-xxx

# Create target group
aws elbv2 create-target-group \
    --name hr-api-tg \
    --protocol HTTP \
    --port 8080 \
    --vpc-id vpc-xxx \
    --target-type ip \
    --health-check-path /health

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn arn:aws:elasticloadbalancing:... \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

#### 8. Deploy Streamlit (Separate ECS Service)
```bash
# Create separate ECR repo
aws ecr create-repository --repository-name hr-system-dashboard

# Build and push Streamlit image
docker build -t hr-system-dashboard -f Dockerfile.streamlit .
docker tag hr-system-dashboard:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-dashboard:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-dashboard:latest

# Register task definition + create service (similar to API, port 8501)
```

#### AWS Cost Estimate (Monthly)

| Service | Spec | Est. Cost |
|---------|------|-----------|
| ECS Fargate (API) | 0.5 vCPU, 1GB RAM, 2 tasks | ~$15–25 |
| ECS Fargate (Dashboard) | 0.25 vCPU, 512MB RAM | ~$8–12 |
| RDS PostgreSQL | db.t3.micro, 20GB | ~$15 |
| ALB | Standard | ~$16 |
| ECR | <1GB storage | ~$0.10 |
| Secrets Manager | 2 secrets | ~$0.80 |
| CloudWatch Logs | Basic | ~$1–3 |
| **Total** | | **~$56–73/mo** |

---

## 14. Deployment Guide — Azure

### Architecture on Azure

```
                    ┌─────────────────┐
                    │  Azure Front    │
                    │  Door / App GW  │
                    └────┬────────────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐
     │  Azure   │ │  Azure   │ │  Azure   │
     │ Container│ │ Container│ │ Container│
     │  Apps    │ │  Apps    │ │  Apps    │
     │ (FastAPI)│ │(Streamlit│ │ (Worker) │
     └────┬─────┘ └──────────┘ └────┬─────┘
          │                         │
          └────────┬────────────────┘
                   ▼
          ┌──────────────────┐
          │  Azure Database  │
          │  for PostgreSQL  │
          └──────────────────┘
                   │
          ┌──────────────────┐
          │  Azure Key Vault │
          │  (secrets)       │
          └──────────────────┘
```

### Step-by-Step Deployment

#### 1. Prerequisites
```bash
# Install Azure CLI
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli

az login
az account set --subscription YOUR_SUBSCRIPTION_ID
```

#### 2. Create Resource Group
```bash
az group create \
    --name hr-system-rg \
    --location eastus
```

#### 3. Create Azure Database for PostgreSQL (Flexible Server)
```bash
az postgres flexible-server create \
    --resource-group hr-system-rg \
    --name hr-system-db \
    --location eastus \
    --admin-user hr_admin \
    --admin-password YOUR_DB_PASSWORD \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --storage-size 32 \
    --version 15 \
    --yes

# Create database
az postgres flexible-server db create \
    --resource-group hr-system-rg \
    --server-name hr-system-db \
    --database-name hr_system

# Allow Azure services to connect
az postgres flexible-server firewall-rule create \
    --resource-group hr-system-rg \
    --name hr-system-db \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 \
    --end-ip-address 0.0.0.0
```

#### 4. Create Azure Key Vault
```bash
az keyvault create \
    --resource-group hr-system-rg \
    --name hr-system-kv \
    --location eastus

az keyvault secret set \
    --vault-name hr-system-kv \
    --name openai-api-key \
    --value "sk-your-openai-key"

az keyvault secret set \
    --vault-name hr-system-kv \
    --name database-url \
    --value "postgresql://hr_admin:YOUR_DB_PASSWORD@hr-system-db.postgres.database.azure.com:5432/hr_system?sslmode=require"
```

#### 5. Create Azure Container Registry (ACR)
```bash
az acr create \
    --resource-group hr-system-rg \
    --name hrsystemacr \
    --sku Basic

# Login to ACR
az acr login --name hrsystemacr

# Build and push
az acr build \
    --registry hrsystemacr \
    --image hr-api:latest \
    --file Dockerfile .

az acr build \
    --registry hrsystemacr \
    --image hr-dashboard:latest \
    --file Dockerfile.streamlit .
```

#### 6. Create Azure Container Apps Environment
```bash
# Install Container Apps extension
az extension add --name containerapp --upgrade

# Create environment
az containerapp env create \
    --resource-group hr-system-rg \
    --name hr-system-env \
    --location eastus
```

#### 7. Deploy FastAPI to Azure Container Apps
```bash
az containerapp create \
    --resource-group hr-system-rg \
    --name hr-api \
    --environment hr-system-env \
    --image hrsystemacr.azurecr.io/hr-api:latest \
    --registry-server hrsystemacr.azurecr.io \
    --target-port 8080 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 5 \
    --cpu 0.5 \
    --memory 1.0Gi \
    --env-vars \
        "LLM_MODEL=gpt-4o-mini" \
        "LLM_TEMPERATURE=0.1" \
        "AGENT_MAX_RETRIES=2" \
    --secrets \
        "openai-key=keyvaultref:https://hr-system-kv.vault.azure.net/secrets/openai-api-key,identityref:/subscriptions/xxx/resourcegroups/hr-system-rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/hr-system-identity" \
        "db-url=keyvaultref:https://hr-system-kv.vault.azure.net/secrets/database-url,identityref:/subscriptions/xxx/resourcegroups/hr-system-rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/hr-system-identity" \
    --secret-env-vars \
        "OPENAI_API_KEY=openai-key" \
        "DATABASE_URL=db-url"
```

#### 8. Deploy Streamlit Dashboard
```bash
az containerapp create \
    --resource-group hr-system-rg \
    --name hr-dashboard \
    --environment hr-system-env \
    --image hrsystemacr.azurecr.io/hr-dashboard:latest \
    --registry-server hrsystemacr.azurecr.io \
    --target-port 8501 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 3 \
    --cpu 0.25 \
    --memory 0.5Gi \
    --env-vars \
        "LLM_MODEL=gpt-4o-mini" \
    --secrets \
        "openai-key=keyvaultref:https://hr-system-kv.vault.azure.net/secrets/openai-api-key,identityref:..." \
        "db-url=keyvaultref:https://hr-system-kv.vault.azure.net/secrets/database-url,identityref:..." \
    --secret-env-vars \
        "OPENAI_API_KEY=openai-key" \
        "DATABASE_URL=db-url"
```

#### 9. Configure Custom Domain (Optional)
```bash
az containerapp hostname add \
    --resource-group hr-system-rg \
    --name hr-api \
    --hostname api.yourdomain.com

az containerapp hostname bind \
    --resource-group hr-system-rg \
    --name hr-api \
    --hostname api.yourdomain.com \
    --environment hr-system-env \
    --validation-method CNAME
```

#### 10. Set Up Monitoring with Azure Monitor
```bash
# Enable Application Insights
az monitor app-insights component create \
    --app hr-system-insights \
    --location eastus \
    --resource-group hr-system-rg

# View logs
az containerapp logs show \
    --resource-group hr-system-rg \
    --name hr-api \
    --follow
```

#### Azure Cost Estimate (Monthly)

| Service | Spec | Est. Cost |
|---------|------|-----------|
| Container Apps (API) | 0.5 vCPU, 1GB RAM | ~$10–20 |
| Container Apps (Dashboard) | 0.25 vCPU, 512MB RAM | ~$5–10 |
| Azure Database for PostgreSQL | Burstable B1ms, 32GB | ~$13 |
| Azure Key Vault | 3 secrets | ~$0.03 |
| Container Registry | Basic tier | ~$5 |
| Application Insights | Basic | ~$2–5 |
| **Total** | | **~$35–53/mo** |

---

## Deployment Comparison Summary

| Feature | GCP (Cloud Run) | AWS (ECS Fargate) | Azure (Container Apps) |
|---------|----------------|-------------------|----------------------|
| **Compute** | Cloud Run | ECS Fargate | Container Apps |
| **Database** | Cloud SQL (PostgreSQL) | RDS (PostgreSQL) | Azure Database for PostgreSQL |
| **Secrets** | Secret Manager | Secrets Manager | Key Vault |
| **Registry** | Artifact Registry | ECR | ACR |
| **Load Balancer** | Built-in (Cloud Run) | ALB (separate) | Built-in (Container Apps) |
| **Scale to Zero** | ✅ Native | ❌ (min 1 task) | ✅ Native |
| **Est. Monthly Cost** | **$17–33** | **$56–73** | **$35–53** |
| **Setup Complexity** | ⭐ Low | ⭐⭐⭐ High | ⭐⭐ Medium |
| **Best For** | Cost-conscious, simple deployments | Enterprise, complex networking | Microsoft ecosystem, balanced |

---

## Production Checklist

Before deploying to production, ensure:

- [ ] Replace SQLite with PostgreSQL (update `DATABASE_URL`)
- [ ] Set `OPENAI_API_KEY` securely (never in code or `.env` in prod)
- [ ] Restrict CORS origins (replace `allow_origins=["*"]`)
- [ ] Add authentication to FastAPI endpoints (OAuth2 / API keys)
- [ ] Add HTTPS (TLS termination at load balancer)
- [ ] Persist pipeline runs to DB (currently in-memory)
- [ ] Set up log aggregation (Cloud Logging / CloudWatch / Azure Monitor)
- [ ] Configure alerting for pipeline failures
- [ ] Set up CI/CD pipeline (GitHub Actions / Cloud Build / CodePipeline)
- [ ] Run `pip install --upgrade` to pin dependency versions in `requirements.txt`
- [ ] Add health check endpoints for container orchestrators
- [ ] Set proper resource limits (CPU/memory) based on load testing
- [ ] Enable auto-scaling based on request volume

---

*Generated from source code analysis of the HR Multi-Agent Recruitment System v2.0*
