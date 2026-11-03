"""Tests for the deployment preflight's tool calling probe."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agentcore"))

import preflight  # noqa: E402


def answer(*blocks):
    client = MagicMock()
    client.converse.return_value = {"output": {"message": {"content": list(blocks)}}}
    return client


def test_model_that_calls_the_tool_passes():
    assert preflight.check_model(answer({"toolUse": {"name": "get_control"}}), "m") is None


def test_model_that_only_answers_text_fails():
    assert preflight.check_model(answer({"text": "A.5.1 is..."}), "m") == "did not call the tool"


def test_model_without_access_reports_the_error():
    client = MagicMock()
    client.converse.side_effect = ClientError({"Error": {"Code": "AccessDeniedException", "Message": "no"}}, "Converse")
    assert "AccessDenied" in preflight.check_model(client, "m")


def test_probe_sends_the_sampling_parameters_the_agents_use():
    client = answer({"toolUse": {"name": "get_control"}})
    preflight.check_model(client, "m")
    assert client.converse.call_args.kwargs["inferenceConfig"]["temperature"] == 0.0


class TestModelLoader:
    def _config(self, monkeypatch, model_id):
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.delenv("SAGEMAKER_ENDPOINT_NAME", raising=False)
        from shared.model_loader import load_model

        return load_model(model_id=model_id, temperature=0.0).get_config()

    def test_claude_does_not_receive_top_p_with_temperature(self, monkeypatch):
        config = self._config(monkeypatch, "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
        assert config["temperature"] == 0.0
        assert "top_p" not in config

    def test_other_models_keep_top_p(self, monkeypatch):
        config = self._config(monkeypatch, "us.amazon.nova-pro-v1:0")
        assert config["top_p"] == 0.9
