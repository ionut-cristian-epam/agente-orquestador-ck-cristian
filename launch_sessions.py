import subprocess
import os
import json
import warnings
warnings.filterwarnings("ignore")

from available_models import SUPPORTED_MODELS_OPENCODE, SUPPORTED_MODELS_COPILOT_CLI

class Session:
    def __init__(self, agent_harness,name,working_dir, LLM="opencode/nemotron-3-super-free",capture_output=True):
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
            shell=True,
            cwd=self.working_dir
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
    
    def create_session(self,capture_output=True):
        print(f"\n--- Creating session: {self.name} (in {self.working_dir}) ---")
        self._run(["acpx", self.agent_harness, "sessions", "new", "--name", self.name],capture_output=capture_output)

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
    def close_session(self):
        print(f"\n--- Closing session: {self.name} ---")
        self._run(["acpx", self.agent_harness, "sessions", "close", self.name])


if __name__ == "__main__":

    debugging_session = Session(
        agent_harness="opencode",
        name="agent_debugging",
        working_dir=os.path.join(os.path.dirname(__file__), "agent_debugging"),
        LLM= "opencode/gpt-5-nano",
        capture_output=True
    )
    deb = debugging_session.prompt_session("What is your LLM",capture_output=True)
    print(f"Debugging Session Output:\n{deb}")
    

    # documentation_session = Session(
    #     name="agent_documentation",
    #     working_dir=os.path.join(os.path.dirname(__file__), "agent_documentation"),
    #     LLM= "amazon-bedrock/moonshot.kimi-k2-thinking",
    #     capture_output=True
        
      
    # )
    # doc = documentation_session.prompt_session("What is your LLM",capture_output=True)
    # print(f"Documentation Session Output:\n{doc}")
    debugging_session.close_session()
    # documentation_session.close_session()
    