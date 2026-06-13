"""
FastAPI server for the HR Multi-Agent System.

Provides REST endpoints to interact with the pipeline,
manage job postings, candidates, and view results.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn

from config.logging_config import get_logger
from database.db import init_db, get_session
from database.models import (
    JobPosting, Candidate, Application, Interview,
    Feedback, Ranking, Offer
)

logger = get_logger(__name__)


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
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class PipelineStartRequest(BaseModel):
    job_title: str = Field(..., description="Title of the job to hire for")
    department: str = Field(default="Engineering")
    requirements: str = Field(..., description="Job requirements")
    candidates: list[dict] = Field(default=[], description="List of candidate dicts with name, email, resume_text")


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


# --- Health Check ---

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# --- Pipeline Endpoints ---

@app.post("/pipeline/start", tags=["Pipeline"])
async def start_pipeline(request: PipelineStartRequest):
    """Start a new hiring pipeline. Runs all 6 agents sequentially."""
    from langchain_core.messages import HumanMessage
    from graph.pipeline import build_pipeline

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
            "job_posting_id": None,
            "job_posting": None,
            "candidates": request.candidates,
            "shortlisted_candidates": [],
            "scheduled_interviews": [],
            "interview_feedback": [],
            "candidate_rankings": [],
            "final_decisions": [],
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

        return {
            "status": "completed",
            "pipeline_status": result.get("pipeline_status", "completed"),
            "current_stage": result.get("current_stage", "complete"),
            "message": "Pipeline completed successfully!",
            "total_messages": len(result.get("messages", [])),
        }

    except Exception as e:
        logger.error("Pipeline failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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


# --- Pipeline Summary ---

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


def run_server():
    """Start the FastAPI server."""
    from config.settings import settings
    uvicorn.run(
        "api.server:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


if __name__ == "__main__":
    run_server()
