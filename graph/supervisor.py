"""
Supervisor Agent — Orchestrates the HR pipeline.

The supervisor evaluates the current state and decides which
worker agent should execute next. It acts as the central router
in the multi-agent system.
"""

import functools

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from config.logging_config import get_logger
from config.settings import settings
from state.hr_state import HRState

logger = get_logger(__name__)


class SupervisorDecision(BaseModel):
    """Structured output for the supervisor's routing decision."""
    next_agent: str = Field(
        description="The next agent to run. Must be one of: "
                    "job_posting, resume_selection, interview_scheduling, "
                    "feedback_collection, candidate_ranking, final_selection, complete"
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent should run next"
    )


SUPERVISOR_SYSTEM_PROMPT = """You are the Supervisor Agent orchestrating an HR recruitment pipeline.

You manage 6 specialized worker agents that execute in sequence:
1. job_posting — Creates the job posting
2. resume_selection — Screens resumes and shortlists candidates
3. interview_scheduling — Schedules interviews for shortlisted candidates
4. feedback_collection — Collects interviewer feedback
5. candidate_ranking — Ranks candidates by composite score
6. final_selection — Makes final hire/reject decisions

Your job is to determine which agent should run NEXT based on the current pipeline state.

Rules:
- Follow the sequential pipeline order (1→2→3→4→5→6→complete)
- Check the current_stage in the state to know where we are
- After the final_selection agent completes, set next_agent to "complete"
- If a stage reports errors, you may retry it or skip to the next stage

Current stage indicators:
- If current_stage is empty or "start" → next is "job_posting"
- If current_stage is "job_posting_complete" → next is "resume_selection"
- If current_stage is "resume_selection_complete" → next is "interview_scheduling"
- If current_stage is "interview_scheduling_complete" → next is "feedback_collection"
- If current_stage is "feedback_collection_complete" → next is "candidate_ranking"
- If current_stage is "candidate_ranking_complete" → next is "final_selection"
- If current_stage is "final_selection_complete" → next is "complete"
"""


@functools.lru_cache(maxsize=1)
def build_supervisor():
    """Build and cache the supervisor LLM with structured output."""
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=0,
        api_key=settings.OPENAI_API_KEY,
    )
    return llm.with_structured_output(SupervisorDecision)


def supervisor_node(state: HRState) -> dict:
    """
    Supervisor node that decides routing.
    Returns the next agent to execute.
    """
    supervisor = build_supervisor()

    current_stage = state.get("current_stage", "start")

    # Build context message for the supervisor
    context = f"""
Current pipeline stage: {current_stage}
Pipeline status: {state.get('pipeline_status', 'running')}

Determine which agent should run next.
"""

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    decision = supervisor.invoke(messages)

    logger.info("=" * 60)
    logger.info("[SUPERVISOR] DECISION: %s", decision.next_agent)
    logger.info("   Reasoning: %s", decision.reasoning)
    logger.info("=" * 60)

    return {
        "next_agent": decision.next_agent,
        "messages": [HumanMessage(content=f"[Supervisor] Routing to: {decision.next_agent}. Reason: {decision.reasoning}")],
    }


def route_to_agent(state: HRState) -> str:
    """Conditional edge function: routes to the next agent based on supervisor's decision."""
    next_agent = state.get("next_agent", "complete")

    valid_agents = [
        "job_posting", "resume_selection", "interview_scheduling",
        "feedback_collection", "candidate_ranking", "final_selection",
        "complete"
    ]

    if next_agent in valid_agents:
        return next_agent
    return "complete"
