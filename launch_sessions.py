import asyncio
import json
import os
import subprocess
import sys
import warnings
from typing import AsyncIterator

from dotenv import load_dotenv
load_dotenv()

warnings.filterwarnings("ignore")

from available_models import SUPPORTED_MODELS_OPENCODE, SUPPORTED_MODELS_COPILOT_CLI


class Session:
    def __init__(self, agent_harness, name, working_dir, LLM="opencode/big-pickle", capture_output=True):
        self.agent_harness = agent_harness
        self.name = name
        self.working_dir = working_dir
        self.LLM = LLM
        if self.agent_harness == "opencode":
            self._set_model_in_config()
        self.create_session(capture_output=capture_output)
        if self.agent_harness == "copilot":
            self._set_model_copilot()

    def _set_model_in_config(self):
        if self.agent_harness == "opencode":
            SUPPORTED_MODELS = SUPPORTED_MODELS_OPENCODE
            file = "opencode.json"

        if self.LLM not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model '{self.LLM}' for {self.agent_harness}. "
                f"Choose from: {', '.join(SUPPORTED_MODELS)}"
            )
        config_path = os.path.join(self.working_dir, file)
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            config = {"$schema": "https://opencode.ai/config.json"}
        config["model"] = self.LLM
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    def _run(self, cmd, capture_output=False):
        output_lines = []
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=(sys.platform == "win32"),
            cwd=self.working_dir,
        ) as proc:
            for line in proc.stdout:
                if capture_output:
                    output_lines.append(line)
                else:
                    print(line, end="")

        return ''.join(output_lines) if capture_output else None

    def _set_model_copilot(self):
        if self.LLM not in SUPPORTED_MODELS_COPILOT_CLI:
            raise ValueError(
                f"Unsupported model '{self.LLM}' for {self.agent_harness}. "
                f"Choose from: {', '.join(SUPPORTED_MODELS_COPILOT_CLI)}"
            )
        print(f"\n--- Setting model for Copilot CLI session '{self.name}' to '{self.LLM}' ---")
        self._run(["acpx", self.agent_harness, "-s", self.name, "set", "model", self.LLM])

    def create_session(self, capture_output=True):
        print(f"\n--- Ensuring session: {self.name} (in {self.working_dir}) ---")
        self._run(
            ["acpx", self.agent_harness, "sessions", "ensure", "--name", self.name],
            capture_output=capture_output,
        )

    def _filter_output(self, raw_output):
        lines = raw_output.splitlines()
        content_lines = [line for line in lines if not line.startswith('[')]
        return '\n'.join(content_lines).strip()

    def prompt_session(self, prompt, capture_output=False):
        if not capture_output:
            print(f"\n--- [{self.name}] {prompt} ---")
        raw = self._run(["acpx", self.agent_harness, "-s", self.name, prompt], capture_output=capture_output)
        if capture_output and raw is not None:
            return self._filter_output(raw)
        return raw

    async def stream_prompt(self, prompt: str) -> AsyncIterator[dict]:
        """Stream ACP JSON-RPC events from acpx as parsed dicts.

        Uses --format json (NDJSON over stdout). Prompt sent via stdin (-f -)
        to avoid any shell-quoting concerns.

        Runs the subprocess in a thread to avoid Windows SelectorEventLoop
        limitations with asyncio.create_subprocess_*.
        """
        import queue as _queue

        cmd = [
            "acpx", "--format", "json",
            self.agent_harness, "-s", self.name,
            "-f", "-",
        ]

        q: _queue.Queue[dict | None] = _queue.Queue()

        def _run_in_thread():
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                shell=(sys.platform == "win32"),
                cwd=self.working_dir,
            )
            assert proc.stdin and proc.stdout
            proc.stdin.write(prompt.encode("utf-8"))
            proc.stdin.flush()
            proc.stdin.close()

            for raw_line in proc.stdout:
                try:
                    obj = json.loads(raw_line.decode("utf-8", errors="replace"))
                    q.put(obj)
                except json.JSONDecodeError:
                    continue
            proc.wait()
            q.put(None)  # sentinel

        loop = asyncio.get_event_loop()
        fut = loop.run_in_executor(None, _run_in_thread)

        _sentinel = object()

        def _poll_queue():
            try:
                return q.get(block=True, timeout=0.5)
            except _queue.Empty:
                return _sentinel

        while True:
            item = await loop.run_in_executor(None, _poll_queue)
            if item is _sentinel:
                if fut.done():
                    break
                continue
            if item is None:
                break
            yield item

        await fut  # propagate any thread exception

    def close_session(self):
        print(f"\n--- Closing session: {self.name} ---")
        self._run(["acpx", self.agent_harness, "sessions", "close", self.name])


if __name__ == "__main__":

    debugging_session = Session(
        agent_harness="opencode",
        name="agent_debugging",
        working_dir=os.path.join(os.path.dirname(__file__), "agent_debugging"),
        LLM="opencode/gpt-5-nano",
        capture_output=True,
    )
    deb = debugging_session.prompt_session("What is your LLM", capture_output=True)
    print(f"Debugging Session Output:\n{deb}")

    debugging_session.close_session()
