import subprocess
import os
import json
import warnings
warnings.filterwarnings("ignore")


SUPPORTED_MODELS = [
    "amazon-bedrock/anthropic.claude-3-5-haiku-20241022-v1:0",
    "amazon-bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
    "amazon-bedrock/anthropic.claude-sonnet-4-20250514-v1:0",
    "amazon-bedrock/amazon.nova-pro-v1:0",
    "amazon-bedrock/amazon.nova-lite-v1:0",
    "amazon-bedrock/amazon.nova-micro-v1:0",
    "opencode/big-pickle",
    "opencode/gpt-5-nano",
    "opencode/mimo-v2-omni-free",
    "opencode/mimo-v2-pro-free",
    "opencode/minimax-m2.5-free",
    "opencode/nemotron-3-super-free",
    "amazon-bedrock/amazon.nova-2-lite-v1:0",
    "amazon-bedrock/amazon.nova-premier-v1:0",
    "amazon-bedrock/anthropic.claude-3-5-sonnet-20240620-v1:0",
    "amazon-bedrock/anthropic.claude-3-7-sonnet-20250219-v1:0",
    "amazon-bedrock/anthropic.claude-3-haiku-20240307-v1:0",
    "amazon-bedrock/anthropic.claude-haiku-4-5-20251001-v1:0",
    "amazon-bedrock/anthropic.claude-opus-4-1-20250805-v1:0",
    "amazon-bedrock/anthropic.claude-opus-4-20250514-v1:0",
    "amazon-bedrock/anthropic.claude-opus-4-5-20251101-v1:0",
    "amazon-bedrock/anthropic.claude-opus-4-6-v1",
    "amazon-bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0",
    "amazon-bedrock/anthropic.claude-sonnet-4-6",
    "amazon-bedrock/deepseek.r1-v1:0",
    "amazon-bedrock/deepseek.v3-v1:0",
    "amazon-bedrock/deepseek.v3.2",
    "amazon-bedrock/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
    "amazon-bedrock/eu.anthropic.claude-opus-4-5-20251101-v1:0",
    "amazon-bedrock/eu.anthropic.claude-opus-4-6-v1",
    "amazon-bedrock/eu.anthropic.claude-sonnet-4-20250514-v1:0",
    "amazon-bedrock/eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "amazon-bedrock/eu.anthropic.claude-sonnet-4-6",
    "amazon-bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0",
    "amazon-bedrock/global.anthropic.claude-opus-4-5-20251101-v1:0",
    "amazon-bedrock/global.anthropic.claude-opus-4-6-v1",
    "amazon-bedrock/global.anthropic.claude-sonnet-4-20250514-v1:0",
    "amazon-bedrock/global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "amazon-bedrock/global.anthropic.claude-sonnet-4-6",
    "amazon-bedrock/google.gemma-3-12b-it",
    "amazon-bedrock/google.gemma-3-27b-it",
    "amazon-bedrock/google.gemma-3-4b-it",
    "amazon-bedrock/meta.llama3-1-405b-instruct-v1:0",
    "amazon-bedrock/meta.llama3-1-70b-instruct-v1:0",
    "amazon-bedrock/meta.llama3-1-8b-instruct-v1:0",
    "amazon-bedrock/meta.llama3-2-11b-instruct-v1:0",
    "amazon-bedrock/meta.llama3-2-1b-instruct-v1:0",
    "amazon-bedrock/meta.llama3-2-3b-instruct-v1:0",
    "amazon-bedrock/meta.llama3-2-90b-instruct-v1:0",
    "amazon-bedrock/meta.llama3-3-70b-instruct-v1:0",
    "amazon-bedrock/meta.llama4-maverick-17b-instruct-v1:0",
    "amazon-bedrock/meta.llama4-scout-17b-instruct-v1:0",
    "amazon-bedrock/minimax.minimax-m2",
    "amazon-bedrock/minimax.minimax-m2.1",
    "amazon-bedrock/minimax.minimax-m2.5",
    "amazon-bedrock/mistral.devstral-2-123b",
    "amazon-bedrock/mistral.magistral-small-2509",
    "amazon-bedrock/mistral.ministral-3-14b-instruct",
    "amazon-bedrock/mistral.ministral-3-3b-instruct",
    "amazon-bedrock/mistral.ministral-3-8b-instruct",
    "amazon-bedrock/mistral.mistral-large-3-675b-instruct",
    "amazon-bedrock/mistral.pixtral-large-2502-v1:0",
    "amazon-bedrock/mistral.voxtral-mini-3b-2507",
    "amazon-bedrock/mistral.voxtral-small-24b-2507",
    "amazon-bedrock/moonshot.kimi-k2-thinking",
    "amazon-bedrock/moonshotai.kimi-k2.5",
    "amazon-bedrock/nvidia.nemotron-nano-12b-v2",
    "amazon-bedrock/nvidia.nemotron-nano-3-30b",
    "amazon-bedrock/nvidia.nemotron-nano-9b-v2",
    "amazon-bedrock/nvidia.nemotron-super-3-120b",
    "amazon-bedrock/openai.gpt-oss-120b-1:0",
    "amazon-bedrock/openai.gpt-oss-20b-1:0",
    "amazon-bedrock/openai.gpt-oss-safeguard-120b",
    "amazon-bedrock/openai.gpt-oss-safeguard-20b",
    "amazon-bedrock/qwen.qwen3-235b-a22b-2507-v1:0",
    "amazon-bedrock/qwen.qwen3-32b-v1:0",
    "amazon-bedrock/qwen.qwen3-coder-30b-a3b-v1:0",
    "amazon-bedrock/qwen.qwen3-coder-480b-a35b-v1:0",
    "amazon-bedrock/qwen.qwen3-next-80b-a3b",
    "amazon-bedrock/qwen.qwen3-vl-235b-a22b",
    "amazon-bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "amazon-bedrock/us.anthropic.claude-opus-4-1-20250805-v1:0",
    "amazon-bedrock/us.anthropic.claude-opus-4-20250514-v1:0",
    "amazon-bedrock/us.anthropic.claude-opus-4-5-20251101-v1:0",
    "amazon-bedrock/us.anthropic.claude-opus-4-6-v1",
    "amazon-bedrock/us.anthropic.claude-sonnet-4-20250514-v1:0",
    "amazon-bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "amazon-bedrock/us.anthropic.claude-sonnet-4-6",
    "amazon-bedrock/writer.palmyra-x4-v1:0",
    "amazon-bedrock/writer.palmyra-x5-v1:0",
    "amazon-bedrock/zai.glm-4.7",
    "amazon-bedrock/zai.glm-4.7-flash",
    "amazon-bedrock/zai.glm-5",
]


