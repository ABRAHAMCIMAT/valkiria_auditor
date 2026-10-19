"""
Unit tests for shared agent tools (RAG, DynamoDB, S3).
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from moto import mock_aws
import boto3


class TestRAGTools:
    """Tests for the RAG knowledge base tools."""

    def test_query_knowledge_base_no_kb_configured(self, monkeypatch):
        """Returns error when KNOWLEDGE_BASE_ID is empty."""
        monkeypatch.setenv("KNOWLEDGE_BASE_ID", "")

        # Re-import to pick up env change
        import importlib
        import backend.agentcore.shared.tools.rag_tools as rag_mod
        importlib.reload(rag_mod)

        result = rag_mod.query_knowledge_base._tool_func(question="test question")
        assert "error" in result
        assert result["answer"] == ""
        assert result["sources"] == []

    def test_query_knowledge_base_success(self, mock_bedrock_rag, monkeypatch):
        """Returns structured answer with sources on success."""
        monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-test-123")

        with patch("boto3.client") as mock_boto:
            mock_client_instance = MagicMock()
            mock_client_instance.retrieve_and_generate.return_value = mock_bedrock_rag
            mock_boto.return_value = mock_client_instance

            # Reload the module to pick up new env and patched client
            import importlib
            import backend.agentcore.shared.tools.rag_tools as rag_mod
            with patch.object(rag_mod, "bedrock_agent_runtime", mock_client_instance):
                with patch.object(rag_mod, "KNOWLEDGE_BASE_ID", "kb-test-123"):
                    result = rag_mod.query_knowledge_base._tool_func(question="What is A.5.1?")

                    assert result["answer"] != ""
                    assert result["source_count"] >= 1
                    assert isinstance(result["sources"], list)

    def test_retrieve_control_evidence_no_kb(self, monkeypatch):
        """Returns error when KB not configured."""
        monkeypatch.setenv("KNOWLEDGE_BASE_ID", "")

        import importlib
        import backend.agentcore.shared.tools.rag_tools as rag_mod
        importlib.reload(rag_mod)

        result = rag_mod.retrieve_control_evidence._tool_func(control_id="A.5.1")
        assert "error" in result


class TestDynamoDBTools:
    """Tests for DynamoDB persistence tools."""

    @mock_aws
    def test_save_audit_finding(self, sample_finding):
        """Successfully saves a finding to DynamoDB."""
        # Create table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="AuditFindings",
            KeySchema=[
                {"AttributeName": "finding_id", "KeyType": "HASH"},
                {"AttributeName": "audit_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "finding_id", "AttributeType": "S"},
                {"AttributeName": "audit_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Patch the module-level dynamodb resource
        with patch("backend.agentcore.shared.tools.dynamodb_tools.dynamodb", dynamodb):
            from backend.agentcore.shared.tools.dynamodb_tools import save_audit_finding
            result = save_audit_finding._tool_func(**sample_finding)

            assert result["status"] == "saved"
            assert result["finding_id"] == "NC-001"
            assert result["audit_id"] == "test_audit_001"

    @mock_aws
    def test_list_audit_findings_empty(self):
        """Returns empty list when no findings exist."""
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="AuditFindings",
            KeySchema=[
                {"AttributeName": "finding_id", "KeyType": "HASH"},
                {"AttributeName": "audit_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "finding_id", "AttributeType": "S"},
                {"AttributeName": "audit_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "audit_id-index",
                    "KeySchema": [
                        {"AttributeName": "audit_id", "KeyType": "HASH"},
                        {"AttributeName": "finding_id", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )

        with patch("backend.agentcore.shared.tools.dynamodb_tools.dynamodb", dynamodb):
            from backend.agentcore.shared.tools.dynamodb_tools import list_audit_findings
            result = list_audit_findings._tool_func(audit_id="nonexistent")

            assert result["count"] == 0
            assert result["findings"] == []

    @mock_aws
    def test_get_document_metadata_not_found(self):
        """Returns error when document not found."""
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="Documents",
            KeySchema=[{"AttributeName": "document_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "document_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        with patch("backend.agentcore.shared.tools.dynamodb_tools.dynamodb", dynamodb):
            from backend.agentcore.shared.tools.dynamodb_tools import get_document_metadata
            result = get_document_metadata._tool_func(document_id="nonexistent-doc")

            assert "error" in result


class TestS3Tools:
    """Tests for S3 storage tools."""

    @mock_aws
    def test_save_report_to_s3(self, monkeypatch):
        """Successfully saves a report to S3."""
        monkeypatch.setenv("BUCKET_NAME", "test-iso27001-bucket")

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-iso27001-bucket")

        with patch("backend.agentcore.shared.tools.s3_tools.s3_client", s3):
            with patch("backend.agentcore.shared.tools.s3_tools.BUCKET_NAME", "test-iso27001-bucket"):
                from backend.agentcore.shared.tools.s3_tools import save_report_to_s3

                result = save_report_to_s3._tool_func(
                    report_content='{"findings": []}',
                    report_type="domain_report",
                    audit_id="test_audit_001",
                    file_format="json",
                )

                assert result["status"] == "saved"
                assert "s3_key" in result
                assert result["audit_id"] == "test_audit_001"
                assert "audits/test_audit_001/domain_report/" in result["s3_key"]

    @mock_aws
    def test_get_document_content(self, monkeypatch):
        """Successfully retrieves document content from S3."""
        monkeypatch.setenv("BUCKET_NAME", "test-iso27001-bucket")

        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-iso27001-bucket")
        s3.put_object(
            Bucket="test-iso27001-bucket",
            Key="raw/test_doc.json",
            Body=json.dumps({"test": "data"}).encode(),
            ContentType="application/json",
        )

        with patch("backend.agentcore.shared.tools.s3_tools.s3_client", s3):
            with patch("backend.agentcore.shared.tools.s3_tools.BUCKET_NAME", "test-iso27001-bucket"):
                from backend.agentcore.shared.tools.s3_tools import get_document_content

                result = get_document_content._tool_func(s3_key="raw/test_doc.json")

                assert result["content"] == {"test": "data"}
                assert result["content_type"] == "application/json"

    def test_save_report_no_bucket(self, monkeypatch):
        """Returns error when BUCKET_NAME is empty."""
        monkeypatch.setenv("BUCKET_NAME", "")

        with patch("backend.agentcore.shared.tools.s3_tools.BUCKET_NAME", ""):
            from backend.agentcore.shared.tools.s3_tools import save_report_to_s3
            result = save_report_to_s3._tool_func(
                report_content="test",
                report_type="test",
                audit_id="test",
            )
            assert "error" in result
