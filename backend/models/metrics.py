"""
Performance Metrics Collection — Captures LLM, agent, and orchestration metrics.

Three levels of metrics:
1. MODEL METRICS: Latency, token utilization, throughput, cost per invocation
2. AGENT METRICS: Tool usage, total processing time, success rate, RAG quality
3. ORCHESTRATION METRICS: End-to-end flow time, per-node timings, bottleneck detection

Metrics are collected via decorators and context managers, then persisted to
DynamoDB for historical analysis and to CloudWatch for real-time monitoring.
"""

import json
import os
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import boto3


# ─────────────────────────────────────────────────────────────────────────────
# METRIC DATA MODELS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ModelMetrics:
    """Level 1: LLM model performance metrics per invocation."""
    invocation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    model_id: str = ""
    model_display_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Latency metrics (milliseconds)
    total_latency_ms: float = 0.0
    time_to_first_token_ms: float = 0.0
    output_tokens_per_second: float = 0.0

    # Token metrics
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    # Cost estimation (USD)
    estimated_cost_usd: float = 0.0

    # Quality signals
    invocation_success: bool = True
    error_type: Optional[str] = None
    was_throttled: bool = False

    def compute_derived(self):
        """Compute derived metrics after raw values are set."""
        self.total_tokens = self.input_tokens + self.output_tokens
        if self.total_latency_ms > 0 and self.output_tokens > 0:
            self.output_tokens_per_second = (
                self.output_tokens / (self.total_latency_ms / 1000.0)
            )


@dataclass
class AgentMetrics:
    """Level 2: Per-agent performance metrics for a single invocation."""
    agent_id: str = ""
    agent_name: str = ""
    session_id: str = ""
    actor_id: str = ""
    invocation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Timing
    total_execution_time_ms: float = 0.0
    llm_time_ms: float = 0.0
    tool_execution_time_ms: float = 0.0
    overhead_time_ms: float = 0.0  # total - llm - tool

    # Model metrics (aggregated across turns within this invocation)
    model_invocations: list[ModelMetrics] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_estimated_cost_usd: float = 0.0

    # Tool usage
    tools_called: list[str] = field(default_factory=list)
    tool_call_count: int = 0
    tool_success_count: int = 0
    tool_error_count: int = 0

    # RAG quality (when applicable)
    rag_queries_made: int = 0
    rag_sources_retrieved: int = 0
    avg_rag_relevance_score: float = 0.0

    # Outcome
    success: bool = True
    error_message: Optional[str] = None
    turns_count: int = 0  # Number of LLM turns in the agent loop

    def compute_aggregates(self):
        """Aggregate model metrics into agent-level summaries."""
        if self.model_invocations:
            self.total_input_tokens = sum(m.input_tokens for m in self.model_invocations)
            self.total_output_tokens = sum(m.output_tokens for m in self.model_invocations)
            self.total_estimated_cost_usd = sum(m.estimated_cost_usd for m in self.model_invocations)
            self.llm_time_ms = sum(m.total_latency_ms for m in self.model_invocations)
            self.turns_count = len(self.model_invocations)
        self.overhead_time_ms = max(0, self.total_execution_time_ms - self.llm_time_ms - self.tool_execution_time_ms)


@dataclass
class OrchestrationNodeMetrics:
    """Metrics for a single node (agent) in the orchestration flow graph."""
    node_id: str = ""
    agent_name: str = ""
    order_index: int = 0  # Execution order in the flow
    status: str = "pending"  # pending, running, completed, failed, skipped

    # Agent-level metrics for this node
    agent_metrics: Optional[AgentMetrics] = None

    # Model-level metrics summary for this node
    model_id_used: str = ""
    llm_latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

    # Node timing within the orchestration
    start_time_ms: float = 0.0  # Relative to orchestration start
    end_time_ms: float = 0.0
    duration_ms: float = 0.0
    wait_time_ms: float = 0.0  # Time waiting before execution started

    # Dependency info
    depends_on: list[str] = field(default_factory=list)
    outputs_to: list[str] = field(default_factory=list)


