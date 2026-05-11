"""
Example: Supervisor agent with sub-agents using ChatOpenRouter.
Shows how tool calls from sub-agents are captured and streamed as AG-UI events.
"""
from langchain_core.tools import tool

from openrouter_agent import build_agent, build_supervisor, stream_agui_events


# ---------------------------------------------------------------------------
# 1. Define tools for sub-agents
# ---------------------------------------------------------------------------

@tool
def search_web(query: str) -> str:
    """Search the web for current information."""
    # Replace with real implementation (Tavily, SerpAPI, etc.)
    return f"Search results for: {query}"


@tool
def query_database(sql: str) -> str:
    """Execute a SQL query against the analytics database."""
    # Replace with real DB connection
    return f"Query results for: {sql}"


@tool
def send_notification(message: str, channel: str = "general") -> str:
    """Send a notification to a Slack channel."""
    return f"Sent to #{channel}: {message}"


# ---------------------------------------------------------------------------
# 2. Build sub-agents (each is a compiled LangGraph graph)
# ---------------------------------------------------------------------------

researcher = build_agent(
    model_name="anthropic/claude-sonnet-4-5",
    tools=[search_web],
    system_prompt="You are a research assistant. Use web search to find information.",
)

analyst = build_agent(
    model_name="anthropic/claude-sonnet-4-5",
    tools=[query_database],
    system_prompt="You are a data analyst. Query the database to answer questions.",
)


# ---------------------------------------------------------------------------
# 3. Build supervisor that delegates to sub-agents
# ---------------------------------------------------------------------------

supervisor = build_supervisor(
    model_name="anthropic/claude-sonnet-4-5",
    sub_agents={
        "researcher": researcher,
        "analyst": analyst,
    },
    tools=[send_notification],  # Supervisor's own tools
    system_prompt="""You are a supervisor that delegates tasks.
    - Use delegate_to_researcher for web research
    - Use delegate_to_analyst for data analysis
    - Use send_notification to alert the team
    Coordinate sub-agents to answer complex questions.""",
)


# ---------------------------------------------------------------------------
# 4. Stream events (captures tool calls from ALL agents)
# ---------------------------------------------------------------------------

async def main():
    from langchain_core.messages import HumanMessage

    messages = [HumanMessage(content="Research current AI trends and check our database for related projects")]

    async for event in stream_agui_events(supervisor, messages, expose_reasoning=True):
        # Each event is an AG-UI event ready to be encoded by EventEncoder
        print(f"Event: {type(event).__name__}", end="")
        if hasattr(event, "delta"):
            print(f" | delta: {event.delta[:80]}...", end="")
        if hasattr(event, "tool_call_name"):
            print(f" | tool: {event.tool_call_name}", end="")
        print()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
