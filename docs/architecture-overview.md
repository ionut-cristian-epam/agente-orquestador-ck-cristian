# Architecture Overview — Agent Harness Orchestrator

**Purpose**: How the system is structured today and where it's headed.

---

## System Architecture

The orchestrator follows a **three-layer architecture**: a Python orchestration layer communicates with coding agents through `acpx`, which handles the ACP protocol translation.

```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                     │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │  Session Manager  │  │  Model Config (opencode.json)│ │
│  │  (Python)         │  │  SUPPORTED_MODELS validation │ │
│  └────────┬─────────┘  └──────────────────────────────┘ │
│           │                                              │
├───────────┼──────────────────────────────────────────────┤
│           ▼             CLI Layer                         │
│  ┌──────────────────┐                                    │
│  │  acpx (npm)      │  ACP protocol ↔ CLI translation   │
│  │  Session storage  │  ~/.acpx/sessions/                │
│  └────────┬─────────┘                                    │
│           │                                              │
├───────────┼──────────────────────────────────────────────┤
│           ▼             Agent Layer                       │
│  ┌──────────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │ OpenCode (default)│  │ Claude Code  │  │ Codex / ... ││
│  └────────┬─────────┘  └──────┬──────┘  └──────┬──────┘│
│           │                    │                 │        │
├───────────┼────────────────────┼─────────────────┼───────┤
│           ▼                    ▼                 ▼        │
│  ┌──────────────────────────────────────────────────────┐│
│  │         LLM Providers (Bedrock, OpenAI, Google, ...) ││
│  └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**Key insight**: The orchestrator never touches the ACP protocol directly. It issues CLI commands to `acpx`, which handles session management, message serialization, and protocol translation. This means switching agents requires only changing the `acpx` subcommand — no orchestrator code changes.

---

## Components

### Session Class

The `Session` class in [launch_session_opencode.py](../launch_session_opencode.py) is the core orchestration unit. It manages the full agent lifecycle:

```python
class Session:
    def __init__(self, name, working_dir, LLM="opencode/nemotron-3-super-free", capture_output=True):
        self.name = name
        self.working_dir = working_dir
        self.LLM = LLM
        self._set_model_in_config()       # Write model to opencode.json
        self.create_session(capture_output)  # acpx sessions new

    def _set_model_in_config(self):       # Validate LLM against SUPPORTED_MODELS, write opencode.json
    def _run(self, cmd, capture_output):  # subprocess.Popen with line-by-line stdout streaming
    def create_session(self, capture_output):  # acpx opencode sessions new --name <name>
    def _filter_output(self, raw_output):      # Strip lines starting with '[' (acpx metadata)
    def prompt_session(self, prompt, capture_output):  # acpx opencode -s <name> "<prompt>"
    def close_session(self):              # acpx opencode sessions close <name>
