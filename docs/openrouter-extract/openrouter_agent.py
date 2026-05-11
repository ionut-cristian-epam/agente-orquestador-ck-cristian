"""
Portable LangGraph agent with ChatOpenRouter.
Captures tool calls from main agent AND sub-agents, emits AG-UI events.

Requirements:
    pip install langchain-openrouter langgraph ag-ui-protocol

Environment:
    OPENROUTER_API_KEY=your_key
"""
import json
import os
import uuid
from typing import AsyncIterator, Sequence

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_openrouter import ChatOpenRouter
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from ag_ui.core import (
    ReasoningMessageChunkEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

def create_openrouter_model(
    model: str = "anthropic/claude-sonnet-4-5",
    temperature: float = 0,
    streaming: bool = True,
):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    return ChatOpenRouter(
        model=model,
        api_key=api_key,
        temperature=temperature,
        streaming=streaming,
    )


# ---------------------------------------------------------------------------
# Build agent graph (single agent with tools)
# ---------------------------------------------------------------------------

def build_agent(
    model_name: str = "anthropic/claude-sonnet-4-5",
    tools: list | None = None,
    system_prompt: str = "You are a helpful assistant.",
):
    tools = tools or []
    base_llm = create_openrouter_model(model_name)
    llm = base_llm.bind_tools(tools) if tools else base_llm

    def agent_node(state: AgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + list(messages)
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = llm.invoke(messages)
                return {"messages": [response]}
            except Exception as e:
                err_str = str(e).lower()
                is_tool_error = "function" in err_str or "tool" in err_str or "failed_generation" in err_str
                if is_tool_error and attempt < max_retries - 1:
                    continue
                if is_tool_error:
                    response = base_llm.invoke(messages)
                    return {"messages": [response]}
                raise

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
    else:
        graph.add_edge("agent", END)
    graph.set_entry_point("agent")
    return graph.compile()


# ---------------------------------------------------------------------------
# Build supervisor graph (main agent + sub-agents)
# ---------------------------------------------------------------------------

def build_supervisor(
    model_name: str = "anthropic/claude-sonnet-4-5",
    sub_agents: dict[str, "CompiledGraph"] | None = None,
    tools: list | None = None,
    system_prompt: str = "You are a supervisor that delegates tasks to sub-agents.",
):
    """
    Build a supervisor graph where sub-agents are nodes.
    astream_events(v2) captures tool calls from ALL nodes including sub-agents.

    sub_agents: {"researcher": compiled_graph, "coder": compiled_graph}
    tools: tools available to the supervisor itself
    """
    sub_agents = sub_agents or {}
    tools = tools or []
    base_llm = create_openrouter_model(model_name)

    all_tool_schemas = list(tools)
    for name, sub_graph in sub_agents.items():
        from langchain_core.tools import tool as tool_decorator

        @tool_decorator(name=f"delegate_to_{name}")
        def delegate(query: str, _name=name) -> str:
            f"""Delegate a task to the {_name} sub-agent."""
            return f"DELEGATE:{_name}:{query}"
        all_tool_schemas.append(delegate)

    llm = base_llm.bind_tools(all_tool_schemas) if all_tool_schemas else base_llm

    def supervisor_node(state: AgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + list(messages)
        response = llm.invoke(messages)
        return {"messages": [response]}

    def route_tools(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            for tc in last.tool_calls:
                name = tc.get("name", "")
                for sub_name in sub_agents:
                    if name == f"delegate_to_{sub_name}":
                        return sub_name
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)

    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge("tools", "supervisor")

    for name, sub_graph in sub_agents.items():
        graph.add_node(name, sub_graph)
        graph.add_edge(name, "supervisor")

    routing = {END: END}
    if tools:
        routing["tools"] = "tools"
    for name in sub_agents:
        routing[name] = name

    graph.add_conditional_edges("supervisor", route_tools, routing)
    graph.set_entry_point("supervisor")
    return graph.compile()


# ---------------------------------------------------------------------------
# Stream AG-UI events from any LangGraph graph
# ---------------------------------------------------------------------------

def _extract_text(chunk) -> str:
    if isinstance(chunk.content, str):
        return chunk.content
    if isinstance(chunk.content, list):
        return "".join(
            b.get("text", "") for b in chunk.content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def _extract_thinking(chunk) -> str:
    if isinstance(chunk.content, list):
        return "".join(
            b.get("thinking", "") for b in chunk.content
            if isinstance(b, dict) and b.get("type") == "thinking"
        )
    return ""


async def stream_agui_events(
    graph,
    messages: Sequence[BaseMessage],
    *,
    msg_id: str | None = None,
    expose_reasoning: bool = True,
    message_collector: list | None = None,
) -> AsyncIterator:
    """
    Stream AG-UI events from a LangGraph graph.
    Captures tool calls from ALL nodes including sub-agents.
    """
    msg_id = msg_id or str(uuid.uuid4())
    emitted_tool_call_ids: set[str] = set()
    text_emitted = False

    async for event in graph.astream_events(
        {"messages": messages},
        version="v2",
    ):
        kind = event.get("event")
        data = event.get("data", {})
        node_name = event.get("name", "")

        # --- Streaming text/thinking chunks ---
        if kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk is None:
                continue
            thinking = _extract_thinking(chunk)
            text = _extract_text(chunk)
            if thinking:
                yield ReasoningMessageChunkEvent(delta=thinking)
            if text:
                text_emitted = True
                yield TextMessageChunkEvent(
                    message_id=msg_id,
                    role="assistant",
                    delta=text,
                )
            continue

        # --- LLM finished — check for tool calls ---
        if kind == "on_chat_model_end":
            output = data.get("output")
            if isinstance(output, AIMessage):
                if message_collector is not None:
                    message_collector.append(output)
                if not text_emitted and not output.tool_calls:
                    final_text = output.content if isinstance(output.content, str) else ""
                    if final_text:
                        text_emitted = True
                        yield TextMessageChunkEvent(
                            message_id=msg_id, role="assistant", delta=final_text,
                        )
                if output.tool_calls:
                    for tc in output.tool_calls:
                        tc_id = tc.get("id") or str(uuid.uuid4())
                        if tc_id in emitted_tool_call_ids:
                            continue
                        emitted_tool_call_ids.add(tc_id)
                        tc_name = tc.get("name", "tool")
                        args_json = json.dumps(tc.get("args", {}), ensure_ascii=False)
                        if expose_reasoning:
                            origin = f" [{node_name}]" if node_name else ""
                            args_preview = args_json if len(args_json) <= 200 else args_json[:197] + "..."
                            yield ReasoningMessageChunkEvent(
                                delta=f"🔧{origin} Calling `{tc_name}` with: `{args_preview}`\n\n",
                            )
                        yield ToolCallChunkEvent(
                            tool_call_id=tc_id,
                            tool_call_name=tc_name,
                            delta=args_json,
                        )
            continue

        # --- Tool finished (main agent or sub-agent) ---
        if kind == "on_tool_end":
            output = data.get("output")
            if isinstance(output, ToolMessage):
                if message_collector is not None:
                    message_collector.append(output)
                content = output.content
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False, default=str)
                if expose_reasoning:
                    origin = f" [{node_name}]" if node_name else ""
                    yield ReasoningMessageChunkEvent(
                        delta=f"✅{origin} Result received ({len(content)} chars). Processing...\n\n",
                    )
                yield ToolCallResultEvent(
                    message_id=output.tool_call_id or str(uuid.uuid4()),
                    tool_call_id=output.tool_call_id or "",
                    content=content,
                    role="tool",
                )
            continue
