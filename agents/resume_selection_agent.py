"""
Resume Selection Agent — Screens resumes against job requirements.

This agent:
1. Retrieves job requirements
2. Evaluates each candidate's resume
3. Assigns screening scores
4. Shortlists candidates above the threshold
"""

import functools

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from config.logging_config import get_logger
from config.metrics import StageTimer
from config.settings import settings
from state.hr_state import HRState
from tools.resume_tools import RESUME_TOOLS

logger = get_logger(__name__)

RESUME_SELECTION_SYSTEM_PROMPT = """You are the Resume Selection Agent in an HR recruitment pipeline.

Your responsibilities:
1. Review each candidate's resume against the job requirements
2. Score each resume on a scale of 0-100 based on:
   - Skills match (40%)
   - Experience relevance (30%)
   - Education fit (15%)
   - Overall presentation (15%)
3. Provide detailed screening notes explaining the score
4. Candidates scoring >= {threshold} are automatically shortlisted

Process:
1. First, use get_job_requirements to understand what the job needs
2. Then, use get_candidates_for_job to see all applicants
3. For each candidate, use score_resume to record your assessment
4. Be fair, objective, and consistent in your scoring

IMPORTANT: You MUST use the tools to score each candidate. Score ALL candidates, not just some.
The screening threshold is {threshold}/100. Be thorough in your evaluation notes.""".format(
    threshold=settings.RESUME_SHORTLIST_THRESHOLD
)


@functools.lru_cache(maxsize=1)
def build_resume_selection_agent():
    """Build and cache the Resume Selection Agent as a LangGraph sub-graph."""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
    )
    llm_with_tools = llm.bind_tools(RESUME_TOOLS)

    def agent_node(state: HRState) -> dict:
        messages = [SystemMessage(content=RESUME_SELECTION_SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: HRState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "done"

    workflow = StateGraph(HRState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(RESUME_TOOLS))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "done": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile(
        recursion_limit=settings.AGENT_RECURSION_LIMIT,
    )


def resume_selection_node(state: HRState) -> dict:
    """Execute the Resume Selection Agent and return updated state."""
    agent = build_resume_selection_agent()
    metrics_list: list = list(state.get("stage_metrics", []))

    with StageTimer("resume_selection") as timer:
        try:
            result = agent.invoke(state)
            timer.count_tool_calls(result.get("messages", []))
            timer.mark_success()

            logger.info("[Resume Selection Agent] Completed successfully (%.1fs)", timer.elapsed_seconds)

            metrics_list.append(timer.to_dict())
            return {
                "messages": result["messages"],
                "current_stage": "resume_selection_complete",
                "stage_metrics": metrics_list,
            }
        except Exception as e:
            logger.error("Resume Selection Agent failed: %s", e, exc_info=True)
            timer.mark_failure(str(e))
            metrics_list.append(timer.to_dict())
            return {
                "messages": [HumanMessage(content=f"[Resume Selection Agent] Error: {e}")],
                "current_stage": "resume_selection",
                "pipeline_status": "running",
                "error_message": str(e),
                "stage_metrics": metrics_list,
            }
