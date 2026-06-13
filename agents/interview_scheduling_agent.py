"""
Interview Scheduling Agent — Schedules interviews for shortlisted candidates.

This agent:
1. Gets the list of shortlisted candidates
2. Checks available time slots
3. Schedules interviews with appropriate interviewers
4. Assigns interview types (technical, behavioral, culture fit)
"""

import functools

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from config.logging_config import get_logger
from config.settings import settings
from state.hr_state import HRState
from tools.scheduling_tools import SCHEDULING_TOOLS

logger = get_logger(__name__)

INTERVIEW_SCHEDULING_SYSTEM_PROMPT = """You are the Interview Scheduling Agent in an HR recruitment pipeline.

Your responsibilities:
1. Schedule interviews for all shortlisted candidates
2. Assign appropriate interview types based on the role
3. Ensure no scheduling conflicts
4. Create a well-organized interview schedule

Guidelines:
- Schedule at least 2 interviews per candidate (technical + behavioral)
- Use different interviewers for different interview types
- Space interviews at least 30 minutes apart
- Use available time slots (check with get_available_slots)
- Assign realistic interviewer names (e.g., "Dr. Sarah Chen - Engineering Lead")

Interview types to schedule:
1. "technical" — Technical skills assessment
2. "behavioral" — Behavioral and soft skills evaluation
3. "culture_fit" — Team and culture fit assessment (optional, for top candidates)

IMPORTANT: Use the tools to schedule each interview. Schedule for ALL shortlisted candidates.
Use list_interviews to verify your scheduled interviews at the end."""


@functools.lru_cache(maxsize=1)
def build_interview_scheduling_agent():
    """Build and cache the Interview Scheduling Agent."""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
    )
    llm_with_tools = llm.bind_tools(SCHEDULING_TOOLS)

    def agent_node(state: HRState) -> dict:
        messages = [SystemMessage(content=INTERVIEW_SCHEDULING_SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: HRState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "done"

    workflow = StateGraph(HRState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(SCHEDULING_TOOLS))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "done": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def interview_scheduling_node(state: HRState) -> dict:
    """Execute the Interview Scheduling Agent."""
    agent = build_interview_scheduling_agent()
    try:
        result = agent.invoke(state)
        return {
            "messages": result["messages"],
            "current_stage": "interview_scheduling_complete",
        }
    except Exception as e:
        logger.error("Interview Scheduling Agent failed: %s", e, exc_info=True)
        return {
            "messages": [HumanMessage(content=f"[Interview Scheduling Agent] Error: {e}")],
            "current_stage": "interview_scheduling_complete",
            "error_message": str(e),
        }
