"""
Supervisor Agent — Orchestrates the HR pipeline.

The supervisor evaluates the current state and decides which
worker agent should execute next. It acts as the central router
in the multi-agent system.

Includes retry logic: if a stage fails and retries remain, the
supervisor re-routes to the same agent. After exhausting retries
it records the failure and routes to the next stage (or complete).
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

# Maps a failed stage to the agent that should handle it
_STAGE_TO_AGENT = {
    "job_posting": "job_posting",
    "resume_selection": "resume_selection",
    "interview_scheduling": "interview_scheduling",
    "feedback_collection": "feedback_collection",
    "candidate_ranking": "candidate_ranking",
    "final_selection": "final_selection",
}

# Maps a *_complete stage to the next agent in line
_NEXT_AFTER_STAGE = {
    "job_posting_complete": "resume_selection",
    "resume_selection_complete": "interview_scheduling",
    "interview_scheduling_complete": "feedback_collection",
    "feedback_collection_complete": "candidate_ranking",
    "candidate_ranking_complete": "final_selection",
    "final_selection_complete": "complete",
}


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

    Retry behaviour:
    - If the last stage set ``error_message`` and ``retry_count`` <
      ``max_retries``, re-route to the same agent and bump the counter.
    - If retries are exhausted, log the failure, clear the error, and
      advance to the next stage.
    """
    current_stage = state.get("current_stage", "start")
    error_message = state.get("error_message")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.AGENT_MAX_RETRIES)
    failed_stages: list = list(state.get("failed_stages", []))

    # ---- Retry / skip-on-error logic ----
    if error_message:
        # Which agent just failed?
        failed_agent = None
        for stage_key, agent_name in _STAGE_TO_AGENT.items():
            if current_stage.startswith(stage_key):
                failed_agent = agent_name
                break

        if failed_agent and retry_count < max_retries:
            logger.warning(
                "[SUPERVISOR] Stage '%s' failed (attempt %d/%d). Retrying agent '%s'...",
                current_stage, retry_count + 1, max_retries, failed_agent,
            )
            return {
                "next_agent": failed_agent,
                "retry_count": retry_count + 1,
                "error_message": None,      # Clear so the agent gets a clean state
                "messages": [
                    HumanMessage(
                        content=(
                            f"[Supervisor] Retrying {failed_agent} "
                            f"(attempt {retry_count + 2}/{max_retries + 1}) "
                            f"after error: {error_message}"
                        )
                    )
                ],
            }
        else:
            # Retries exhausted — record failure and move on
            logger.error(
                "[SUPERVISOR] Stage '%s' failed after %d retries. Skipping.",
                current_stage, max_retries,
            )
            failed_stages.append(current_stage)

            # Determine which stage to advance to
            next_agent = _NEXT_AFTER_STAGE.get(
                f"{current_stage}_complete"
                if not current_stage.endswith("_complete") else current_stage,
                "complete",
            )

            return {
                "next_agent": next_agent,
                "retry_count": 0,
                "error_message": None,
                "failed_stages": failed_stages,
                "pipeline_status": "running",
                "messages": [
                    HumanMessage(
                        content=(
                            f"[Supervisor] Stage '{current_stage}' failed permanently "
                            f"after {max_retries} retries. Advancing to '{next_agent}'. "
                            f"Last error: {error_message}"
                        )
                    )
                ],
            }

    # ---- Normal routing (no error) ----
    # Reset retry counter on success
    supervisor = build_supervisor()

    context = f"""
Current pipeline stage: {current_stage}
Pipeline status: {state.get('pipeline_status', 'running')}
Failed stages so far: {failed_stages or 'none'}

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
        "retry_count": 0,   # Reset on successful advance
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
