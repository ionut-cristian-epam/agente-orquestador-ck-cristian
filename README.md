# Agent Harness Orchestrator

Python-native orchestrator for managing parallel AI coding agent sessions over the [Agent Client Protocol (ACP)](https://agentcommunicationprotocol.dev).

Instead of wrapping terminals and scraping ANSI output, this project talks to coding agents through [`acpx`](https://www.npmjs.com/package/acpx) — a headless CLI client that converts ACP protocol messages into structured, typed interactions. One orchestrator, many agents.

---

## Features

- **Multi-agent sessions** — Run multiple agents in parallel, each with its own model, working directory, and config
- **90+ supported models** — AWS Bedrock (Claude, Llama, Mistral, Qwen, DeepSeek, ...) and OpenCode free tier
- **15+ agent harnesses** — OpenCode, Claude Code, Codex, Gemini, Cursor, Copilot, Kiro, and more via `acpx`
- **Structured output** — Typed ACP messages (thinking, tool calls, diffs) instead of raw text
- **Persistent sessions** — Sessions survive across invocations, crash-recover automatically
- **Dynamic model config** — Model is validated and injected into `opencode.json` at session creation

---

## Prerequisites

| Requirement | Version | Install |
|-------------|---------|---------|
| Python | 3.8+ | [python.org](https://python.org/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| acpx | latest | `npm install -g acpx@latest` |
| OpenCode | latest | `npm install -g opencode-ai@latest` |

For AWS Bedrock models, configure your AWS credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`).

---

## Installation

```bash
git clone https://github.com/your-org/agent-harness-orchestrator.git
cd agent-harness-orchestrator

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Quick Start

### Create and prompt a session

```python
from launch_session_opencode import Session
import os

session = Session(
    name="my_agent",
    working_dir=os.path.join(os.path.dirname(__file__), "agent_debugging"),
    LLM="amazon-bedrock/anthropic.claude-sonnet-4-6"
)

# Send a prompt and capture the response
response = session.prompt_session("Fix the failing test in test_auth.py", capture_output=True)
print(response)

# Send a prompt with real-time streaming output
session.prompt_session("Now add edge case tests for empty credentials")

# Clean up
session.close_session()
```

### Run multiple agents

```python
debugging = Session(
    name="agent_debugging",
    working_dir="./agent_debugging",
    LLM="amazon-bedrock/anthropic.claude-sonnet-4-6"
)

documentation = Session(
    name="agent_documentation",
    working_dir="./agent_documentation",
    LLM="amazon-bedrock/moonshot.kimi-k2-thinking"
)

deb = debugging.prompt_session("What is your LLM", capture_output=True)
doc = documentation.prompt_session("What is your LLM", capture_output=True)

print(f"Debugging: {deb}")
print(f"Documentation: {doc}")

debugging.close_session()
documentation.close_session()
```

### Clean up sessions

```python
from remove_session import remove_session, remove_all_sessions

# Remove a specific session
remove_session("agent_debugging")

# Remove all sessions
remove_all_sessions()
```

---

## Project Structure

```
agent-harness-orchestrator/
├── launch_session_opencode.py   # Session class — create, prompt, close agent sessions
├── remove_session.py            # Session cleanup — remove by name or remove all
├── requirements.txt             # Python dependencies
├── agent_debugging/
│   └── opencode.json            # Model config (written dynamically per session)
├── agent_documentation/
│   └── opencode.json            # Model config (written dynamically per session)
└── docs/
    ├── concept.md               # Problem statement, vision, key differentiators
    ├── technology-stack.md      # ACP, acpx, OpenCode, planned tools (githubkit, Textual, FastAPI)
    └── architecture-overview.md # System architecture, data flow, session lifecycle, roadmap
```

---

## API Reference

### `Session(name, working_dir, LLM, capture_output)`

Creates a new agent session.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | Session name (used for `acpx -s <name>`) |
| `working_dir` | `str` | — | Agent's working directory (contains `opencode.json`) |
| `LLM` | `str` | `"opencode/nemotron-3-super-free"` | Model identifier (validated against `SUPPORTED_MODELS`) |
| `capture_output` | `bool` | `True` | Capture or stream stdout during session creation |

### `session.prompt_session(prompt, capture_output)`

Sends a prompt to the session.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | `str` | — | The prompt text to send |
| `capture_output` | `bool` | `False` | `True` = return filtered string, `False` = print in real time |

**Returns**: Filtered agent response (`str`) if `capture_output=True`, else `None`.

### `session.close_session()`

Closes the session via `acpx opencode sessions close`.

### `remove_session(session_name)`

Removes a session by name — deletes `.json` and `.stream.ndjson` files from `~/.acpx/sessions/` and updates the index.

### `remove_all_sessions()`

Removes all sessions from `~/.acpx/sessions/`.

---

## Supported Agents

Any agent with an `acpx` adapter works. To switch agents, change the `acpx opencode` commands in `Session._run()` to `acpx <agent>`:

| Agent | Command | Notes |
|-------|---------|-------|
| OpenCode | `acpx opencode` | Default — open-source, provider-agnostic |
| Claude Code | `acpx claude` | Anthropic Claude Code |
| Codex | `acpx codex` | OpenAI Codex CLI |
| Gemini | `acpx gemini` | Google Gemini CLI |
| Cursor | `acpx cursor` | Cursor CLI agent |
| Copilot | `acpx copilot` | GitHub Copilot CLI |
| Pi | `acpx pi` | Pi Coding Agent |
| Kiro | `acpx kiro` | Kiro CLI |
| Kilocode | `acpx kilocode` | Kilocode agent |
| Qwen | `acpx qwen` | Qwen Code |
| Custom | `acpx --agent <cmd>` | Any ACP-compatible server |

---

## Documentation

Detailed documentation lives in `docs/`:

- **[Concept](docs/concept.md)** — Problem statement, vision, what patterns we adopt and why
- **[Technology Stack](docs/technology-stack.md)** — ACP protocol, acpx, OpenCode, opencode-ai SDK, planned integrations (githubkit, Textual, FastAPI)
- **[Architecture Overview](docs/architecture-overview.md)** — System layers, data flow, session lifecycle, design decisions, future roadmap

---

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| **1** | Async + concurrent sessions (`asyncio`, `anyio`) | Planned |
| **2** | GitHub reaction loop (`githubkit` — PRs, CI webhooks, review routing) | Planned |
| **3** | Dashboard (Textual TUI → FastAPI + HTMX web UI) | Planned |
| **4** | Multi-agent coordination (task decomposition, result aggregation) | Planned |

---

## License

[MIT](LICENSE) — Copyright (c) 2026 NEORIS
