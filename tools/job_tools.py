"""
Tools for the Job Posting Agent.
Handles creating, updating, and managing job postings.
"""

from langchain_core.tools import tool
from database.db import get_session
from database.models import JobPosting


@tool
def create_job_posting(
    title: str,
    description: str,
    requirements: str,
    department: str = "Engineering",
    salary_range: str = "Competitive",
    location: str = "Remote",
    employment_type: str = "Full-time",
    preferred_qualifications: str = ""
) -> dict:
    """Create a new job posting in the database.

    Args:
        title: Job title (e.g., "Senior Software Engineer")
        description: Full job description
        requirements: Required qualifications (comma or newline separated)
        department: Department name
        salary_range: Salary range (e.g., "$120k-$160k")
        location: Work location
        employment_type: Full-time, Part-time, Contract
        preferred_qualifications: Nice-to-have qualifications

    Returns:
        Dictionary with the created job posting details
    """
    with get_session() as session:
        posting = JobPosting(
            title=title,
            description=description,
            requirements=requirements,
            department=department,
            salary_range=salary_range,
            location=location,
            employment_type=employment_type,
            preferred_qualifications=preferred_qualifications,
            status="open",
        )
        session.add(posting)
        session.flush()
        result = posting.to_dict()
    return result


@tool
def list_job_postings(status: str = "open") -> list[dict]:
    """List all job postings, optionally filtered by status.

    Args:
        status: Filter by status (open, closed, filled, or 'all')

    Returns:
        List of job posting dictionaries
    """
    with get_session() as session:
        query = session.query(JobPosting)
        if status != "all":
            query = query.filter(JobPosting.status == status)
        postings = query.all()
        return [p.to_dict() for p in postings]


@tool
def get_job_posting(job_id: int) -> dict:
    """Get a specific job posting by ID.

    Args:
        job_id: The job posting ID

    Returns:
        Job posting dictionary or error message
    """
    with get_session() as session:
        posting = session.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not posting:
            return {"error": f"Job posting {job_id} not found"}
        return posting.to_dict()


@tool
def update_job_posting(job_id: int, status: str) -> dict:
    """Update the status of a job posting.

    Args:
        job_id: The job posting ID
        status: New status (open, closed, filled)

    Returns:
        Updated job posting dictionary
    """
    with get_session() as session:
        posting = session.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not posting:
            return {"error": f"Job posting {job_id} not found"}
        posting.status = status
        session.flush()
        return posting.to_dict()


# Export all tools for this agent
JOB_TOOLS = [create_job_posting, list_job_postings, get_job_posting, update_job_posting]
