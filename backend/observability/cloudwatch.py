"""
CloudWatch Metrics Publisher — Publishes model, agent, and orchestration metrics
to CloudWatch under a custom namespace for dashboards and alarms.

Metrics hierarchy:
- Namespace: AgentCore/ISO27001Audit
- Dimensions: AgentName, ModelId, FlowType

All publishing is non-blocking: failures are logged but never break agent execution.
"""

import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError


NAMESPACE = "AgentCore/ISO27001Audit"
REGION = os.environ.get("AWS_REGION", "us-east-1")


class CloudWatchPublisher:
    """
    Publishes custom metrics to CloudWatch.

    Metrics are batched (up to 20 per PutMetricData call) and published
    with appropriate dimensions for slicing in dashboards.
    """

    def __init__(self, namespace: str = NAMESPACE, region: str = None):
        self.namespace = namespace
        self.region = region or REGION
        self._client = None
        self._buffer: list[dict] = []
        self._max_buffer_size = 20  # CloudWatch limit per API call

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("cloudwatch", region_name=self.region)
        return self._client

    def _flush(self):
        """Flush buffered metrics to CloudWatch."""
        if not self._buffer:
            return
        try:
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=self._buffer[:20],
            )
            self._buffer = self._buffer[20:]
        except (ClientError, Exception):
            self._buffer.clear()  # Drop on error, never block

    def _add_metric(self, metric_name: str, value: float, unit: str, dimensions: list[dict]):
        """Add a metric to the buffer, flush when full."""
        self._buffer.append({
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
            "Timestamp": datetime.now(timezone.utc),
            "Dimensions": dimensions,
        })
        if len(self._buffer) >= self._max_buffer_size:
            self._flush()

    def flush(self):
        """Force flush remaining metrics."""
        while self._buffer:
            self._flush()

    # ─────────────────────────────────────────────────────────────────────
    # LEVEL 1: Model Metrics
    # ─────────────────────────────────────────────────────────────────────

    def publish_model_metrics(
        self,
        model_id: str,
        agent_name: str,
        latency_ms: float,
        ttft_ms: float,
        input_tokens: int,
        output_tokens: int,
        output_tokens_per_second: float,
        cost_usd: float,
        success: bool = True,
        throttled: bool = False,
    ):
        """Publish Level 1 model performance metrics."""
        dims_model = [{"Name": "ModelId", "Value": model_id}]
        dims_both = [
            {"Name": "ModelId", "Value": model_id},
            {"Name": "AgentName", "Value": agent_name},
        ]

        self._add_metric("ModelLatency", latency_ms, "Milliseconds", dims_model)
        self._add_metric("ModelTTFT", ttft_ms, "Milliseconds", dims_model)
        self._add_metric("ModelInputTokens", float(input_tokens), "Count", dims_model)
        self._add_metric("ModelOutputTokens", float(output_tokens), "Count", dims_model)
        self._add_metric("ModelOTPS", output_tokens_per_second, "Count/Second", dims_model)
        self._add_metric("ModelCostUSD", cost_usd, "None", dims_model)
        self._add_metric("ModelInvocations", 1.0, "Count", dims_model)
        self._add_metric("ModelSuccess", 1.0 if success else 0.0, "Count", dims_model)

        if throttled:
            self._add_metric("ModelThrottles", 1.0, "Count", dims_model)

        # Cross-dimension: model performance per agent
        self._add_metric("ModelLatencyByAgent", latency_ms, "Milliseconds", dims_both)
        self._add_metric("ModelTokensByAgent", float(input_tokens + output_tokens), "Count", dims_both)

    # ─────────────────────────────────────────────────────────────────────
    # LEVEL 2: Agent Metrics
    # ─────────────────────────────────────────────────────────────────────

    def publish_agent_metrics(
        self,
        agent_name: str,
        total_execution_time_ms: float,
        llm_time_ms: float,
        tool_time_ms: float,
        overhead_time_ms: float,
        total_input_tokens: int,
        total_output_tokens: int,
        tool_call_count: int,
        tool_error_count: int,
        turns_count: int,
        rag_queries: int,
        cost_usd: float,
        success: bool = True,
    ):
        """Publish Level 2 agent performance metrics."""
        dims = [{"Name": "AgentName", "Value": agent_name}]

        self._add_metric("AgentExecutionTime", total_execution_time_ms, "Milliseconds", dims)
        self._add_metric("AgentLLMTime", llm_time_ms, "Milliseconds", dims)
        self._add_metric("AgentToolTime", tool_time_ms, "Milliseconds", dims)
        self._add_metric("AgentOverheadTime", overhead_time_ms, "Milliseconds", dims)
        self._add_metric("AgentInputTokens", float(total_input_tokens), "Count", dims)
        self._add_metric("AgentOutputTokens", float(total_output_tokens), "Count", dims)
        self._add_metric("AgentToolCalls", float(tool_call_count), "Count", dims)
        self._add_metric("AgentToolErrors", float(tool_error_count), "Count", dims)
        self._add_metric("AgentTurns", float(turns_count), "Count", dims)
        self._add_metric("AgentRAGQueries", float(rag_queries), "Count", dims)
        self._add_metric("AgentCostUSD", cost_usd, "None", dims)
        self._add_metric("AgentSuccess", 1.0 if success else 0.0, "Count", dims)
        self._add_metric("AgentInvocations", 1.0, "Count", dims)

        # Efficiency ratios
        if total_execution_time_ms > 0:
            llm_ratio = llm_time_ms / total_execution_time_ms
            self._add_metric("AgentLLMTimeRatio", llm_ratio, "None", dims)

    # ─────────────────────────────────────────────────────────────────────
    # LEVEL 3: Orchestration Flow Metrics
    # ─────────────────────────────────────────────────────────────────────

    def publish_orchestration_metrics(
        self,
        flow_id: str,
        total_flow_time_ms: float,
        critical_path_time_ms: float,
        total_agents_invoked: int,
        total_tokens: int,
        total_cost_usd: float,
        total_tool_calls: int,
        bottleneck_node: str,
        bottleneck_reason: str,
        success: bool = True,
        failed_nodes: int = 0,
    ):
        """Publish Level 3 orchestration flow metrics."""
        dims = [{"Name": "FlowType", "Value": "audit_orchestration"}]

        self._add_metric("FlowTotalTime", total_flow_time_ms, "Milliseconds", dims)
        self._add_metric("FlowCriticalPathTime", critical_path_time_ms, "Milliseconds", dims)
        self._add_metric("FlowAgentsInvoked", float(total_agents_invoked), "Count", dims)
        self._add_metric("FlowTotalTokens", float(total_tokens), "Count", dims)
        self._add_metric("FlowTotalCost", total_cost_usd, "None", dims)
        self._add_metric("FlowTotalToolCalls", float(total_tool_calls), "Count", dims)
        self._add_metric("FlowSuccess", 1.0 if success else 0.0, "Count", dims)
        self._add_metric("FlowFailedNodes", float(failed_nodes), "Count", dims)

        # Parallelism efficiency: critical path vs total time
        if total_flow_time_ms > 0:
            parallelism = critical_path_time_ms / total_flow_time_ms
            self._add_metric("FlowParallelismRatio", parallelism, "None", dims)

        # Bottleneck tracking (with additional dimension)
        if bottleneck_node:
            bn_dims = [
                {"Name": "FlowType", "Value": "audit_orchestration"},
                {"Name": "BottleneckNode", "Value": bottleneck_node},
            ]
            self._add_metric("FlowBottleneckOccurrence", 1.0, "Count", bn_dims)

        self.flush()

    # ─────────────────────────────────────────────────────────────────────
    # PER-NODE (within orchestration)
    # ─────────────────────────────────────────────────────────────────────

    def publish_node_metrics(
        self,
        node_id: str,
        agent_name: str,
        duration_ms: float,
        wait_time_ms: float,
        llm_time_ms: float,
        tool_time_ms: float,
        tokens: int,
        cost_usd: float,
        status: str,
    ):
        """Publish per-node metrics within an orchestration flow."""
        dims = [
            {"Name": "AgentName", "Value": agent_name},
            {"Name": "FlowNode", "Value": node_id},
        ]

        self._add_metric("NodeDuration", duration_ms, "Milliseconds", dims)
        self._add_metric("NodeWaitTime", wait_time_ms, "Milliseconds", dims)
        self._add_metric("NodeLLMTime", llm_time_ms, "Milliseconds", dims)
        self._add_metric("NodeToolTime", tool_time_ms, "Milliseconds", dims)
        self._add_metric("NodeTokens", float(tokens), "Count", dims)
        self._add_metric("NodeCost", cost_usd, "None", dims)

        if status == "failed":
            self._add_metric("NodeFailures", 1.0, "Count", dims)
