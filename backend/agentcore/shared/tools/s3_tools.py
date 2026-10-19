"""
S3 tools for document retrieval and report storage.
Used by agents to access source documents and persist audit outputs.
"""

import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from strands import tool


REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")

s3_client = boto3.client("s3", region_name=REGION)


@tool
def get_document_content(s3_key: str) -> dict:
    """
    Retrieve document content from S3. Supports JSON and text-based files.

    Args:
        s3_key: The S3 object key (e.g., 'processed/adp/doc123/output.md').

    Returns:
        Dict with 'content' (string), 'content_type', and 'size_bytes'.
    """
    if not BUCKET_NAME:
        return {"error": "BUCKET_NAME not configured"}

    response = s3_client.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    content_type = response["ContentType"]
    body = response["Body"].read()

    # Handle JSON vs text content
    if "json" in content_type:
        content = json.loads(body.decode("utf-8"))
    else:
        content = body.decode("utf-8", errors="replace")

    return {
        "s3_key": s3_key,
        "content": content,
        "content_type": content_type,
        "size_bytes": response["ContentLength"],
    }


@tool
def save_report_to_s3(
    report_content: str,
    report_type: str,
    audit_id: str,
    file_format: str = "json",
) -> dict:
    """
    Save an audit report or intermediate result to S3.

    Args:
        report_content: The report content (JSON string or plain text).
        report_type: Type of report (e.g., 'domain_report', 'consolidated_report', 'finding_details').
        audit_id: The audit identifier this report belongs to.
        file_format: File format - 'json' or 'md' (default: 'json').

    Returns:
        Dict with 's3_key' of the saved report and 'bucket'.
    """
    if not BUCKET_NAME:
        return {"error": "BUCKET_NAME not configured"}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    extension = "json" if file_format == "json" else "md"
    content_type = "application/json" if file_format == "json" else "text/markdown"

    s3_key = f"audits/{audit_id}/{report_type}/{timestamp}_{unique_id}.{extension}"

    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=s3_key,
        Body=report_content.encode("utf-8"),
        ContentType=content_type,
        Metadata={
            "audit_id": audit_id,
            "report_type": report_type,
            "generated_at": timestamp,
        },
    )

    return {
        "status": "saved",
        "bucket": BUCKET_NAME,
        "s3_key": s3_key,
        "report_type": report_type,
        "audit_id": audit_id,
    }
