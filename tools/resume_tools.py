"""
Tools for the Resume Selection Agent.
Handles resume screening, scoring, and shortlisting candidates.
"""

from langchain_core.tools import tool
from database.db import get_session
from database.models import Candidate, Application, JobPosting
from config.settings import settings


@tool
def add_candidate(
    name: str,
    email: str,
    resume_text: str,
    phone: str = "",
    skills: str = "",
    experience_years: int = 0,
    education: str = ""
) -> dict:
    """Add a new candidate to the system.

    Args:
        name: Candidate's full name
        email: Candidate's email address
        resume_text: Full resume text content
        phone: Phone number
        skills: Comma-separated list of skills
        experience_years: Years of experience
        education: Education background

    Returns:
        Created candidate dictionary
    """
    with get_session() as session:
        # Check if candidate already exists
        existing = session.query(Candidate).filter(Candidate.email == email).first()
        if existing:
            return {"info": f"Candidate {name} already exists", **existing.to_dict()}

        candidate = Candidate(
            name=name,
            email=email,
            resume_text=resume_text,
            phone=phone,
            skills=skills,
            experience_years=experience_years,
            education=education,
            status="applied",
        )
        session.add(candidate)
        session.flush()
        return candidate.to_dict()


@tool
def create_application(candidate_id: int, job_posting_id: int) -> dict:
    """Create an application linking a candidate to a job posting.

    Args:
        candidate_id: The candidate's ID
        job_posting_id: The job posting's ID

    Returns:
        Created application dictionary
    """
    with get_session() as session:
        application = Application(
            candidate_id=candidate_id,
            job_posting_id=job_posting_id,
        )
        session.add(application)
        session.flush()
        return application.to_dict()


@tool
def score_resume(application_id: int, score: float, notes: str) -> dict:
    """Record a screening score for an application.

    Args:
        application_id: The application ID
        score: Screening score from 0 to 100
        notes: Screening notes explaining the score

    Returns:
        Updated application dictionary
    """
    with get_session() as session:
        app = session.query(Application).filter(Application.id == application_id).first()
        if not app:
            return {"error": f"Application {application_id} not found"}
        app.screening_score = score
        app.screening_notes = notes
        app.is_shortlisted = score >= settings.RESUME_SHORTLIST_THRESHOLD
        if app.is_shortlisted:
            candidate = session.query(Candidate).filter(Candidate.id == app.candidate_id).first()
            if candidate:
                candidate.status = "shortlisted"
        session.flush()
        return app.to_dict()


@tool
def get_candidates_for_job(job_posting_id: int) -> list[dict]:
    """Get all candidates who applied for a specific job.

    Args:
        job_posting_id: The job posting ID

    Returns:
        List of application dictionaries with candidate info
    """
    with get_session() as session:
        apps = session.query(Application).filter(
            Application.job_posting_id == job_posting_id
        ).all()
        results = []
        for app in apps:
            data = app.to_dict()
            candidate = session.query(Candidate).filter(
                Candidate.id == app.candidate_id
            ).first()
            if candidate:
                data["resume_text"] = candidate.resume_text
                data["skills"] = candidate.skills
                data["experience_years"] = candidate.experience_years
            results.append(data)
        return results


@tool
def get_shortlisted_candidates(job_posting_id: int) -> list[dict]:
    """Get all shortlisted candidates for a job.

    Args:
        job_posting_id: The job posting ID

    Returns:
        List of shortlisted candidate dictionaries
    """
    with get_session() as session:
        apps = session.query(Application).filter(
            Application.job_posting_id == job_posting_id,
            Application.is_shortlisted == True
        ).all()
        results = []
        for app in apps:
            candidate = session.query(Candidate).filter(
                Candidate.id == app.candidate_id
            ).first()
            if candidate:
                results.append({
                    **candidate.to_dict(),
                    "application_id": app.id,
                    "screening_score": app.screening_score,
                })
        return results


@tool
def get_job_requirements(job_posting_id: int) -> dict:
    """Get the requirements for a specific job posting.

    Args:
        job_posting_id: The job posting ID

    Returns:
        Dictionary with job requirements
    """
    with get_session() as session:
        job = session.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
        if not job:
            return {"error": f"Job posting {job_posting_id} not found"}
        return {
            "title": job.title,
            "requirements": job.requirements,
            "preferred_qualifications": job.preferred_qualifications,
            "description": job.description,
        }


RESUME_TOOLS = [
    add_candidate, create_application, score_resume,
    get_candidates_for_job, get_shortlisted_candidates, get_job_requirements
]
