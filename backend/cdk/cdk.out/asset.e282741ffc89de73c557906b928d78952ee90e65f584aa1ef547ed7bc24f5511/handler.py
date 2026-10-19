"""
Lambda handler for the Strands Agents orchestrator.
Entry point for API Gateway → Lambda invocation.
"""

import json
import uuid

from backend.strandsagents.orchestrator import run_audit


def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda entry point."""
    # Parse request body
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else event

    organization_context = body.get("organization_context", "")
    audit_type = body.get("audit_type", "internal")
    audit_id = body.get("audit_id", f"strands_{uuid.uuid4().hex[:8]}")
    session_id = body.get("session_id", f"session_{uuid.uuid4().hex[:8]}")
    actor_id = body.get("actor_id", "system")

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
        )

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "audit_id": audit_id,
                "framework": "strands-agents",
                "report": result.get("report", "")[:10000],
                "flow_metrics": result.get("flow_metrics", {}),
            }, default=str),
        }
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(exc)[:500],
                "audit_id": audit_id,
                "framework": "strands-agents",
            }),
        }
