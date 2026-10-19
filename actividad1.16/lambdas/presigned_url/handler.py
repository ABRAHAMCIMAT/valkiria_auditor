"""
Lambda: presigned_url
Genera una URL prefirmada de S3 para que el cliente suba un archivo directamente
al bucket sin pasar por el servidor. Invocada desde API Gateway (POST /upload/presigned-url).

Request body:
    {
        "file_name": "IEEG-Resultados.pdf",
        "content_type": "application/pdf"   # opcional, default application/octet-stream
    }

Response:
    {
        "upload_url": "https://s3.amazonaws.com/...",
        "s3_key": "raw/IEEG-Resultados.pdf",
        "expires_in": 3600
    }
"""

import json
import os
import uuid
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")

BUCKET_NAME         = os.environ["BUCKET_NAME"]
UPLOAD_PREFIX       = os.environ.get("UPLOAD_PREFIX", "raw/")
URL_EXPIRATION_SECS = int(os.environ.get("URL_EXPIRATION_SECONDS", "3600"))

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/octet-stream",
    "text/plain",
    "application/json",
    "text/csv",
    "application/x-yaml",
}


def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }


def lambda_handler(event: dict, context) -> dict:
    """Entry point for API Gateway Lambda proxy integration."""
    # Handle preflight OPTIONS
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": _cors_headers(), "body": ""}

    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _error(400, "Invalid JSON body")

    file_name    = body.get("file_name", "").strip()
    content_type = body.get("content_type", "application/octet-stream").strip()

    # Validate inputs
    if not file_name:
        return _error(400, "file_name is required")

    if content_type not in ALLOWED_CONTENT_TYPES:
        return _error(400, f"content_type '{content_type}' not allowed. "
                           f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}")

    # Build S3 key: raw/<uuid>_<file_name> to avoid collisions
    unique_prefix = uuid.uuid4().hex[:8]
    s3_key = f"{UPLOAD_PREFIX}{unique_prefix}_{file_name}"

    # Generate presigned PUT URL
    try:
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket":      BUCKET_NAME,
                "Key":         s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=URL_EXPIRATION_SECS,
        )
    except ClientError as exc:
        print(f"[ERROR] generate_presigned_url failed: {exc}")
        return _error(500, "Could not generate presigned URL")

    response_body = {
        "upload_url": upload_url,
        "s3_key":     s3_key,
        "bucket":     BUCKET_NAME,
        "expires_in": URL_EXPIRATION_SECS,
        "instructions": (
            "Use HTTP PUT to upload the file to upload_url. "
            "Set Content-Type header to match the requested content_type."
        ),
    }

    print(f"[INFO] Presigned URL generated for s3://{BUCKET_NAME}/{s3_key}")

    return {
        "statusCode": 200,
        "headers": {**_cors_headers(), "Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }


def _error(status_code: int, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {**_cors_headers(), "Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
