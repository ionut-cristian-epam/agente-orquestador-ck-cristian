import subprocess
import os
import socket
import time
import warnings
warnings.filterwarnings("ignore")

from opencode_ai import APIConnectionError, Opencode



class Session:
    def __init__(self, name, working_dir):
        self.name = name
        self.working_dir = working_dir
        self.create_session()
    
    def _run(self, cmd, capture_output=False):
        output_lines = []
        with subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True, 
            shell=True,
            cwd=self.working_dir
        ) as proc:
            for line in proc.stdout:
                if capture_output:
                    output_lines.append(line)
                else:
                    print(line, end="")
        
        return ''.join(output_lines) if capture_output else None
    
    def create_session(self):
        print(f"\n--- Creating session: {self.name} (in {self.working_dir}) ---")
        self._run(["acpx", "opencode", "sessions", "new", "--name", self.name])

    def prompt_session(self, prompt, capture_output=False):
        if not capture_output:
            print(f"\n--- [{self.name}] {prompt} ---")
        return self._run(["acpx", "opencode", "-s", self.name, prompt], capture_output=capture_output)
    def close_session(self):
        print(f"\n--- Closing session: {self.name} ---")
        self._run(["acpx", "opencode", "sessions", "close", self.name])


if __name__ == "__main__":
    # Launch session for agent_debugging (with md-to-pdf skill)
    debugging_session = Session(
        name="agent_debugging",
        working_dir=os.path.join(os.path.dirname(__file__), "agent_debugging")
    )
    debugging_session.prompt_session("What is your LLM")
    
    # Launch session for agent_documentation (with executing-plans skill)
    documentation_session = Session(
        name="agent_documentation",
        working_dir=os.path.join(os.path.dirname(__file__), "agent_documentation")
    )
    documentation_session.prompt_session("What is your LLM")

    debugging_session.close_session()
    documentation_session.close_session()
    