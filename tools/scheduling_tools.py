"""
Tools for the Interview Scheduling Agent.
Handles scheduling interviews and managing the calendar.
"""

from datetime import datetime, timedelta, timezone
from langchain_core.tools import tool
from database.db import get_session
from database.models import Interview, Candidate


@tool
def schedule_interview(
    candidate_id: int,
    interviewer_name: str,
    interview_type: str = "technical",
    scheduled_date: str = "",
    scheduled_time: str = "10:00",
    duration_minutes: int = 60,
    interviewer_email: str = "",
) -> dict:
    """Schedule an interview for a candidate.

    Args:
        candidate_id: The candidate's ID
        interviewer_name: Name of the interviewer
        interview_type: Type of interview (technical, behavioral, culture_fit)
        scheduled_date: Date in YYYY-MM-DD format (defaults to next business day)
        scheduled_time: Time in HH:MM format (24-hour)
        duration_minutes: Duration of the interview
        interviewer_email: Email of the interviewer

    Returns:
        Created interview dictionary
    """
    # Parse or default the date
    if scheduled_date:
        try:
            date = datetime.strptime(scheduled_date, "%Y-%m-%d")
        except ValueError:
            date = datetime.now(timezone.utc) + timedelta(days=1)
    else:
        # Default to next business day
        date = datetime.now(timezone.utc) + timedelta(days=1)
        while date.weekday() >= 5:  # Skip weekends
            date += timedelta(days=1)

    # Parse time
    try:
        hour, minute = map(int, scheduled_time.split(":"))
        interview_datetime = date.replace(hour=hour, minute=minute, second=0)
    except (ValueError, TypeError):
        interview_datetime = date.replace(hour=10, minute=0, second=0)

    with get_session() as session:
        candidate = session.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            return {"error": f"Candidate {candidate_id} not found"}

        interview = Interview(
            candidate_id=candidate_id,
            interviewer_name=interviewer_name,
            interviewer_email=interviewer_email,
            interview_type=interview_type,
            scheduled_time=interview_datetime,
            duration_minutes=duration_minutes,
            meeting_link=f"https://meet.example.com/hr-interview-{candidate_id}-{interview_type}",
            status="scheduled",
        )
        session.add(interview)

        # Update candidate status
        candidate.status = "interviewing"
        session.flush()
        return interview.to_dict()


@tool
def list_interviews(candidate_id: int = 0, status: str = "all") -> list[dict]:
    """List interviews, optionally filtered by candidate or status.

    Args:
        candidate_id: Filter by candidate ID (0 for all)
        status: Filter by status (scheduled, completed, cancelled, or 'all')

    Returns:
        List of interview dictionaries
    """
    with get_session() as session:
        query = session.query(Interview)
        if candidate_id > 0:
            query = query.filter(Interview.candidate_id == candidate_id)
        if status != "all":
            query = query.filter(Interview.status == status)
        interviews = query.order_by(Interview.scheduled_time).all()
        return [i.to_dict() for i in interviews]


@tool
def update_interview_status(interview_id: int, status: str) -> dict:
    """Update the status of an interview.

    Args:
        interview_id: The interview ID
        status: New status (scheduled, completed, cancelled)

    Returns:
        Updated interview dictionary
    """
    with get_session() as session:
        interview = session.query(Interview).filter(Interview.id == interview_id).first()
        if not interview:
            return {"error": f"Interview {interview_id} not found"}
        interview.status = status
        session.flush()
        return interview.to_dict()


@tool
def get_available_slots(date: str = "") -> list[str]:
    """Get available interview time slots for a given date.

    Args:
        date: Date in YYYY-MM-DD format (defaults to tomorrow)

    Returns:
        List of available time slots
    """
    # Simulated availability — in production this would check a real calendar
    all_slots = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
        "16:00", "16:30"
    ]

    if not date:
        target_date = datetime.now(timezone.utc) + timedelta(days=1)
        date = target_date.strftime("%Y-%m-%d")

    # Check which slots are already booked
    with get_session() as session:
        try:
            target = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return all_slots

        booked = session.query(Interview).filter(
            Interview.scheduled_time >= target,
            Interview.scheduled_time < target + timedelta(days=1),
            Interview.status == "scheduled"
        ).all()

        booked_times = {i.scheduled_time.strftime("%H:%M") for i in booked}
        available = [s for s in all_slots if s not in booked_times]
        return available


SCHEDULING_TOOLS = [schedule_interview, list_interviews, update_interview_status, get_available_slots]
