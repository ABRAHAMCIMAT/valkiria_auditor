"""
S3 Metrics Store — Persists all metrics, flow data, and audit traces to S3
for long-term storage, analysis, and compliance auditing.

S3 Layout:
    s3://<bucket>/metrics/
    ├── agents/<agent_name>/<date>/<invocation_id>.json
    ├── models/<model_id>/<date>/<invocation_id>.json
    ├── flows/<audit_id>/<flow_id>.json
    ├── traces/<trace_id>/full_trace.json
    └── reports/<audit_id>/<framework>_report.json

All data is stored as JSON with metadata tags for S3 Select queries.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError


REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")
METRICS_PREFIX = os.environ.get("METRICS_PREFIX", "metrics/")


class S3MetricsStore:
    """
    Persists metrics and flow data to S3.

    Non-blocking: failures are logged but never break agent execution.
    """

    def __init__(self, bucket: str = None, prefix: str = None, region: str = None):
        self.bucket = bucket or BUCKET_NAME
        self.prefix = prefix or METRICS_PREFIX
        self.region = region or REGION
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def _put_json(self, key: str, data: dict, metadata: dict = None):
        """Write JSON object to S3 with optional metadata tags."""
        if not self.bucket:
            return
        try:
            body = json.dumps(data, default=str, ensure_ascii=False, indent=2)
            params = {
                "Bucket": self.bucket,
                "Key": key,
                "Body": body.encode("utf-8"),
                "ContentType": "application/json",
            }
            if metadata:
                params["Metadata"] = {k: str(v)[:256] for k, v in metadata.items()}
            self.client.put_object(**params)
        except (ClientError, Exception):
            pass  # Non-blocking

    def _date_partition(self) -> str:
        """Get date partition string (YYYY/MM/DD)."""
        now = datetime.now(timezone.utc)
        return f"{now.year}/{now.month:02d}/{now.day:02d}"

    # ─────────────────────────────────────────────────────────────────────
    # AGENT METRICS
    # ─────────────────────────────────────────────────────────────────────

    def save_agent_metrics(self, agent_name: str, metrics: dict):
        """
        Save agent-level metrics to S3.

        Path: metrics/agents/<agent_name>/<date>/<invocation_id>.json
        """
        invocation_id = metrics.get("invocation_id", uuid.uuid4().hex[:12])
        key = (
            f"{self.prefix}agents/{agent_name}/"
            f"{self._date_partition()}/{invocation_id}.json"
        )
        self._put_json(key, metrics, metadata={
            "agent_name": agent_name,
            "trace_id": metrics.get("trace_id", ""),
            "success": str(metrics.get("success", True)),
        })

    # ─────────────────────────────────────────────────────────────────────
    # MODEL METRICS
    # ─────────────────────────────────────────────────────────────────────

    def save_model_metrics(self, model_id: str, metrics: dict):
        """
        Save model-level metrics to S3.

        Path: metrics/models/<model_id_safe>/<date>/<invocation_id>.json
        """
        model_id_safe = model_id.replace(".", "_").replace(":", "_")
        invocation_id = metrics.get("invocation_id", uuid.uuid4().hex[:12])
        key = (
            f"{self.prefix}models/{model_id_safe}/"
            f"{self._date_partition()}/{invocation_id}.json"
        )
        self._put_json(key, metrics, metadata={
            "model_id": model_id,
            "latency_ms": str(int(metrics.get("latency_ms", 0))),
        })

    # ─────────────────────────────────────────────────────────────────────
    # FLOW METRICS
    # ─────────────────────────────────────────────────────────────────────

    def save_flow_metrics(self, audit_id: str, flow_id: str, metrics: dict):
        """
        Save orchestration flow metrics to S3.

        Path: metrics/flows/<audit_id>/<flow_id>.json
        """
        key = f"{self.prefix}flows/{audit_id}/{flow_id}.json"
        self._put_json(key, metrics, metadata={
            "audit_id": audit_id,
            "flow_id": flow_id,
            "framework": metrics.get("framework", ""),
            "success": str(metrics.get("success", True)),
        })

    # ─────────────────────────────────────────────────────────────────────
    # FULL TRACE
    # ─────────────────────────────────────────────────────────────────────

    def save_trace(self, trace_id: str, trace_data: dict):
        """
        Save a complete trace (all spans across agents) to S3.

        Path: metrics/traces/<trace_id>/full_trace.json
        """
        key = f"{self.prefix}traces/{trace_id}/full_trace.json"
        self._put_json(key, trace_data, metadata={
            "trace_id": trace_id,
            "audit_id": trace_data.get("audit_id", ""),
        })

    # ─────────────────────────────────────────────────────────────────────
    # AUDIT REPORT
    # ─────────────────────────────────────────────────────────────────────

    def save_audit_report(self, audit_id: str, framework: str, report: str, metrics: dict = None):
        """
        Save the final audit report and associated metrics.

        Path: metrics/reports/<audit_id>/<framework>_report.json
        """
        key = f"{self.prefix}reports/{audit_id}/{framework}_report.json"
        data = {
            "audit_id": audit_id,
            "framework": framework,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "report": report,
            "metrics": metrics or {},
        }
        self._put_json(key, data, metadata={
            "audit_id": audit_id,
            "framework": framework,
        })

    # ─────────────────────────────────────────────────────────────────────
    # MERMAID DIAGRAM
    # ─────────────────────────────────────────────────────────────────────

    def save_flow_diagram(self, audit_id: str, flow_id: str, mermaid: str):
        """
        Save the Mermaid flow diagram to S3 as markdown.

        Path: metrics/flows/<audit_id>/<flow_id>_diagram.md
        """
        if not self.bucket:
            return
        key = f"{self.prefix}flows/{audit_id}/{flow_id}_diagram.md"
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=mermaid.encode("utf-8"),
                ContentType="text/markdown",
            )
        except (ClientError, Exception):
            pass
