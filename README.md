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
│   └── supervisor.py        # Supervisor routing logic
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
│   └── logging_config.py    # Centralized logging
│
├── database/
│   ├── db.py                # SQLAlchemy engine & session management
│   └── models.py            # ORM models (7 tables)
│
├── api/
│   └── server.py            # FastAPI REST server
│
└── ui/
    └── dashboard.py         # Streamlit dashboard
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
| `POST` | `/pipeline/start` | Start a full hiring pipeline |
| `GET` | `/pipeline/summary/{job_id}` | Pipeline summary for a job |
| `GET` | `/jobs` | List all job postings |
| `GET` | `/jobs/{job_id}` | Get a specific job posting |
| `GET` | `/candidates` | List all candidates |
| `POST` | `/candidates` | Add a new candidate |
| `GET` | `/interviews` | List all interviews |
| `GET` | `/feedback` | List all feedback |
| `POST` | `/feedback` | Submit interviewer feedback |
| `GET` | `/rankings` | List candidate rankings |
| `GET` | `/decisions` | List hiring decisions |

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
- [ ] **Major:** Evaluation framework — step-level metrics, automated production monitoring

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request