"""LangGraph-based in-process agent harness.

Builds a tool-using StateGraph and streams events translated to AG-UI format.
Unlike CLI harnesses, this runs directly in the FastAPI process — no subprocess,
no acpx, no ACP protocol.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Annotated, AsyncIterator, TypedDict

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from ag_ui.core import (
    BaseEvent,
    ReasoningMessageChunkEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class SportsAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def _tavily_search(query: str, max_results: int = 5) -> str:
    """Search via Tavily API. Requires TAVILY_API_KEY."""
    from tavily import TavilyClient
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY not set")
    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results)
    results = response.get("results", [])
    if not results:
        return "No results found."
    formatted = []
    for r in results:
        formatted.append(
            f"- **{r.get('title', 'Untitled')}**\n  {r.get('content', '')[:300]}\n  Source: {r.get('url', '')}"
        )
    return "\n\n".join(formatted)


def _ddg_search(query: str, max_results: int = 5) -> str:
    """Fallback search via DuckDuckGo (no API key required)."""
    try:
        from ddgs import DDGS
    except ImportError:
        return "Search unavailable: no Tavily key and ddgs package missing."
    with DDGS() as ddg:
        results = list(ddg.text(query, max_results=max_results))
    if not results:
        return "No results found."
    formatted = []
    for r in results:
        formatted.append(
            f"- **{r.get('title', 'Untitled')}**\n  {r.get('body', '')[:300]}\n  Source: {r.get('href', '')}"
        )
    return "\n\n".join(formatted)


def _do_search(query: str) -> str:
    """Use Tavily if key is set, otherwise DuckDuckGo."""
    if os.environ.get("TAVILY_API_KEY"):
        try:
            return _tavily_search(query)
        except Exception as e:
            print(f"[langgraph] Tavily failed: {e}, falling back to DuckDuckGo", flush=True)
    return _ddg_search(query)


@tool
def web_search(query: str) -> str:
    """Search the web for information. Use for current events, news, or facts you don't know.

    Args:
        query: The search query.

    Returns:
        Top search results with titles, snippets, and source URLs.
    """
    return _do_search(query)


@tool
def get_sport_rules(sport_name: str) -> str:
    """Search for the official rules of a specific sport.

    Use this when the user asks specifically about how a sport is played,
    its rules, fouls, scoring system, or regulations.

    Args:
        sport_name: Name of the sport (e.g. "cricket", "rugby", "padel").

    Returns:
        Search results focused on official rules of the sport.
    """
    query = f"official rules of {sport_name} how to play scoring fouls"
    return _do_search(query)


SPORTS_TOOLS = [web_search, get_sport_rules]

_TOOL_NAMES = {t.name for t in SPORTS_TOOLS}


# ---------------------------------------------------------------------------
# Recover tool calls from malformed LLM output (Groq/Llama)
# ---------------------------------------------------------------------------

def _parse_failed_generation(error: Exception) -> list[dict] | None:
    """Extract tool calls from Groq's failed_generation error field.

    Llama models on Groq sometimes emit tool calls as text instead of structured
    function calling, e.g.:
      <function=web_search(query="...")></function>
      <function=web_search [{"query": "..."}]</function>
      <function=web_search{"query": "..."}</function>

    Returns a list of {name, args, id} dicts if parseable, else None.
    """
    import re

    err_str = str(error)
    pattern = r"<function=(\w+)\s*(\(.*?\)|\[.*?\]|\{.*?\})\s*>?<?/?function>?"
    matches = re.findall(pattern, err_str)
    if not matches:
        return None

    calls = []
    for func_name, raw_args in matches:
        if func_name not in _TOOL_NAMES:
            continue
        raw_args = raw_args.strip()
        args = {}
        # Format: (query="value") or (query="value", max_results=5)
        if raw_args.startswith("(") and raw_args.endswith(")"):
            inner = raw_args[1:-1]
            for pair in re.findall(r'(\w+)\s*=\s*"([^"]*)"', inner):
                args[pair[0]] = pair[1]
            for pair in re.findall(r'(\w+)\s*=\s*(\d+)', inner):
                args[pair[0]] = int(pair[1])
        # Format: [{"key": "value"}] or {"key": "value"}
        else:
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, list) and parsed:
                    args = parsed[0] if isinstance(parsed[0], dict) else {}
                elif isinstance(parsed, dict):
                    args = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        if args:
            calls.append({
                "name": func_name,
                "args": args,
                "id": f"recovered_{uuid.uuid4().hex[:8]}",
            })

    return calls if calls else None


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

def _create_chat_model(model_name: str):
    """Build a langchain ChatModel from a 'provider/model' string.

    Validates that the matching API key environment variable is set.

    Supported providers:
      Paid:  openai, anthropic, google
      Free:  groq, nagaai, openrouter, cerebras
             (all OpenAI-compatible endpoints; require their respective API keys)
    """
    if "/" not in model_name:
        raise ValueError(f"Invalid model name '{model_name}': expected 'provider/model_id'")

    provider, model_id = model_name.split("/", 1)
    provider = provider.lower()

    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not set in environment")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_id, streaming=True)

    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model_name=model_id, streaming=True)

    if provider == "google":
        if not os.environ.get("GOOGLE_API_KEY"):
            raise RuntimeError("GOOGLE_API_KEY not set in environment")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_id)

    # --- Free / OpenAI-compatible relays ---

    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment")
        from langchain_groq import ChatGroq
        # streaming=False: ChatGroq streaming + bind_tools drops tool_call_chunks
        # aggregation, leaving AIMessage.tool_calls empty. Non-streaming invoke
        # returns full tool_calls reliably; astream_events still emits
        # on_chat_model_end and the synthetic-chunk fallback covers UI streaming.
        return ChatGroq(
            model=model_id,
            api_key=api_key,
            streaming=False,
        )

    if provider == "nagaai":
        api_key = os.environ.get("NAGA_API_KEY")
        if not api_key:
            raise RuntimeError("NAGA_API_KEY not set in environment")
        from langchain_openai import ChatOpenAI
        # NagaAI model IDs may include path segments (e.g. "meta/llama-3.3-70b").
        # The provider prefix is stripped; the rest is passed verbatim.
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url="https://api.naga.ac/v1",
            streaming=True,
        )

    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set in environment")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            streaming=True,
        )

    if provider == "cerebras":
        api_key = os.environ.get("CEREBRAS_API_KEY")
        if not api_key:
            raise RuntimeError("CEREBRAS_API_KEY not set in environment")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_id,
            api_key=api_key,
            base_url="https://api.cerebras.ai/v1",
            streaming=True,
        )

    raise ValueError(f"Unknown provider '{provider}' in model '{model_name}'")


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_sports_agent(model_name: str, system_prompt: str):
    """Build a compiled StateGraph for the sports expert agent.

    Architecture:
      START -> agent (LLM with tools bound)
      agent --[tool_calls?]--> tools (ToolNode) -> agent
      agent --[no tool_calls]--> END
    """
    base_llm = _create_chat_model(model_name)
    llm = base_llm.bind_tools(SPORTS_TOOLS)
    tool_names = [t.name for t in SPORTS_TOOLS]
    print(f"[langgraph] Graph built — model={model_name!r} tools={tool_names}", flush=True)

    # Verify tool binding produced valid schemas
    try:
        bound_kwargs = llm.kwargs if hasattr(llm, "kwargs") else {}
        n_tools = len(bound_kwargs.get("tools", []))
        print(f"[langgraph] Tool binding check: {n_tools} tool schema(s) in LLM kwargs", flush=True)
    except Exception as e:
        print(f"[langgraph] Tool binding check failed: {e}", flush=True)

    def agent_node(state: SportsAgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + list(messages)
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = llm.invoke(messages)
                print(f"[langgraph] agent_node response: tool_calls={len(response.tool_calls) if hasattr(response, 'tool_calls') and response.tool_calls else 0}", flush=True)
                return {"messages": [response]}
            except Exception as e:
                err_str = str(e).lower()
                is_tool_error = "function" in err_str or "tool" in err_str or "failed_generation" in err_str
                if not is_tool_error:
                    raise
                # Try to recover tool calls from malformed generation
                recovered = _parse_failed_generation(e)
                if recovered:
                    print(f"[langgraph] Recovered {len(recovered)} tool call(s) from failed_generation: {[c['name'] for c in recovered]}", flush=True)
                    return {"messages": [AIMessage(
                        content="",
                        tool_calls=recovered,
                    )]}
                if attempt < max_retries - 1:
                    print(f"[langgraph] Tool call generation failed (attempt {attempt + 1}), retrying: {e}", flush=True)
                    continue
                print(f"[langgraph] Tool call retries exhausted — falling back to response without tools: {e}", flush=True)
                response = base_llm.invoke(messages)
                return {"messages": [response]}

    def should_continue(state: SportsAgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(SportsAgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(SPORTS_TOOLS))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


# ---------------------------------------------------------------------------
# Event streaming: LangGraph events -> AG-UI events
# ---------------------------------------------------------------------------

def _extract_text_from_chunk(chunk: AIMessageChunk) -> str:
    """Pull plain text from an AIMessageChunk. Handles list-of-blocks for Anthropic."""
    content = chunk.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


def _extract_thinking_from_chunk(chunk: AIMessageChunk) -> str:
    """Pull native thinking/reasoning content from an AIMessageChunk.

    Currently only Anthropic Claude with extended_thinking emits thinking blocks
    in the list-of-blocks content format.
    """
    content = chunk.content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                btype = block.get("type")
                if btype == "thinking":
                    parts.append(block.get("thinking", ""))
                elif btype == "redacted_thinking":
                    parts.append("[redacted thinking]")
        return "".join(parts)
    return ""


async def stream_langgraph_events(
    graph,
    messages: list[BaseMessage],
    *,
    msg_id_seed: str | None = None,
    message_collector: list | None = None,
    expose_reasoning: bool = True,
) -> AsyncIterator[BaseEvent]:
    """Invoke the graph with the given messages and yield AG-UI events.

    Translation rules:
      on_chat_model_stream (text content)     -> TextMessageChunkEvent
      on_chat_model_stream (thinking content) -> ReasoningMessageChunkEvent
      on_chat_model_end (tool_calls)          -> ReasoningMessageChunkEvent (synthetic)
                                              + ToolCallChunkEvent
      on_tool_end                             -> ReasoningMessageChunkEvent (synthetic)
                                              + ToolCallResultEvent

    If `expose_reasoning` is True (default), synthetic ReasoningMessageChunkEvents
    are inserted before tool calls and after tool results to make the agent's
    chain-of-thought visible to the user.

    If message_collector is provided, the full AIMessage/ToolMessage objects
    produced by the graph are appended to it in execution order.
    """
    msg_id = msg_id_seed or str(uuid.uuid4())
    emitted_tool_call_ids: set[str] = set()
    text_emitted = False
    llm_call_count = 0

    async for event in graph.astream_events(
        {"messages": messages},
        version="v2",
    ):
        kind = event.get("event")
        data = event.get("data", {})

        # --- Graph node transitions ---
        if kind == "on_chain_start":
            node_name = event.get("name", "")
            if node_name in ("agent", "tools") and expose_reasoning:
                label = "🧠 Pensando..." if node_name == "agent" else "⚙️ Ejecutando tools..."
                yield ReasoningMessageChunkEvent(delta=f"**{label}**\n\n")
            continue

        # --- Recovered tool calls (manually constructed AIMessage, no on_chat_model_end) ---
        if kind == "on_chain_end":
            node_name = event.get("name", "")
            if node_name == "agent":
                output = data.get("output", {})
                msgs = output.get("messages", []) if isinstance(output, dict) else []
                for m in msgs:
                    if isinstance(m, AIMessage) and m.tool_calls and not any(
                        tc.get("id", "") in emitted_tool_call_ids for tc in m.tool_calls
                    ):
                        if expose_reasoning:
                            yield ReasoningMessageChunkEvent(
                                delta=f"🔄 **Recuperado {len(m.tool_calls)} tool call(s) de formato malformado:**\n\n",
                            )
                        for tc in m.tool_calls:
                            tc_id = tc.get("id") or str(uuid.uuid4())
                            if tc_id in emitted_tool_call_ids:
                                continue
                            emitted_tool_call_ids.add(tc_id)
                            tc_name = tc.get("name", "tool")
                            args_json = json.dumps(tc.get("args", {}), ensure_ascii=False)
                            if expose_reasoning:
                                yield ReasoningMessageChunkEvent(
                                    delta=f"- `{tc_name}({args_json})`\n",
                                )
                            yield ToolCallChunkEvent(
                                tool_call_id=tc_id,
                                tool_call_name=tc_name,
                                delta=args_json,
                            )
                        if expose_reasoning:
                            yield ReasoningMessageChunkEvent(delta="\n")
            continue

        # --- LLM invocation start ---
        if kind == "on_chat_model_start":
            llm_call_count += 1
            if expose_reasoning:
                suffix = "" if llm_call_count == 1 else f" (iteración {llm_call_count})"
                yield ReasoningMessageChunkEvent(
                    delta=f"💬 Consultando LLM{suffix}...\n\n",
                )
            continue

        if kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk is None:
                continue
            thinking = _extract_thinking_from_chunk(chunk)
            text = _extract_text_from_chunk(chunk)
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

        if kind == "on_chat_model_end":
            output = data.get("output")
            if isinstance(output, AIMessage):
                if message_collector is not None:
                    message_collector.append(output)
                if not text_emitted and not output.tool_calls:
                    final_text = output.content if isinstance(output.content, str) else ""
                    if not final_text and isinstance(output.content, list):
                        parts = []
                        for block in output.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                parts.append(block.get("text", ""))
                        final_text = "".join(parts)
                    if final_text:
                        text_emitted = True
                        yield TextMessageChunkEvent(
                            message_id=msg_id,
                            role="assistant",
                            delta=final_text,
                        )
                if output.tool_calls:
                    if expose_reasoning:
                        yield ReasoningMessageChunkEvent(
                            delta=f"🔧 **Decidió llamar {len(output.tool_calls)} tool(s):**\n\n",
                        )
                    for tc in output.tool_calls:
                        tc_id = tc.get("id") or str(uuid.uuid4())
                        if tc_id in emitted_tool_call_ids:
                            continue
                        emitted_tool_call_ids.add(tc_id)
                        tc_name = tc.get("name", "tool")
                        args_json = json.dumps(tc.get("args", {}), ensure_ascii=False)
                        if expose_reasoning:
                            yield ReasoningMessageChunkEvent(
                                delta=f"- `{tc_name}({args_json})`\n",
                            )
                        yield ToolCallChunkEvent(
                            tool_call_id=tc_id,
                            tool_call_name=tc_name,
                            delta=args_json,
                        )
                    if expose_reasoning:
                        yield ReasoningMessageChunkEvent(delta="\n")
                elif not output.tool_calls and expose_reasoning:
                    yield ReasoningMessageChunkEvent(
                        delta="📝 Generando respuesta final...\n\n",
                    )
            continue

        if kind == "on_tool_end":
            output = data.get("output")
            if isinstance(output, ToolMessage):
                if message_collector is not None:
                    message_collector.append(output)
                content = output.content
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False, default=str)
                if expose_reasoning:
                    preview = content[:500] + "..." if len(content) > 500 else content
                    yield ReasoningMessageChunkEvent(
                        delta=f"✅ **Resultado** ({len(content)} chars):\n\n```\n{preview}\n```\n\n",
                    )
                yield ToolCallResultEvent(
                    message_id=output.tool_call_id or str(uuid.uuid4()),
                    tool_call_id=output.tool_call_id or "",
                    content=content,
                    role="tool",
                )
            continue