@dataclass
class OrchestrationFlowMetrics:
    """Level 3: End-to-end orchestration flow metrics with node graph."""
    flow_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    audit_id: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Orchestration timing
    total_flow_time_ms: float = 0.0
    critical_path_time_ms: float = 0.0  # Longest sequential chain

    # Node metrics (the DAG)
    nodes: list[OrchestrationNodeMetrics] = field(default_factory=list)

    # Aggregated stats
    total_agents_invoked: int = 0
    total_llm_invocations: int = 0
    total_tokens_consumed: int = 0
    total_estimated_cost_usd: float = 0.0
    total_tool_calls: int = 0

    # Bottleneck analysis
    bottleneck_node: str = ""  # Node with highest duration
    bottleneck_reason: str = ""  # "llm_latency" | "tool_execution" | "wait_time"
    slowest_model_call_ms: float = 0.0

    # Outcome
    success: bool = True
    failed_nodes: list[str] = field(default_factory=list)

    def compute_aggregates(self):
        """Compute flow-level aggregates from node metrics."""
        self.total_agents_invoked = len([n for n in self.nodes if n.status == "completed"])

        total_tokens = 0
        total_cost = 0.0
        total_tools = 0
        total_llm = 0
        max_duration = 0.0
        bottleneck = ""

        for node in self.nodes:
            if node.agent_metrics:
                total_tokens += (node.agent_metrics.total_input_tokens + node.agent_metrics.total_output_tokens)
                total_cost += node.agent_metrics.total_estimated_cost_usd
                total_tools += node.agent_metrics.tool_call_count
                total_llm += node.agent_metrics.turns_count

            if node.duration_ms > max_duration:
                max_duration = node.duration_ms
                bottleneck = node.node_id

            if node.status == "failed":
                self.failed_nodes.append(node.node_id)

        self.total_tokens_consumed = total_tokens
        self.total_estimated_cost_usd = total_cost
        self.total_tool_calls = total_tools
        self.total_llm_invocations = total_llm
        self.bottleneck_node = bottleneck

        if bottleneck:
            bn = next((n for n in self.nodes if n.node_id == bottleneck), None)
            if bn and bn.agent_metrics:
                if bn.agent_metrics.llm_time_ms > bn.agent_metrics.tool_execution_time_ms:
                    self.bottleneck_reason = "llm_latency"
                else:
                    self.bottleneck_reason = "tool_execution"

        self.success = len(self.failed_nodes) == 0


# ─────────────────────────────────────────────────────────────────────────────
# METRICS COLLECTOR
# ─────────────────────────────────────────────────────────────────────────────

