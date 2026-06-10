"""
Tools for the Final Selection Agent.
Handles making offer/reject decisions and generating summaries.
"""

from langchain_core.tools import tool
from database.db import get_session
from database.models import Offer, Candidate, JobPosting, Ranking, Application


@tool
def make_decision(
    candidate_id: int,
    job_posting_id: int,
    decision: str,
    justification: str,
    salary_offered: str = "",
    start_date: str = "",
) -> dict:
    """Record a hiring decision for a candidate.

    Args:
        candidate_id: The candidate's ID
        job_posting_id: The job posting ID
        decision: 'offer', 'reject', or 'waitlist'
        justification: Explanation for the decision
        salary_offered: Salary offered (if decision is 'offer')
        start_date: Proposed start date (YYYY-MM-DD format)

    Returns:
        Created offer/decision dictionary
    """
    valid_decisions = ["offer", "reject", "waitlist"]
    if decision not in valid_decisions:
        return {"error": f"Invalid decision. Must be one of: {valid_decisions}"}

    from datetime import datetime

    parsed_start = None
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            pass

    with get_session() as session:
        offer = Offer(
            candidate_id=candidate_id,
            job_posting_id=job_posting_id,
            decision=decision,
            justification=justification,
            salary_offered=salary_offered,
            start_date=parsed_start,
        )
        session.add(offer)

        # Update candidate status
        candidate = session.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            if decision == "offer":
                candidate.status = "selected"
            elif decision == "reject":
                candidate.status = "rejected"
            # waitlist keeps current status

        session.flush()
        return offer.to_dict()


@tool
def generate_offer_summary(candidate_id: int, job_posting_id: int) -> dict:
    """Generate a summary of all data for a candidate to aid in decision making.

    Args:
        candidate_id: The candidate's ID
        job_posting_id: The job posting ID

    Returns:
        Comprehensive summary of the candidate's journey
    """
    with get_session() as session:
        candidate = session.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return {"error": f"Candidate {candidate_id} not found"}

        job = session.query(JobPosting).filter(JobPosting.id == job_posting_id).first()

        # Get application & screening info
        app = session.query(Application).filter(
            Application.candidate_id == candidate_id,
            Application.job_posting_id == job_posting_id
        ).first()

        # Get ranking
        ranking = None
        if app:
            ranking = session.query(Ranking).filter(
                Ranking.application_id == app.id
            ).first()

        # Get all interview feedback
        from database.models import Interview, Feedback
        interviews = session.query(Interview).filter(
            Interview.candidate_id == candidate_id
        ).all()

        feedback_list = []
        for interview in interviews:
            if interview.feedback:
                feedback_list.append({
                    "type": interview.interview_type,
                    "interviewer": interview.interviewer_name,
                    "rating": interview.feedback.overall_rating,
                    "recommendation": interview.feedback.recommendation,
                    "strengths": interview.feedback.strengths,
                    "weaknesses": interview.feedback.weaknesses,
                })

        return {
            "candidate": candidate.to_dict(),
            "job_title": job.title if job else "Unknown",
            "screening_score": app.screening_score if app else None,
            "screening_notes": app.screening_notes if app else None,
            "ranking": ranking.to_dict() if ranking else None,
            "interview_feedback": feedback_list,
            "total_interviews": len(feedback_list),
        }


@tool
def get_all_decisions(job_posting_id: int = 0) -> list[dict]:
    """Get all hiring decisions, optionally filtered by job posting.

    Args:
        job_posting_id: Filter by job posting ID (0 for all)

    Returns:
        List of decision dictionaries
    """
    with get_session() as session:
        query = session.query(Offer)
        if job_posting_id > 0:
            query = query.filter(Offer.job_posting_id == job_posting_id)
        offers = query.all()
        return [o.to_dict() for o in offers]


@tool
def get_pipeline_summary(job_posting_id: int) -> dict:
    """Get a complete summary of the hiring pipeline for a job posting.

    Args:
        job_posting_id: The job posting ID

    Returns:
        Pipeline summary with counts at each stage
    """
    with get_session() as session:
        job = session.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
        if not job:
            return {"error": f"Job posting {job_posting_id} not found"}

        total_apps = session.query(Application).filter(
            Application.job_posting_id == job_posting_id
        ).count()

        shortlisted = session.query(Application).filter(
            Application.job_posting_id == job_posting_id,
            Application.is_shortlisted == True
        ).count()

        offers = session.query(Offer).filter(
            Offer.job_posting_id == job_posting_id,
            Offer.decision == "offer"
        ).count()

        rejections = session.query(Offer).filter(
            Offer.job_posting_id == job_posting_id,
            Offer.decision == "reject"
        ).count()

        return {
            "job_title": job.title,
            "total_applicants": total_apps,
            "shortlisted": shortlisted,
            "offers_made": offers,
            "rejections": rejections,
            "status": job.status,
        }


SELECTION_TOOLS = [make_decision, generate_offer_summary, get_all_decisions, get_pipeline_summary]
