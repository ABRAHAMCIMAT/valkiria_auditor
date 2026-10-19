"""
DynamoDB tools for audit data persistence.
Used by agents to read/write audit findings and document metadata.
"""

import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool


REGION = os.environ.get("AWS_REGION", "us-east-1")
DOCUMENTS_TABLE = os.environ.get("DOCUMENTS_TABLE", "Documents")
AUDITS_TABLE = os.environ.get("AUDITS_TABLE", "Audits")
FINDINGS_TABLE = os.environ.get("FINDINGS_TABLE", "AuditFindings")

dynamodb = boto3.resource("dynamodb", region_name=REGION)


@tool
def get_document_metadata(document_id: str) -> dict:
    """
    Retrieve metadata for a document from DynamoDB.

    Args:
        document_id: The unique document identifier.

    Returns:
        Dict with document metadata (name, type, upload date, status, tenant_id).
    """
    table = dynamodb.Table(DOCUMENTS_TABLE)
    response = table.get_item(Key={"document_id": document_id})
    item = response.get("Item")
    if not item:
        return {"error": f"Document {document_id} not found"}
    return {
        "document_id": item["document_id"],
        "file_name": item.get("file_name", ""),
        "document_type": item.get("document_type", ""),
        "upload_timestamp": item.get("upload_timestamp", ""),
        "status": item.get("status", ""),
        "tenant_id": item.get("tenant_id", ""),
        "s3_key": item.get("s3_key", ""),
    }


@tool
def save_audit_finding(
    audit_id: str,
    finding_id: str,
    control_id: str,
    control_name: str,
    conformity_level: str,
    risk_level: str,
    description: str,
    recommendation: str,
    evidence: list[str] = [],
    actor_id: str = "system",
) -> dict:
    """
    Save an audit finding to DynamoDB.

    Args:
        audit_id: The parent audit identifier.
        finding_id: Unique finding ID (e.g., 'NC-001').
        control_id: ISO 27001:2022 control reference (e.g., 'A.5.1').
        control_name: Human-readable control name.
        conformity_level: One of: conforming, minor_nonconformity, major_nonconformity, opportunity_for_improvement.
        risk_level: One of: critical, high, medium, low, informational.
        description: Detailed finding description.
        recommendation: Corrective action recommendation.
        evidence: List of evidence references.
        actor_id: ID of the user/agent creating the finding.

    Returns:
        Dict with the created finding record.
    """
    table = dynamodb.Table(FINDINGS_TABLE)
    now = datetime.now(timezone.utc).isoformat()
    item = {
        "finding_id": finding_id,
        "audit_id": audit_id,
        "control_id": control_id,
        "control_name": control_name,
        "conformity_level": conformity_level,
        "risk_level": risk_level,
        "description": description,
        "recommendation": recommendation,
        "evidence": evidence,
        "created_at": now,
        "created_by": actor_id,
        "status": "draft",
    }
    table.put_item(Item=item)
    return {"status": "saved", "finding_id": finding_id, "audit_id": audit_id}


@tool
def list_audit_findings(audit_id: str) -> dict:
    """
    List all findings for a given audit.

    Args:
        audit_id: The audit identifier to query findings for.

    Returns:
        Dict with 'findings' list and 'count'.
    """
    table = dynamodb.Table(FINDINGS_TABLE)
    response = table.query(
        IndexName="audit_id-index",
        KeyConditionExpression=boto3.dynamodb.conditions.Key("audit_id").eq(audit_id),
    )
    items = response.get("Items", [])
    return {
        "audit_id": audit_id,
        "findings": items,
        "count": len(items),
    }
