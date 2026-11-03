"""
End-to-end test against a deployed environment. It runs a real audit over the
ACME test data, so it invokes Bedrock and costs money: excluded by default.

    export E2E_API_URL=https://<api>/v1
    export E2E_ID_TOKEN=<Cognito ID token of tenant A>
    export E2E_OTHER_TENANT_TOKEN=<ID token of tenant B>   # optional
    pytest -c backend/pytest.ini --rootdir=backend backend/tests/e2e -m e2e -s
"""

import json
import os
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

TESTSETS = Path(__file__).resolve().parents[3] / "testsets"
EVIDENCE_FILES = [
    "politicas_seguridad_informacion.md",
    "controles_personas_evidencia.md",
    "seguridad_fisica_evaluacion.md",
    "sonarqube_report.json",
]
AUDIT_TIMEOUT_SECONDS = 3600
POLL_SECONDS = 30
MIN_COVERAGE = 0.95  # Success criterion defined in Avance 7
TOTAL_CONTROLS = 93


@pytest.fixture
def api():
    url = os.environ.get("E2E_API_URL")
    token = os.environ.get("E2E_ID_TOKEN")
    if not url or not token:
        pytest.skip("E2E_API_URL and E2E_ID_TOKEN are required")
    with httpx.Client(base_url=url.rstrip("/"), headers={"Authorization": f"Bearer {token}"}, timeout=30) as client:
        yield client


def test_endpoints_require_a_token():
    url = os.environ.get("E2E_API_URL")
    if not url:
        pytest.skip("E2E_API_URL is required")
    assert httpx.get(f"{url.rstrip('/')}/auditorias", timeout=30).status_code == 401


def test_full_audit_covers_all_domains(api):
    files = [TESTSETS / name for name in EVIDENCE_FILES]
    created = api.post("/auditorias", json={
        "nombre": f"E2E {int(time.time())}",
        "isoVersion": "2022",
        "framework": "strands",
        "descripcion": "ACME Corp S.A. de C.V., tecnología, 120 empleados en 3 ubicaciones.",
        "archivos": [{"name": f.name, "size": f.stat().st_size, "type": "text/plain"} for f in files],
    })
    assert created.status_code == 201, created.text
    audit = created.json()

    for upload, path in zip(audit["uploads"], files):
        assert httpx.put(upload["url"], headers=upload["headers"], content=path.read_bytes(), timeout=60).status_code == 200

    started = api.post("/audit/strands", json={"audit_id": audit["id"]})
    assert started.status_code == 202, started.text
    assert api.post("/audit/strands", json={"audit_id": audit["id"]}).status_code == 409

    deadline = time.time() + AUDIT_TIMEOUT_SECONDS
    detail = {}
    while time.time() < deadline:
        detail = api.get(f"/auditorias/{audit['id']}").json()
        print(f"[INFO] {detail['estado']}: {detail['resumen']['evaluados']} controles evaluados")
        if detail["estado"] in ("completada", "error"):
            break
        time.sleep(POLL_SECONDS)

    assert detail.get("estado") == "completada", json.dumps(detail, default=str)[:1000]
    assert detail["report_url"].startswith("https://")
    assert httpx.get(detail["report_url"], timeout=60).status_code == 200

    evaluated = {agent["nombre"]: agent["controles_evaluados"] for agent in detail["agentes"]}
    assert all(count > 0 for count in evaluated.values()), evaluated
    assert detail["resumen"]["evaluados"] / TOTAL_CONTROLS >= MIN_COVERAGE, detail["resumen"]

    other_token = os.environ.get("E2E_OTHER_TENANT_TOKEN")
    if other_token:
        foreign = httpx.get(
            f"{str(api.base_url).rstrip('/')}/auditorias/{audit['id']}",
            headers={"Authorization": f"Bearer {other_token}"},
            timeout=30,
        )
        assert foreign.status_code == 404
