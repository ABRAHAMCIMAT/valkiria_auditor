"""
Fine-tuning targets: one adapter per agent, each with its own base model.
The system prompt is the one the agent uses in production, so the adapter is
trained on the same instructions it will receive.
"""

import importlib.util
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "agentcore" / "shared" / "prompts"

SUB_AGENT_BASE = "mistralai/Ministral-3-8B-Instruct-2512"
ORCHESTRATOR_BASE = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"

AGENTS = {
    "planning": {"base_model": SUB_AGENT_BASE, "prompt": "planning"},
    "evidence": {"base_model": SUB_AGENT_BASE, "prompt": "evidence"},
    "controls_a5": {"base_model": SUB_AGENT_BASE, "prompt": "organizational_controls", "domain": "A.5", "controls": 37},
    "controls_a6": {"base_model": SUB_AGENT_BASE, "prompt": "people_controls", "domain": "A.6", "controls": 8},
    "controls_a7": {"base_model": SUB_AGENT_BASE, "prompt": "physical_controls", "domain": "A.7", "controls": 14},
    "controls_a8": {"base_model": SUB_AGENT_BASE, "prompt": "technological_controls", "domain": "A.8", "controls": 34},
    "consolidation": {"base_model": ORCHESTRATOR_BASE, "prompt": "consolidation"},
}

ANNEX_A_2022 = {
    f"{config['domain']}.{number}"
    for config in AGENTS.values() if "domain" in config
    for number in range(1, config["controls"] + 1)
}


def system_prompt(agent: str) -> str:
    """Load the production system prompt of an agent."""
    path = PROMPTS_DIR / f"{AGENTS[agent]['prompt']}.py"
    spec = importlib.util.spec_from_file_location(f"prompt_{agent}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SYSTEM_PROMPT
