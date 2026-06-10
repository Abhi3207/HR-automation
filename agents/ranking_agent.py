"""
Candidate Ranking Agent — Ranks candidates using composite scoring.

This agent:
1. Calculates composite scores from resume + interview data
2. Generates detailed analysis for each candidate
3. Produces final rankings
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from config.settings import settings
from state.hr_state import HRState
from tools.ranking_tools import RANKING_TOOLS

RANKING_SYSTEM_PROMPT = """You are the Candidate Ranking Agent in an HR recruitment pipeline.

Your responsibilities:
1. Calculate composite scores for each candidate
2. Analyze each candidate's strengths and fit
3. Create a ranked list of candidates
4. Provide detailed analysis for each ranking

Process:
1. Use calculate_composite_score for each application to get raw scores
2. Analyze the results and determine rankings (1 = best candidate)
3. Write a detailed analysis for each candidate explaining their ranking
4. Use save_ranking to record each candidate's rank and score

Ranking criteria weights:
- Resume/screening score: 30%
- Interview performance: 70%

In your analysis, consider:
- Consistency across interview ratings
- Balance of technical and soft skills
- Overall recommendation consensus from interviewers
- Any red flags or standout qualities

IMPORTANT: Calculate scores and save rankings for ALL candidates with applications.
Use calculate_composite_score first, then save_ranking with your analysis."""


def build_ranking_agent():
    """Build the Candidate Ranking Agent."""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
    )
    llm_with_tools = llm.bind_tools(RANKING_TOOLS)

    def agent_node(state: HRState) -> dict:
        messages = [SystemMessage(content=RANKING_SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: HRState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "done"

    workflow = StateGraph(HRState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(RANKING_TOOLS))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "done": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def ranking_node(state: HRState) -> dict:
    """Execute the Candidate Ranking Agent."""
    agent = build_ranking_agent()
    result = agent.invoke(state)
    return {
        "messages": result["messages"],
        "current_stage": "candidate_ranking_complete",
    }
