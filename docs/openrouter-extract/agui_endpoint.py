"""
FastAPI endpoint that streams AG-UI events via SSE.
Manages reasoning lifecycle (start/content/end) and tool call tracking.

This is the SSE layer between your agent and CopilotKit frontend.
Drop this into any FastAPI app.

Requirements:
    pip install fastapi uvicorn ag-ui-protocol
"""
import json
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ag_ui.core import (
    ReasoningMessageChunkEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningMessageStartEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageChunkEvent,
    ToolCallChunkEvent,
    ToolCallResultEvent,
)
from ag_ui.encoder import EventEncoder

from openrouter_agent import build_agent, stream_agui_events

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store your compiled graphs here
_graphs: dict = {}


def get_or_build_graph(name: str):
    """Lazy graph build. Customize per your agents."""
    if name not in _graphs:
        # Example: build a simple agent. Replace with your own tools/config.
        _graphs[name] = build_agent(
            model_name="anthropic/claude-sonnet-4-5",
            tools=[],  # Add your tools here
            system_prompt="You are a helpful assistant.",
        )
    return _graphs[name]


# ---------------------------------------------------------------------------
# AG-UI streaming endpoint
# ---------------------------------------------------------------------------

@app.post("/agent/{name}")
async def run_agent(name: str, request: Request):
    body = await request.json()

    # Extract last user message from AG-UI RunAgentInput
    messages_raw = body.get("messages", [])
    prompt = ""
    for msg in reversed(messages_raw):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                prompt = content
            elif isinstance(content, list):
                prompt = " ".join(
                    p.get("text", "") for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            break

    if not prompt:
        return StreamingResponse(
            iter(["event: error\ndata: No prompt found\n\n"]),
            media_type="text/event-stream",
        )

    graph = get_or_build_graph(name)

    async def event_gen():
        encoder = EventEncoder()
        run_id = str(uuid.uuid4())
        thread_id = body.get("threadId", str(uuid.uuid4()))
        msg_id = str(uuid.uuid4())
        reasoning_id = str(uuid.uuid4())
        reasoning_started = False

        # --- Run lifecycle ---
        yield encoder.encode(RunStartedEvent(runId=run_id, threadId=thread_id))

        try:
            from langchain_core.messages import HumanMessage
            input_messages = [HumanMessage(content=prompt)]

            async for ev in stream_agui_events(graph, input_messages, msg_id=msg_id):

                # --- Reasoning (thinking) lifecycle ---
                if isinstance(ev, ReasoningMessageChunkEvent):
                    if not reasoning_started:
                        yield encoder.encode(ReasoningMessageStartEvent(
                            messageId=reasoning_id,
                            role="reasoning",
                        ))
                        reasoning_started = True
                    yield encoder.encode(ReasoningMessageContentEvent(
                        messageId=reasoning_id,
                        delta=ev.delta,
                    ))
                    continue

                # --- Tool call ---
                # CopilotKit auto-wraps TOOL_CALL_CHUNK with START/ARGS/END
                if isinstance(ev, ToolCallChunkEvent):
                    ev.parent_message_id = msg_id
                    yield encoder.encode(ev)
                    continue

                # --- Tool result ---
                if isinstance(ev, ToolCallResultEvent):
                    yield encoder.encode(ev)
                    continue

                # --- Text message ---
                if isinstance(ev, TextMessageChunkEvent):
                    if reasoning_started:
                        yield encoder.encode(ReasoningMessageEndEvent(
                            messageId=reasoning_id,
                        ))
                        reasoning_started = False
                        reasoning_id = str(uuid.uuid4())
                    ev.message_id = msg_id
                    yield encoder.encode(ev)
                    continue

        except Exception as e:
            from ag_ui.core import RunErrorEvent
            yield encoder.encode(RunErrorEvent(
                runId=run_id,
                message=str(e),
            ))
        finally:
            if reasoning_started:
                yield encoder.encode(ReasoningMessageEndEvent(
                    messageId=reasoning_id,
                ))
            yield encoder.encode(RunFinishedEvent(runId=run_id, threadId=thread_id))

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
