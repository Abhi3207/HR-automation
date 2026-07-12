# 🏢 HR Multi-Agent Recruitment System — Architecture Document

> **Version:** 3.0
> **Last Updated:** 2026-07-12
> **Source of Truth:** Generated from exhaustive source-code analysis

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Layers](#2-architecture-layers)
3. [Data-Flow & Sequence Diagrams](#3-data-flow--sequence-diagrams)
4. [Pipeline Walkthrough (Step-by-Step)](#4-pipeline-walkthrough-step-by-step)
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
5. [Agent Sub-Graph Architecture](#5-agent-sub-graph-architecture)
6. [Tool Inventory & Mapping](#6-tool-inventory--mapping)
7. [Database Schema (ERD)](#7-database-schema-erd)
8. [API Layer](#8-api-layer)
9. [Dashboard (UI Layer)](#9-dashboard-ui-layer)
10. [Observability & Metrics](#10-observability--metrics)
11. [Resilience & Error Handling](#11-resilience--error-handling)
12. [Complete Tech Stack Summary](#12-complete-tech-stack-summary)
13. [Project Directory Structure](#13-project-directory-structure)
14. [A2A Communication (Future Roadmap)](#14-a2a-communication-future-roadmap)
15. [Local Development Guide (Docker Compose)](#15-local-development-guide-docker-compose)
16. [Deployment Guide — GCP](#16-deployment-guide--gcp)
17. [Deployment Guide — AWS](#17-deployment-guide--aws)
18. [Deployment Guide — Azure](#18-deployment-guide--azure)
19. [Cloud Deployment Comparison](#19-cloud-deployment-comparison)
20. [Production Readiness Checklist](#20-production-readiness-checklist)
21. [Environment Variable Reference](#21-environment-variable-reference)

---

## 1. System Overview

The **HR Multi-Agent Recruitment System** automates the end-to-end hiring pipeline using a **multi-agent architecture** powered by **LangGraph**. Six specialized AI agents — orchestrated by a central Supervisor — collaboratively handle every stage of recruitment, from job posting creation to final hire/reject decisions.

### Core Design Principles

| Principle | How It's Implemented |
|---|---|
| **Separation of concerns** | Each pipeline stage is a dedicated agent with its own LangGraph sub-graph and tool set |
| **Shared state** | A single `HRState` `TypedDict` flows through the entire graph; the `messages` field uses an append-only `add_messages` reducer |
| **Deterministic routing** | Supervisor uses `ChatOpenAI.with_structured_output(SupervisorDecision)` — Pydantic-validated, guaranteed-valid routing |
| **Resilience** | Configurable per-stage retry (default 2) with skip-on-exhaustion; per-agent exception isolation |
| **Observability** | `StageTimer` context manager records wall-clock time, tool-call count, and success/error status per stage |
| **Multi-interface** | CLI (`main.py`), REST API (FastAPI on Uvicorn), and interactive Dashboard (Streamlit) |

### Key Numbers at a Glance

| Metric | Value |
|---|---|
| Worker agents | 6 |
| LangChain `@tool` functions | 24 total across 6 tool modules |
| Database tables (ORM models) | 7 |
| REST API endpoints | 16 |
| Dashboard pages | 9 |
| Lines of Python (approx.) | ~3,500 |

---

## 2. Architecture Layers

### Layered ASCII Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                                │
│  ┌─────────────────┐   ┌───────────────────┐   ┌────────────────────┐   │
│  │   CLI (main.py) │   │ FastAPI REST API   │   │ Streamlit Dashboard│   │
│  │   argparse       │   │ uvicorn + async    │   │ Interactive UI     │   │
│  └────────┬────────┘   └────────┬──────────┘   └────────┬───────────┘   │
│           └─────────────┬───────┴────────────────────────┘               │
│                         ▼                                                │
├──────────────────────────────────────────────────────────────────────────┤
│                       ORCHESTRATION LAYER                                │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │              LangGraph StateGraph (Main Pipeline)                │   │
│   │                                                                  │   │
│   │   START ──► SUPERVISOR ──┬──► Agent 1 ──► SUPERVISOR            │   │
│   │                          ├──► Agent 2 ──► SUPERVISOR             │   │
│   │                          ├──► Agent 3 ──► SUPERVISOR             │   │
│   │                          ├──► Agent 4 ──► SUPERVISOR             │   │
│   │                          ├──► Agent 5 ──► SUPERVISOR             │   │
│   │                          ├──► Agent 6 ──► SUPERVISOR             │   │
│   │                          └──► END (complete)                     │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                         │                                                │
├─────────────────────────┼────────────────────────────────────────────────┤
│                      AGENT LAYER                                         │
│                                                                          │
│   ┌────────────┐ ┌────────────┐ ┌──────────────┐                        │
│   │ Job Posting │ │  Resume    │ │  Interview   │                        │
│   │   Agent     │ │ Selection  │ │ Scheduling   │                        │
│   └────────────┘ └────────────┘ └──────────────┘                        │
│   ┌────────────┐ ┌────────────┐ ┌──────────────┐                        │
│   │  Feedback  │ │  Ranking   │ │    Final     │                        │
│   │ Collection │ │   Agent    │ │  Selection   │                        │
│   └────────────┘ └────────────┘ └──────────────┘                        │
│                                                                          │
│   Each agent = LangGraph sub-graph: agent_node ↔ ToolNode                │
│                         │                                                │
├─────────────────────────┼────────────────────────────────────────────────┤
│                      TOOLS LAYER (LangChain @tool)                       │
│                                                                          │
│   job_tools.py │ resume_tools.py │ scheduling_tools.py                   │
│   feedback_tools.py │ ranking_tools.py │ selection_tools.py              │
│                                                                          │
│   Each tool function performs DB CRUD via SQLAlchemy sessions             │
│                         │                                                │
├─────────────────────────┼────────────────────────────────────────────────┤
│                      DATA LAYER                                          │
│                                                                          │
│   SQLAlchemy 2.0 ORM  ──►  SQLite (hr_system.db)                        │
│   7 tables: job_postings, candidates, applications,                      │
│             interviews, feedback, rankings, offers                       │
│                                                                          │
├──────────────────────────────────────────────────────────────────────────┤
│                    EXTERNAL SERVICES                                     │
│                                                                          │
│   OpenAI API (GPT-4o-mini) — LLM inference for all agents               │
└──────────────────────────────────────────────────────────────────────────┘
```

### Mermaid — Component Diagram

```mermaid
graph TB
    subgraph Presentation
        CLI["CLI — main.py"]
        API["FastAPI REST API"]
        UI["Streamlit Dashboard"]
    end

    subgraph Orchestration
        Pipeline["LangGraph StateGraph"]
        Supervisor["Supervisor Agent"]
    end

    subgraph Agents
        JP["Job Posting Agent"]
        RS["Resume Selection Agent"]
        IS["Interview Scheduling Agent"]
        FC["Feedback Collection Agent"]
        CR["Candidate Ranking Agent"]
        FS["Final Selection Agent"]
    end

    subgraph Tools
        JT["job_tools.py — 4 tools"]
        RT["resume_tools.py — 6 tools"]
        ST["scheduling_tools.py — 4 tools"]
        FT["feedback_tools.py — 4 tools"]
        RKT["ranking_tools.py — 3 tools"]
        SLT["selection_tools.py — 4 tools"]
    end

    subgraph Data
        ORM["SQLAlchemy 2.0 ORM"]
        DB[("SQLite — hr_system.db")]
    end

    subgraph External
        LLM["OpenAI GPT-4o-mini"]
    end

    CLI --> Pipeline
    API --> Pipeline
    UI --> DB

    Pipeline --> Supervisor
    Supervisor --> JP
    Supervisor --> RS
    Supervisor --> IS
    Supervisor --> FC
    Supervisor --> CR
    Supervisor --> FS

    JP --> JT
    RS --> RT
    IS --> ST
    FC --> FT
    CR --> RKT
    FS --> SLT

    JT --> ORM
    RT --> ORM
    ST --> ORM
    FT --> ORM
    RKT --> ORM
    SLT --> ORM
    ORM --> DB

    JP --> LLM
    RS --> LLM
    IS --> LLM
    FC --> LLM
    CR --> LLM
    FS --> LLM
    Supervisor --> LLM
```

---

## 3. Data-Flow & Sequence Diagrams

### Pipeline Flow (Mermaid)

```mermaid
stateDiagram-v2
    [*] --> Supervisor : initial HRState

    Supervisor --> JobPosting : stage = start
    JobPosting --> Supervisor : stage = job_posting_complete

    Supervisor --> ResumeSelection : stage = job_posting_complete
    ResumeSelection --> Supervisor : stage = resume_selection_complete

    Supervisor --> InterviewScheduling : stage = resume_selection_complete
    InterviewScheduling --> Supervisor : stage = interview_scheduling_complete

    Supervisor --> FeedbackCollection : stage = interview_scheduling_complete
    FeedbackCollection --> Supervisor : stage = feedback_collection_complete

    Supervisor --> CandidateRanking : stage = feedback_collection_complete
    CandidateRanking --> Supervisor : stage = candidate_ranking_complete

    Supervisor --> FinalSelection : stage = candidate_ranking_complete
    FinalSelection --> Supervisor : stage = final_selection_complete

    Supervisor --> [*] : stage = final_selection_complete → COMPLETE
```

### Sequence Diagram — Full Pipeline Run

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py / API
    participant Pipeline as LangGraph Pipeline
    participant Sup as Supervisor
    participant Agent as Worker Agent
    participant Tools as ToolNode
    participant LLM as OpenAI GPT-4o-mini
    participant DB as SQLite

    User->>Main: Start pipeline (job details + candidates)
    Main->>DB: init_db() + seed candidates
    Main->>Pipeline: pipeline.invoke(initial_state)

    loop For each of 6 stages
        Pipeline->>Sup: supervisor_node(state)
        Sup->>LLM: Structured output request (SupervisorDecision)
        LLM-->>Sup: {next_agent, reasoning}
        Sup-->>Pipeline: Updated state with next_agent

        Pipeline->>Agent: agent_wrapper_node(state)
        Note over Agent: StageTimer starts

        loop ReAct loop (max 25 iterations)
            Agent->>LLM: System prompt + messages
            LLM-->>Agent: Response (± tool_calls)
            alt Has tool_calls
                Agent->>Tools: Execute tool functions
                Tools->>DB: CRUD operations
                DB-->>Tools: Results
                Tools-->>Agent: Tool results as messages
            else No tool_calls
                Agent-->>Pipeline: Done — return updated state
            end
        end

        Note over Agent: StageTimer ends, metrics recorded
        Agent-->>Pipeline: {messages, current_stage, stage_metrics}
    end

    Pipeline-->>Main: Final state (completed)
    Main-->>User: Summary + metrics
```

### Data Flow Through Database Tables

```mermaid
flowchart LR
    JP["job_postings"] --> APP["applications"]
    CAND["candidates"] --> APP
    APP --> |"screening_score ≥ 60"| SHORT["Shortlisted"]
    SHORT --> INT["interviews"]
    INT --> FB["feedback"]
    APP --> RANK["rankings"]
    FB --> RANK
    RANK --> OFFER["offers"]
    CAND --> INT
    CAND --> OFFER
    JP --> OFFER
```

---

## 4. Pipeline Walkthrough (Step-by-Step)

### Step 0 — Configuration & Bootstrapping

**What happens:** The system loads environment variables, validates the OpenAI API key, initializes the database, and sets up logging.

| Aspect | Detail |
|---|---|
| **Files** | [`config/settings.py`](config/settings.py), [`config/logging_config.py`](config/logging_config.py), [`database/db.py`](database/db.py) |
| **Tech** | `python-dotenv` → `os.getenv()` → `Settings` class; Python `logging` module; `SQLAlchemy` engine |
| **Data** | `.env` file → `Settings` module-level singleton instance; `hr_system.db` → SQLAlchemy `engine` |
| **Validation** | `settings.validate()` — raises `ValueError` if `OPENAI_API_KEY` is missing or placeholder |

**Key Configuration Values:**

| Variable | Default | Source |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | `.env` |
| `LLM_MODEL` | `gpt-4o-mini` | `.env` |
| `LLM_TEMPERATURE` | `0.1` | `.env` |
| `DATABASE_URL` | `sqlite:///./hr_system.db` | `.env` |
| `API_HOST` / `API_PORT` | `0.0.0.0` / `8000` | `.env` |
| `RESUME_SHORTLIST_THRESHOLD` | `60` | `.env` |
| `MAX_INTERVIEWS_PER_CANDIDATE` | `3` | `.env` |
| `AGENT_RECURSION_LIMIT` | `25` | `.env` |
| `AGENT_TIMEOUT_SECONDS` | `120` | `.env` |
| `AGENT_MAX_RETRIES` | `2` | `.env` |
| `LOG_LEVEL` | `INFO` | `.env` (read in `logging_config.py`) |

**Bootstrap Flow:**
```
.env  ──►  python-dotenv  ──►  Settings.__init__()  ──►  settings.validate()
                                                              │
SQLAlchemy engine ◄── DATABASE_URL ◄──────────────────────────┘
        │
        ▼
Base.metadata.create_all()  →  7 tables created in SQLite
```

---

### Step 1 — State Initialization

**What happens:** The shared `HRState` TypedDict is created with the initial hiring request, candidate data, and empty containers for every pipeline stage output.

| Aspect | Detail |
|---|---|
| **Files** | [`state/hr_state.py`](state/hr_state.py), [`main.py`](main.py) (lines 138–177) |
| **Tech** | `TypedDict`, `langchain_core.messages.HumanMessage`, `langgraph.graph.message.add_messages` reducer |
| **Data** | Initial `HumanMessage` with job title/requirements/candidates; 4 sample candidates pre-seeded into DB |

**HRState Fields:**

| Category | Fields | Type |
|---|---|---|
| **Messages** | `messages` | `Annotated[list[BaseMessage], add_messages]` — append-only conversation history |
| **Pipeline Control** | `current_stage`, `next_agent`, `pipeline_status`, `error_message`, `retry_count`, `max_retries`, `failed_stages` | `str`, `int`, `Optional[str]`, `list[str]` |
| **Job Data** | `job_posting_id`, `job_posting` | `Optional[int]`, `Optional[dict]` |
| **Candidate Data** | `candidates`, `shortlisted_candidates` | `list[dict]` |
| **Interview Data** | `scheduled_interviews` | `list[dict]` |
| **Feedback Data** | `interview_feedback` | `list[dict]` |
| **Ranking Data** | `candidate_rankings` | `list[dict]` |
| **Decision Data** | `final_decisions` | `list[dict]` |
| **Observability** | `stage_metrics` | `list[dict]` |

**Stage Constants** (exported from `hr_state.py`):
```python
STAGES = {
    "JOB_POSTING": "job_posting",
    "RESUME_SELECTION": "resume_selection",
    "INTERVIEW_SCHEDULING": "interview_scheduling",
    "FEEDBACK_COLLECTION": "feedback_collection",
    "CANDIDATE_RANKING": "candidate_ranking",
    "FINAL_SELECTION": "final_selection",
    "COMPLETE": "complete",
}
```

---

### Step 2 — Supervisor Routing

**What happens:** The Supervisor agent evaluates the current pipeline state and decides which worker agent should execute next. It uses an LLM with **structured output** (`SupervisorDecision`) to guarantee valid routing.

| Aspect | Detail |
|---|---|
| **Files** | [`graph/supervisor.py`](graph/supervisor.py), [`graph/pipeline.py`](graph/pipeline.py) |
| **Tech** | `ChatOpenAI.with_structured_output()`, `pydantic.BaseModel`, LangGraph conditional edges |
| **LLM Model** | GPT-4o-mini (**temperature=0** for deterministic routing) |
| **Input** | Reads `current_stage`, `error_message`, `retry_count`, `failed_stages`, `pipeline_status` from `HRState` |
| **Output** | Sets `next_agent` to one of the 7 valid targets |

**SupervisorDecision Pydantic Model:**
```python
class SupervisorDecision(BaseModel):
    next_agent: str   # One of 7 valid agents + "complete"
    reasoning: str    # Brief explanation of the routing decision
```

**Deterministic Routing Map** (from `_NEXT_AFTER_STAGE` in `supervisor.py`):
```
"start"                           → "job_posting"
"job_posting_complete"            → "resume_selection"
"resume_selection_complete"       → "interview_scheduling"
"interview_scheduling_complete"   → "feedback_collection"
"feedback_collection_complete"    → "candidate_ranking"
"candidate_ranking_complete"      → "final_selection"
"final_selection_complete"        → "complete" (→ END)
```

**Retry Logic (Supervisor Error Handling):**
```
if error_message:
    if retry_count < max_retries:
        → Re-route to SAME agent, bump retry_count
        → Clear error_message for clean slate
        → Inject retry context as HumanMessage
    else:
        → Log failure, add to failed_stages[]
        → Advance to NEXT stage (or "complete")
        → Reset retry_count = 0
else:
    → LLM-based routing decision via structured output
    → Reset retry_count = 0
```

**`route_to_agent` Function** (conditional edge in the pipeline graph):

Validates `state["next_agent"]` against the 7 valid targets. Falls back to `"complete"` for any invalid value.

---

### Step 3 — Job Posting Agent

**What happens:** Generates a professional, detailed job posting based on the hiring requirements and saves it to the database.

| Aspect | Detail |
|---|---|
| **File** | [`agents/job_posting_agent.py`](agents/job_posting_agent.py) |
| **Tools File** | [`tools/job_tools.py`](tools/job_tools.py) |
| **LLM Config** | GPT-4o-mini, temperature=0.1 |
| **Tools** | `create_job_posting`, `list_job_postings`, `get_job_posting`, `update_job_posting` |
| **Input** | Job title, department, requirements from the initial `HumanMessage` |
| **Output** | New row in `job_postings` table; `current_stage` → `"job_posting_complete"` |
| **DB Table** | `job_postings` (12 columns — see [Schema](#7-database-schema-erd)) |

**Agent Sub-Graph Flow:**
```
agent_node (LLM reasoning) ──► should_continue?
    ├── has tool_calls → ToolNode (executes DB tools) → back to agent_node
    └── no tool_calls  → END (done)
```

**Metrics:** `StageTimer("job_posting")` records wall-clock time, tool-call count, success/error status.

---

### Step 4 — Resume Selection Agent

**What happens:** Screens every candidate's resume against the job requirements, assigns a 0–100 score, and automatically shortlists candidates above the threshold (default: 60).

| Aspect | Detail |
|---|---|
| **File** | [`agents/resume_selection_agent.py`](agents/resume_selection_agent.py) |
| **Tools File** | [`tools/resume_tools.py`](tools/resume_tools.py) |
| **LLM Config** | GPT-4o-mini, temperature=0.1 |
| **Tools** | `get_job_requirements`, `get_candidates_for_job`, `add_candidate`, `create_application`, `score_resume`, `get_shortlisted_candidates` |
| **Input** | Job posting ID, candidate resumes from DB |
| **Output** | `applications` table rows with screening scores; candidates ≥ threshold marked `is_shortlisted=True`; candidate status → `"shortlisted"` |
| **DB Tables** | `candidates`, `applications` |

**Scoring Criteria (LLM-Guided):**

| Weight | Category |
|---|---|
| 40% | Skills match |
| 30% | Experience relevance |
| 15% | Education fit |
| 15% | Overall presentation |

**Threshold:** Candidates scoring ≥ `RESUME_SHORTLIST_THRESHOLD` (default 60) are auto-shortlisted.

---

### Step 5 — Interview Scheduling Agent

**What happens:** Schedules interviews for all shortlisted candidates with appropriate interviewers, types, and time slots.

| Aspect | Detail |
|---|---|
| **File** | [`agents/interview_scheduling_agent.py`](agents/interview_scheduling_agent.py) |
| **Tools File** | [`tools/scheduling_tools.py`](tools/scheduling_tools.py) |
| **LLM Config** | GPT-4o-mini, temperature=0.1 |
| **Tools** | `get_available_slots`, `schedule_interview`, `list_interviews`, `update_interview_status` |
| **Input** | Shortlisted candidate IDs from previous stage |
| **Output** | `interviews` table rows; candidate status → `"interviewing"` |
| **DB Table** | `interviews` (11 columns) |

**Interview Types:**

| Type | Focus |
|---|---|
| `technical` | Technical skills assessment |
| `behavioral` | Soft skills and behavioral evaluation |
| `culture_fit` | Team and culture fit (optional, top candidates) |

**Scheduling Rules:**
- Minimum 2 interviews per candidate (technical + behavioral)
- Different interviewers for different types
- Available slots: `09:00–11:30, 13:00–16:30` (half-hour increments; 14 total slots)
- Already-booked slots are excluded dynamically via `get_available_slots`
- Auto-generates meeting links: `https://meet.example.com/hr-interview-{candidate_id}-{type}`
- Default duration: 60 minutes
- Auto-skips weekends when defaulting dates

---

### Step 6 — Feedback Collection Agent

**What happens:** Generates realistic, structured interviewer feedback for all scheduled interviews (simulated in demo mode).

| Aspect | Detail |
|---|---|
| **File** | [`agents/feedback_agent.py`](agents/feedback_agent.py) |
| **Tools File** | [`tools/feedback_tools.py`](tools/feedback_tools.py) |
| **LLM Config** | GPT-4o-mini, **temperature=0.3** (higher for varied/realistic feedback) |
| **Tools** | `get_pending_feedback`, `submit_feedback`, `get_feedback_for_candidate`, `get_all_feedback_summary` |
| **Input** | Scheduled interview records from DB |
| **Output** | `feedback` table rows with multi-dimensional ratings; interview status → `"completed"` |
| **DB Table** | `feedback` (12 columns, 1:1 with `interviews` via UNIQUE constraint) |

**Rating Dimensions:**

| Rating | Scale | Focus |
|---|---|---|
| `technical_rating` | 1–10 | Technical competency |
| `communication_rating` | 1–10 | Communication skills |
| `culture_fit_rating` | 1–10 | Cultural alignment |
| `overall_rating` | 1.0–10.0 | Overall impression |

**Recommendation Levels:** `strong_hire`, `hire`, `maybe`, `no_hire`

**Duplicate Prevention:** `submit_feedback` checks for existing feedback on the same `interview_id` before inserting.

---

### Step 7 — Candidate Ranking Agent

**What happens:** Calculates composite scores from resume screening + interview performance and produces a ranked list of all candidates.

| Aspect | Detail |
|---|---|
| **File** | [`agents/ranking_agent.py`](agents/ranking_agent.py) |
| **Tools File** | [`tools/ranking_tools.py`](tools/ranking_tools.py) |
| **LLM Config** | GPT-4o-mini, temperature=0.1 |
| **Tools** | `calculate_composite_score`, `save_ranking`, `get_rankings` |
| **Input** | Application screening scores, interview feedback ratings |
| **Output** | `rankings` table rows with composite scores, rank positions, LLM-generated analysis |
| **DB Table** | `rankings` (8 columns, with JSON `score_breakdown`) |

**Composite Scoring Formula:**
```
resume_score_normalized = screening_score / 10.0      (0–10 scale)
interview_score = avg(all_feedback.overall_rating)     (0–10 scale)

composite = (resume_score × 0.30) + (interview_score × 0.70)
```

| Weight | Source |
|---|---|
| **30%** | Resume/screening score (from `applications.screening_score`) |
| **70%** | Interview performance (average `feedback.overall_rating`) |

**Side Effect:** Candidate status → `"ranked"` after `save_ranking`.

---

### Step 8 — Final Selection Agent

**What happens:** Reviews the complete candidate journey (resume → screening → interviews → rankings) and makes final hire/reject/waitlist decisions with justifications.

| Aspect | Detail |
|---|---|
| **File** | [`agents/final_selection_agent.py`](agents/final_selection_agent.py) |
| **Tools File** | [`tools/selection_tools.py`](tools/selection_tools.py) |
| **LLM Config** | GPT-4o-mini, temperature=0.1 |
| **Tools** | `generate_offer_summary`, `make_decision`, `get_all_decisions`, `get_pipeline_summary` |
| **Input** | Candidate profiles, screening scores, interview feedback, rankings |
| **Output** | `offers` table rows with decisions + justifications; candidate status → `"selected"` or `"rejected"` |
| **DB Table** | `offers` (9 columns) |

**Decision Criteria:**

| Decision | When Applied |
|---|---|
| `offer` | Top-ranked candidates with `strong_hire` / `hire` recommendations |
| `waitlist` | Borderline candidates with mixed feedback (status unchanged) |
| `reject` | Low-ranked candidates or those with `no_hire` recommendations |

**Pipeline Status:** This agent sets `pipeline_status` → `"completed"` on success.

---

### Step 9 — Pipeline Completion

**What happens:** The Supervisor receives `current_stage = "final_selection_complete"`, routes to `"complete"` which maps to `END` in the LangGraph, terminating execution.

| Aspect | Detail |
|---|---|
| **Files** | [`graph/pipeline.py`](graph/pipeline.py) (line 60: `"complete": END`) |
| **Data** | Final `HRState` with all accumulated messages, metrics, and results |
| **Output** | Pipeline status → `"completed"`; all `stage_metrics` logged to console |

---

## 5. Agent Sub-Graph Architecture

Every worker agent follows the same **ReAct (Reason + Act)** pattern, implemented as a LangGraph sub-graph:

```mermaid
graph LR
    A["agent_node — LLM"] -->|has tool_calls?| B{Decision}
    B -->|YES| C["ToolNode — Execute tools"]
    C --> A
    B -->|NO| D["END"]
```

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

**Canonical Pattern (all 6 agents):**

```python
# 1. Build LLM with tools bound
llm_with_tools = ChatOpenAI(
    model=settings.LLM_MODEL,
    temperature=settings.LLM_TEMPERATURE,  # 0.3 for feedback agent
    api_key=settings.OPENAI_API_KEY,
).bind_tools(AGENT_TOOLS)

# 2. agent_node: prepend system prompt, invoke LLM
def agent_node(state: HRState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 3. should_continue: check if LLM wants to call tools
def should_continue(state: HRState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "done"

# 4. Assemble sub-graph
workflow = StateGraph(HRState)
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(AGENT_TOOLS))
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "done": END})
workflow.add_edge("tools", "agent")
compiled = workflow.compile(recursion_limit=settings.AGENT_RECURSION_LIMIT)
```

**Wrapper Node** (used in the main pipeline — same pattern in all 6 agents):
```python
def agent_wrapper_node(state: HRState) -> dict:
    agent = build_agent()  # @functools.lru_cache(maxsize=1) — built once
    metrics_list = list(state.get("stage_metrics", []))

    with StageTimer("stage_name") as timer:
        try:
            result = agent.invoke(state)
            timer.count_tool_calls(result.get("messages", []))
            timer.mark_success()
            metrics_list.append(timer.to_dict())
            return {
                "messages": result["messages"],
                "current_stage": "stage_name_complete",
                "stage_metrics": metrics_list,
            }
        except Exception as e:
            timer.mark_failure(str(e))
            metrics_list.append(timer.to_dict())
            return {
                "messages": [HumanMessage(content=f"[Agent] Error: {e}")],
                "current_stage": "stage_name",
                "error_message": str(e),
                "stage_metrics": metrics_list,
            }
```

**Key Implementation Details:**
- All agents use `@functools.lru_cache(maxsize=1)` to build the sub-graph exactly once
- The wrapper catches all exceptions and records them in `HRState.error_message` for the Supervisor's retry logic
- `stage_metrics` is a copy (not a reference) to prevent mutation issues across state transitions

---

## 6. Tool Inventory & Mapping

### Complete Tool Registry

| Agent | Module | Tool Function | Purpose | DB Tables Touched |
|---|---|---|---|---|
| **Job Posting** | `job_tools.py` | `create_job_posting` | Create a new job posting | `job_postings` |
| | | `list_job_postings` | List postings by status | `job_postings` |
| | | `get_job_posting` | Get posting by ID | `job_postings` |
| | | `update_job_posting` | Update posting status | `job_postings` |
| **Resume Selection** | `resume_tools.py` | `add_candidate` | Add/deduplicate candidate | `candidates` |
| | | `create_application` | Link candidate to job | `applications` |
| | | `score_resume` | Record screening score + auto-shortlist | `applications`, `candidates` |
| | | `get_candidates_for_job` | Get all applicants for a job | `applications`, `candidates` |
| | | `get_shortlisted_candidates` | Get shortlisted candidates | `applications`, `candidates` |
| | | `get_job_requirements` | Get job requirements | `job_postings` |
| **Interview Scheduling** | `scheduling_tools.py` | `schedule_interview` | Schedule an interview | `interviews`, `candidates` |
| | | `list_interviews` | List interviews (filterable) | `interviews` |
| | | `update_interview_status` | Update interview status | `interviews` |
| | | `get_available_slots` | Get available time slots | `interviews` |
| **Feedback Collection** | `feedback_tools.py` | `submit_feedback` | Submit interview feedback | `feedback`, `interviews` |
| | | `get_feedback_for_candidate` | Get all feedback for a candidate | `interviews`, `feedback` |
| | | `get_pending_feedback` | Get interviews needing feedback | `interviews`, `feedback` |
| | | `get_all_feedback_summary` | Summarize all feedback | `feedback`, `interviews`, `candidates` |
| **Candidate Ranking** | `ranking_tools.py` | `calculate_composite_score` | Calculate weighted composite score | `applications`, `interviews`, `feedback` |
| | | `save_ranking` | Save ranking entry | `rankings`, `applications`, `candidates` |
| | | `get_rankings` | Get ranked list | `rankings`, `applications`, `candidates` |
| **Final Selection** | `selection_tools.py` | `make_decision` | Record hire/reject/waitlist | `offers`, `candidates` |
| | | `generate_offer_summary` | Generate candidate journey summary | `candidates`, `applications`, `rankings`, `interviews`, `feedback`, `job_postings` |
| | | `get_all_decisions` | Get all decisions | `offers` |
| | | `get_pipeline_summary` | Pipeline funnel summary | `job_postings`, `applications`, `offers` |

**Total: 24 tools across 6 modules**

---

## 7. Database Schema (ERD)

### Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    job_postings ||--o{ applications : "has"
    job_postings ||--o{ offers : "results in"
    candidates ||--o{ applications : "applies"
    candidates ||--o{ interviews : "attends"
    candidates ||--o{ offers : "receives"
    applications ||--o{ rankings : "ranked"
    interviews ||--|| feedback : "has"

    job_postings {
        int id PK
        string title
        string department
        text description
        text requirements
        text preferred_qualifications
        string salary_range
        string location
        string employment_type
        string status
        datetime created_at
        datetime updated_at
    }

    candidates {
        int id PK
        string name
        string email UK
        string phone
        text resume_text
        text skills
        int experience_years
        string education
        string status
        datetime created_at
    }

    applications {
        int id PK
        int candidate_id FK
        int job_posting_id FK
        float screening_score
        text screening_notes
        boolean is_shortlisted
        datetime applied_at
    }

    interviews {
        int id PK
        int candidate_id FK
        string interviewer_name
        string interviewer_email
        string interview_type
        datetime scheduled_time
        int duration_minutes
        string meeting_link
        string status
        text notes
        datetime created_at
    }

    feedback {
        int id PK
        int interview_id FK_UK
        string interviewer_name
        int technical_rating
        int communication_rating
        int culture_fit_rating
        float overall_rating
        text strengths
        text weaknesses
        string recommendation
        text detailed_notes
        datetime submitted_at
    }

    rankings {
        int id PK
        int application_id FK
        float resume_score
        float interview_score
        float overall_score
        int rank
        json score_breakdown
        text analysis
        datetime created_at
    }

    offers {
        int id PK
        int candidate_id FK
        int job_posting_id FK
        string decision
        string salary_offered
        datetime start_date
        text justification
        text offer_letter_summary
        datetime created_at
    }
```

### ASCII ERD (for terminals)

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
│ updated_at        │                │              │           ▼
└──────────────────┘                │              │   ┌──────────────────┐
        │                           │              │   │    rankings       │
        │                           ▼              │   ├──────────────────┤
        │                  ┌──────────────────┐    │   │ id          (PK) │
        │                  │   interviews      │    │   │ application_id(FK│
        │                  ├──────────────────┤    │   │ resume_score     │
        │                  │ id          (PK) │    │   │ interview_score  │
        │                  │ candidate_id (FK)│────┘   │ overall_score    │
        │                  │ interviewer_name  │        │ rank             │
        │                  │ interviewer_email │        │ score_breakdown  │
        │                  │ interview_type    │        │ analysis         │
        │                  │ scheduled_time    │        │ created_at       │
        │                  │ duration_minutes  │        └──────────────────┘
        │                  │ meeting_link      │
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

**Summary:**

| Aspect | Detail |
|---|---|
| **Table Count** | 7 |
| **ORM** | SQLAlchemy 2.0+ with `declarative_base()` |
| **Database** | SQLite (file: `hr_system.db`) — swappable to PostgreSQL/MySQL via `DATABASE_URL` |
| **Session Management** | `get_session()` context manager (auto-commit/rollback); `get_db_session()` raw session |
| **Schema Ops** | `init_db()` creates tables; `drop_db()` drops all tables |
| **SQLite Config** | `check_same_thread=False` for multi-threaded access |

---

## 8. API Layer

### Tech Stack

| Component | Technology |
|---|---|
| Framework | **FastAPI** 0.115+ |
| Server | **Uvicorn** (ASGI, hot-reload in dev) |
| Validation | **Pydantic** v2 BaseModel |
| CORS | `CORSMiddleware` (allow all origins in dev) |
| Lifecycle | `asynccontextmanager` lifespan (replaces deprecated `@app.on_event`) |
| Background Execution | `FastAPI.BackgroundTasks` + `threading.Lock` for run tracking |
| Pipeline Run Storage | **In-memory** dict `_pipeline_runs` (keyed by `run_id`, an 8-char UUID prefix) |

### Endpoints

| Method | Endpoint | Tag | Purpose | Response |
|---|---|---|---|---|
| `GET` | `/health` | System | Health check | `{"status": "healthy", "version": "2.0.0"}` |
| `POST` | `/pipeline/start` | Pipeline | Start async pipeline | `PipelineRunResponse` (run_id, status, message) |
| `GET` | `/pipeline/status/{run_id}` | Pipeline | Poll run status | `PipelineStatusResponse` |
| `GET` | `/pipeline/metrics/{run_id}` | Pipeline | Per-stage metrics | `{run_id, status, stage_metrics[], failed_stages[]}` |
| `GET` | `/pipeline/runs` | Pipeline | List all runs | Array of `{run_id, status, started_at}` |
| `GET` | `/pipeline/summary/{job_id}` | Pipeline | DB-based funnel summary | `{job, total_applicants, shortlisted, interviews_conducted, offers_made}` |
| `GET` | `/jobs` | Jobs | List all job postings | Array of `JobPosting` dicts |
| `GET` | `/jobs/{job_id}` | Jobs | Get specific job posting | `JobPosting` dict |
| `GET` | `/candidates` | Candidates | List all candidates | Array of `Candidate` dicts |
| `POST` | `/candidates` | Candidates | Add a new candidate | Created `Candidate` dict |
| `GET` | `/interviews` | Interviews | List all interviews | Array of `Interview` dicts |
| `GET` | `/feedback` | Feedback | List all feedback | Array of `Feedback` dicts |
| `POST` | `/feedback` | Feedback | Submit feedback | Created `Feedback` dict |
| `GET` | `/rankings` | Rankings | List all rankings (sorted) | Sorted `Ranking` array with `candidate_name` |
| `GET` | `/decisions` | Decisions | List all hiring decisions | Array of `Offer` dicts |

**Total: 15 endpoints (+ Swagger/ReDoc auto-generated by FastAPI)**

### Request/Response Schemas (Pydantic v2)

```python
# Request Models
class PipelineStartRequest(BaseModel):
    job_title: str                  # Required
    department: str = "Engineering"
    requirements: str               # Required
    candidates: list[dict] = []     # Optional candidate list

class CandidateInput(BaseModel):
    name: str
    email: str
    resume_text: str
    phone: str = ""
    skills: str = ""
    experience_years: int = 0
    education: str = ""

class FeedbackInput(BaseModel):
    interview_id: int
    interviewer_name: str
    overall_rating: float
    recommendation: str
    technical_rating: int = 0
    communication_rating: int = 0
    culture_fit_rating: int = 0
    strengths: str = ""
    weaknesses: str = ""

# Response Models
class PipelineRunResponse(BaseModel):
    run_id: str
    status: str = "started"
    message: str = "Pipeline started in background"

class PipelineStatusResponse(BaseModel):
    run_id: str
    status: str                        # started, running, completed, error
    current_stage: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
    total_messages: Optional[int]
    stage_metrics: Optional[list[dict]]
```

---

## 9. Dashboard (UI Layer)

### Tech Stack

| Component | Technology |
|---|---|
| Framework | **Streamlit** 1.45+ |
| Data manipulation | **Pandas** |
| Charts | Streamlit built-in `st.bar_chart()` |
| Layout | `st.columns()`, `st.expander()`, `st.tabs()` |
| Styling | Custom CSS injected via `st.markdown(unsafe_allow_html=True)` — gradient headers, metric cards |
| Export | CSV download via `st.download_button()` |
| File size | 635 lines |

### Pages

| Page | Sidebar Label | Features |
|---|---|---|
| 📊 **Dashboard** | Dashboard | KPI metrics (jobs, candidates, interviews, offers, rejections), pipeline stage progress bar, recent activity feed |
| 📋 **Job Postings** | Job Postings | Expandable cards with description, requirements, salary, status |
| 👥 **Candidates** | Candidates | Summary table + CSV export, detailed per-candidate view |
| 📅 **Interviews** | Interviews | Table with candidate, interviewer, type, time, status + CSV export |
| 💬 **Feedback** | Feedback | Per-feedback expandable cards with ratings, strengths, weaknesses |
| 🏆 **Rankings** | Rankings | Ranked table with medal icons (🥇🥈🥉), detailed analysis per candidate |
| ✅ **Decisions** | Decisions | Summary metrics (offers/rejections/waitlist), per-decision detail, CSV export |
| 📈 **Compare Candidates** | Compare | Side-by-side bar chart + top-3 detail cards |
| 🚀 **Run Pipeline** | Run Pipeline | Form to start a new pipeline with custom job + candidates (via API) |

---

## 10. Observability & Metrics

### StageTimer (`config/metrics.py`)

```python
@dataclass
class StageTimer:
    stage_name: str
    start_time: float       # Set on __enter__
    end_time: float         # Set on __exit__
    elapsed_seconds: float  # end - start (rounded to 3 dp)
    status: str             # "running" → "success" | "error"
    error_detail: str       # Error message if failed
    tool_call_count: int    # Counted from AI messages with tool_calls

    # Context manager: times the agent execution
    # count_tool_calls(): iterates messages, counts tool_call entries
    # mark_success() / mark_failure(reason): set status
    # to_dict(): returns {stage, elapsed_seconds, status, error, tool_calls}
```

### Metrics Collection Flow

```mermaid
flowchart LR
    A["Agent wrapper node"] --> B["StageTimer.__enter__"]
    B --> C["agent.invoke(state)"]
    C --> D["timer.count_tool_calls()"]
    D --> E["timer.mark_success()"]
    E --> F["StageTimer.__exit__"]
    F --> G["state.stage_metrics.append(timer.to_dict())"]
```

### Available Metrics Per Stage

| Metric | Type | Description |
|---|---|---|
| `stage` | `string` | Stage name (e.g., `"job_posting"`, `"resume_selection"`) |
| `elapsed_seconds` | `float` | Wall-clock execution time |
| `status` | `string` | `"success"` or `"error"` |
| `error` | `string | null` | Error message (if failed) |
| `tool_calls` | `int` | Number of LangChain tool invocations |

### Where Metrics Are Surfaced

| Interface | How |
|---|---|
| **CLI** | Printed per-stage after pipeline completion (main.py lines 194–200) |
| **REST API** | `GET /pipeline/metrics/{run_id}` returns `stage_metrics[]` |
| **Dashboard** | Pipeline progress bar on the 📊 Dashboard page |

---

## 11. Resilience & Error Handling

### Retry Mechanism

```mermaid
flowchart TD
    A["Supervisor receives state"] --> B{error_message?}
    B -->|No| C["Normal LLM routing"]
    C --> D["Reset retry_count = 0"]
    B -->|Yes| E{"retry_count < max_retries?"}
    E -->|Yes| F["Re-route to SAME agent"]
    F --> G["retry_count += 1"]
    G --> H["Clear error_message"]
    E -->|No| I["Add to failed_stages"]
    I --> J["Advance to NEXT stage"]
    J --> K["Reset retry_count = 0"]
```

### Guardrails

| Guardrail | Default | Purpose |
|---|---|---|
| `AGENT_RECURSION_LIMIT` | 25 | Max LLM ↔ tool loops per agent sub-graph |
| `AGENT_TIMEOUT_SECONDS` | 120 | Max wall-clock time per agent (config only, not yet enforced) |
| `AGENT_MAX_RETRIES` | 2 | Retries before supervisor skips a failed stage |

### Error Propagation Chain

```
Agent tool raises exception
  → agent sub-graph catches in wrapper node (try/except)
  → sets error_message in HRState
  → sets current_stage to the *failed* stage (not _complete)
  → Supervisor detects error_message on next invocation
  → Retry or skip based on retry_count vs max_retries
  → On skip: failed stage added to failed_stages[], next agent invoked
```

### Exception Isolation

Each agent wrapper wraps the **entire** sub-graph invocation in `try/except Exception`. This prevents a single agent failure from crashing the pipeline — the error is captured in state and handed to the Supervisor for retry/skip logic.

---

## 12. Complete Tech Stack Summary

### Core AI Framework

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Agent Orchestration | **LangGraph** | ≥0.4.0 | StateGraph, conditional routing, sub-graphs, END sentinel |
| LLM Framework | **LangChain** | ≥0.3.0 | Tool abstraction (`@tool`), message types, `ToolNode` |
| LLM Provider | **langchain-openai** | ≥0.3.0 | `ChatOpenAI`, `with_structured_output()`, `bind_tools()` |
| LLM Core | **langchain-core** | ≥0.3.0 | `BaseMessage`, `SystemMessage`, `HumanMessage` |

### API & Web

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| REST API | **FastAPI** | ≥0.115.0 | Async REST endpoints, background tasks, lifespan |
| ASGI Server | **Uvicorn** | ≥0.34.0 | High-performance Python web server with hot-reload |
| Dashboard | **Streamlit** | ≥1.45.0 | Interactive data dashboard with custom CSS |
| HTTP Client | **httpx** | ≥0.27.0 | Async HTTP requests (used by Streamlit → API) |

### Data & Validation

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| ORM | **SQLAlchemy** | ≥2.0.0 | Database abstraction, models, sessions, migrations |
| Database | **SQLite** | Built-in | File-based relational storage (swappable) |
| Validation | **Pydantic** | ≥2.0.0 | Request/response schemas, `SupervisorDecision` structured output |
| Data Analysis | **Pandas** | Latest | DataFrame operations, CSV export in dashboard |
| Numerical | **NumPy** | Latest | Numerical computations |
| ML | **Transformers** | Latest | Hugging Face transformers (included in dependencies) |

### Configuration & Utilities

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Environment | **python-dotenv** | ≥1.0.0 | `.env` file loading |
| Logging | Python `logging` | stdlib | Structured console logging (`HH:MM:SS | LEVEL | name | msg`) |
| CLI | Python `argparse` | stdlib | Command-line interface (`run`, `api`, `ui`, `init`, `reset`) |
| Caching | `functools.lru_cache` | stdlib | One-time build of agent sub-graphs and supervisor LLM |

### External Services

| Service | Usage | Default Model |
|---|---|---|
| **OpenAI API** | All LLM inference (6 agents + supervisor) | `gpt-4o-mini` (configurable via `LLM_MODEL`) |

---

## 13. Project Directory Structure

```
hr-multi-agent-system/
│
├── main.py                          # CLI entry point (run, api, ui, init, reset) — 314 lines
├── requirements.txt                 # Python dependencies (14 packages)
├── .env.example                     # Environment variable template
├── .gitignore                       # Git ignore rules
├── README.md                        # Project README
├── architecture.md                  # ← This file
├── a2a.md                           # A2A (Agent-to-Agent) protocol migration plan
├── hr_system.db                     # SQLite database (auto-generated)
│
├── config/                          # ⚙️ Configuration Layer
│   ├── __init__.py
│   ├── settings.py                  # Settings class (module-level singleton) — 91 lines
│   ├── logging_config.py            # setup_logging() + get_logger() — 52 lines
│   └── metrics.py                   # StageTimer @dataclass context manager — 78 lines
│
├── state/                           # 📦 Shared State
│   ├── __init__.py
│   └── hr_state.py                  # HRState TypedDict + STAGES constant — 66 lines
│
├── graph/                           # 🔀 Pipeline Orchestration
│   ├── __init__.py
│   ├── pipeline.py                  # StateGraph assembly (7 nodes + conditional edges) — 80 lines
│   └── supervisor.py                # Supervisor routing + retry logic — 218 lines
│
├── agents/                          # 🤖 AI Agents (LangGraph sub-graphs)
│   ├── __init__.py
│   ├── job_posting_agent.py         # Stage 1: Job posting creation — 119 lines
│   ├── resume_selection_agent.py    # Stage 2: Resume screening — 119 lines
│   ├── interview_scheduling_agent.py # Stage 3: Interview scheduling — 119 lines
│   ├── feedback_agent.py            # Stage 4: Feedback collection — 125 lines
│   ├── ranking_agent.py             # Stage 5: Candidate ranking — 122 lines
│   └── final_selection_agent.py     # Stage 6: Final decisions — 121 lines
│
├── tools/                           # 🔧 LangChain @tool Functions (DB operations)
│   ├── __init__.py
│   ├── job_tools.py                 # 4 tools: create/list/get/update job postings — 112 lines
│   ├── resume_tools.py              # 6 tools: candidate + application management — 188 lines
│   ├── scheduling_tools.py          # 4 tools: interview scheduling + calendar — 159 lines
│   ├── feedback_tools.py            # 4 tools: feedback submission + queries — 145 lines
│   ├── ranking_tools.py             # 3 tools: score calculation + ranking — 153 lines
│   └── selection_tools.py           # 4 tools: offer/reject decisions + summaries — 193 lines
│
├── database/                        # 💾 Data Layer
│   ├── __init__.py
│   ├── db.py                        # SQLAlchemy engine, session management — 61 lines
│   └── models.py                    # 7 ORM models (declarative_base), each with to_dict() — 248 lines
│
├── api/                             # 🌐 REST API
│   ├── __init__.py
│   ├── server.py                    # FastAPI app + 15 endpoints (lifespan-based startup) — 418 lines
│   └── schemas.py                   # Pydantic request/response models — 67 lines
│
└── ui/                              # 🖥️ Dashboard
    └── dashboard.py                 # Streamlit app (9 pages) — 635 lines
```

---

## 14. A2A Communication (Future Roadmap)

A detailed plan exists to migrate the current shared-state architecture to the **Google A2A (Agent-to-Agent) Protocol**, turning each agent into an independent, discoverable HTTP microservice communicating via JSON-RPC 2.0.

| Aspect | Detail |
|---|---|
| **Document** | [`a2a.md`](a2a.md) |
| **Protocol** | JSON-RPC 2.0 with `message/send`, `message/stream`, `tasks/get`, `tasks/cancel` |
| **Discovery** | Each agent publishes an Agent Card at `/.well-known/agent.json` |
| **Task Lifecycle** | `submitted → working → completed | failed | canceled` |
| **Benefits** | Decoupled agents, independent deployment/scaling, runtime discovery, language-agnostic |

> **Status:** This migration is **not yet implemented** — the current system uses the shared `HRState` TypedDict approach described in this document.

---

## 15. Local Development Guide (Docker Compose)

### Quick Start (without Docker)

```bash
# 1. Clone the repo
git clone https://github.com/your-org/hr-multi-agent-system.git
cd hr-multi-agent-system

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 5. Initialize database
python main.py init

# 6. Run the demo pipeline
python main.py run

# 7. Start the API server (separate terminal)
python main.py api

# 8. Launch the dashboard (separate terminal)
python main.py ui
```

### Docker Compose (for Production-like Setup)

```yaml
# docker-compose.yml
version: "3.9"

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8080"
    environment:
      - LLM_MODEL=gpt-4o-mini
      - LLM_TEMPERATURE=0.1
      - DATABASE_URL=postgresql://hr_user:password@db:5432/hr_system
      - AGENT_MAX_RETRIES=2
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy

  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    ports:
      - "8501:8501"
    environment:
      - DATABASE_URL=postgresql://hr_user:password@db:5432/hr_system
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: hr_user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: hr_system
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U hr_user -d hr_system"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary gunicorn
COPY . .
EXPOSE 8080
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8080"]
```

```dockerfile
# Dockerfile.streamlit
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "ui/dashboard.py", "--server.port=8501", \
     "--server.headless=true", "--server.address=0.0.0.0"]
```

---

## 16. Deployment Guide — GCP

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

### Step-by-Step

#### 1. Prerequisites
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
    secretmanager.googleapis.com artifactregistry.googleapis.com
```

#### 2. Create Cloud SQL (PostgreSQL)
```bash
gcloud sql instances create hr-system-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YOUR_DB_PASSWORD

gcloud sql databases create hr_system --instance=hr-system-db

gcloud sql users create hr_user \
    --instance=hr-system-db \
    --password=YOUR_USER_PASSWORD
```

#### 3. Store Secrets
```bash
echo -n "sk-your-openai-key" | gcloud secrets create OPENAI_API_KEY --data-file=-

echo -n "postgresql://hr_user:YOUR_USER_PASSWORD@/hr_system?host=/cloudsql/YOUR_PROJECT:us-central1:hr-system-db" \
    | gcloud secrets create DATABASE_URL --data-file=-
```

#### 4. Build & Push
```bash
gcloud artifacts repositories create hr-system \
    --repository-format=docker --location=us-central1

gcloud builds submit \
    --tag us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-api:latest .
```

#### 5. Deploy FastAPI
```bash
gcloud run deploy hr-api \
    --image=us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-api:latest \
    --platform=managed --region=us-central1 \
    --allow-unauthenticated --port=8080 \
    --memory=1Gi --cpu=1 \
    --min-instances=0 --max-instances=5 \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest" \
    --add-cloudsql-instances=YOUR_PROJECT:us-central1:hr-system-db \
    --set-env-vars="LLM_MODEL=gpt-4o-mini,LLM_TEMPERATURE=0.1,AGENT_MAX_RETRIES=2"
```

#### 6. Deploy Streamlit
```bash
gcloud builds submit \
    --tag us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-dashboard:latest \
    -f Dockerfile.streamlit .

gcloud run deploy hr-dashboard \
    --image=us-central1-docker.pkg.dev/YOUR_PROJECT/hr-system/hr-dashboard:latest \
    --platform=managed --region=us-central1 \
    --allow-unauthenticated --port=8501 \
    --memory=512Mi \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest" \
    --add-cloudsql-instances=YOUR_PROJECT:us-central1:hr-system-db
```

#### 7. Custom Domain (Optional)
```bash
gcloud run domain-mappings create \
    --service=hr-api --domain=api.yourdomain.com --region=us-central1
```

#### GCP Cost Estimate

| Service | Spec | Est. Cost/mo |
|---|---|---|
| Cloud Run (API) | 1 vCPU, 1GB RAM, ~100 hrs | ~$5–15 |
| Cloud Run (Dashboard) | 1 vCPU, 512MB RAM | ~$3–8 |
| Cloud SQL (PostgreSQL) | db-f1-micro | ~$9 |
| Secret Manager | 3 secrets | ~$0.06 |
| Artifact Registry | <1GB | ~$0.10 |
| **Total** | | **~$17–33** |

---

## 17. Deployment Guide — AWS

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

### Step-by-Step

#### 1. Prerequisites
```bash
aws configure
# Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, region
```

#### 2. VPC & Networking
```bash
aws ec2 create-vpc --cidr-block 10.0.0.0/16 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=hr-system-vpc}]'

aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 \
    --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 \
    --availability-zone us-east-1b

aws ec2 create-security-group --group-name hr-system-sg \
    --description "HR System" --vpc-id vpc-xxx
```

#### 3. Create RDS PostgreSQL
```bash
aws rds create-db-subnet-group \
    --db-subnet-group-name hr-system-subnets \
    --db-subnet-group-description "HR System subnets" \
    --subnet-ids subnet-xxx1 subnet-xxx2

aws rds create-db-instance \
    --db-instance-identifier hr-system-db \
    --db-instance-class db.t3.micro \
    --engine postgres --engine-version 15.4 \
    --master-username hr_admin --master-user-password YOUR_DB_PASSWORD \
    --allocated-storage 20 --db-name hr_system \
    --vpc-security-group-ids sg-xxx \
    --db-subnet-group-name hr-system-subnets \
    --no-publicly-accessible
```

#### 4. Store Secrets
```bash
aws secretsmanager create-secret \
    --name hr-system/openai-api-key --secret-string "sk-your-openai-key"

aws secretsmanager create-secret \
    --name hr-system/database-url \
    --secret-string "postgresql://hr_admin:YOUR_DB_PASSWORD@hr-system-db.xxx.us-east-1.rds.amazonaws.com:5432/hr_system"
```

#### 5. ECR & Push
```bash
aws ecr create-repository --repository-name hr-system-api

aws ecr get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t hr-system-api .
docker tag hr-system-api:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-api:latest
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-api:latest
```

#### 6. ECS Cluster & Service

**Task Definition (`task-definition.json`):**
```json
{
  "family": "hr-system-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::YOUR_ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "hr-api",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/hr-system-api:latest",
      "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
      "environment": [
        {"name": "LLM_MODEL", "value": "gpt-4o-mini"},
        {"name": "LLM_TEMPERATURE", "value": "0.1"},
        {"name": "AGENT_MAX_RETRIES", "value": "2"}
      ],
      "secrets": [
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:hr-system/openai-api-key"},
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT:secret:hr-system/database-url"}
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
aws ecs register-task-definition --cli-input-json file://task-definition.json
aws ecs create-cluster --cluster-name hr-system-cluster

aws ecs create-service \
    --cluster hr-system-cluster \
    --service-name hr-api-service \
    --task-definition hr-system-api:1 \
    --desired-count 2 --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx1,subnet-xxx2],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### 7. Application Load Balancer
```bash
aws elbv2 create-load-balancer --name hr-system-alb \
    --subnets subnet-xxx1 subnet-xxx2 --security-groups sg-xxx

aws elbv2 create-target-group --name hr-api-tg \
    --protocol HTTP --port 8080 --vpc-id vpc-xxx \
    --target-type ip --health-check-path /health

aws elbv2 create-listener --load-balancer-arn arn:aws:elasticloadbalancing:... \
    --protocol HTTP --port 80 \
    --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

#### AWS Cost Estimate

| Service | Spec | Est. Cost/mo |
|---|---|---|
| ECS Fargate (API) | 0.5 vCPU, 1GB RAM, 2 tasks | ~$15–25 |
| ECS Fargate (Dashboard) | 0.25 vCPU, 512MB RAM | ~$8–12 |
| RDS PostgreSQL | db.t3.micro, 20GB | ~$15 |
| ALB | Standard | ~$16 |
| ECR | <1GB | ~$0.10 |
| Secrets Manager | 2 secrets | ~$0.80 |
| CloudWatch Logs | Basic | ~$1–3 |
| **Total** | | **~$56–73** |

---

## 18. Deployment Guide — Azure

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

### Step-by-Step

#### 1. Prerequisites
```bash
az login
az account set --subscription YOUR_SUBSCRIPTION_ID
```

#### 2. Resource Group
```bash
az group create --name hr-system-rg --location eastus
```

#### 3. Azure Database for PostgreSQL
```bash
az postgres flexible-server create \
    --resource-group hr-system-rg --name hr-system-db \
    --location eastus --admin-user hr_admin \
    --admin-password YOUR_DB_PASSWORD \
    --sku-name Standard_B1ms --tier Burstable \
    --storage-size 32 --version 15 --yes

az postgres flexible-server db create \
    --resource-group hr-system-rg --server-name hr-system-db \
    --database-name hr_system

az postgres flexible-server firewall-rule create \
    --resource-group hr-system-rg --name hr-system-db \
    --rule-name AllowAzureServices \
    --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
```

#### 4. Azure Key Vault
```bash
az keyvault create --resource-group hr-system-rg \
    --name hr-system-kv --location eastus

az keyvault secret set --vault-name hr-system-kv \
    --name openai-api-key --value "sk-your-openai-key"

az keyvault secret set --vault-name hr-system-kv \
    --name database-url \
    --value "postgresql://hr_admin:YOUR_DB_PASSWORD@hr-system-db.postgres.database.azure.com:5432/hr_system?sslmode=require"
```

#### 5. Azure Container Registry (ACR)
```bash
az acr create --resource-group hr-system-rg --name hrsystemacr --sku Basic
az acr login --name hrsystemacr

az acr build --registry hrsystemacr --image hr-api:latest --file Dockerfile .
az acr build --registry hrsystemacr --image hr-dashboard:latest --file Dockerfile.streamlit .
```

#### 6. Container Apps Environment
```bash
az extension add --name containerapp --upgrade

az containerapp env create \
    --resource-group hr-system-rg --name hr-system-env --location eastus
```

#### 7. Deploy FastAPI
```bash
az containerapp create \
    --resource-group hr-system-rg --name hr-api \
    --environment hr-system-env \
    --image hrsystemacr.azurecr.io/hr-api:latest \
    --registry-server hrsystemacr.azurecr.io \
    --target-port 8080 --ingress external \
    --min-replicas 0 --max-replicas 5 \
    --cpu 0.5 --memory 1.0Gi \
    --env-vars "LLM_MODEL=gpt-4o-mini" "LLM_TEMPERATURE=0.1" "AGENT_MAX_RETRIES=2"
```

#### 8. Deploy Streamlit
```bash
az containerapp create \
    --resource-group hr-system-rg --name hr-dashboard \
    --environment hr-system-env \
    --image hrsystemacr.azurecr.io/hr-dashboard:latest \
    --registry-server hrsystemacr.azurecr.io \
    --target-port 8501 --ingress external \
    --min-replicas 0 --max-replicas 3 \
    --cpu 0.25 --memory 0.5Gi
```

#### 9. Monitoring
```bash
az monitor app-insights component create \
    --app hr-system-insights --location eastus --resource-group hr-system-rg

az containerapp logs show \
    --resource-group hr-system-rg --name hr-api --follow
```

#### Azure Cost Estimate

| Service | Spec | Est. Cost/mo |
|---|---|---|
| Container Apps (API) | 0.5 vCPU, 1GB RAM | ~$10–20 |
| Container Apps (Dashboard) | 0.25 vCPU, 512MB RAM | ~$5–10 |
| Azure Database for PostgreSQL | Burstable B1ms, 32GB | ~$13 |
| Azure Key Vault | 3 secrets | ~$0.03 |
| Container Registry | Basic tier | ~$5 |
| Application Insights | Basic | ~$2–5 |
| **Total** | | **~$35–53** |

---

## 19. Cloud Deployment Comparison

| Feature | GCP (Cloud Run) | AWS (ECS Fargate) | Azure (Container Apps) |
|---|---|---|---|
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

## 20. Production Readiness Checklist

- [ ] Replace SQLite with PostgreSQL (update `DATABASE_URL`)
- [ ] Set `OPENAI_API_KEY` securely (never in code or `.env` in prod)
- [ ] Restrict CORS origins (replace `allow_origins=["*"]`)
- [ ] Add authentication to FastAPI endpoints (OAuth2 / API keys)
- [ ] Add HTTPS (TLS termination at load balancer)
- [ ] Persist pipeline runs to DB (currently in-memory `_pipeline_runs` dict)
- [ ] Enforce `AGENT_TIMEOUT_SECONDS` (currently config-only, not enforced in code)
- [ ] Set up log aggregation (Cloud Logging / CloudWatch / Azure Monitor)
- [ ] Configure alerting for pipeline failures
- [ ] Set up CI/CD pipeline (GitHub Actions / Cloud Build / CodePipeline)
- [ ] Pin dependency versions in `requirements.txt` (currently uses `>=` ranges)
- [ ] Add health check endpoints for container orchestrators (✅ `/health` exists)
- [ ] Set proper resource limits (CPU/memory) based on load testing
- [ ] Enable auto-scaling based on request volume
- [ ] Add rate limiting to API endpoints
- [ ] Implement proper DB connection pooling for PostgreSQL

---

## 21. Environment Variable Reference

Complete list of environment variables recognized by the system (see [`.env.example`](.env.example)):

| Variable | Default | Used In | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | *(required)* | `settings.py` | OpenAI API key for LLM inference |
| `LLM_MODEL` | `gpt-4o-mini` | `settings.py` | Model name for all agents + supervisor |
| `LLM_TEMPERATURE` | `0.1` | `settings.py` | Default temperature for agent LLM calls (feedback agent overrides to 0.3; supervisor uses 0) |
| `DATABASE_URL` | `sqlite:///./hr_system.db` | `settings.py` | SQLAlchemy database URL |
| `API_HOST` | `0.0.0.0` | `settings.py` | FastAPI server bind address |
| `API_PORT` | `8000` | `settings.py` | FastAPI server port |
| `RESUME_SHORTLIST_THRESHOLD` | `60` | `settings.py` | Minimum screening score (0–100) to auto-shortlist |
| `MAX_INTERVIEWS_PER_CANDIDATE` | `3` | `settings.py` | Maximum interviews scheduled per candidate |
| `AGENT_RECURSION_LIMIT` | `25` | `settings.py` | Max LLM ↔ tool loops per agent sub-graph |
| `AGENT_TIMEOUT_SECONDS` | `120` | `settings.py` | Max wall-clock time per agent (config only — not enforced) |
| `AGENT_MAX_RETRIES` | `2` | `settings.py` | Retries before supervisor skips a failed stage |
| `LOG_LEVEL` | `INFO` | `logging_config.py` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

---

*Generated from exhaustive source-code analysis of the HR Multi-Agent Recruitment System v3.0 — 2026-07-12*
