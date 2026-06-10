"""
Pipeline Graph Assembly — The main LangGraph StateGraph.

Assembles the supervisor and all 6 worker agents into a single
compiled graph with conditional routing.

Flow:
  START → supervisor → [conditional] → agent_1..6 → supervisor → ... → END
"""

from langgraph.graph import StateGraph, END

from state.hr_state import HRState
from graph.supervisor import supervisor_node, route_to_agent
from agents.job_posting_agent import job_posting_node
from agents.resume_selection_agent import resume_selection_node
from agents.interview_scheduling_agent import interview_scheduling_node
from agents.feedback_agent import feedback_node
from agents.ranking_agent import ranking_node
from agents.final_selection_agent import final_selection_node


def build_pipeline():
    """
    Build the complete HR recruitment pipeline graph.

    Returns a compiled LangGraph that orchestrates:
    Supervisor → Job Posting → Resume Selection → Interview Scheduling
             → Feedback → Ranking → Final Selection → END
    """

    workflow = StateGraph(HRState)

    # --- Add all nodes ---
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("job_posting", job_posting_node)
    workflow.add_node("resume_selection", resume_selection_node)
    workflow.add_node("interview_scheduling", interview_scheduling_node)
    workflow.add_node("feedback_collection", feedback_node)
    workflow.add_node("candidate_ranking", ranking_node)
    workflow.add_node("final_selection", final_selection_node)

    # --- Set entry point ---
    workflow.set_entry_point("supervisor")

    # --- Supervisor routes to the appropriate agent ---
    workflow.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "job_posting": "job_posting",
            "resume_selection": "resume_selection",
            "interview_scheduling": "interview_scheduling",
            "feedback_collection": "feedback_collection",
            "candidate_ranking": "candidate_ranking",
            "final_selection": "final_selection",
            "complete": END,
        }
    )

    # --- Each agent routes back to supervisor after completion ---
    workflow.add_edge("job_posting", "supervisor")
    workflow.add_edge("resume_selection", "supervisor")
    workflow.add_edge("interview_scheduling", "supervisor")
    workflow.add_edge("feedback_collection", "supervisor")
    workflow.add_edge("candidate_ranking", "supervisor")
    workflow.add_edge("final_selection", "supervisor")

    # --- Compile the graph ---
    compiled = workflow.compile()

    print("[OK] HR Pipeline graph compiled successfully.")
    print("   Nodes: supervisor + 6 worker agents")
    print("   Flow: supervisor -> agent -> supervisor -> ... -> END")

    return compiled
