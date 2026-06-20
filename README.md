# 🏢 HR Multi-Agent Recruitment System

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-purple)
![FastAPI](https://img.shields.io/badge/FastAPI-REST%20API-green)

An automated HR recruitment pipeline powered by **LangGraph** multi-agent architecture. Each stage of the hiring process is handled by a dedicated AI agent, orchestrated by a central Supervisor.

## Architecture

```
Supervisor → Job Posting → Resume Screening → Interview Scheduling
          → Feedback Collection → Candidate Ranking → Final Selection
```

## Agents

| Agent | Role |
|-------|------|
| 🎯 **Supervisor** | Orchestrates the pipeline, routes tasks to worker agents |
| 📋 **Job Posting** | Generates and manages job descriptions |
| 📄 **Resume Selection** | Screens resumes against job requirements |
| 📅 **Interview Scheduling** | Schedules interviews for shortlisted candidates |
| 💬 **Feedback Collection** | Collects and structures interviewer feedback |
| 🏆 **Candidate Ranking** | Ranks candidates using composite scoring |
| ✅ **Final Selection** | Makes hire/reject decisions |

## Key Features

- **Retry & resilience** — Supervisor auto-retries failed stages (configurable, default 2 retries) before skipping
- **Recursion limits** — Each agent sub-graph has a configurable recursion limit (default 25) to prevent runaway loops
- **Async pipeline API** — `POST /pipeline/start` returns a `run_id` immediately; poll status via `/pipeline/status/{run_id}`
- **Per-stage observability** — Stage timing, tool-call counts, and success/failure tracked automatically
- **Enhanced dashboard** — Pipeline progress bar, candidate comparison charts, CSV export

## Project Structure

```
hr-multi-agent-system/
├── main.py                  # CLI entry point (run, api, ui, init, reset)
├── requirements.txt
├── .env.example
│
├── agents/                  # LangGraph agent sub-graphs
│   ├── job_posting_agent.py
│   ├── resume_selection_agent.py
│   ├── interview_scheduling_agent.py
│   ├── feedback_agent.py
│   ├── ranking_agent.py
│   └── final_selection_agent.py
│
├── graph/                   # Pipeline orchestration
│   ├── pipeline.py          # StateGraph assembly
│   └── supervisor.py        # Supervisor routing + retry logic
│
├── tools/                   # LangChain tools (DB operations)
│   ├── job_tools.py
│   ├── resume_tools.py
│   ├── scheduling_tools.py
│   ├── feedback_tools.py
│   ├── ranking_tools.py
│   └── selection_tools.py
│
├── state/
│   └── hr_state.py          # Shared HRState TypedDict
│
├── config/
│   ├── settings.py          # Environment-based configuration
│   ├── logging_config.py    # Centralized logging
│   └── metrics.py           # StageTimer & observability utilities
│
├── database/
│   ├── db.py                # SQLAlchemy engine & session management
│   └── models.py            # ORM models (7 tables)
│
├── api/
│   ├── server.py            # FastAPI REST server (async pipeline)
│   └── schemas.py           # Pydantic request/response models
│
└── ui/
    └── dashboard.py         # Streamlit dashboard (enhanced)
```

## Quick Start

### 1. Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### 2. Run

```bash
# Full pipeline demo
python main.py run

# FastAPI server
python main.py api

# Streamlit dashboard
python main.py ui

# Initialize database only
python main.py init

# Reset database (drop + recreate)
python main.py reset

# Verbose mode (DEBUG logging)
python main.py run --verbose
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/pipeline/start` | Start a pipeline (async, returns run_id) |
| `GET` | `/pipeline/status/{run_id}` | Check pipeline run status |
| `GET` | `/pipeline/metrics/{run_id}` | Per-stage metrics for a run |
| `GET` | `/pipeline/runs` | List all pipeline runs |
| `GET` | `/pipeline/summary/{job_id}` | DB-based summary for a job |
| `GET` | `/jobs` | List all job postings |
| `GET` | `/jobs/{job_id}` | Get a specific job posting |
| `GET` | `/candidates` | List all candidates |
| `POST` | `/candidates` | Add a new candidate |
| `GET` | `/interviews` | List all interviews |
| `GET` | `/feedback` | List all feedback |
| `POST` | `/feedback` | Submit interviewer feedback |
| `GET` | `/rankings` | List candidate rankings |
| `GET` | `/decisions` | List hiring decisions |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required. Your OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model to use |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature |
| `DATABASE_URL` | `sqlite:///./hr_system.db` | Database connection string |
| `RESUME_SHORTLIST_THRESHOLD` | `60` | Minimum score to shortlist (0–100) |
| `AGENT_RECURSION_LIMIT` | `25` | Max LLM↔tool loops per agent |
| `AGENT_TIMEOUT_SECONDS` | `120` | Max wall-clock time per agent |
| `AGENT_MAX_RETRIES` | `2` | Retries before skipping a failed stage |

## Tech Stack

- **LangGraph** — Agent orchestration & state management
- **LangChain + OpenAI** — LLM integration
- **FastAPI** — REST API
- **Streamlit** — Dashboard UI
- **SQLAlchemy + SQLite** — Data persistence

## Roadmap

- [ ] Implement A2A (Agent-to-Agent) protocol
- [ ] Make each agent an independent service
- [ ] Support one-ask to multiple-agent flows
- [x] ~~Evaluation framework — step-level metrics~~ (v2.0)
- [ ] Automated production monitoring & alerting
- [ ] Persistent pipeline run storage (currently in-memory)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request