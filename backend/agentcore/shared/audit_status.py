"""
Audit status persistence, shared by the AgentCore orchestrator and the
framework Lambdas. Keeps the record the frontend polls up to date.

Only depends on boto3 so it can be imported from any runtime.
"""

import os
from datetime import datetime, timezone
from functools import wraps

import boto3


ESTADO_EN_PROGRESO = "en_progreso"
ESTADO_COMPLETADA = "completada"
ESTADO_ERROR = "error"
ERROR_MESSAGE_LIMIT = 500


def update_audit_status(tenant_id: str, audit_id: str, estado: str, **fields) -> bool:
    """
    Update the status of an audit record. Returns False when no table is configured.

    Args:
        tenant_id: Tenant that owns the audit (partition key).
        audit_id: Audit identifier (sort key).
        estado: New status (en_progreso, completada, error).
        **fields: Extra attributes to store, e.g. report_key or error.
    """
    table_name = os.environ.get("AUDITS_TABLE", "")
    if not table_name or not tenant_id or not audit_id:
        print(f"[WARN] Audit status not persisted: audit={audit_id} estado={estado}")
        return False

    now = datetime.now(timezone.utc).isoformat()
    values = {"estado": estado, "actualizacion": now, **fields}
    if estado == ESTADO_COMPLETADA:
        values["completada"] = now

    names = {f"#f{i}": key for i, key in enumerate(values)}
    attrs = {f":v{i}": value for i, value in enumerate(values.values())}
    expression = "SET " + ", ".join(f"#f{i} = :v{i}" for i in range(len(values)))

    table = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1")).Table(table_name)
    table.update_item(
        Key={"tenant_id": tenant_id, "id": audit_id},
        UpdateExpression=expression,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=attrs,
    )
    return True


def track_audit_status(handler):
    """
    Decorator for framework Lambda handlers invoked asynchronously by the API.
    Records the outcome on the audit when the event carries a tenant_id;
    synchronous invocations without tenant context are left untouched.
    """
    @wraps(handler)
    def wrapper(event, context):
        tenant_id = event.get("tenant_id", "") if isinstance(event, dict) else ""
        audit_id = event.get("audit_id", "") if isinstance(event, dict) else ""
        try:
            result = handler(event, context)
        except Exception as exc:
            update_audit_status(tenant_id, audit_id, ESTADO_ERROR, error=str(exc)[:ERROR_MESSAGE_LIMIT])
            raise

        if tenant_id:
            if result.get("statusCode") == 200:
                update_audit_status(tenant_id, audit_id, ESTADO_COMPLETADA)
            else:
                update_audit_status(
                    tenant_id, audit_id, ESTADO_ERROR,
                    error=str(result.get("body", ""))[:ERROR_MESSAGE_LIMIT],
                )
        return result
    return wrapper
