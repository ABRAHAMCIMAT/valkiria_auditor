"""
Orchestration Flow Tracker — Tracks the full audit DAG with per-node observability.

Integrates with the ObservabilityCollector to provide Level 3 metrics:
- Per-node timing, wait time, and dependency resolution
- Bottleneck detection with root cause
- CloudWatch publication of orchestration-level metrics
- Visual flow output (Mermaid + JSON)

Usage in the consolidation agent:

    from backend.observability.flow_tracker import FlowTracker

    tracker = FlowTracker(audit_id="audit_001", session_id="session_xyz")

    with tracker.node("planning", agent_name="planning_agent", model_id="openai.gpt-oss-120b-1:0") as node:
        result = invoke_planning_agent(...)
        node.set_result(input_tokens=300, output_tokens=1200, tool_calls=3, cost=0.002)

    with tracker.node("evidence", agent_name="evidence_agent", model_id="qwen.qwen3-32b-v1:0") as node:
        result = invoke_evidence_agent(...)
        node.set_result(input_tokens=500, output_tokens=2000, tool_calls=8, cost=0.001)

    # Finalize
    summary = tracker.finalize()
    mermaid = tracker.mermaid_diagram()
"""

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from backend.observability.logging import StructuredLogger, TraceContext
from backend.observability.cloudwatch import CloudWatchPublisher
from backend.observability.s3_store import S3MetricsStore


@dataclass
class NodeResult:
    """Results captured for a single orchestration node."""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    cost_usd: float = 0.0
    llm_time_ms: float = 0.0
    tool_time_ms: float = 0.0
    turns: int = 0
    success: bool = True
    error: str = ""


@dataclass
class NodeRecord:
    """Internal tracking for a flow node."""
    node_id: str = ""
    agent_name: str = ""
    model_id: str = ""
    order: int = 0
    status: str = "pending"
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    wait_time_ms: float = 0.0
    result: Optional[NodeResult] = None


# Standard audit flow DAG
AUDIT_FLOW_EDGES = {
    "planning": [],
    "evidence": ["planning"],
    "org_controls": ["evidence"],
    "people_controls": ["evidence"],
    "tech_controls": ["evidence"],
    "consolidation": ["org_controls", "people_controls", "tech_controls"],
}


