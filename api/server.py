"""
FastAPI server for the HR Multi-Agent System.

Provides REST endpoints to interact with the pipeline,
manage job postings, candidates, and view results.

Pipeline execution is asynchronous — a POST to /pipeline/start
returns a run_id immediately, and the caller can poll status
via GET /pipeline/status/{run_id}.
"""

import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config.logging_config import get_logger
from config.settings import settings
from database.db import init_db, get_session
from database.models import (
    JobPosting, Candidate, Application, Interview,
    Feedback, Ranking, Offer
)
from api.schemas import (
    PipelineStartRequest, CandidateInput, FeedbackInput,
    PipelineRunResponse, PipelineStatusResponse,
)

logger = get_logger(__name__)

# --- In-memory pipeline run tracker ---
# {run_id: {status, current_stage, started_at, completed_at, error, total_messages, stage_metrics}}
_pipeline_runs: dict[str, dict] = {}
_runs_lock = threading.Lock()


# --- Lifespan (replaces deprecated @app.on_event) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs startup logic before yield, shutdown after."""
    init_db()
    logger.info("FastAPI server started — database initialized")
    yield
    logger.info("FastAPI server shutting down")


app = FastAPI(
    title="HR Multi-Agent Recruitment System",
    description="Automated HR recruitment pipeline powered by LangGraph agents",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pipeline background runner ---

def _run_pipeline_background(run_id: str, request: PipelineStartRequest):
    """Execute the full pipeline in a background thread."""
    from langchain_core.messages import HumanMessage
    from graph.pipeline import build_pipeline

    with _runs_lock:
        _pipeline_runs[run_id]["status"] = "running"

    try:
        pipeline = build_pipeline()

        # Build initial prompt
        candidate_info = ""
        if request.candidates:
            candidate_info = "\n\nCandidates to evaluate:\n"
            for c in request.candidates:
                candidate_info += f"- {c.get('name', 'Unknown')}: {c.get('resume_text', '')[:200]}...\n"

        initial_state = {
            "messages": [
                HumanMessage(content=f"""
Start the HR recruitment pipeline for the following position:

Job Title: {request.job_title}
Department: {request.department}
Requirements: {request.requirements}
{candidate_info}

Please proceed through all stages of the pipeline:
1. Create the job posting
2. Screen resumes and shortlist candidates
3. Schedule interviews
4. Collect interviewer feedback
5. Rank candidates
6. Make final selections
""")
            ],
            "current_stage": "start",
            "next_agent": "",
            "pipeline_status": "running",
            "error_message": None,
            "retry_count": 0,
            "max_retries": settings.AGENT_MAX_RETRIES,
            "failed_stages": [],
            "job_posting_id": None,
            "job_posting": None,
            "candidates": request.candidates,
            "shortlisted_candidates": [],
            "scheduled_interviews": [],
            "interview_feedback": [],
            "candidate_rankings": [],
            "final_decisions": [],
            "stage_metrics": [],
        }

        # Add candidates to DB first
        if request.candidates:
            with get_session() as session:
                for c_data in request.candidates:
                    existing = session.query(Candidate).filter(
                        Candidate.email == c_data.get("email", "")
                    ).first()
                    if not existing:
                        candidate = Candidate(
                            name=c_data.get("name", "Unknown"),
                            email=c_data.get("email", "unknown@email.com"),
                            resume_text=c_data.get("resume_text", ""),
                            skills=c_data.get("skills", ""),
                            experience_years=c_data.get("experience_years", 0),
                            education=c_data.get("education", ""),
                        )
                        session.add(candidate)

        # Run the pipeline
        result = pipeline.invoke(initial_state)

        with _runs_lock:
            _pipeline_runs[run_id].update({
                "status": result.get("pipeline_status", "completed"),
                "current_stage": result.get("current_stage", "complete"),
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "total_messages": len(result.get("messages", [])),
                "stage_metrics": result.get("stage_metrics", []),
                "failed_stages": result.get("failed_stages", []),
            })

        logger.info("Pipeline run %s completed successfully", run_id)

    except Exception as e:
        logger.error("Pipeline run %s failed: %s", run_id, e, exc_info=True)
        with _runs_lock:
            _pipeline_runs[run_id].update({
                "status": "error",
                "error": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })


# --- Health Check ---

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


# --- Pipeline Endpoints ---

@app.post("/pipeline/start", tags=["Pipeline"], response_model=PipelineRunResponse)
async def start_pipeline(request: PipelineStartRequest, background_tasks: BackgroundTasks):
    """Start a new hiring pipeline asynchronously.

    Returns a run_id immediately. Poll GET /pipeline/status/{run_id} for progress.
    """
    run_id = str(uuid.uuid4())[:8]

    with _runs_lock:
        _pipeline_runs[run_id] = {
            "status": "started",
            "current_stage": "start",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "error": None,
            "total_messages": 0,
            "stage_metrics": [],
            "failed_stages": [],
        }

    background_tasks.add_task(_run_pipeline_background, run_id, request)

    logger.info("Pipeline run %s queued", run_id)
    return PipelineRunResponse(
        run_id=run_id,
        status="started",
        message="Pipeline started in background. Poll /pipeline/status/{run_id} for progress.",
    )


@app.get("/pipeline/status/{run_id}", tags=["Pipeline"], response_model=PipelineStatusResponse)
async def pipeline_status(run_id: str):
    """Check the status of a pipeline run."""
    with _runs_lock:
        run = _pipeline_runs.get(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found")

    return PipelineStatusResponse(
        run_id=run_id,
        status=run["status"],
        current_stage=run.get("current_stage"),
        started_at=run.get("started_at"),
        completed_at=run.get("completed_at"),
        error=run.get("error"),
        total_messages=run.get("total_messages"),
        stage_metrics=run.get("stage_metrics"),
    )


@app.get("/pipeline/metrics/{run_id}", tags=["Pipeline"])
async def pipeline_metrics(run_id: str):
    """Get per-stage metrics for a pipeline run."""
    with _runs_lock:
        run = _pipeline_runs.get(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run '{run_id}' not found")

    return {
        "run_id": run_id,
        "status": run["status"],
        "stage_metrics": run.get("stage_metrics", []),
        "failed_stages": run.get("failed_stages", []),
    }


@app.get("/pipeline/runs", tags=["Pipeline"])
async def list_pipeline_runs():
    """List all pipeline runs (in-memory)."""
    with _runs_lock:
        return [
            {"run_id": rid, "status": data["status"], "started_at": data.get("started_at")}
            for rid, data in _pipeline_runs.items()
        ]


# --- Pipeline Summary (DB-based) ---

@app.get("/pipeline/summary/{job_id}", tags=["Pipeline"])
async def pipeline_summary(job_id: int):
    """Get a complete pipeline summary for a job posting."""
    with get_session() as session:
        job = session.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        total_apps = session.query(Application).filter(
            Application.job_posting_id == job_id
        ).count()

        shortlisted = session.query(Application).filter(
            Application.job_posting_id == job_id,
            Application.is_shortlisted.is_(True)
        ).count()

        interviews_count = session.query(Interview).join(
            Application, Interview.candidate_id == Application.candidate_id
        ).filter(Application.job_posting_id == job_id).count()

        offers = session.query(Offer).filter(
            Offer.job_posting_id == job_id, Offer.decision == "offer"
        ).count()

        return {
            "job": job.to_dict(),
            "total_applicants": total_apps,
            "shortlisted": shortlisted,
            "interviews_conducted": interviews_count,
            "offers_made": offers,
        }


# --- Job Posting Endpoints ---

@app.get("/jobs", tags=["Jobs"])
async def list_jobs():
    """List all job postings."""
    with get_session() as session:
        jobs = session.query(JobPosting).all()
        return [j.to_dict() for j in jobs]


@app.get("/jobs/{job_id}", tags=["Jobs"])
async def get_job(job_id: int):
    """Get a specific job posting."""
    with get_session() as session:
        job = session.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.to_dict()


# --- Candidate Endpoints ---

@app.get("/candidates", tags=["Candidates"])
async def list_candidates():
    """List all candidates."""
    with get_session() as session:
        candidates = session.query(Candidate).all()
        return [c.to_dict() for c in candidates]


@app.post("/candidates", tags=["Candidates"])
async def add_candidate(candidate: CandidateInput):
    """Add a new candidate."""
    with get_session() as session:
        c = Candidate(
            name=candidate.name,
            email=candidate.email,
            resume_text=candidate.resume_text,
            phone=candidate.phone,
            skills=candidate.skills,
            experience_years=candidate.experience_years,
            education=candidate.education,
        )
        session.add(c)
        session.flush()
        return c.to_dict()


# --- Interview Endpoints ---

@app.get("/interviews", tags=["Interviews"])
async def list_interviews():
    """List all interviews."""
    with get_session() as session:
        interviews = session.query(Interview).all()
        return [i.to_dict() for i in interviews]


# --- Feedback Endpoints ---

@app.get("/feedback", tags=["Feedback"])
async def list_feedback():
    """List all feedback."""
    with get_session() as session:
        all_fb = session.query(Feedback).all()
        return [f.to_dict() for f in all_fb]


@app.post("/feedback", tags=["Feedback"])
async def submit_feedback(fb: FeedbackInput):
    """Submit interviewer feedback."""
    with get_session() as session:
        feedback = Feedback(
            interview_id=fb.interview_id,
            interviewer_name=fb.interviewer_name,
            overall_rating=fb.overall_rating,
            recommendation=fb.recommendation,
            technical_rating=fb.technical_rating,
            communication_rating=fb.communication_rating,
            culture_fit_rating=fb.culture_fit_rating,
            strengths=fb.strengths,
            weaknesses=fb.weaknesses,
        )
        session.add(feedback)
        session.flush()
        return feedback.to_dict()


# --- Rankings Endpoints ---

@app.get("/rankings", tags=["Rankings"])
async def list_rankings():
    """List all candidate rankings."""
    with get_session() as session:
        rankings = session.query(Ranking).order_by(Ranking.rank).all()
        results = []
        for r in rankings:
            data = r.to_dict()
            if r.application and r.application.candidate:
                data["candidate_name"] = r.application.candidate.name
            results.append(data)
        return results


# --- Decisions Endpoints ---

@app.get("/decisions", tags=["Decisions"])
async def list_decisions():
    """List all hiring decisions."""
    with get_session() as session:
        offers = session.query(Offer).all()
        return [o.to_dict() for o in offers]


def run_server():
    """Start the FastAPI server."""
    uvicorn.run(
        "api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


if __name__ == "__main__":
    run_server()
