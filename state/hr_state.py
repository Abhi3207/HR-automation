"""
Shared state definition for the HR Multi-Agent pipeline.
This TypedDict is the single source of truth flowing through the LangGraph.
"""

from typing import TypedDict, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class HRState(TypedDict):
    """
    Shared state for the HR recruitment pipeline graph.

    All agents read from and write to this state.
    The `messages` field uses the `add_messages` reducer to append
    rather than overwrite messages, preserving conversation history.
    """

    # --- Message History ---
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Pipeline Control ---
    current_stage: str          # Current pipeline stage name
    next_agent: str             # Supervisor's routing decision
    pipeline_status: str        # "running", "completed", "error"
    error_message: Optional[str]  # Error details if pipeline fails

    # --- Job Posting Data ---
    job_posting_id: Optional[int]
    job_posting: Optional[dict]

    # --- Candidate Data ---
    candidates: list[dict]              # All candidates with resumes
    shortlisted_candidates: list[dict]  # After resume screening

    # --- Interview Data ---
    scheduled_interviews: list[dict]    # Interview schedule entries

    # --- Feedback Data ---
    interview_feedback: list[dict]      # Collected interviewer feedback

    # --- Ranking Data ---
    candidate_rankings: list[dict]      # Scored & ranked candidates

    # --- Final Decisions ---
    final_decisions: list[dict]         # Offer/reject decisions


# Stage constants for routing
STAGES = {
    "JOB_POSTING": "job_posting",
    "RESUME_SELECTION": "resume_selection",
    "INTERVIEW_SCHEDULING": "interview_scheduling",
    "FEEDBACK_COLLECTION": "feedback_collection",
    "CANDIDATE_RANKING": "candidate_ranking",
    "FINAL_SELECTION": "final_selection",
    "COMPLETE": "complete",
}
