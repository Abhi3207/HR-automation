"""
Tools for the Feedback Collection Agent.
Handles collecting, validating, and summarizing interviewer feedback.
"""

from langchain_core.tools import tool
from database.db import get_session
from database.models import Feedback, Interview, Candidate


@tool
def submit_feedback(
    interview_id: int,
    interviewer_name: str,
    overall_rating: float,
    recommendation: str,
    technical_rating: int = 0,
    communication_rating: int = 0,
    culture_fit_rating: int = 0,
    strengths: str = "",
    weaknesses: str = "",
    detailed_notes: str = ""
) -> dict:
    """Submit feedback for a completed interview.

    Args:
        interview_id: The interview ID
        interviewer_name: Name of the interviewer
        overall_rating: Overall rating from 1.0 to 10.0
        recommendation: strong_hire, hire, maybe, or no_hire
        technical_rating: Technical skills rating (1-10, 0 if N/A)
        communication_rating: Communication rating (1-10, 0 if N/A)
        culture_fit_rating: Culture fit rating (1-10, 0 if N/A)
        strengths: Key strengths observed
        weaknesses: Areas of concern
        detailed_notes: Detailed feedback notes

    Returns:
        Created feedback dictionary
    """
    valid_recommendations = ["strong_hire", "hire", "maybe", "no_hire"]
    if recommendation not in valid_recommendations:
        return {"error": f"Invalid recommendation. Must be one of: {valid_recommendations}"}

    with get_session() as session:
        interview = session.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            return {"error": f"Interview {interview_id} not found"}

        # Check if feedback already exists
        existing = session.query(Feedback).filter(Feedback.interview_id == interview_id).first()
        if existing:
            return {"info": "Feedback already submitted for this interview", **existing.to_dict()}

        feedback = Feedback(
            interview_id=interview_id,
            interviewer_name=interviewer_name,
            overall_rating=max(1.0, min(10.0, overall_rating)),
            recommendation=recommendation,
            technical_rating=max(0, min(10, technical_rating)),
            communication_rating=max(0, min(10, communication_rating)),
            culture_fit_rating=max(0, min(10, culture_fit_rating)),
            strengths=strengths,
            weaknesses=weaknesses,
            detailed_notes=detailed_notes,
        )
        session.add(feedback)

        # Mark interview as completed
        interview.status = "completed"
        session.flush()
        return feedback.to_dict()


@tool
def get_feedback_for_candidate(candidate_id: int) -> list[dict]:
    """Get all feedback for a specific candidate across all interviews.

    Args:
        candidate_id: The candidate's ID

    Returns:
        List of feedback dictionaries
    """
    with get_session() as session:
        interviews = session.query(Interview).filter(
            Interview.candidate_id == candidate_id
        ).all()

        results = []
        for interview in interviews:
            if interview.feedback:
                data = interview.feedback.to_dict()
                data["interview_type"] = interview.interview_type
                results.append(data)
        return results


@tool
def get_pending_feedback() -> list[dict]:
    """Get all interviews that are scheduled but don't have feedback yet.

    Returns:
        List of interview dictionaries awaiting feedback
    """
    with get_session() as session:
        interviews = session.query(Interview).filter(
            Interview.status == "scheduled"
        ).all()

        pending = []
        for interview in interviews:
            if not interview.feedback:
                data = interview.to_dict()
                pending.append(data)
        return pending


@tool
def get_all_feedback_summary() -> list[dict]:
    """Get a summary of all submitted feedback.

    Returns:
        List of feedback summaries grouped by candidate
    """
    with get_session() as session:
        all_feedback = session.query(Feedback).all()
        summaries = []
        for fb in all_feedback:
            interview = fb.interview
            candidate = interview.candidate if interview else None
            summaries.append({
                "candidate_name": candidate.name if candidate else "Unknown",
                "candidate_id": interview.candidate_id if interview else None,
                "interview_type": interview.interview_type if interview else None,
                "overall_rating": fb.overall_rating,
                "recommendation": fb.recommendation,
                "strengths": fb.strengths,
                "weaknesses": fb.weaknesses,
            })
        return summaries


FEEDBACK_TOOLS = [submit_feedback, get_feedback_for_candidate, get_pending_feedback, get_all_feedback_summary]
