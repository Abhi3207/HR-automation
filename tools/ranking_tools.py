"""
Tools for the Candidate Ranking Agent.
Handles computing composite scores and ranking candidates.
"""

from langchain_core.tools import tool
from database.db import get_session
from database.models import Ranking, Application, Feedback, Interview, Candidate


@tool
def calculate_composite_score(
    application_id: int,
    resume_weight: float = 0.3,
    interview_weight: float = 0.7
) -> dict:
    """Calculate a composite score for a candidate's application.

    Combines resume screening score and interview feedback into a weighted score.

    Args:
        application_id: The application ID
        resume_weight: Weight for resume score (0.0 to 1.0)
        interview_weight: Weight for interview score (0.0 to 1.0)

    Returns:
        Score breakdown dictionary
    """
    with get_session() as session:
        app = session.query(Application).filter(Application.id == application_id).first()
        if not app:
            return {"error": f"Application {application_id} not found"}

        # Get resume score (normalized to 0-10 scale)
        resume_score = (app.screening_score or 0) / 10.0

        # Get interview feedback scores
        interviews = session.query(Interview).filter(
            Interview.candidate_id == app.candidate_id
        ).all()

        interview_ratings = []
        feedback_details = []
        for interview in interviews:
            if interview.feedback:
                interview_ratings.append(interview.feedback.overall_rating)
                feedback_details.append({
                    "type": interview.interview_type,
                    "rating": interview.feedback.overall_rating,
                    "recommendation": interview.feedback.recommendation,
                })

        interview_score = sum(interview_ratings) / len(interview_ratings) if interview_ratings else 0

        # Calculate composite
        composite = (resume_score * resume_weight) + (interview_score * interview_weight)

        # Determine recommendation counts
        rec_counts = {}
        for fb in feedback_details:
            rec = fb["recommendation"]
            rec_counts[rec] = rec_counts.get(rec, 0) + 1

        return {
            "application_id": application_id,
            "candidate_id": app.candidate_id,
            "resume_score": round(resume_score, 2),
            "interview_score": round(interview_score, 2),
            "composite_score": round(composite, 2),
            "num_interviews": len(interview_ratings),
            "feedback_details": feedback_details,
            "recommendation_counts": rec_counts,
        }


@tool
def save_ranking(
    application_id: int,
    resume_score: float,
    interview_score: float,
    overall_score: float,
    rank: int,
    analysis: str = "",
    score_breakdown: dict = None
) -> dict:
    """Save a ranking entry for an application.

    Args:
        application_id: The application ID
        resume_score: Resume screening score (0-10)
        interview_score: Average interview score (0-10)
        overall_score: Composite overall score (0-10)
        rank: Rank position (1 = best)
        analysis: LLM-generated analysis text
        score_breakdown: Detailed scoring breakdown

    Returns:
        Created ranking dictionary
    """
    with get_session() as session:
        ranking = Ranking(
            application_id=application_id,
            resume_score=resume_score,
            interview_score=interview_score,
            overall_score=overall_score,
            rank=rank,
            analysis=analysis,
            score_breakdown=score_breakdown or {},
        )
        session.add(ranking)

        # Update candidate status
        app = session.query(Application).filter(Application.id == application_id).first()
        if app:
            candidate = session.query(Candidate).filter(Candidate.id == app.candidate_id).first()
            if candidate:
                candidate.status = "ranked"

        session.flush()
        return ranking.to_dict()


@tool
def get_rankings(job_posting_id: int = 0) -> list[dict]:
    """Get all rankings, optionally filtered by job posting.

    Args:
        job_posting_id: Filter by job posting ID (0 for all)

    Returns:
        List of ranking dictionaries sorted by rank
    """
    with get_session() as session:
        query = session.query(Ranking)
        if job_posting_id > 0:
            query = query.join(Application).filter(
                Application.job_posting_id == job_posting_id
            )
        rankings = query.order_by(Ranking.rank).all()

        results = []
        for r in rankings:
            data = r.to_dict()
            app = r.application
            if app and app.candidate:
                data["candidate_name"] = app.candidate.name
                data["candidate_id"] = app.candidate_id
            results.append(data)
        return results


RANKING_TOOLS = [calculate_composite_score, save_ranking, get_rankings]
