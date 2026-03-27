# Technology Stack — Agent Harness Orchestrator

**Purpose**: Reference for every technology used in the system — what it is, why it's chosen, and how it fits.

---

## Core Protocol: Agent Client Protocol (ACP)

### What is ACP

The **Agent Client Protocol (ACP)** is an open protocol for communication between AI agents, applications, and humans. Originally developed by IBM's BeeAI team, ACP is now part of A2A under the Linux Foundation.

ACP provides a standardized RESTful API that enables agents to:

- Send and receive rich messages (text, code, files, media)
- Respond synchronously, asynchronously, or as a stream
- Expose their capabilities for discovery
- Collaborate on long-running tasks
- Maintain state across interactions via sessions

**Specification**: [agentcommunicationprotocol.dev](https://agentcommunicationprotocol.dev)  
**Source**: [github.com/i-am-bee/acp](https://github.com/i-am-bee/acp) (archived — now part of A2A)

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Agent Manifest** | Describes an agent's capabilities — name, description, metadata — for discovery without exposing implementation |
| **Run** | A single agent execution with specific inputs. Supports sync, async, or streaming |
| **Message** | The core communication structure — a sequence of ordered, multimodal parts |
| **MessagePart** | Individual content units within a Message: text, image, JSON, code diffs |
| **Await** | Lets agents pause execution to request information from the client before resuming |
| **Session** | Maintains state and conversation history across multiple interactions using session identifiers |

### Why ACP Over PTY Scraping

| Aspect | PTY Scraping | ACP |
|--------|-------------|-----|
| Output format | Raw ANSI character stream | Typed JSON messages (thinking, tool_call, diff, text) |
| Session state | Lost on terminal close | Persisted across invocations, crash-recoverable |
| Multi-agent | One tmux pane per agent, manual tracking | Named sessions, parallel workstreams, queue-aware |
| Cancellation | `Ctrl+C` / `kill` — destructive | Cooperative `session/cancel` — preserves state |
| Agent switching | Rewrite scraping logic per agent | Same protocol, any ACP-compatible agent |
| Structured data | Regex parsing of ANSI output | Native JSON with content types and metadata |

---

## CLI Layer: acpx

### What is acpx

`acpx` is a headless CLI client for the Agent Client Protocol. It translates ACP protocol messages into a clean command-line interface, so orchestrators and scripts can talk to coding agents over structured protocol instead of scraping terminal output.

**Package**: [npmjs.com/package/acpx](https://www.npmjs.com/package/acpx) (v0.3.1, MIT, 349k weekly downloads)  
**Source**: [github.com/openclaw/acpx](https://github.com/openclaw/acpx)  
**Install**: `npm install -g acpx@latest`

### Key Features

- **Persistent sessions**: Multi-turn conversations that survive across invocations, scoped per repository
- **Named sessions**: Run parallel workstreams in the same repo (`-s backend`, `-s frontend`)
- **Prompt queueing**: Submit prompts while one is already running — they execute in order
- **Cooperative cancel**: `cancel` sends ACP `session/cancel` without tearing down session state
- **Crash reconnect**: Dead agent processes are detected; sessions are reloaded automatically
- **Structured output**: Typed ACP messages (thinking, tool calls, diffs) instead of ANSI scraping
- **Output formats**: `text` (human-readable), `json` (NDJSON for automation), `quiet` (final text only)
- **Fire-and-forget**: `--no-wait` queues a prompt and returns immediately
- **Session controls**: `set-mode` and `set` for runtime configuration changes

### Commands Used in This Project

These are the actual `acpx` commands used in [launch_session_opencode.py](../launch_session_opencode.py):

```bash
# Create a new named session in a specific working directory
acpx opencode sessions new --name <session_name>

# Send a prompt to a named session
acpx opencode -s <session_name> "<prompt>"

# Close a session
acpx opencode sessions close <session_name>
```

Other useful commands for orchestration:

```bash
# List all sessions for an agent
acpx opencode sessions list

# Inspect session metadata
acpx opencode sessions show

# View turn history
acpx opencode sessions history --limit 10

# Check process status (running/dead/no-session)
acpx opencode status

# One-shot execution (no saved session)
acpx opencode exec "<prompt>"

# Idempotent session creation (create or reuse)
acpx opencode sessions ensure --name <name>
```

### Session Storage

`acpx` stores all session data under `~/.acpx/sessions/`:

```
~/.acpx/sessions/
├── index.json              # Master index: all sessions with metadata
├── <session-id>.json       # Per-session metadata (name, cwd, status, timestamps)
└── <session-id>.stream.ndjson  # Per-session event stream (prompts, responses, tool calls)
```

The `index.json` structure (referenced in [remove_session.py](../remove_session.py)):

```json
{
  "entries": [
    {
      "acpxRecordId": "<uuid>",
      "name": "agent_debugging",
      "cwd": "/path/to/agent_debugging",
      "closed": false,
      "lastUsedAt": "2026-03-27T10:00:00Z"
    }
  ],
  "files": ["<uuid>.json", "<uuid>.stream.ndjson"]
}
```

### Configuration

`acpx` reads config from two locations (later wins):

1. **Global**: `~/.acpx/config.json`
2. **Project**: `<cwd>/.acpxrc.json`

```json
{
  "defaultAgent": "opencode",
  "defaultPermissions": "approve-all",
  "ttl": 300,
  "timeout": null,
  "format": "text"
}
```

---

## Default Agent Harness: OpenCode

### What is OpenCode

**OpenCode** is an open-source AI coding agent with 131k+ GitHub stars. It provides a terminal UI and a client/server architecture that supports multiple LLM providers.

**Source**: [github.com/sst/opencode](https://github.com/sst/opencode) (by anomalyco/SST)  
**Install**: `npm i -g opencode-ai@latest` or `brew install opencode`  
**Docs**: [opencode.ai/docs](https://opencode.ai/docs)

### Key Characteristics

- **Provider-agnostic**: Works with Claude, OpenAI, Google, AWS Bedrock, local models
- **Client/server architecture**: The TUI is one client; mobile apps, remote access, and ACP are also possible
- **Built-in agents**: `build` (full-access development) and `plan` (read-only analysis)
- **100% open source** (MIT license)
- **LSP support** out of the box
- **ACP support** via `acpx opencode` — exposes OpenCode sessions through ACP protocol

### Agent Configuration

Each agent directory in this project holds an `opencode.json` that configures the model. The `Session` class automatically writes this config based on the `LLM` parameter:

```python
Session(
    name="agent_debugging",
    working_dir="./agent_debugging",
    LLM="amazon-bedrock/anthropic.claude-sonnet-4-6"
)
```

This generates:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "amazon-bedrock/anthropic.claude-sonnet-4-6"
}
```

The project supports 90+ models across AWS Bedrock and OpenCode's free tier, validated against a `SUPPORTED_MODELS` list at session creation time.

---

## Python SDK: opencode-ai

### What is it

The `opencode-ai` Python library provides REST API access to OpenCode sessions. It offers both synchronous and asynchronous clients for programmatic control.

**Package**: [pypi.org/project/opencode-ai](https://pypi.org/project/opencode-ai/) (v0.1.0a36)  
**Source**: [github.com/sst/opencode-sdk-python](https://github.com/sst/opencode-sdk-python)

### Usage

```python
from opencode_ai import Opencode

client = Opencode()
sessions = client.session.list()
```

Async:
```python
from opencode_ai import AsyncOpencode

client = AsyncOpencode()
sessions = await client.session.list()
```

Streaming:
```python
stream = client.event.list()
for events in stream:
    print(events)
```

### Role in This Project

Available as a dependency for direct REST API access. As the orchestrator grows, the SDK enables:
- Direct REST API calls when CLI overhead is undesirable
- Async session management for parallel agent orchestration
- Streaming responses for real-time agent monitoring
- Programmatic session introspection without parsing CLI output

---

## Supported Agents via acpx

`acpx` provides built-in ACP adapters for these coding agents:

| Agent | Command | Adapter | Notes |
|-------|---------|---------|-------|
| **OpenCode** | `acpx opencode` | `npx -y opencode-ai acp` | Default agent in this project |
| **Codex** | `acpx codex` | `codex-acp` | OpenAI Codex CLI |
| **Claude Code** | `acpx claude` | `claude-agent-acp` | Anthropic Claude Code |
| **Pi** | `acpx pi` | `pi-acp` | Pi Coding Agent |
| **OpenClaw** | `acpx openclaw` | native ACP bridge | OpenClaw ACP bridge |
| **Gemini** | `acpx gemini` | native (`gemini --acp`) | Google Gemini CLI |
| **Cursor** | `acpx cursor` | native (`cursor-agent acp`) | Cursor CLI agent |
| **Copilot** | `acpx copilot` | native (`copilot --acp --stdio`) | GitHub Copilot CLI |
| **Factory Droid** | `acpx droid` | native | Factory Droid |
| **iFlow** | `acpx iflow` | native (`iflow --experimental-acp`) | iFlow CLI |
| **Kilocode** | `acpx kilocode` | `npx -y @kilocode/cli acp` | Kilocode agent |
| **Kimi** | `acpx kimi` | native (`kimi acp`) | Kimi CLI |
| **Kiro** | `acpx kiro` | native (`kiro-cli acp`) | Kiro CLI |
| **Qwen** | `acpx qwen` | native (`qwen --acp`) | Qwen Code |
| **Custom** | `acpx --agent <cmd>` | any ACP server | Escape hatch |

To use a different agent, change the `acpx opencode` calls in `Session._run()` to `acpx <agent>`. No other orchestrator changes needed.

---

## GitHub Integration: githubkit

### What is githubkit

**githubkit** is a modern, fully-typed GitHub SDK for Python inspired by [octokit](https://github.com/octokit). It provides async-native access to GitHub's REST API, GraphQL API, and typed webhook event parsing.

**Package**: [pypi.org/project/githubkit](https://pypi.org/project/githubkit/) (v0.15.1)  
**Source**: [github.com/yanyongyu/githubkit](https://github.com/yanyongyu/githubkit) (MIT license)  
**Install**: `pip install githubkit`

### Why githubkit Over Alternatives

| | **githubkit** | **PyGithub** | **httpx raw** |
|---|---|---|---|
| **License** | MIT | LGPL-3.0 | — |
| **Async** | Native | No | Manual |
| **Pydantic models** | Built-in | No | Manual |
| **HTTP client** | httpx (same as this project) | requests | httpx |
| **GraphQL** | Yes | No | Manual |
| **REST API** | Auto-generated, always current | Hand-maintained | Manual |
| **Typing** | Full | Partial | Manual |
| **Webhook parsing** | Typed events | No | Manual |

githubkit uses **httpx + Pydantic** — the exact same foundation as the rest of this project. Zero new dependencies, same async patterns.

### Key Features for This Project

- **Async-native**: Same `await` pattern as `AsyncOpencode` — fits the existing `Session` class
- **Typed webhook events**: Critical for the reaction system — parse `CheckRunEvent`, `PullRequestReviewEvent`, etc. without manual JSON handling
- **GraphQL support**: Batch queries (e.g., fetch all open PRs + CI status in one call) instead of N+1 REST requests
- **REST API versioning**: Always up to date with GitHub's API, including GHEC support

### Usage

```python
from githubkit import GitHub

# Async — same pattern as the Session class
github = GitHub("<token>")
resp = await github.rest.repos.async_get("owner", "repo")
repo = resp.parsed_data
print(repo.full_name)

# Create a PR
await github.rest.pulls.async_create(
    "owner", "repo",
    title="Fix: resolve flaky test",
    head="fix/flaky-test",
    base="main",
    body="Agent-generated fix for checkout timeout"
)

# Check CI status
statuses = await github.rest.repos.async_get_combined_status_for_ref(
    "owner", "repo", "fix/flaky-test"
)
print(statuses.parsed_data.state)  # "success" | "failure" | "pending"
```

### Webhook Event Parsing (Reaction System)

```python
from githubkit.webhooks import parse

# Parse incoming webhook → typed event object
event = parse(request.headers, request.body)

# CI failure → re-prompt agent
if event.action == "completed" and event.check_run.conclusion == "failure":
    await session.prompt_session(f"CI failed: {event.check_run.output.summary}")

# Review comment → route to agent
if event.action == "submitted" and event.review.state == "changes_requested":
    await session.prompt_session(f"Review feedback: {event.review.body}")
```

### Role in This Project

githubkit enables the full **reaction lifecycle**:
1. **PR creation**: Agent finishes work → orchestrator creates PR via REST API
2. **CI monitoring**: Poll or receive webhooks for CI status → route failures back to agent
3. **Review routing**: Parse review comments → forward to agent session as prompts
4. **Merge automation**: Approved + green CI → trigger merge via API

---

## Frontend Dashboard

### Phase 1: Textual (TUI + Web)

**Textual** is a Python TUI framework that builds cross-platform terminal interfaces with a simple Python API. Apps run in the terminal **and** in the browser via `textual serve`.

**Package**: [pypi.org/project/textual](https://pypi.org/project/textual/) (v8.2.0)  
**Source**: [github.com/Textualize/textual](https://github.com/Textualize/textual) (35k stars, MIT license)  
**Install**: `pip install textual textual-dev`

#### Why Textual for Phase 1

- **Pure Python** — no JavaScript toolchain, no React/Vue build step
- **Async-native** — runs on asyncio, same as the orchestrator
- **Terminal + browser** — `textual serve` exposes any Textual app as a web page
- **Rich widget library** — DataTable, Log, Tree, Input, ProgressBar out of the box
- **Fast to build** — working session dashboard in days, not weeks

#### Dashboard Capabilities

```python
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Header, Footer, Log

class SessionDashboard(App):
    CSS = """
    Screen { layout: grid; grid-size: 2; }
    DataTable { height: 1fr; }
    Log { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable()    # Session list: name, status, agent, last prompt
        yield Log()          # Real-time agent output stream
        yield Footer()
```

Run in terminal: `python dashboard.py`  
Run in browser: `textual serve dashboard.py`

### Phase 2: FastAPI (REST/WebSocket Backend)

**FastAPI** is a high-performance Python web framework for building APIs, built on Starlette and Pydantic.

**Package**: [pypi.org/project/fastapi](https://pypi.org/project/fastapi/) (v0.135.2)  
**Source**: [github.com/fastapi/fastapi](https://github.com/fastapi/fastapi) (96.6k stars, MIT license)  
**Install**: `pip install "fastapi[standard]"`

#### Why FastAPI for Phase 2

- **Same ecosystem** — built on Pydantic + Starlette (httpx for testing), zero new paradigms
- **WebSocket support** — stream agent output to web clients in real time
- **Auto-generated API docs** — Swagger UI at `/docs`, ReDoc at `/redoc`
- **Production-ready** — used by Microsoft, Netflix, Uber at scale
- **Webhook receiver** — receive GitHub webhook events for the reaction system

#### API Surface

```python
from fastapi import FastAPI, WebSocket

app = FastAPI(title="Agent Harness Orchestrator")

@app.get("/sessions")
async def list_sessions():
    """List all active agent sessions."""
    ...

@app.post("/sessions/{name}/prompt")
async def prompt_session(name: str, prompt: str):
    """Send a prompt to a named session."""
    ...

@app.websocket("/sessions/{name}/stream")
async def stream_output(websocket: WebSocket, name: str):
    """Stream real-time agent output via WebSocket."""
    await websocket.accept()
    ...

@app.post("/webhooks/github")
async def github_webhook(request: Request):
    """Receive GitHub webhook events for CI/review reactions."""
    ...
```

#### Frontend Pairing

FastAPI serves as the **backend API**. For the web frontend:
- **HTMX** — minimal JS, server-rendered HTML with real-time updates. No build step.
- **Jinja2 templates** — bundled with FastAPI, render session dashboards server-side.

This avoids a full React/Vue SPA while still delivering a functional web UI.

---

## Python Ecosystem

### Current Dependencies

From [requirements.txt](../requirements.txt):

| Package | Version | Role |
|---------|---------|------|
| `opencode-ai` | 0.1.0a36 | Python SDK for OpenCode REST API |
| `pydantic` | 2.12.5 | Data validation and settings management |
| `pydantic_core` | 2.41.5 | Pydantic core (Rust-backed) |
| `httpx` | 0.28.1 | HTTP client (used by opencode-ai) |
| `anyio` | 4.13.0 | Async compatibility layer (asyncio/trio) |
| `certifi` | 2026.2.25 | TLS certificate bundle |
| `h11` | 0.16.0 | HTTP/1.1 protocol library |
| `httpcore` | 1.0.9 | Low-level HTTP transport |
| `idna` | 3.11 | Internationalized domain names |
| `sniffio` | 1.3.1 | Async library detection |
| `typing-inspection` | 0.4.2 | Runtime typing introspection |
| `typing_extensions` | — | Backport of typing features |
| `annotated-types` | 0.7.0 | PEP 593 Annotated type metadata |
| `distro` | 1.9.0 | OS distribution identification |

### Key Libraries Explained

**Pydantic** — Used for defining session models, configuration schemas, and validating agent responses. When the orchestrator grows beyond the current `Session` class, Pydantic models will define the session state machine, agent configs, and event types.

**httpx** — The async-capable HTTP client that powers the `opencode-ai` SDK. Also available directly for making REST calls to ACP servers when bypassing the CLI layer.

**anyio** — Provides async primitives that work with both `asyncio` and `trio`. Enables the orchestrator to manage multiple agent sessions concurrently without blocking.

---

## External Requirements

| Requirement | Purpose | Install |
|-------------|---------|---------|
| **Node.js 18+** | Required for `acpx` and agent adapters | [nodejs.org](https://nodejs.org/) |
| **npm** | Install `acpx` globally | Bundled with Node.js |
| **Python 3.8+** | Orchestrator runtime | [python.org](https://python.org/) |
| **Git** | Agent workspace management | Pre-installed on most systems |

Agent-specific:
| Agent | Requirement |
|-------|-------------|
| OpenCode | `npm i -g opencode-ai` or `brew install opencode` |
| Claude Code | Anthropic API key + `claude` CLI |
| Codex | OpenAI API key + Codex CLI |
| Gemini | Google API key + Gemini CLI |

API keys are configured through environment variables or agent-specific config files — never hardcoded in the orchestrator.

---

## Stack Summary

| Layer | Tool | Role | Status |
|-------|------|------|--------|
| **Agent protocol** | `acpx` | Headless ACP CLI — session management | In use |
| **Default agent** | OpenCode | AI coding agent (provider-agnostic) | In use |
| **Agent SDK** | `opencode-ai` | Python REST client for OpenCode | In use |
| **Data models** | Pydantic | Shared validation across all layers | In use |
| **HTTP client** | httpx | Shared async HTTP across all layers | In use |
| **Async runtime** | anyio | Concurrent session management | In use |
| **GitHub integration** | githubkit | REST + GraphQL + typed webhook events | Planned |
| **Frontend (Phase 1)** | Textual | TUI dashboard + browser via `textual serve` | Planned |
| **API backend (Phase 2)** | FastAPI | REST/WebSocket API for web dashboard | Planned |

All planned tools share the same **httpx + Pydantic** foundation — zero dependency conflicts, same async patterns everywhere.