# Approximate pricing per 1M tokens (input/output) for cost estimation
_MODEL_PRICING = {
    # OpenAI GPT
    "openai.gpt-oss-120b-1:0": {"input": 1.20, "output": 4.80},
    # Qwen3
    "qwen.qwen3-32b-v1:0": {"input": 0.30, "output": 1.20},
    # Anthropic Claude
    "anthropic.claude-haiku-4-5-20250514-v1:0": {"input": 0.80, "output": 4.00},
    "anthropic.claude-sonnet-4-6-20250514-v1:0": {"input": 3.00, "output": 15.00},
    # Meta Llama
    "meta.llama4-maverick-17b-instruct-v1:0": {"input": 0.20, "output": 0.60},
    # Mistral
    "mistral.mistral-large-2407-v1:0": {"input": 2.00, "output": 6.00},
    # DeepSeek
    "deepseek.deepseek-r1-v1:0": {"input": 1.35, "output": 5.40},
}


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate invocation cost in USD based on token counts."""
    # Try exact match, then prefix match for cross-region IDs
    pricing = _MODEL_PRICING.get(model_id)
    if not pricing:
        # Try stripping cross-region prefix (e.g., "us.amazon.nova-pro-v1:0" → "amazon.nova-pro-v1:0")
        base_id = model_id.split(".", 1)[-1] if model_id.startswith("us.") else model_id
        pricing = _MODEL_PRICING.get(base_id, {"input": 1.0, "output": 4.0})  # Default estimate

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class MetricsCollector:
    """
    Collects performance metrics at all three levels during agent execution.

    Usage:
        collector = MetricsCollector(agent_name="planning_agent")

        # Track a model invocation
        with collector.track_model_invocation("amazon.nova-pro-v1:0") as model_ctx:
            response = bedrock_model.invoke(...)
            model_ctx.set_tokens(input_tokens=150, output_tokens=500)

        # Track a tool call
        with collector.track_tool_call("query_knowledge_base") as tool_ctx:
            result = query_knowledge_base(question="...")

        # Get final metrics
        agent_metrics = collector.finalize()
    """

    def __init__(self, agent_name: str, session_id: str = "", actor_id: str = ""):
        self.agent_name = agent_name
        self.session_id = session_id
        self.actor_id = actor_id
        self._start_time = time.perf_counter()
        self._model_metrics: list[ModelMetrics] = []
        self._tool_calls: list[dict] = []
        self._rag_queries: list[dict] = []

    @contextmanager
    def track_model_invocation(self, model_id: str, model_display_name: str = ""):
        """Context manager to track a single LLM invocation."""
        metric = ModelMetrics(model_id=model_id, model_display_name=model_display_name)
        start = time.perf_counter()
        ttft_recorded = False

        class _ModelContext:
            def set_tokens(self, input_tokens: int, output_tokens: int):
                metric.input_tokens = input_tokens
                metric.output_tokens = output_tokens

            def set_ttft(self, ttft_ms: float):
                nonlocal ttft_recorded
                metric.time_to_first_token_ms = ttft_ms
                ttft_recorded = True

            def set_error(self, error_type: str):
                metric.invocation_success = False
                metric.error_type = error_type

            def set_throttled(self):
                metric.was_throttled = True

            def set_cache_tokens(self, read: int = 0, write: int = 0):
                metric.cache_read_tokens = read
                metric.cache_write_tokens = write

        ctx = _ModelContext()
        try:
            yield ctx
        except Exception as exc:
            metric.invocation_success = False
            metric.error_type = type(exc).__name__
            raise
        finally:
            metric.total_latency_ms = (time.perf_counter() - start) * 1000
            metric.estimated_cost_usd = estimate_cost(
                model_id, metric.input_tokens, metric.output_tokens
            )
            metric.compute_derived()
            self._model_metrics.append(metric)

    @contextmanager
    def track_tool_call(self, tool_name: str):
        """Context manager to track a tool execution."""
        start = time.perf_counter()
        call_info = {"tool_name": tool_name, "success": True, "duration_ms": 0, "error": None}

        try:
            yield call_info
        except Exception as exc:
            call_info["success"] = False
            call_info["error"] = str(exc)
            raise
        finally:
            call_info["duration_ms"] = (time.perf_counter() - start) * 1000
            self._tool_calls.append(call_info)

            # Track RAG-specific metrics
            if "rag" in tool_name.lower() or "knowledge" in tool_name.lower():
                self._rag_queries.append(call_info)

    def record_rag_result(self, sources_retrieved: int, relevance_score: float = 0.0):
        """Record RAG retrieval quality metrics."""
        self._rag_queries.append({
            "sources_retrieved": sources_retrieved,
            "relevance_score": relevance_score,
        })

    def finalize(self) -> AgentMetrics:
        """Compute and return final agent-level metrics."""
        total_time = (time.perf_counter() - self._start_time) * 1000

        metrics = AgentMetrics(
            agent_name=self.agent_name,
            session_id=self.session_id,
            actor_id=self.actor_id,
            total_execution_time_ms=total_time,
            model_invocations=self._model_metrics,
            tools_called=[tc["tool_name"] for tc in self._tool_calls],
            tool_call_count=len(self._tool_calls),
            tool_success_count=sum(1 for tc in self._tool_calls if tc["success"]),
            tool_error_count=sum(1 for tc in self._tool_calls if not tc["success"]),
            tool_execution_time_ms=sum(tc["duration_ms"] for tc in self._tool_calls),
            rag_queries_made=len(self._rag_queries),
        )

        if self._rag_queries:
            sources = [q.get("sources_retrieved", 0) for q in self._rag_queries if "sources_retrieved" in q]
            metrics.rag_sources_retrieved = sum(sources)
            scores = [q.get("relevance_score", 0) for q in self._rag_queries if q.get("relevance_score", 0) > 0]
            if scores:
                metrics.avg_rag_relevance_score = sum(scores) / len(scores)

        metrics.compute_aggregates()
        return metrics


# ─────────────────────────────────────────────────────────────────────────────
# METRICS STORE (DynamoDB + CloudWatch)
# ─────────────────────────────────────────────────────────────────────────────

class MetricsStore:
    """
    Persists metrics to DynamoDB for historical analysis and publishes
    key metrics to CloudWatch for real-time monitoring and alarms.
    """

    def __init__(self, region: str = None, table_name: str = None):
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.table_name = table_name or os.environ.get("METRICS_TABLE", "AgentCoreMetrics")
        self._dynamodb = None
        self._cloudwatch = None

    @property
    def dynamodb(self):
        if self._dynamodb is None:
            self._dynamodb = boto3.resource("dynamodb", region_name=self.region)
        return self._dynamodb

    @property
    def cloudwatch(self):
        if self._cloudwatch is None:
            self._cloudwatch = boto3.client("cloudwatch", region_name=self.region)
        return self._cloudwatch

    def save_agent_metrics(self, metrics: AgentMetrics):
        """Save agent metrics to DynamoDB and publish to CloudWatch."""
        table = self.dynamodb.Table(self.table_name)

        # Serialize for DynamoDB (flatten model_invocations to JSON)
        item = {
            "metric_id": metrics.invocation_id,
            "metric_type": "agent",
            "agent_name": metrics.agent_name,
            "session_id": metrics.session_id,
            "timestamp": metrics.timestamp,
            "total_execution_time_ms": int(metrics.total_execution_time_ms),
            "llm_time_ms": int(metrics.llm_time_ms),
            "tool_execution_time_ms": int(metrics.tool_execution_time_ms),
            "total_input_tokens": metrics.total_input_tokens,
            "total_output_tokens": metrics.total_output_tokens,
            "total_estimated_cost_usd": str(metrics.total_estimated_cost_usd),
            "tool_call_count": metrics.tool_call_count,
            "turns_count": metrics.turns_count,
            "success": metrics.success,
            "model_invocations_json": json.dumps([asdict(m) for m in metrics.model_invocations]),
        }
        table.put_item(Item=item)

        # Publish key metrics to CloudWatch
        self._publish_agent_cloudwatch(metrics)

    def save_flow_metrics(self, flow: OrchestrationFlowMetrics):
        """Save orchestration flow metrics to DynamoDB."""
        table = self.dynamodb.Table(self.table_name)
        item = {
            "metric_id": flow.flow_id,
            "metric_type": "orchestration_flow",
            "audit_id": flow.audit_id,
            "session_id": flow.session_id,
            "timestamp": flow.timestamp,
            "total_flow_time_ms": int(flow.total_flow_time_ms),
            "total_agents_invoked": flow.total_agents_invoked,
            "total_tokens_consumed": flow.total_tokens_consumed,
            "total_estimated_cost_usd": str(flow.total_estimated_cost_usd),
            "bottleneck_node": flow.bottleneck_node,
            "bottleneck_reason": flow.bottleneck_reason,
            "success": flow.success,
            "nodes_json": json.dumps([asdict(n) for n in flow.nodes], default=str),
        }
        table.put_item(Item=item)

        # Publish orchestration CloudWatch metrics
        self._publish_flow_cloudwatch(flow)

    def get_best_model_for_agent(self, agent_name: str) -> Optional[str]:
        """
        Query historical metrics to find the best-performing model for an agent.
        Best = lowest latency with success rate > 95%.
        """
        # This would query DynamoDB with a GSI on agent_name + timestamp
        # Simplified placeholder — in production, add GSI and proper query
        return None

    def _publish_agent_cloudwatch(self, metrics: AgentMetrics):
        """Publish agent-level metrics to CloudWatch."""
        try:
            namespace = "AgentCore/ISO27001Audit"
            dimensions = [
                {"Name": "AgentName", "Value": metrics.agent_name},
            ]

            metric_data = [
                {
                    "MetricName": "AgentExecutionTime",
                    "Value": metrics.total_execution_time_ms,
                    "Unit": "Milliseconds",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "AgentLLMTime",
                    "Value": metrics.llm_time_ms,
                    "Unit": "Milliseconds",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "AgentToolTime",
                    "Value": metrics.tool_execution_time_ms,
                    "Unit": "Milliseconds",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "AgentInputTokens",
                    "Value": float(metrics.total_input_tokens),
                    "Unit": "Count",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "AgentOutputTokens",
                    "Value": float(metrics.total_output_tokens),
                    "Unit": "Count",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "AgentToolCalls",
                    "Value": float(metrics.tool_call_count),
                    "Unit": "Count",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "AgentCostUSD",
                    "Value": metrics.total_estimated_cost_usd,
                    "Unit": "None",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "AgentSuccess",
                    "Value": 1.0 if metrics.success else 0.0,
                    "Unit": "Count",
                    "Dimensions": dimensions,
                },
            ]

            self.cloudwatch.put_metric_data(Namespace=namespace, MetricData=metric_data)
        except Exception:
            pass  # Non-blocking: metrics failure should not break agent execution

    def _publish_flow_cloudwatch(self, flow: OrchestrationFlowMetrics):
        """Publish orchestration flow metrics to CloudWatch."""
        try:
            namespace = "AgentCore/ISO27001Audit"
            dimensions = [{"Name": "FlowType", "Value": "audit_orchestration"}]

            metric_data = [
                {
                    "MetricName": "OrchestrationFlowTime",
                    "Value": flow.total_flow_time_ms,
                    "Unit": "Milliseconds",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "OrchestrationTotalTokens",
                    "Value": float(flow.total_tokens_consumed),
                    "Unit": "Count",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "OrchestrationTotalCost",
                    "Value": flow.total_estimated_cost_usd,
                    "Unit": "None",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "OrchestrationAgentsInvoked",
                    "Value": float(flow.total_agents_invoked),
                    "Unit": "Count",
                    "Dimensions": dimensions,
                },
                {
                    "MetricName": "OrchestrationSuccess",
                    "Value": 1.0 if flow.success else 0.0,
                    "Unit": "Count",
                    "Dimensions": dimensions,
                },
            ]

            self.cloudwatch.put_metric_data(Namespace=namespace, MetricData=metric_data)
        except Exception:
            pass
