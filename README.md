# 🏢 HR Multi-Agent Recruitment System

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

## Quick Start

### 1. Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

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
```

## Tech Stack

- **LangGraph** — Agent orchestration & state management
- **LangChain + OpenAI** — LLM integration
- **FastAPI** — REST API
- **Streamlit** — Dashboard UI
- **SQLAlchemy + SQLite** — Data persistence


Next Plans:

    implement a2a
    make each agent independent service
    one ask to multiple agent flows

    major: evaluation, at what steps and how to automate and maintain it in production