class FlowTracker:
    """
    Tracks execution of the orchestration flow and publishes Level 3 metrics.
    """

    def __init__(
        self,
        audit_id: str = "",
        session_id: str = "",
        actor_id: str = "",
        trace_ctx: Optional[TraceContext] = None,
        publish_metrics: bool = True,
    ):
        self.audit_id = audit_id
        self.session_id = session_id
        self.flow_id = uuid.uuid4().hex[:12]

        self.trace_ctx = trace_ctx or TraceContext(
            audit_id=audit_id,
            session_id=session_id,
            actor_id=actor_id,
        )

        self.logger = StructuredLogger(
            agent_name="orchestration_flow",
            trace_ctx=self.trace_ctx,
        )

        self._publisher = CloudWatchPublisher() if publish_metrics else None
        self._s3_store = S3MetricsStore() if publish_metrics else None
        self._start_time = time.perf_counter()
        self._nodes: dict[str, NodeRecord] = {}
        self._node_order = 0

        self.logger.info("Orchestration flow started", flow_id=self.flow_id, audit_id=audit_id)

    @contextmanager
    def node(self, node_id: str, agent_name: str = "", model_id: str = ""):
        """
        Context manager to track a single node execution.

        Args:
            node_id: Unique node identifier (e.g., 'planning', 'evidence').
            agent_name: Name of the agent handling this node.
            model_id: LLM model used by this agent.
        """
        record = NodeRecord(
            node_id=node_id,
            agent_name=agent_name or node_id,
            model_id=model_id,
            order=self._node_order,
            status="running",
            start_time=time.perf_counter(),
        )
        self._node_order += 1

        # Calculate wait time from dependencies
        deps = AUDIT_FLOW_EDGES.get(node_id, [])
        if deps:
            latest_dep_end = 0.0
            for dep_id in deps:
                dep = self._nodes.get(dep_id)
                if dep and dep.end_time > 0:
                    latest_dep_end = max(latest_dep_end, dep.end_time)
            if latest_dep_end > 0:
                record.wait_time_ms = max(0, (record.start_time - latest_dep_end)) * 1000

        self.logger.info(f"Node {node_id} started", node_id=node_id, agent_name=agent_name, model_id=model_id)

        class _NodeCtx:
            def set_result(
                self_inner,
                input_tokens: int = 0,
                output_tokens: int = 0,
                tool_calls: int = 0,
                tool_errors: int = 0,
                cost: float = 0.0,
                llm_time_ms: float = 0.0,
                tool_time_ms: float = 0.0,
                turns: int = 0,
            ):
                record.result = NodeResult(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    tool_calls=tool_calls,
                    tool_errors=tool_errors,
                    cost_usd=cost,
                    llm_time_ms=llm_time_ms,
                    tool_time_ms=tool_time_ms,
                    turns=turns,
                )

            def set_error(self_inner, error: str):
                record.status = "failed"
                if record.result is None:
                    record.result = NodeResult()
                record.result.success = False
                record.result.error = error

        ctx = _NodeCtx()
        try:
            yield ctx
        except Exception as exc:
            record.status = "failed"
            if record.result is None:
                record.result = NodeResult(success=False, error=str(exc)[:200])
            self.logger.error(f"Node {node_id} failed", node_id=node_id, error=str(exc)[:200])
            raise
        finally:
            record.end_time = time.perf_counter()
            record.duration_ms = (record.end_time - record.start_time) * 1000
            if record.status == "running":
                record.status = "completed"
            self._nodes[node_id] = record

            self.logger.info(
                f"Node {node_id} {record.status}",
                node_id=node_id,
                duration_ms=round(record.duration_ms, 2),
                status=record.status,
            )

            # Publish per-node metrics
            if self._publisher and record.result:
                self._publisher.publish_node_metrics(
                    node_id=node_id,
                    agent_name=record.agent_name,
                    duration_ms=record.duration_ms,
                    wait_time_ms=record.wait_time_ms,
                    llm_time_ms=record.result.llm_time_ms,
                    tool_time_ms=record.result.tool_time_ms,
                    tokens=record.result.input_tokens + record.result.output_tokens,
                    cost_usd=record.result.cost_usd,
                    status=record.status,
                )

    def finalize(self) -> dict:
        """Finalize flow tracking, compute aggregates, publish orchestration metrics."""
        total_flow_time = (time.perf_counter() - self._start_time) * 1000

        # Aggregate
        total_tokens = 0
        total_cost = 0.0
        total_tool_calls = 0
        total_agents = 0
        failed_nodes = []
        bottleneck_id = ""
        max_duration = 0.0

        for node_id, record in self._nodes.items():
            if record.status == "completed":
                total_agents += 1
            if record.status == "failed":
                failed_nodes.append(node_id)
            if record.result:
                total_tokens += record.result.input_tokens + record.result.output_tokens
                total_cost += record.result.cost_usd
                total_tool_calls += record.result.tool_calls
            if record.duration_ms > max_duration:
                max_duration = record.duration_ms
                bottleneck_id = node_id

        # Determine bottleneck reason
        bottleneck_reason = ""
        if bottleneck_id and self._nodes[bottleneck_id].result:
            r = self._nodes[bottleneck_id].result
            if r.llm_time_ms > r.tool_time_ms:
                bottleneck_reason = "llm_latency"
            elif r.tool_time_ms > r.llm_time_ms:
                bottleneck_reason = "tool_execution"
            else:
                bottleneck_reason = "balanced"

        # Critical path
        critical_path_ms = self._compute_critical_path()

        success = len(failed_nodes) == 0

        self.logger.info(
            "Orchestration flow completed",
            flow_id=self.flow_id,
            total_flow_time_ms=round(total_flow_time, 2),
            total_agents_invoked=total_agents,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            bottleneck_node=bottleneck_id,
            bottleneck_reason=bottleneck_reason,
            success=success,
        )

        # Publish flow-level metrics
        if self._publisher:
            self._publisher.publish_orchestration_metrics(
                flow_id=self.flow_id,
                total_flow_time_ms=total_flow_time,
                critical_path_time_ms=critical_path_ms,
                total_agents_invoked=total_agents,
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
                total_tool_calls=total_tool_calls,
                bottleneck_node=bottleneck_id,
                bottleneck_reason=bottleneck_reason,
                success=success,
                failed_nodes=len(failed_nodes),
            )

        # Build result
        result = {
            "flow_id": self.flow_id,
            "audit_id": self.audit_id,
            "session_id": self.session_id,
            "trace_id": self.trace_ctx.trace_id,
            "total_flow_time_ms": round(total_flow_time, 2),
            "critical_path_time_ms": round(critical_path_ms, 2),
            "total_agents_invoked": total_agents,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "total_tool_calls": total_tool_calls,
            "bottleneck_node": bottleneck_id,
            "bottleneck_reason": bottleneck_reason,
            "success": success,
            "failed_nodes": failed_nodes,
            "nodes": {
                nid: {
                    "agent_name": n.agent_name,
                    "model_id": n.model_id,
                    "duration_ms": round(n.duration_ms, 2),
                    "wait_time_ms": round(n.wait_time_ms, 2),
                    "status": n.status,
                    "tokens": (n.result.input_tokens + n.result.output_tokens) if n.result else 0,
                    "cost_usd": round(n.result.cost_usd, 6) if n.result else 0,
                    "tool_calls": n.result.tool_calls if n.result else 0,
                }
                for nid, n in self._nodes.items()
            },
        }

        # Persist flow metrics and diagram to S3
        if self._s3_store:
            self._s3_store.save_flow_metrics(self.audit_id, self.flow_id, result)
            self._s3_store.save_flow_diagram(self.audit_id, self.flow_id, self.mermaid_diagram())

        return result

    def _compute_critical_path(self) -> float:
        """Compute longest sequential dependency chain duration."""
        memo: dict[str, float] = {}

        def longest(node_id: str) -> float:
            if node_id in memo:
                return memo[node_id]
            record = self._nodes.get(node_id)
            duration = record.duration_ms if record else 0.0
            deps = AUDIT_FLOW_EDGES.get(node_id, [])
            if not deps:
                memo[node_id] = duration
                return duration
            max_dep = max(longest(d) for d in deps if d in self._nodes)
            result = max_dep + duration
            memo[node_id] = result
            return result

        if not self._nodes:
            return 0.0
        return max(longest(nid) for nid in self._nodes if nid in AUDIT_FLOW_EDGES)

    def mermaid_diagram(self) -> str:
        """Generate a Mermaid flowchart with per-node metrics."""
        lines = ["```mermaid", "flowchart TD", ""]

        for node_id, record in self._nodes.items():
            tokens = 0
            cost = 0.0
            if record.result:
                tokens = record.result.input_tokens + record.result.output_tokens
                cost = record.result.cost_usd

            label = (
                f"{record.agent_name}\\n"
                f"⏱ {record.duration_ms:.0f}ms\\n"
                f"🔤 {tokens} tok\\n"
                f"💰 ${cost:.4f}"
            )

            if record.status == "failed":
                lines.append(f'    {node_id}[/"{label}"/]:::failed')
            elif node_id == self._get_bottleneck_id():
                lines.append(f'    {node_id}["{label}"]:::bottleneck')
            else:
                lines.append(f'    {node_id}["{label}"]:::ok')

        lines.append("")

        # Edges
        for node_id, deps in AUDIT_FLOW_EDGES.items():
            if node_id in self._nodes:
                for dep in deps:
                    if dep in self._nodes:
                        lines.append(f"    {dep} --> {node_id}")

        lines.extend([
            "",
            "    classDef ok fill:#d4edda,stroke:#28a745",
            "    classDef failed fill:#f8d7da,stroke:#dc3545",
            "    classDef bottleneck fill:#fff3cd,stroke:#ffc107",
            "```",
        ])
        return "\n".join(lines)

    def _get_bottleneck_id(self) -> str:
        if not self._nodes:
            return ""
        return max(self._nodes.items(), key=lambda x: x[1].duration_ms)[0]