```

**Model validation**: Before creating a session, `_set_model_in_config()` validates the requested LLM against a `SUPPORTED_MODELS` list (~90 models across AWS Bedrock and OpenCode free tier). Invalid models raise a `ValueError` immediately — fail fast, no wasted API calls.

**Config injection**: The model is written to `opencode.json` in the agent's working directory before launching the session. This is how OpenCode knows which LLM to use.

**Output filtering**: `_filter_output()` strips `acpx` metadata lines (those starting with `[`) from raw output, returning only the agent's actual response content.

### Session Cleanup

[remove_session.py](../remove_session.py) handles session cleanup by directly manipulating `acpx`'s storage:

1. Read `~/.acpx/sessions/index.json`
2. Find the session entry by name
3. Delete the associated `.json` and `.stream.ndjson` files
4. Remove the entry from `index.json`
5. Write the updated index back

Provides both `remove_session(name)` for single sessions and `remove_all_sessions()` for full cleanup.

### Agent Configuration

Each agent type has its own directory with an `opencode.json` config file:

```
agent_debugging/
└── opencode.json    # Model config for the debugging agent

agent_documentation/
└── opencode.json    # Model config for the documentation agent
```

The config is dynamically written by `Session._set_model_in_config()`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "amazon-bedrock/anthropic.claude-sonnet-4-6"
}
```

---

## Data Flow

### Creating a Session

```
User / Script
      │
      ▼
Session.__init__(name, working_dir, LLM)
      │
      ├── _set_model_in_config()
      │     └── Validate LLM ∈ SUPPORTED_MODELS
      │     └── Write opencode.json in working_dir
      │
      └── create_session()
            └── _run("acpx opencode sessions new --name <name>")
                  │
                  ▼
              acpx CLI
                  │
                  ├── Creates session entry in ~/.acpx/sessions/index.json
                  ├── Creates <session-id>.json (metadata)
                  ├── Creates <session-id>.stream.ndjson (event log)
                  └── Spawns OpenCode agent process (reads opencode.json)
```

### Sending a Prompt

```
prompt_session("Fix the failing test")
      │
      └── _run("acpx opencode -s <name> 'Fix the failing test'")
            │
            ▼
        acpx CLI
            │
            ├── Looks up session by name in index.json
            ├── Serializes prompt as ACP Message
            ├── Sends to running OpenCode agent
            │
            ▼
        OpenCode Agent
            │
            ├── Sends prompt to LLM (Bedrock/OpenAI/...)
            ├── Receives LLM response
            ├── Executes tool calls (file edits, terminal, etc.)
            ├── Streams output back through ACP
            │
            ▼
        acpx CLI
            │
            ├── Translates ACP messages to text/json output
            ├── Appends to .stream.ndjson
            │
            ▼
        _run() → stdout line-by-line
            │
            ├── If capture_output=True → collect in list → _filter_output()
            └── If capture_output=False → print() each line in real time
```

### Multi-Agent Orchestration

```
__main__
      │
      ├── Session("agent_debugging", LLM="claude-sonnet-4-6")
      │     ├── prompt_session("What is your LLM")
      │     └── (keeps running)
      │
      └── Session("agent_documentation", LLM="kimi-k2-thinking")
            ├── prompt_session("What is your LLM")
            └── (keeps running)
      │
      └── debugging_session.close_session()
```

Each session runs in its own working directory with its own `opencode.json`, so agents can use different models and have isolated file system access.

---

## Session Lifecycle

### Current State: Simple Lifecycle

```
┌───────────┐      ┌───────────┐      ┌───────────┐
│  Create    │ ──── │  Prompt   │ ──── │  Close    │
│  Session   │      │  (1..N)   │      │  Session  │
└───────────┘      └───────────┘      └───────────┘
```

1. **Create**: `Session.__init__()` validates model, writes config, calls `acpx sessions new`
2. **Prompt**: `prompt_session()` sends prompts, optionally captures/filters output
3. **Close**: `close_session()` or `remove_session()` tears down the session

### Target State: Full Lifecycle (Planned)

```
┌───────────┐      ┌───────────┐      ┌───────────┐      ┌───────────┐
│  Create    │ ──── │  Prompt   │ ──── │  Observe  │ ──── │  React    │
│  Session   │      │  (1..N)   │      │  Output   │      │  to Event │
└───────────┘      └───────────┘      └───────────┘      └───────────┘
                                             │                   │
                                             │    ┌──────────┐   │
                                             └────│  Close   │───┘
                                                  │  Session │
                                                  └──────────┘
```

The reaction loop is the key addition:
- **Observe**: Monitor agent output, CI status, PR reviews, webhook events
- **React**: Route events back to the agent as new prompts — CI failure → "fix this", review comment → "address this feedback"
- **Close**: Only when the task is fully complete (code merged, CI green, reviews approved)

---

## Session Storage Architecture

### Orchestrator Layer

```
agent-harness-orchestrator/
├── launch_session_opencode.py   # Session class + SUPPORTED_MODELS
├── remove_session.py            # Session cleanup utilities
├── requirements.txt             # Python dependencies
├── agent_debugging/
│   └── opencode.json            # Model config (written dynamically)
├── agent_documentation/
│   └── opencode.json            # Model config (written dynamically)
└── docs/
    ├── concept.md
    ├── technology-stack.md
    └── architecture-overview.md
```

### acpx Layer

```
~/.acpx/
├── config.json                       # Global acpx config
└── sessions/
    ├── index.json                    # Master session index
    ├── <uuid>.json                   # Per-session metadata
    └── <uuid>.stream.ndjson          # Per-session event stream
```

### Agent Layer

Each agent directory acts as an isolated workspace. The agent can read/write files within its `working_dir` but operates independently from other agents:

```
agent_debugging/
├── opencode.json                     # LLM model config
├── .opencode/                        # OpenCode state (created by agent)
└── (agent-created files)             # Code, tests, etc.
```

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Shell via `subprocess.Popen`** | Simple, synchronous model that's easy to debug. No async complexity until needed. `shell=True` allows piping and glob expansion in commands. |
| **`acpx` as CLI intermediary** | Avoids reimplementing ACP protocol in Python. Handles session persistence, crash recovery, prompt queueing. Swapping agents is a one-line change. |
| **Model validation at init** | Fail fast — catch typos and unsupported models before spawning any processes or making API calls. |
| **Config injection (opencode.json)** | Dynamic model selection per session without environment variables or CLI flags. Each agent directory gets its own config. |
| **Output filtering** | `acpx` metadata lines (timestamps, event types) are stripped to give callers clean agent output. |
| **Direct file manipulation for cleanup** | `remove_session.py` manipulates `~/.acpx/sessions/` directly rather than using `acpx` CLI, enabling bulk cleanup and index repair. |
| **Per-agent working directories** | Isolation — agents can't accidentally modify each other's files. Each directory is a self-contained workspace. |

---

## Future Architecture Direction

### Phase 1 — Async + Concurrent Sessions

Move from sequential `subprocess.Popen` to async execution:
- Replace `_run()` with `asyncio.create_subprocess_exec()`
- Enable parallel agent sessions (e.g., debugging + documentation running concurrently)
- Use `anyio` for async primitives (already in dependencies)

### Phase 2 — GitHub Reaction Loop

Add event-driven orchestration with `githubkit`:
- Create PRs from agent output
- Receive CI webhooks → route failures back to agent
- Parse review comments → forward as new prompts
- Auto-merge when conditions are met (CI green + approved)

### Phase 3 — Dashboard (Textual → FastAPI)

Real-time visibility into agent sessions:
- **Textual TUI**: Session table, live output stream, prompt input — runs in terminal and browser
- **FastAPI API**: REST/WebSocket backend for web clients, GitHub webhook receiver
- **HTMX frontend**: Server-rendered HTML with real-time updates, minimal JavaScript

### Phase 4 — Multi-Agent Coordination

Agents working together on complex tasks:
- Task decomposition: break large issues into sub-tasks, assign to specialized agents
- Result aggregation: combine outputs from multiple agents into cohesive PRs
- Conflict resolution: detect when agents modify overlapping files
- Session routing: direct prompts to the right agent based on task type