class Session:
    def __init__(self, name, working_dir, LLM="opencode/nemotron-3-super-free",capture_output=True):
        self.name = name
        self.working_dir = working_dir
        self.LLM = LLM
        self._set_model_in_config()
        self.create_session(capture_output=capture_output)
    
    def _set_model_in_config(self):
        if self.LLM not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model '{self.LLM}'. "
                f"Choose from: {', '.join(SUPPORTED_MODELS)}"
            )
        config_path = os.path.join(self.working_dir, "opencode.json")
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
    
    def create_session(self,capture_output=True):
        print(f"\n--- Creating session: {self.name} (in {self.working_dir}) ---")
        self._run(["acpx", "opencode", "sessions", "new", "--name", self.name],capture_output=capture_output)

    def _filter_output(self, raw_output):
        lines = raw_output.splitlines()
        content_lines = [line for line in lines if not line.startswith('[')]
        return '\n'.join(content_lines).strip()

    def prompt_session(self, prompt, capture_output=False):
        if not capture_output:
            print(f"\n--- [{self.name}] {prompt} ---")
        raw = self._run(["acpx", "opencode", "-s", self.name, prompt], capture_output=capture_output)
        if capture_output and raw is not None:
            return self._filter_output(raw)
        return raw
    def close_session(self):
        print(f"\n--- Closing session: {self.name} ---")
        self._run(["acpx", "opencode", "sessions", "close", self.name])


if __name__ == "__main__":

    debugging_session = Session(
        name="agent_debugging",
        working_dir=os.path.join(os.path.dirname(__file__), "agent_debugging"),
        LLM= "amazon-bedrock/anthropic.claude-sonnet-4-6",
        capture_output=True
    )
    deb = debugging_session.prompt_session("What is your LLM",capture_output=True)
    print(f"Debugging Session Output:\n{deb}")
    

    documentation_session = Session(
        name="agent_documentation",
        working_dir=os.path.join(os.path.dirname(__file__), "agent_documentation"),
        LLM= "amazon-bedrock/moonshot.kimi-k2-thinking",
        capture_output=True
        
      
    )
    doc = documentation_session.prompt_session("What is your LLM",capture_output=True)
    print(f"Documentation Session Output:\n{doc}")
    debugging_session.close_session()
    documentation_session.close_session()
    