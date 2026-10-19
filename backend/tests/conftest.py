"""
Shared fixtures for the ISO 27001 audit system test suite.
"""

import sys
import json
import os
import pytest
import boto3
from unittest.mock import patch, MagicMock
from moto import mock_aws


# ─────────────────────────────────────────────────────────────────────────────
# MOCK UNAVAILABLE THIRD-PARTY MODULES
# ─────────────────────────────────────────────────────────────────────────────

# Mock modules that may not be installable on all Python versions
_MOCK_MODULES = [
    "langgraph", "langgraph.graph",
    "langchain_aws", "langchain_core", "langchain_core.messages",
    "crewai", "crewai.llm",
]

for mod_name in _MOCK_MODULES:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Provide mock classes that the orchestrators import
sys.modules["langgraph.graph"].StateGraph = MagicMock
sys.modules["langgraph.graph"].START = "START"
sys.modules["langgraph.graph"].END = "END"
sys.modules["langchain_aws"].ChatBedrock = MagicMock
sys.modules["langchain_core.messages"].HumanMessage = MagicMock
sys.modules["langchain_core.messages"].SystemMessage = MagicMock
sys.modules["crewai"].Agent = MagicMock
sys.modules["crewai"].Crew = MagicMock
sys.modules["crewai"].Task = MagicMock
sys.modules["crewai"].Process = MagicMock()
sys.modules["crewai"].Process.sequential = "sequential"
sys.modules["crewai.llm"].LLM = MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT SETUP
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set required environment variables for all tests."""
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("BUCKET_NAME", "test-iso27001-bucket")
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "test-kb-id")
    monkeypatch.setenv("FINDINGS_TABLE", "AuditFindings")
    monkeypatch.setenv("DOCUMENTS_TABLE", "Documents")
    monkeypatch.setenv("METRICS_TABLE", "AgentCoreMetrics")
    monkeypatch.setenv("PRIMARY_MODEL_ID", "openai.gpt-oss-120b-1:0")
    monkeypatch.setenv("FAST_MODEL_ID", "qwen.qwen3-32b-v1:0")
    monkeypatch.setenv("VECTOR_STORE_BUCKET", "iso27001-vectors-e16")
    monkeypatch.setenv("VECTOR_STORE_INDEX", "iso27001-compliance-index")
    monkeypatch.setenv("EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")


# ─────────────────────────────────────────────────────────────────────────────
# AWS MOCKS
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_bucket():
    """Create a mocked S3 bucket."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-iso27001-bucket")
        yield s3


@pytest.fixture
def dynamodb_tables():
    """Create mocked DynamoDB tables."""
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

        # Findings table
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

        # Documents table
        dynamodb.create_table(
            TableName="Documents",
            KeySchema=[
                {"AttributeName": "document_id", "KeyType": "HASH"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "document_id", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield dynamodb


# ─────────────────────────────────────────────────────────────────────────────
# BEDROCK MOCKS
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_bedrock_converse():
    """Mock Bedrock converse API for agent invocations."""
    mock_response = {
        "output": {
            "message": {
                "content": [{"text": json.dumps({
                    "control_id": "A.5.1",
                    "short_description": "Políticas de seguridad",
                    "observations": ["Política existente pero no actualizada en 18 meses."],
                    "ranking": "No conformidad menor",
                    "ranking_judgement": "La política existe pero no cumple el ciclo de revisión.",
                    "recommendations": ["Establecer revisión anual de la política."],
                    "documents_reviewed": ["Politica_Seguridad_v2.pdf"]
                }, ensure_ascii=False)}]
            }
        },
        "usage": {"inputTokens": 500, "outputTokens": 200}
    }

    with patch("boto3.client") as mock_client:
        bedrock_mock = MagicMock()
        bedrock_mock.converse.return_value = mock_response
        mock_client.return_value = bedrock_mock
        yield bedrock_mock


@pytest.fixture
def mock_bedrock_rag():
    """Mock Bedrock RetrieveAndGenerate API for RAG queries."""
    mock_response = {
        "output": {"text": "Control A.5.1 requires an information security policy."},
        "citations": [
            {
                "retrievedReferences": [
                    {
                        "content": {"text": "The organization shall define an information security policy."},
                        "location": {"s3Location": {"uri": "s3://bucket/raw/iso27001.pdf"}},
                    }
                ]
            }
        ],
    }
    return mock_response


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLE DATA FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_audit_payload():
    """Standard audit request payload."""
    return {
        "organization_context": "ACME Corp, empresa tecnológica con 200 empleados que maneja datos financieros.",
        "audit_type": "internal",
        "audit_id": "test_audit_001",
        "session_id": "test_session_001",
        "actor_id": "test_auditor",
    }


@pytest.fixture
def sample_finding():
    """Sample audit finding data."""
    return {
        "audit_id": "test_audit_001",
        "finding_id": "NC-001",
        "control_id": "A.5.1",
        "control_name": "Políticas de seguridad de la información",
        "conformity_level": "minor_nonconformity",
        "risk_level": "medium",
        "description": "La política de seguridad no ha sido revisada en 18 meses.",
        "recommendation": "Establecer ciclo de revisión anual con aprobación por dirección.",
        "evidence": ["Politica_Seguridad_v2.pdf", "Acta_Revision_2024.pdf"],
        "actor_id": "test_auditor",
    }


@pytest.fixture
def sample_lambda_event():
    """Sample API Gateway Lambda event."""
    return {
        "body": json.dumps({
            "organization_context": "ACME Corp, fintech, 200 employees",
            "audit_type": "internal",
        }),
        "httpMethod": "POST",
        "headers": {"Content-Type": "application/json"},
    }


@pytest.fixture
def sample_evidence_context():
    """Sample RAG retrieved context for agent evaluation."""
    return [
        {
            "document": "Politica_Seguridad_v2.pdf",
            "content": "La política de seguridad fue aprobada en enero de 2024. Define roles y responsabilidades para la protección de la información.",
        },
        {
            "document": "Acta_Comite_Seguridad_Q4_2025.pdf",
            "content": "El comité de seguridad se reunió en noviembre de 2025. Se revisaron incidentes del trimestre.",
        },
        {
            "document": "Plan_Capacitacion_2025.pdf",
            "content": "Programa de awareness con 85% de completitud. No incluye capacitación por roles.",
        },
    ]
