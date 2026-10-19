"""
Orchestration Tracker — Tracks the full multi-agent audit flow execution,
producing the Level 3 orchestration metrics with visual flow data.

Usage in the consolidation agent:

    from backend.models.orchestration_tracker import OrchestrationTracker

    tracker = OrchestrationTracker(audit_id="audit_001", session_id="session_xyz")

    # Track each sub-agent invocation
    with tracker.track_node("planning", model_id="amazon.nova-pro-v1:0") as node:
        result = invoke_planning_agent(...)
        node.set_agent_metrics(agent_metrics)

    with tracker.track_node("evidence", model_id="amazon.nova-lite-v1:0") as node:
        result = invoke_evidence_agent(...)
        node.set_agent_metrics(agent_metrics)

    # ... parallel domain agents ...

    # Finalize and get flow metrics + visualization
    flow_metrics = tracker.finalize()
    mermaid = tracker.get_mermaid_diagram()
    graph_json = tracker.get_flow_graph()
    report = tracker.get_bottleneck_report()
"""

import time
from contextlib import contextmanager
from typing import Optional

from backend.models.metrics import (
    AgentMetrics,
    MetricsStore,
    OrchestrationFlowMetrics,
    OrchestrationNodeMetrics,
)
from backend.models.flow_visualizer import (
    generate_bottleneck_report,
    generate_flow_graph_json,
    generate_mermaid_diagram,
)


class OrchestrationTracker:
    """
    Tracks execution of the full orchestration flow across multiple agents.
    Produces Level 3 metrics and visualization data.
    """

    def __init__(self, audit_id: str = "", session_id: str = ""):
        self.audit_id = audit_id
        self.session_id = session_id
        self._start_time = time.perf_counter()
        self._nodes: dict[str, OrchestrationNodeMetrics] = {}
        self._node_order = 0
        self._flow_metrics: Optional[OrchestrationFlowMetrics] = None

    @contextmanager
    def track_node(self, node_id: str, model_id: str = "", agent_name: str = ""):
        """
        Context manager to track a single node (agent) in the orchestration flow.

        Args:
            node_id: Unique node identifier (e.g., 'planning', 'evidence', 'org_controls').
            model_id: Bedrock model ID used by this agent.
            agent_name: Display name for the agent.
        """
        node = OrchestrationNodeMetrics(
            node_id=node_id,
            agent_name=agent_name or node_id,
            order_index=self._node_order,
            model_id_used=model_id,
            status="running",
            start_time_ms=(time.perf_counter() - self._start_time) * 1000,
        )
        self._node_order += 1

        # Calculate wait time (time since last node completed)
        if self._nodes:
            last_end = max(n.end_time_ms for n in self._nodes.values() if n.end_time_ms > 0)
            node.wait_time_ms = max(0, node.start_time_ms - last_end)

        class _NodeContext:
            def set_agent_metrics(self_inner, metrics: AgentMetrics):
                node.agent_metrics = metrics
                node.input_tokens = metrics.total_input_tokens
                node.output_tokens = metrics.total_output_tokens
                node.llm_latency_ms = metrics.llm_time_ms

            def set_error(self_inner, error: str):
                node.status = "failed"

            def skip(self_inner):
                node.status = "skipped"

        ctx = _NodeContext()
        try:
            yield ctx
        except Exception:
            node.status = "failed"
            raise
        finally:
            node.end_time_ms = (time.perf_counter() - self._start_time) * 1000
            node.duration_ms = node.end_time_ms - node.start_time_ms
            if node.status == "running":
                node.status = "completed"
            self._nodes[node_id] = node

    def finalize(self, persist: bool = True) -> OrchestrationFlowMetrics:
        """
        Finalize the orchestration tracking and compute flow-level metrics.

        Args:
            persist: Whether to save metrics to DynamoDB/CloudWatch.

        Returns:
            Complete OrchestrationFlowMetrics.
        """
        total_time = (time.perf_counter() - self._start_time) * 1000

        flow = OrchestrationFlowMetrics(
            audit_id=self.audit_id,
            session_id=self.session_id,
            total_flow_time_ms=total_time,
            nodes=list(self._nodes.values()),
        )
        flow.compute_aggregates()

        # Compute critical path (longest sequential chain)
        flow.critical_path_time_ms = self._compute_critical_path()

        self._flow_metrics = flow

        if persist:
            try:
                store = MetricsStore()
                store.save_flow_metrics(flow)
            except Exception:
                pass  # Non-blocking

        return flow

    def _compute_critical_path(self) -> float:
        """
        Compute the critical path time (longest sequential dependency chain).
        Uses the DAG structure to find the longest path.
        """
        from backend.models.flow_visualizer import AUDIT_FLOW_DEFINITION

        # Build adjacency list
        graph = {}
        for node_def in AUDIT_FLOW_DEFINITION["nodes"]:
            graph[node_def["id"]] = node_def["depends_on"]

        # Find longest path using DFS
        def longest_path(node_id: str, memo: dict) -> float:
            if node_id in memo:
                return memo[node_id]

            node = self._nodes.get(node_id)
            duration = node.duration_ms if node else 0

            deps = graph.get(node_id, [])
            if not deps:
                memo[node_id] = duration
                return duration

            max_dep_path = max(longest_path(dep, memo) for dep in deps)
            result = max_dep_path + duration
            memo[node_id] = result
            return result

        memo = {}
        if self._nodes:
            return max(longest_path(nid, memo) for nid in graph.keys() if nid in self._nodes)
        return 0.0

    def get_mermaid_diagram(self) -> str:
        """Get Mermaid diagram of the flow with metrics annotations."""
        if not self._flow_metrics:
            self.finalize(persist=False)
        return generate_mermaid_diagram(self._flow_metrics)

    def get_flow_graph(self) -> dict:
        """Get JSON graph structure for frontend visualization."""
        if not self._flow_metrics:
            self.finalize(persist=False)
        return generate_flow_graph_json(self._flow_metrics)

    def get_bottleneck_report(self) -> str:
        """Get markdown bottleneck analysis report."""
        if not self._flow_metrics:
            self.finalize(persist=False)
        return generate_bottleneck_report(self._flow_metrics)

    def get_summary(self) -> dict:
        """Get a quick summary of the flow execution."""
        if not self._flow_metrics:
            self.finalize(persist=False)
        fm = self._flow_metrics
        return {
            "flow_id": fm.flow_id,
            "audit_id": fm.audit_id,
            "total_flow_time_ms": round(fm.total_flow_time_ms, 1),
            "total_flow_time_seconds": round(fm.total_flow_time_ms / 1000, 2),
            "agents_invoked": fm.total_agents_invoked,
            "total_tokens": fm.total_tokens_consumed,
            "total_cost_usd": fm.total_estimated_cost_usd,
            "bottleneck_node": fm.bottleneck_node,
            "bottleneck_reason": fm.bottleneck_reason,
            "success": fm.success,
            "failed_nodes": fm.failed_nodes,
        }
