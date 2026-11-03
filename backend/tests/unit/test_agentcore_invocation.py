"""
Tests for the AgentCore orchestrator wiring: sub-agent invocation, domain
coverage, and the asynchronous audit flow used by the API.
"""

import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

AGENTCORE_DIR = Path(__file__).resolve().parents[2] / "agentcore"
sys.path.insert(0, str(AGENTCORE_DIR))

from shared import audit_status, invocation  # noqa: E402


@pytest.fixture
def orchestrator(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    path = AGENTCORE_DIR / "consolidation_agent" / "src" / "main.py"
    spec = importlib.util.spec_from_file_location("consolidation_main", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def reset_client(monkeypatch):
    monkeypatch.setattr(invocation, "_client", None)
    for key in invocation.LOCAL_PORTS:
        monkeypatch.delenv(f"{key}_AGENT_ARN", raising=False)
        monkeypatch.delenv(f"{key}_AGENT_ENDPOINT", raising=False)
    monkeypatch.delenv("LOCAL_DEV", raising=False)


class TestInvokeSubAgent:
    def test_uses_signed_runtime_call_when_arn_is_configured(self, monkeypatch):
        monkeypatch.setenv("PHYSICAL_CONTROLS_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:1:runtime/x")
        client = MagicMock()
        client.invoke_agent_runtime.return_value = {"response": io.BytesIO(b'{"response": "ok"}')}
        monkeypatch.setattr(invocation, "_client", client)

        result = invocation.invoke_sub_agent("PHYSICAL_CONTROLS", {"prompt": "p", "session_id": "s"})

        assert result == {"response": "ok"}
        kwargs = client.invoke_agent_runtime.call_args.kwargs
        assert kwargs["agentRuntimeArn"].endswith("runtime/x")
        assert json.loads(kwargs["payload"])["prompt"] == "p"

    def test_session_id_meets_api_minimum_length(self):
        assert len(invocation.runtime_session_id("s", "PEOPLE_CONTROLS")) >= 33

    def test_sub_agents_get_distinct_sessions(self):
        assert invocation.runtime_session_id("audit", "PLANNING") != invocation.runtime_session_id("audit", "EVIDENCE")

    def test_missing_arn_outside_local_dev_is_an_error_not_localhost(self):
        with patch.object(invocation.httpx, "post") as post:
            result = invocation.invoke_sub_agent("PLANNING", {"prompt": "p"})
        post.assert_not_called()
        assert result["status"] == "error"

    def test_failure_tells_orchestrator_not_to_invent_findings(self, monkeypatch):
        monkeypatch.setenv("TECH_CONTROLS_AGENT_ARN", "arn")
        client = MagicMock()
        client.invoke_agent_runtime.side_effect = RuntimeError("throttled")
        monkeypatch.setattr(invocation, "_client", client)

        result = invocation.invoke_sub_agent("TECH_CONTROLS", {"prompt": "p"})

        assert result["status"] == "error"
        assert "NOT EVALUATED" in result["instruction"]

    @pytest.mark.parametrize("key,port", list(invocation.LOCAL_PORTS.items()))
    def test_local_dev_uses_documented_port(self, monkeypatch, key, port):
        monkeypatch.setenv("LOCAL_DEV", "1")
        response = MagicMock()
        response.json.return_value = {"response": "ok"}
        with patch.object(invocation.httpx, "post", return_value=response) as post:
            invocation.invoke_sub_agent(key, {"prompt": "p"})
        assert post.call_args.args[0] == f"http://localhost:{port}/invocations"

    def test_local_ports_are_unique(self):
        assert len(set(invocation.LOCAL_PORTS.values())) == len(invocation.LOCAL_PORTS)


class TestOrchestratorCoverage:
    def test_every_annex_a_domain_has_an_invocation_tool(self, orchestrator):
        for name in ("organizational", "people", "physical", "technological"):
            assert callable(getattr(orchestrator, f"invoke_{name}_controls_agent"))

    def test_every_tool_named_in_the_prompt_exists(self, orchestrator):
        from shared.prompts.consolidation import SYSTEM_PROMPT
        import re

        for tool_name in re.findall(r"`(invoke_\w+)`", SYSTEM_PROMPT):
            assert hasattr(orchestrator, tool_name), f"{tool_name} is in the prompt but not implemented"

    def test_agent_receives_the_physical_controls_tool(self, orchestrator):
        with patch.object(orchestrator, "Agent") as agent, patch.object(orchestrator, "load_model"):
            agent.return_value.return_value = "report"
            orchestrator.invoke({"prompt": "audit"})
        assert orchestrator.invoke_physical_controls_agent in agent.call_args.kwargs["tools"]


@pytest.fixture
def audit_infra(monkeypatch):
    with mock_aws():
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        monkeypatch.setenv("AUDITS_TABLE", "Audits")
        monkeypatch.setenv("BUCKET_NAME", "reports-bucket")
        monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")
        table = boto3.resource("dynamodb").create_table(
            TableName="Audits",
            KeySchema=[
                {"AttributeName": "tenant_id", "KeyType": "HASH"},
                {"AttributeName": "id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "tenant_id", "AttributeType": "S"},
                {"AttributeName": "id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3")
        s3.create_bucket(Bucket="reports-bucket")
        table.put_item(Item={"tenant_id": "t1", "id": "a1", "estado": "en_progreso"})
        yield table, s3


class TestAsyncAudit:
    def test_async_request_returns_immediately(self, orchestrator):
        with patch.object(orchestrator, "threading") as threading_mod, \
                patch.object(orchestrator.app, "add_async_task", return_value=7):
            result = orchestrator.invoke({"async": True, "audit_id": "a1", "tenant_id": "t1", "prompt": "p"})
        assert result["status"] == "accepted"
        threading_mod.Thread.return_value.start.assert_called_once()

    def test_success_stores_report_and_completes(self, orchestrator, audit_infra):
        table, s3 = audit_infra
        payload = {"audit_id": "a1", "tenant_id": "t1", "prompt": "p"}
        with patch.object(orchestrator, "_run_audit", return_value="# Reporte"), \
                patch.object(orchestrator.app, "complete_async_task") as complete:
            orchestrator._run_audit_in_background(payload, "s", "t1", 7)

        item = table.get_item(Key={"tenant_id": "t1", "id": "a1"})["Item"]
        assert item["estado"] == "completada"
        assert s3.get_object(Bucket="reports-bucket", Key=item["report_key"])["Body"].read() == b"# Reporte"
        complete.assert_called_once_with(7)

    def test_failure_is_recorded_and_task_is_released(self, orchestrator, audit_infra):
        table, _ = audit_infra
        payload = {"audit_id": "a1", "tenant_id": "t1", "prompt": "p"}
        with patch.object(orchestrator, "_run_audit", side_effect=RuntimeError("boom")), \
                patch.object(orchestrator.app, "complete_async_task") as complete:
            orchestrator._run_audit_in_background(payload, "s", "t1", 7)

        item = table.get_item(Key={"tenant_id": "t1", "id": "a1"})["Item"]
        assert item["estado"] == "error"
        assert "boom" in item["error"]
        complete.assert_called_once_with(7)


class TestTrackAuditStatus:
    def test_records_completion(self, audit_infra):
        table, _ = audit_infra
        handler = audit_status.track_audit_status(lambda e, c: {"statusCode": 200})
        handler({"tenant_id": "t1", "audit_id": "a1"}, None)
        assert table.get_item(Key={"tenant_id": "t1", "id": "a1"})["Item"]["estado"] == "completada"

    def test_records_error_response(self, audit_infra):
        table, _ = audit_infra
        handler = audit_status.track_audit_status(lambda e, c: {"statusCode": 500, "body": "bad"})
        handler({"tenant_id": "t1", "audit_id": "a1"}, None)
        assert table.get_item(Key={"tenant_id": "t1", "id": "a1"})["Item"]["estado"] == "error"

    def test_synchronous_events_are_untouched(self, audit_infra):
        table, _ = audit_infra
        handler = audit_status.track_audit_status(lambda e, c: {"statusCode": 200})
        assert handler({"organization_context": "x"}, None) == {"statusCode": 200}
        assert table.get_item(Key={"tenant_id": "t1", "id": "a1"})["Item"]["estado"] == "en_progreso"


class TestGatewayTools:
    def _load(self, monkeypatch):
        monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        spec = importlib.util.spec_from_file_location(
            "gateway_handler", AGENTCORE_DIR / "gateway_tools" / "handler.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _context(self, name):
        context = MagicMock()
        context.client_context.custom = {"bedrockAgentCoreToolName": name}
        return context

    def test_strips_target_prefix_and_retrieves(self, monkeypatch):
        module = self._load(monkeypatch)
        module.bedrock_agent = MagicMock()
        module.bedrock_agent.retrieve.return_value = {
            "retrievalResults": [{"content": {"text": "A.5.1"}, "score": 0.9}]
        }
        result = module.lambda_handler({"query": "politicas"}, self._context("kb___query_knowledge_base"))
        assert result["results"][0]["text"] == "A.5.1"

    def test_caps_requested_results(self, monkeypatch):
        module = self._load(monkeypatch)
        module.bedrock_agent = MagicMock()
        module.bedrock_agent.retrieve.return_value = {"retrievalResults": []}
        module.lambda_handler({"query": "q", "number_of_results": 9999}, self._context("kb___query_knowledge_base"))
        config = module.bedrock_agent.retrieve.call_args.kwargs["retrievalConfiguration"]
        assert config["vectorSearchConfiguration"]["numberOfResults"] == module.MAX_RESULTS

    def test_unknown_tool_is_rejected(self, monkeypatch):
        module = self._load(monkeypatch)
        assert "error" in module.lambda_handler({}, self._context("kb___drop_everything"))
