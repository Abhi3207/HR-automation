"""
Final Selection Agent — Makes hire/reject/waitlist decisions.

This agent:
1. Reviews candidate rankings and complete profiles
2. Makes final hiring decisions
3. Generates justifications for each decision
4. Produces offer summaries
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
from tools.selection_tools import SELECTION_TOOLS

logger = get_logger(__name__)

FINAL_SELECTION_SYSTEM_PROMPT = """You are the Final Selection Agent in an HR recruitment pipeline.

Your responsibilities:
1. Review the complete candidate journey (resume, interviews, rankings)
2. Make final hiring decisions: offer, reject, or waitlist
3. Provide detailed justifications for each decision
4. Suggest salary offers for selected candidates

Decision guidelines:
- "offer": Top-ranked candidates with strong_hire or hire recommendations
- "waitlist": Borderline candidates with mixed feedback
- "reject": Low-ranked candidates or those with "no_hire" recommendations
- Typically select 1-2 top candidates for offers

Process:
1. Use generate_offer_summary for each ranked candidate to review their full profile
2. Make decisions using make_decision for each candidate
3. Provide thorough justification explaining why
4. Include salary suggestions for candidates receiving offers
5. Use get_pipeline_summary at the end to verify the pipeline results

IMPORTANT: Make a decision for EVERY ranked candidate.
Be decisive but fair. Document your reasoning clearly."""


@functools.lru_cache(maxsize=1)
def build_final_selection_agent():
    """Build and cache the Final Selection Agent."""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
    )
    llm_with_tools = llm.bind_tools(SELECTION_TOOLS)

    def agent_node(state: HRState) -> dict:
        messages = [SystemMessage(content=FINAL_SELECTION_SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: HRState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "done"

    workflow = StateGraph(HRState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(SELECTION_TOOLS))

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


def final_selection_node(state: HRState) -> dict:
    """Execute the Final Selection Agent."""
    agent = build_final_selection_agent()
    metrics_list: list = list(state.get("stage_metrics", []))

    with StageTimer("final_selection") as timer:
        try:
            result = agent.invoke(state)
            timer.count_tool_calls(result.get("messages", []))
            timer.mark_success()

            logger.info("[Final Selection Agent] Completed successfully (%.1fs)", timer.elapsed_seconds)

            metrics_list.append(timer.to_dict())
            return {
                "messages": result["messages"],
                "current_stage": "final_selection_complete",
                "pipeline_status": "completed",
                "stage_metrics": metrics_list,
            }
        except Exception as e:
            logger.error("Final Selection Agent failed: %s", e, exc_info=True)
            timer.mark_failure(str(e))
            metrics_list.append(timer.to_dict())
            return {
                "messages": [HumanMessage(content=f"[Final Selection Agent] Error: {e}")],
                "current_stage": "final_selection",
                "pipeline_status": "running",
                "error_message": str(e),
                "stage_metrics": metrics_list,
            }
