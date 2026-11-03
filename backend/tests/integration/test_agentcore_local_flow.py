"""
Integration test of the orchestrator flow over real HTTP, without AWS.

Each sub-agent runs its real AgentCore app on a local port (only the LLM is
replaced), and the real orchestrator Agent runs with a scripted model that calls
every sub-agent tool. This is the LOCAL_DEV path documented in IMPLEMENTATION.md.
"""

import importlib.util
import socket
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
import uvicorn
from strands.models import Model

AGENTCORE_DIR = Path(__file__).resolve().parents[2] / "agentcore"
sys.path.insert(0, str(AGENTCORE_DIR))

SUB_AGENTS = {
    "PLANNING": "planning_agent",
    "EVIDENCE": "evidence_agent",
    "ORG_CONTROLS": "organizational_controls_agent",
    "PEOPLE_CONTROLS": "people_controls_agent",
    "PHYSICAL_CONTROLS": "physical_controls_agent",
    "TECH_CONTROLS": "technological_controls_agent",
}
TOOLS_IN_ORDER = [
    "invoke_planning_agent",
    "invoke_evidence_agent",
    "invoke_organizational_controls_agent",
    "invoke_people_controls_agent",
    "invoke_physical_controls_agent",
    "invoke_technological_controls_agent",
]


def load_agent_module(agent_dir):
    spec = importlib.util.spec_from_file_location(f"{agent_dir}_main", AGENTCORE_DIR / agent_dir / "src" / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ScriptedModel(Model):
    """Calls each tool once, in order, then ends with the tool results it received."""

    def __init__(self, tools):
        self.pending = list(tools)
        self.tool_results = []

    def update_config(self, **model_config):
        pass

    def get_config(self):
        return {}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        for content in messages[-1]["content"]:
            if "toolResult" in content:
                self.tool_results.append(content["toolResult"])

        yield {"messageStart": {"role": "assistant"}}
        if self.pending:
            name = self.pending.pop(0)
            yield {"contentBlockStart": {"start": {"toolUse": {"name": name, "toolUseId": f"id-{name}"}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": '{"prompt": "evaluar", "session_id": "s1"}'}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": "Reporte consolidado"}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}


@pytest.fixture
def running_sub_agents(monkeypatch):
    """Serve the real app of each sub-agent, replacing only its LLM agent."""
    monkeypatch.setenv("LOCAL_DEV", "1")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.delenv("AGENTCORE_MEMORY_ID", raising=False)

    calls = {}
    servers = []
    for key, agent_dir in SUB_AGENTS.items():
        module = load_agent_module(agent_dir)
        module.load_model = MagicMock()

        def fake_agent(name=agent_dir, **kwargs):
            calls[name] = kwargs["tools"]
            return MagicMock(return_value=f"resultado de {name}")

        module.Agent = fake_agent
        port = free_port()
        monkeypatch.setenv(f"{key}_AGENT_ENDPOINT", f"http://127.0.0.1:{port}/invocations")
        monkeypatch.delenv(f"{key}_AGENT_ARN", raising=False)

        server = uvicorn.Server(uvicorn.Config(module.app, host="127.0.0.1", port=port, log_level="error"))
        threading.Thread(target=server.run, daemon=True).start()
        servers.append((server, port))

    for _, port in servers:
        for _ in range(100):
            try:
                if httpx.get(f"http://127.0.0.1:{port}/ping", timeout=1).status_code == 200:
                    break
            except httpx.TransportError:
                time.sleep(0.05)
        else:
            pytest.fail(f"Sub-agent on port {port} did not start")

    yield calls

    for server, _ in servers:
        server.should_exit = True


def test_orchestrator_reaches_every_sub_agent_over_http(running_sub_agents):
    orchestrator = load_agent_module("consolidation_agent")
    model = ScriptedModel(TOOLS_IN_ORDER)
    orchestrator.load_model = lambda **kwargs: model

    result = orchestrator.invoke({"prompt": "Auditoría completa", "session_id": "s1"})

    assert result["response"].strip() == "Reporte consolidado"
    assert set(running_sub_agents) == set(SUB_AGENTS.values())

    results = "\n".join(str(tool_result) for tool_result in model.tool_results)
    assert len(model.tool_results) == len(TOOLS_IN_ORDER)
    for agent_dir in SUB_AGENTS.values():
        assert f"resultado de {agent_dir}" in results
    assert "Sub-agent invocation failed" not in results


def test_unreachable_sub_agent_reaches_the_model_as_not_evaluated(running_sub_agents, monkeypatch):
    monkeypatch.setenv("PHYSICAL_CONTROLS_AGENT_ENDPOINT", f"http://127.0.0.1:{free_port()}/invocations")
    orchestrator = load_agent_module("consolidation_agent")
    model = ScriptedModel(["invoke_physical_controls_agent"])
    orchestrator.load_model = lambda **kwargs: model

    orchestrator.invoke({"prompt": "Auditoría", "session_id": "s1"})

    assert "NOT EVALUATED" in str(model.tool_results[0])
