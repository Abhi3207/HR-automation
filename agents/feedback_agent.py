"""
Feedback Collection Agent — Collects and structures interviewer feedback.

This agent:
1. Identifies completed interviews needing feedback
2. Generates realistic interviewer feedback (simulated)
3. Structures feedback with ratings, strengths, weaknesses
4. Validates completeness of feedback
"""

import functools

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from config.logging_config import get_logger
from config.settings import settings
from state.hr_state import HRState
from tools.feedback_tools import FEEDBACK_TOOLS

logger = get_logger(__name__)

FEEDBACK_COLLECTION_SYSTEM_PROMPT = """You are the Feedback Collection Agent in an HR recruitment pipeline.

Your responsibilities:
1. Collect structured feedback for all scheduled interviews
2. Generate realistic, detailed interviewer assessments
3. Ensure all required fields are filled
4. Provide balanced evaluations

For each interview, submit feedback with:
- overall_rating: 1.0-10.0 (be realistic, not everyone is a 10)
- technical_rating: 1-10 (for technical interviews)
- communication_rating: 1-10
- culture_fit_rating: 1-10
- recommendation: "strong_hire", "hire", "maybe", or "no_hire"
- strengths: Specific positive observations
- weaknesses: Constructive areas of concern
- detailed_notes: Comprehensive interview notes

Guidelines:
- Be realistic and varied in your ratings (not all candidates are equal)
- Provide specific, actionable feedback
- Use the interviewer name from the interview record
- Different interview types should focus on different aspects
- Technical interviews should emphasize technical_rating
- Behavioral interviews should emphasize communication_rating

IMPORTANT: Submit feedback for ALL scheduled interviews using the submit_feedback tool.
First use get_pending_feedback or list interviews to find all interviews needing feedback."""


@functools.lru_cache(maxsize=1)
def build_feedback_agent():
    """Build and cache the Feedback Collection Agent."""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0.3,  # Slightly higher for varied feedback
        api_key=settings.OPENAI_API_KEY,
    )
    llm_with_tools = llm.bind_tools(FEEDBACK_TOOLS)

    def agent_node(state: HRState) -> dict:
        messages = [SystemMessage(content=FEEDBACK_COLLECTION_SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: HRState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "done"

    workflow = StateGraph(HRState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(FEEDBACK_TOOLS))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "done": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def feedback_node(state: HRState) -> dict:
    """Execute the Feedback Collection Agent."""
    agent = build_feedback_agent()
    try:
        result = agent.invoke(state)
        return {
            "messages": result["messages"],
            "current_stage": "feedback_collection_complete",
        }
    except Exception as e:
        logger.error("Feedback Collection Agent failed: %s", e, exc_info=True)
        return {
            "messages": [HumanMessage(content=f"[Feedback Collection Agent] Error: {e}")],
            "current_stage": "feedback_collection_complete",
            "error_message": str(e),
        }
