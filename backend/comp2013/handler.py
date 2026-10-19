"""
Lambda handler for the ISO 27001:2013 (comp2013) orchestrator.
Entry point for API Gateway → Lambda invocation.
"""

import json
import uuid

from backend.comp2013.orchestrator import run_audit


def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entry point."""
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    organization_context = body.get("organization_context", "")
    audit_type = body.get("audit_type", "internal")
    audit_id = body.get("audit_id", f"comp2013_{uuid.uuid4().hex[:8]}")
    session_id = body.get("session_id", f"session_{uuid.uuid4().hex[:8]}")
    actor_id = body.get("actor_id", "system")
    agents_in_scope = body.get("agents_in_scope", None)
    controls_in_scope = body.get("controls_in_scope", None)
    run_judge = body.get("run_judge", False)

    if not organization_context:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "organization_context is required"}),
        }

    try:
        result = run_audit(
            organization_context=organization_context,
            audit_type=audit_type,
            audit_id=audit_id,
            session_id=session_id,
            actor_id=actor_id,
            agents_in_scope=agents_in_scope,
            controls_in_scope=controls_in_scope,
            run_judge=run_judge,
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "audit_id": audit_id,
                "framework": "comp2013",
                "standard": "ISO/IEC 27001:2013",
                "total_controls_evaluated": result.get("total_controls_evaluated", 0),
                "severity_counts": result.get("severity_counts", {}),
                "agent_metrics": result.get("agent_metrics", {}),
                "findings": result.get("findings", [])[:50],  # Cap response size
                "flow_metrics": result.get("flow_metrics", {}),
            }, default=str, ensure_ascii=False),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(exc)[:500],
                "audit_id": audit_id,
                "framework": "comp2013",
            }),
        }
