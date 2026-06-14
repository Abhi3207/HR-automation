"""
Pydantic request/response schemas for the HR API.

Centralises all API models so server.py stays focused on routing logic.
"""

from pydantic import BaseModel, Field
from typing import Optional


# --- Request Models ---

class PipelineStartRequest(BaseModel):
    """Request body for POST /pipeline/start."""
    job_title: str = Field(..., description="Title of the job to hire for")
    department: str = Field(default="Engineering")
    requirements: str = Field(..., description="Job requirements")
    candidates: list[dict] = Field(
        default=[],
        description="List of candidate dicts with name, email, resume_text, skills, etc.",
    )


class CandidateInput(BaseModel):
    """Request body for POST /candidates."""
    name: str
    email: str
    resume_text: str
    phone: str = ""
    skills: str = ""
    experience_years: int = 0
    education: str = ""


class FeedbackInput(BaseModel):
    """Request body for POST /feedback."""
    interview_id: int
    interviewer_name: str
    overall_rating: float
    recommendation: str
    technical_rating: int = 0
    communication_rating: int = 0
    culture_fit_rating: int = 0
    strengths: str = ""
    weaknesses: str = ""


# --- Response Models ---

class PipelineRunResponse(BaseModel):
    """Response for POST /pipeline/start (async mode)."""
    run_id: str
    status: str = "started"
    message: str = "Pipeline started in background"


class PipelineStatusResponse(BaseModel):
    """Response for GET /pipeline/status/{run_id}."""
    run_id: str
    status: str                     # started, running, completed, error
    current_stage: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    total_messages: Optional[int] = None
    stage_metrics: Optional[list[dict]] = None
