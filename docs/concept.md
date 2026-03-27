# Concept — Agent Harness Orchestrator

**Purpose**: Explain the core idea, the problem being solved.

---

## Problem Statement

Running a single AI coding agent in a terminal is straightforward. Running multiple agents across different tasks, repositories, and models is a coordination problem:

- **Manual session management**: Each agent needs its own session created, tracked, and cleaned up. Without an orchestrator, you open separate terminals, remember which agent runs where, and manually close everything when done.
- **PTY scraping is fragile**: Traditional approaches wrap agent terminals in tmux/screen and scrape ANSI output. This breaks on multi-line tool calls, loses structured data (diffs, tool results, thinking steps), and requires parsing heuristics that differ per agent.
- **No structured communication**: Without a protocol, the orchestrator can't reliably distinguish between agent thinking, tool calls, tool results, and final output. It's all raw text.
- **Agent lock-in**: Most orchestrators are tightly coupled to one agent (e.g., Claude Code, Codex). Switching agents means rewriting the integration layer.
- **State fragmentation**: Session state, conversation history, and agent metadata end up scattered across tmux panes, log files, and ad-hoc metadata files with no unified access pattern.

## Vision

**Agent Harness Orchestrator** is a Python-native system that manages parallel AI coding agent sessions over the **Agent Client Protocol (ACP)** — a structured, REST-based protocol for agent communication.

Instead of wrapping terminals and scraping output, the orchestrator talks to agents through `acpx` — a headless CLI client that converts ACP protocol messages into a clean command-line interface. Every interaction (create session, send prompt, read response, close session) goes through a typed protocol, not raw text parsing.

The result:

- **One orchestrator, many agents**: The same `Session` class works with OpenCode, Codex, Claude Code, Gemini, Cursor, Copilot, and 10+ other agents — all via `acpx <agent>`.
- **Structured responses**: Agent output arrives as typed ACP messages — thinking steps, tool calls, diffs, and final text — not ANSI character streams.
- **Persistent sessions**: Sessions survive across invocations and crash-recover automatically. Named sessions enable parallel workstreams in the same project.
- **Python-first**: The entire orchestration layer is Python — easy to extend, test, and integrate with existing Python tooling (CI pipelines, REST APIs, data processing).

### What we take from it

| Concept | Reference Implementation | Our Adaptation |
|---------|--------------------------|----------------|
| **Session lifecycle** | State machine: spawning → working → pr_open → ci_failed → review → merge → done | Same state progression, implemented in Python with ACP session states |
| **Agent-agnostic design** | 8 plugin slots (Runtime, Agent, Workspace, Tracker, SCM, Notifier, Terminal, Lifecycle) | Agent-agnostic via ACP — any `acpx`-supported harness works without a custom plugin |
| **Reaction system** | Polling GitHub for CI failures and review comments, routing events back to agents | Same pattern: CI / review events trigger agent re-prompting |
| **Per-project isolation** | Git worktrees with hash-based namespacing | Per-agent working directories with independent `opencode.json` configs |
| **Prompt assembly** | 3-layer system: base instructions + project context + user rules | Equivalent layering via ACP session context and agent-specific skills |

## Key Differentiators

### 1. ACP-First Architecture

Every agent interaction goes through the Agent Client Protocol. This means:
- Structured JSON messages instead of ANSI text streams
- Built-in session persistence and crash recovery
- Prompt queueing — submit work while an agent is busy
- Cooperative cancellation via `session/cancel`
- Mode switching and config changes via `session/set_mode` and `session/set_config_option`

### 2. Universal Agent Support via `acpx`

`acpx` provides ACP adapters for 15+ coding agents out of the box:

| Agent | Command | Description |
|-------|---------|-------------|
| OpenCode | `acpx opencode` | Open-source, provider-agnostic coding agent |
| Codex | `acpx codex` | OpenAI Codex CLI |
| Claude Code | `acpx claude` | Anthropic Claude Code |
| Gemini | `acpx gemini` | Google Gemini CLI |
| Cursor | `acpx cursor` | Cursor CLI agent |
| Copilot | `acpx copilot` | GitHub Copilot CLI |
| Pi | `acpx pi` | Pi Coding Agent |
| Kiro | `acpx kiro` | Kiro CLI |
| Kilocode | `acpx kilocode` | Kilocode agent |
| Custom | `acpx --agent ./my-server` | Any ACP-compatible server |

Adding a new agent requires zero orchestrator changes — just `acpx <new-agent> "do work"`.

### 3. Python-Native

- No Node.js/TypeScript toolchain required
- Integrates naturally with Python CI/CD pipelines, REST frameworks, and data tools
- Dependencies are minimal: `pydantic`, `httpx`, `anyio`
- The `opencode-ai` Python SDK provides direct REST API access when CLI isn't sufficient

### 4. Lightweight by Design

The current orchestrator is two files:
- `launch_session_opencode.py` — Create sessions, send prompts, close sessions
- `remove_session.py` — Clean up session storage

This is intentional. The goal is to build the minimum viable orchestration layer first, then grow toward the richer feature set (reactions, CI integration, dashboard) as needs emerge.

## What This Project Is Not

- **Not a general-purpose agent framework**: It orchestrates coding agent sessions, not arbitrary AI workflows.
- **Not a replacement for the agents themselves**: OpenCode, Codex, Claude Code do the actual coding work. This project manages their sessions.
- **Not a dashboard (yet)**: The current interface is programmatic Python. A web dashboard is a future goal, not a launch requirement.
- **Not tied to a single LLM provider**: Through `acpx` and agent-specific configs, any model supported by any agent harness is usable.

## Summary

Agent Harness Orchestrator manages parallel AI coding agent sessions in Python on top of the Agent Client Protocol. It applies proven orchestration patterns — session lifecycle management, agent-agnostic design, reaction-based automation — through a structured protocol that talks to 15+ coding agents instead of per-agent terminal scraping.
