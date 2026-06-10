"""
Job Posting Agent — Creates and manages job postings.

This agent is built as a LangGraph StateGraph that:
1. Receives job requirements from the supervisor
2. Uses the LLM to generate a comprehensive job description
3. Saves the posting to the database via tools
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from config.settings import settings
from state.hr_state import HRState
from tools.job_tools import JOB_TOOLS

# System prompt for this agent
JOB_POSTING_SYSTEM_PROMPT = """You are the Job Posting Agent in an HR recruitment pipeline.

Your responsibilities:
1. Create professional, detailed job postings based on the hiring requirements
2. Generate comprehensive job descriptions with clear responsibilities
3. List required and preferred qualifications
4. Include salary range, location, and employment type

When creating a job posting:
- Write a compelling job description that attracts top talent
- Clearly separate required vs preferred qualifications
- Include specific technical skills, experience levels, and education requirements
- Make the posting professional and inclusive

Use the create_job_posting tool to save the job posting to the database.
After creating the posting, confirm the details in your response.

IMPORTANT: You MUST use the tools to create the job posting. Do not just describe what you would do."""


def build_job_posting_agent():
    """Build the Job Posting Agent as a LangGraph sub-graph."""

    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        api_key=settings.OPENAI_API_KEY,
    )
    llm_with_tools = llm.bind_tools(JOB_TOOLS)

    def agent_node(state: HRState) -> dict:
        """The LLM reasoning node."""
        messages = [SystemMessage(content=JOB_POSTING_SYSTEM_PROMPT)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: HRState) -> str:
        """Check if the agent needs to call tools or is done."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "done"

    # Build the sub-graph
    workflow = StateGraph(HRState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(JOB_TOOLS))

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {"tools": "tools", "done": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# Wrapper function for use as a node in the main pipeline
def job_posting_node(state: HRState) -> dict:
    """Execute the Job Posting Agent and return updated state."""
    agent = build_job_posting_agent()
    result = agent.invoke(state)
    return {
        "messages": result["messages"],
        "current_stage": "job_posting_complete",
    }
