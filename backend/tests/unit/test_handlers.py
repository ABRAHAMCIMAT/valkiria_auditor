"""
Unit tests for Lambda handlers (API Gateway → Lambda integration).
"""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestStrandsHandler:
    """Tests for the Strands Agents Lambda handler."""

    @patch("backend.strandsagents.orchestrator.run_audit")
    def test_handler_success(self, mock_run_audit, sample_lambda_event):
        """Returns 200 with valid audit result."""
        mock_run_audit.return_value = {
            "report": "Consolidated audit report...",
            "flow_metrics": {"total_time": 5.2},
        }

        from backend.strandsagents.handler import lambda_handler
        result = lambda_handler(sample_lambda_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["framework"] == "strands-agents"
        assert "report" in body

    @patch("backend.strandsagents.orchestrator.run_audit")
    def test_handler_missing_context(self, mock_run_audit):
        """Returns 400 when organization_context is missing."""
        event = {"body": json.dumps({})}

        from backend.strandsagents.handler import lambda_handler
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body

    @patch("backend.strandsagents.orchestrator.run_audit")
    def test_handler_exception(self, mock_run_audit, sample_lambda_event):
        """Returns 500 on orchestrator error."""
        mock_run_audit.side_effect = RuntimeError("Model invocation failed")

        import importlib
        import backend.strandsagents.handler as handler_mod
        with patch.object(handler_mod, "run_audit", mock_run_audit):
            result = handler_mod.lambda_handler(sample_lambda_event, None)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body
        assert "Model invocation failed" in body["error"]


class TestLangGraphHandler:
    """Tests for the LangGraph Lambda handler."""

    @patch("backend.langgraph.orchestrator.run_audit")
    def test_handler_success(self, mock_run_audit, sample_lambda_event):
        """Returns 200 with valid audit result."""
        mock_run_audit.return_value = {
            "report": "LangGraph audit report...",
            "executive_summary": "Summary...",
            "flow_metrics": {},
        }

        from backend.langgraph.handler import lambda_handler
        result = lambda_handler(sample_lambda_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["framework"] == "langgraph"

    @patch("backend.langgraph.orchestrator.run_audit")
    def test_handler_missing_context(self, mock_run_audit):
        """Returns 400 when organization_context missing."""
        event = {"body": json.dumps({"audit_type": "internal"})}

        from backend.langgraph.handler import lambda_handler
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400


class TestCrewAIHandler:
    """Tests for the CrewAI Lambda handler."""

    @patch("backend.crewai.orchestrator.run_audit")
    def test_handler_success(self, mock_run_audit, sample_lambda_event):
        """Returns 200 with valid audit result."""
        mock_run_audit.return_value = {
            "report": "CrewAI audit report...",
            "flow_metrics": {},
        }

        from backend.crewai.handler import lambda_handler
        result = lambda_handler(sample_lambda_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["framework"] == "crewai"


class TestComp2013Handler:
    """Tests for the ISO 27001:2013 comp2013 Lambda handler."""

    @patch("backend.comp2013.orchestrator.run_audit")
    def test_handler_success(self, mock_run_audit, sample_lambda_event):
        """Returns 200 with valid audit result."""
        mock_run_audit.return_value = {
            "total_controls_evaluated": 10,
            "severity_counts": {"Conforme": 5, "No conformidad menor": 3, "No conformidad mayor": 2},
            "agent_metrics": {"gobernanza": {"controls_evaluated": 10}},
            "findings": [],
            "flow_metrics": {},
        }

        from backend.comp2013.handler import lambda_handler
        result = lambda_handler(sample_lambda_event, None)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["framework"] == "comp2013"
        assert body["standard"] == "ISO/IEC 27001:2013"

    @patch("backend.comp2013.orchestrator.run_audit")
    def test_handler_missing_context(self, mock_run_audit):
        """Returns 400 when organization_context missing."""
        event = {"body": json.dumps({})}

        from backend.comp2013.handler import lambda_handler
        result = lambda_handler(event, None)

        assert result["statusCode"] == 400

    @patch("backend.comp2013.orchestrator.run_audit")
    def test_handler_with_agent_scope(self, mock_run_audit):
        """Passes agents_in_scope correctly to orchestrator."""
        mock_run_audit.return_value = {"findings": [], "flow_metrics": {}, "total_controls_evaluated": 0, "severity_counts": {}, "agent_metrics": {}}

        event = {"body": json.dumps({
            "organization_context": "Test org",
            "agents_in_scope": ["gobernanza"],
            "run_judge": True,
        })}

        import backend.comp2013.handler as handler_mod
        with patch.object(handler_mod, "run_audit", mock_run_audit):
            handler_mod.lambda_handler(event, None)

        mock_run_audit.assert_called_once()
        call_kwargs = mock_run_audit.call_args.kwargs
        assert call_kwargs["agents_in_scope"] == ["gobernanza"]
        assert call_kwargs["run_judge"] is True
