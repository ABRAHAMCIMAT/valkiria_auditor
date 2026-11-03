"""
Tests for the platform API: tenant isolation, the audit lifecycle, and the
response shape the frontend detail page depends on.
"""

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import urlparse

import boto3
import pytest
from moto import mock_aws

HANDLER = Path(__file__).resolve().parents[2] / "api" / "handler.py"


def event(method, resource, tenant=None, sub="user-1", body=None, params=None, headers=None):
    claims = {"sub": sub}
    if tenant:
        claims["cognito:groups"] = tenant
    return {
        "httpMethod": method,
        "resource": resource,
        "pathParameters": params,
        "headers": headers or {},
        "body": json.dumps(body) if body is not None else None,
        "requestContext": {"authorizer": {"claims": claims}},
    }


@pytest.fixture
def api(monkeypatch):
    with mock_aws():
        for key, value in {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_DEFAULT_REGION": "us-east-1",
            "AUDITS_TABLE": "Audits",
            "FINDINGS_TABLE": "Findings",
            "DATA_BUCKET": "data",
            "ALLOWED_ORIGIN": "https://app.example.com",
            "FRAMEWORK_FUNCTIONS": json.dumps({"strands": "fn-strands", "comp2013": "fn-comp"}),
        }.items():
            monkeypatch.setenv(key, value)
        monkeypatch.delenv("ORCHESTRATOR_RUNTIME_ARN", raising=False)

        dynamodb = boto3.resource("dynamodb")
        dynamodb.create_table(
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
        dynamodb.create_table(
            TableName="Findings",
            KeySchema=[
                {"AttributeName": "finding_id", "KeyType": "HASH"},
                {"AttributeName": "audit_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "finding_id", "AttributeType": "S"},
                {"AttributeName": "audit_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[{
                "IndexName": "audit_id-index",
                "KeySchema": [
                    {"AttributeName": "audit_id", "KeyType": "HASH"},
                    {"AttributeName": "finding_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }],
            BillingMode="PAY_PER_REQUEST",
        )
        boto3.client("s3").create_bucket(Bucket="data")

        spec = importlib.util.spec_from_file_location("platform_api", HANDLER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.lambda_client = MagicMock()
        yield module


def call(api, *args, **kwargs):
    result = api.lambda_handler(event(*args, **kwargs), None)
    return result["statusCode"], json.loads(result["body"])


def create(api, tenant="acme", **overrides):
    body = {"nombre": "Auditoria", "isoVersion": "2022", "framework": "strands", **overrides}
    status, item = call(api, "POST", "/auditorias", tenant=tenant, body=body)
    assert status == 201
    return item


class TestAuthorization:
    def test_missing_claims_are_rejected(self, api):
        result = api.lambda_handler({"httpMethod": "GET", "resource": "/auditorias"}, None)
        assert result["statusCode"] == 401

    def test_tenant_header_cannot_override_token(self, api):
        item = create(api, tenant="victim")
        status, items = call(
            api, "GET", "/auditorias", tenant="attacker", headers={"X-Tenant-Id": "victim"}
        )
        assert status == 200
        assert item["id"] not in [i["id"] for i in items]

    def test_other_tenant_cannot_read_audit(self, api):
        item = create(api, tenant="victim")
        status, _ = call(api, "GET", "/auditorias/{id}", tenant="attacker", params={"id": item["id"]})
        assert status == 404

    def test_other_tenant_cannot_delete_audit(self, api):
        item = create(api, tenant="victim")
        status, _ = call(api, "DELETE", "/auditorias/{id}", tenant="attacker", params={"id": item["id"]})
        assert status == 404
        status, _ = call(api, "GET", "/auditorias/{id}", tenant="victim", params={"id": item["id"]})
        assert status == 200

    def test_other_tenant_cannot_run_audit(self, api):
        item = create(api, tenant="victim")
        status, _ = call(
            api, "POST", "/audit/{framework}", tenant="attacker",
            params={"framework": "strands"}, body={"audit_id": item["id"]},
        )
        assert status == 404
        api.lambda_client.invoke.assert_not_called()

    def test_users_without_group_do_not_share_a_tenant(self, api):
        status, item = call(api, "POST", "/auditorias", sub="u1", body={"nombre": "x", "isoVersion": "2022"})
        assert status == 201
        _, items = call(api, "GET", "/auditorias", sub="u2")
        assert items == []

    @pytest.mark.parametrize("raw,expected", [("[acme]", "acme"), ("[acme other]", "acme"), ("acme,other", "acme")])
    def test_group_claim_formats(self, api, raw, expected):
        tenant, _ = api.get_tenant(event("GET", "/auditorias", tenant=raw))
        assert tenant == expected


class TestAuditLifecycle:
    def test_invalid_iso_version_is_rejected(self, api):
        status, _ = call(api, "POST", "/auditorias", tenant="acme", body={"nombre": "x", "isoVersion": "1999"})
        assert status == 400

    def test_invalid_json_is_a_client_error(self, api):
        bad = event("POST", "/auditorias", tenant="acme")
        bad["body"] = "{nope"
        assert api.lambda_handler(bad, None)["statusCode"] == 400

    def test_upload_keys_are_tenant_scoped_and_sanitized(self, api):
        item = create(api, archivos=[{"name": "../../otro tenant/sonar.json", "type": "application/json"}])
        key = item["archivos"][0]["key"]
        assert key.startswith(f"uploads/acme/{item['id']}/")
        assert ".." not in key
        assert item["uploads"][0]["headers"]["Content-Type"] == "application/json"
        assert key in urlparse(item["uploads"][0]["url"]).path

    def test_too_many_files_are_rejected(self, api):
        files = [{"name": f"{i}.md"} for i in range(api.MAX_FILES_PER_AUDIT + 1)]
        status, _ = call(api, "POST", "/auditorias", tenant="acme",
                         body={"nombre": "x", "isoVersion": "2022", "archivos": files})
        assert status == 400

    def test_run_returns_202_and_marks_in_progress(self, api):
        item = create(api, descripcion="ACME, 120 empleados")
        status, body = call(api, "POST", "/audit/{framework}", tenant="acme",
                            params={"framework": "strands"}, body={"audit_id": item["id"]})
        assert status == 202
        kwargs = api.lambda_client.invoke.call_args.kwargs
        assert kwargs["InvocationType"] == "Event"
        payload = json.loads(kwargs["Payload"])
        assert payload["tenant_id"] == "acme"
        assert "ACME, 120 empleados" in payload["organization_context"]
        assert item["id"] in payload["organization_context"]
        _, detail = call(api, "GET", "/auditorias/{id}", tenant="acme", params={"id": item["id"]})
        assert detail["estado"] == "en_progreso"

    def test_double_run_only_dispatches_once(self, api):
        item = create(api)
        kwargs = dict(tenant="acme", params={"framework": "strands"}, body={"audit_id": item["id"]})
        assert call(api, "POST", "/audit/{framework}", **kwargs)[0] == 202
        assert call(api, "POST", "/audit/{framework}", **kwargs)[0] == 409
        assert api.lambda_client.invoke.call_count == 1

    def test_dispatch_failure_marks_error_and_allows_retry(self, api):
        item = create(api)
        api.lambda_client.invoke.side_effect = RuntimeError("down")
        kwargs = dict(tenant="acme", params={"framework": "strands"}, body={"audit_id": item["id"]})
        assert call(api, "POST", "/audit/{framework}", **kwargs)[0] == 502
        api.lambda_client.invoke.side_effect = None
        assert call(api, "POST", "/audit/{framework}", **kwargs)[0] == 202

    def test_unknown_framework_is_rejected(self, api):
        item = create(api)
        status, _ = call(api, "POST", "/audit/{framework}", tenant="acme",
                         params={"framework": "nope"}, body={"audit_id": item["id"]})
        assert status == 404

    def test_strands_uses_agentcore_runtime_when_configured(self, api, monkeypatch):
        monkeypatch.setattr(api, "ORCHESTRATOR_RUNTIME_ARN", "arn:runtime")
        runtime = MagicMock()
        runtime.invoke_agent_runtime.return_value = {"response": MagicMock()}
        monkeypatch.setattr(api.boto3, "client", lambda name: runtime)
        item = create(api)
        status, _ = call(api, "POST", "/audit/{framework}", tenant="acme",
                         params={"framework": "strands"}, body={"audit_id": item["id"]})
        assert status == 202
        kwargs = runtime.invoke_agent_runtime.call_args.kwargs
        payload = json.loads(kwargs["payload"])
        assert payload["async"] is True
        assert payload["actor_id"] == "acme"
        assert len(kwargs["runtimeSessionId"]) >= 33

    def test_running_audit_cannot_be_deleted(self, api):
        item = create(api)
        call(api, "POST", "/audit/{framework}", tenant="acme",
             params={"framework": "strands"}, body={"audit_id": item["id"]})
        assert call(api, "DELETE", "/auditorias/{id}", tenant="acme", params={"id": item["id"]})[0] == 409


class TestDetailShape:
    def test_empty_audit_renders_without_findings(self, api):
        item = create(api)
        status, detail = call(api, "GET", "/auditorias/{id}", tenant="acme", params={"id": item["id"]})
        assert status == 200
        assert detail["hallazgos"] == []
        assert detail["resumen"]["total_controles"] == 93
        assert len(detail["agentes"]) == 4

    def test_findings_are_summarized(self, api):
        item = create(api)
        findings = boto3.resource("dynamodb").Table("Findings")
        rows = [
            ("NC-1", "A.5.1", "major_nonconformity"),
            ("NC-2", "A.7.1", "minor_nonconformity"),
            ("OK-1", "A.8.1", "conforming"),
            ("OI-1", "A.6.3", "opportunity_for_improvement"),
        ]
        for finding_id, control, level in rows:
            findings.put_item(Item={
                "finding_id": finding_id, "audit_id": item["id"], "control_id": control,
                "conformity_level": level, "description": "d", "created_at": "2026-01-01",
            })
        _, detail = call(api, "GET", "/auditorias/{id}", tenant="acme", params={"id": item["id"]})
        assert detail["resumen"]["no_conformes"] == 2
        assert detail["resumen"]["conformes"] == 1
        assert detail["resumen"]["parcialmente_conformes"] == 1
        assert {h["severidad"] for h in detail["hallazgos"]} == {"alta", "media", "baja"}
        counts = {a["nombre"]: a["controles_evaluados"] for a in detail["agentes"]}
        assert counts["Agente Controles Físicos"] == 1

    def test_cors_origin_is_restricted(self, api):
        result = api.lambda_handler(event("GET", "/auditorias", tenant="acme"), None)
        assert result["headers"]["Access-Control-Allow-Origin"] == "https://app.example.com"

    def test_new_evaluation_has_null_result(self, api):
        status, item = call(api, "POST", "/evaluaciones", tenant="acme", body={"nombre": "x", "isoVersion": "2022"})
        assert status == 201
        assert item["resultado"] is None
