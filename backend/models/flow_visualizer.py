"""
Orchestration Flow Visualizer — Generates a visual DAG representation
of the multi-agent audit flow with per-node metrics.

Outputs:
- Mermaid diagram (for Markdown/documentation rendering)
- JSON graph structure (for frontend visualization)
- Bottleneck analysis report

Each node in the graph represents an AgentCore agent, with:
- LLM metrics: model used, latency, tokens, TTFT
- Agent metrics: execution time, tool calls, success/failure
- Flow metrics: wait time, critical path membership
"""

import json
from dataclasses import asdict
from typing import Optional

from backend.models.metrics import (
    AgentMetrics,
    OrchestrationFlowMetrics,
    OrchestrationNodeMetrics,
)


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATION FLOW DEFINITION
# ─────────────────────────────────────────────────────────────────────────────

# Define the standard ISO 27001 audit flow DAG
AUDIT_FLOW_DEFINITION = {
    "nodes": [
        {
            "id": "planning",
            "agent_name": "planning_agent",
            "label": "Planificación",
            "description": "Generate audit plan (scope, schedule, criteria)",
            "order": 0,
            "depends_on": [],
        },
        {
            "id": "evidence",
            "agent_name": "evidence_agent",
            "label": "Recopilación de Evidencia",
            "description": "Retrieve and organize documentary evidence via RAG",
            "order": 1,
            "depends_on": ["planning"],
        },
        {
            "id": "org_controls",
            "agent_name": "organizational_controls_agent",
            "label": "Controles Organizacionales (A.5)",
            "description": "Evaluate 37 organizational controls",
            "order": 2,
            "depends_on": ["evidence"],
        },
        {
            "id": "people_controls",
            "agent_name": "people_controls_agent",
            "label": "Controles de Personas (A.6)",
            "description": "Evaluate 8 people controls",
            "order": 2,  # Parallel with org_controls
            "depends_on": ["evidence"],
        },
        {
            "id": "tech_controls",
            "agent_name": "technological_controls_agent",
            "label": "Controles Tecnológicos (A.8)",
            "description": "Evaluate 34 technological controls",
            "order": 2,  # Parallel with org_controls
            "depends_on": ["evidence"],
        },
        {
            "id": "consolidation",
            "agent_name": "consolidation_agent",
            "label": "Consolidación y Reporte",
            "description": "Verify consistency, generate final audit report",
            "order": 3,
            "depends_on": ["org_controls", "people_controls", "tech_controls"],
        },
    ],
    "edges": [
        {"from": "planning", "to": "evidence"},
        {"from": "evidence", "to": "org_controls"},
        {"from": "evidence", "to": "people_controls"},
        {"from": "evidence", "to": "tech_controls"},
        {"from": "org_controls", "to": "consolidation"},
        {"from": "people_controls", "to": "consolidation"},
        {"from": "tech_controls", "to": "consolidation"},
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# MERMAID DIAGRAM GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_mermaid_diagram(flow_metrics: Optional[OrchestrationFlowMetrics] = None) -> str:
    """
    Generate a Mermaid flowchart diagram of the orchestration flow.
    If flow_metrics are provided, nodes are annotated with actual performance data.

    Args:
        flow_metrics: Optional flow metrics for annotation.

    Returns:
        Mermaid diagram string.
    """
    lines = [
        "```mermaid",
        "flowchart TD",
        "",
    ]

    # Build node lookup from metrics
    node_metrics_map = {}
    if flow_metrics:
        for node in flow_metrics.nodes:
            node_metrics_map[node.node_id] = node

    # Define nodes
    for node_def in AUDIT_FLOW_DEFINITION["nodes"]:
        node_id = node_def["id"]
        label = node_def["label"]

        # Add metrics annotation if available
        nm = node_metrics_map.get(node_id)
        if nm and nm.agent_metrics:
            am = nm.agent_metrics
            annotation = (
                f"{label}\\n"
                f"⏱ {am.total_execution_time_ms:.0f}ms\\n"
                f"🔤 {am.total_input_tokens + am.total_output_tokens} tokens\\n"
                f"🔧 {am.tool_call_count} tools\\n"
                f"💰 ${am.total_estimated_cost_usd:.4f}"
            )
            # Style based on status
            if nm.status == "failed":
                lines.append(f"    {node_id}[/\"{annotation}\"/]:::failed")
            elif node_id == flow_metrics.bottleneck_node:
                lines.append(f"    {node_id}[\"{annotation}\"]:::bottleneck")
            else:
                lines.append(f"    {node_id}[\"{annotation}\"]:::success")
        else:
            lines.append(f"    {node_id}[\"{label}\"]")

    lines.append("")

    # Define edges
    for edge in AUDIT_FLOW_DEFINITION["edges"]:
        src = edge["from"]
        dst = edge["to"]

        # Add edge timing if available
        dst_node = node_metrics_map.get(dst)
        if dst_node and dst_node.wait_time_ms > 0:
            lines.append(f"    {src} -->|wait: {dst_node.wait_time_ms:.0f}ms| {dst}")
        else:
            lines.append(f"    {src} --> {dst}")

    lines.append("")

    # Style definitions
    lines.extend([
        "    classDef success fill:#d4edda,stroke:#28a745,color:#155724",
        "    classDef failed fill:#f8d7da,stroke:#dc3545,color:#721c24",
        "    classDef bottleneck fill:#fff3cd,stroke:#ffc107,color:#856404",
        "```",
    ])

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# JSON GRAPH EXPORT (for frontend visualization)
# ─────────────────────────────────────────────────────────────────────────────

def generate_flow_graph_json(flow_metrics: Optional[OrchestrationFlowMetrics] = None) -> dict:
    """
    Generate a JSON graph structure for frontend visualization.
    Each node includes agent and LLM metrics as attributes.

    Args:
        flow_metrics: Optional flow metrics for enrichment.

    Returns:
        Dict with 'nodes', 'edges', 'summary', and 'bottlenecks'.
    """
    node_metrics_map = {}
    if flow_metrics:
        for node in flow_metrics.nodes:
            node_metrics_map[node.node_id] = node

    graph_nodes = []
    for node_def in AUDIT_FLOW_DEFINITION["nodes"]:
        node_id = node_def["id"]
        graph_node = {
            "id": node_id,
            "label": node_def["label"],
            "agent_name": node_def["agent_name"],
            "description": node_def["description"],
            "order": node_def["order"],
            "depends_on": node_def["depends_on"],
            # Metrics (populated if available)
            "metrics": {
                "status": "pending",
                "execution_time_ms": 0,
                "llm_time_ms": 0,
                "tool_time_ms": 0,
                "wait_time_ms": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "tool_calls": 0,
                "estimated_cost_usd": 0.0,
                "model_id": "",
                "model_display_name": "",
                "turns_count": 0,
                "ttft_ms": 0.0,
                "output_tokens_per_second": 0.0,
                "success": True,
                "is_bottleneck": False,
            },
        }

        # Enrich with actual metrics
        nm = node_metrics_map.get(node_id)
        if nm:
            graph_node["metrics"]["status"] = nm.status
            graph_node["metrics"]["execution_time_ms"] = round(nm.duration_ms, 1)
            graph_node["metrics"]["wait_time_ms"] = round(nm.wait_time_ms, 1)
            graph_node["metrics"]["model_id"] = nm.model_id_used
            graph_node["metrics"]["input_tokens"] = nm.input_tokens
            graph_node["metrics"]["output_tokens"] = nm.output_tokens
            graph_node["metrics"]["total_tokens"] = nm.input_tokens + nm.output_tokens
            graph_node["metrics"]["llm_time_ms"] = round(nm.llm_latency_ms, 1)

            if nm.agent_metrics:
                am = nm.agent_metrics
                graph_node["metrics"]["tool_time_ms"] = round(am.tool_execution_time_ms, 1)
                graph_node["metrics"]["tool_calls"] = am.tool_call_count
                graph_node["metrics"]["estimated_cost_usd"] = am.total_estimated_cost_usd
                graph_node["metrics"]["turns_count"] = am.turns_count
                graph_node["metrics"]["success"] = am.success

                # First model invocation TTFT
                if am.model_invocations:
                    first = am.model_invocations[0]
                    graph_node["metrics"]["ttft_ms"] = first.time_to_first_token_ms
                    graph_node["metrics"]["output_tokens_per_second"] = first.output_tokens_per_second
                    graph_node["metrics"]["model_display_name"] = first.model_display_name

            if flow_metrics and node_id == flow_metrics.bottleneck_node:
                graph_node["metrics"]["is_bottleneck"] = True

        graph_nodes.append(graph_node)

    # Build summary
    summary = {
        "total_flow_time_ms": flow_metrics.total_flow_time_ms if flow_metrics else 0,
        "total_tokens": flow_metrics.total_tokens_consumed if flow_metrics else 0,
        "total_cost_usd": flow_metrics.total_estimated_cost_usd if flow_metrics else 0,
        "agents_invoked": flow_metrics.total_agents_invoked if flow_metrics else 0,
        "success": flow_metrics.success if flow_metrics else True,
        "bottleneck_node": flow_metrics.bottleneck_node if flow_metrics else "",
        "bottleneck_reason": flow_metrics.bottleneck_reason if flow_metrics else "",
    }

    # Bottleneck analysis
    bottlenecks = []
    if flow_metrics:
        sorted_nodes = sorted(
            [n for n in flow_metrics.nodes if n.duration_ms > 0],
            key=lambda n: n.duration_ms,
            reverse=True,
        )
        for node in sorted_nodes[:3]:  # Top 3 slowest
            reason = "unknown"
            if node.agent_metrics:
                if node.agent_metrics.llm_time_ms > node.agent_metrics.tool_execution_time_ms:
                    reason = "llm_latency"
                elif node.agent_metrics.tool_execution_time_ms > node.agent_metrics.llm_time_ms:
                    reason = "tool_execution"
                else:
                    reason = "balanced"
            bottlenecks.append({
                "node_id": node.node_id,
                "agent_name": node.agent_name,
                "duration_ms": round(node.duration_ms, 1),
                "reason": reason,
                "recommendation": _get_optimization_recommendation(node, reason),
            })

    return {
        "flow_id": flow_metrics.flow_id if flow_metrics else "",
        "nodes": graph_nodes,
        "edges": AUDIT_FLOW_DEFINITION["edges"],
        "summary": summary,
        "bottlenecks": bottlenecks,
    }


def _get_optimization_recommendation(node: OrchestrationNodeMetrics, reason: str) -> str:
    """Generate optimization recommendation based on bottleneck analysis."""
    if reason == "llm_latency":
        return (
            f"Consider using a faster model (Nova Lite/Micro) for {node.agent_name}, "
            f"or reduce prompt size by summarizing evidence before passing to the agent."
        )
    elif reason == "tool_execution":
        return (
            f"Tool execution dominates {node.agent_name} time. Consider caching RAG results, "
            f"batching tool calls, or parallelizing evidence retrieval."
        )
    else:
        return (
            f"Execution time for {node.agent_name} is balanced between LLM and tools. "
            f"Consider both model optimization and tool caching."
        )


# ─────────────────────────────────────────────────────────────────────────────
# BOTTLENECK ANALYSIS REPORT
# ─────────────────────────────────────────────────────────────────────────────

def generate_bottleneck_report(flow_metrics: OrchestrationFlowMetrics) -> str:
    """
    Generate a human-readable bottleneck analysis report.

    Args:
        flow_metrics: Completed orchestration flow metrics.

    Returns:
        Markdown-formatted analysis report.
    """
    lines = [
        "# Orchestration Flow Performance Report",
        "",
        f"**Flow ID:** {flow_metrics.flow_id}",
        f"**Audit ID:** {flow_metrics.audit_id}",
        f"**Timestamp:** {flow_metrics.timestamp}",
        f"**Status:** {'✅ Success' if flow_metrics.success else '❌ Failed'}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Flow Time | {flow_metrics.total_flow_time_ms:.0f} ms ({flow_metrics.total_flow_time_ms/1000:.1f}s) |",
        f"| Agents Invoked | {flow_metrics.total_agents_invoked} |",
        f"| Total LLM Invocations | {flow_metrics.total_llm_invocations} |",
        f"| Total Tokens | {flow_metrics.total_tokens_consumed:,} |",
        f"| Total Cost | ${flow_metrics.total_estimated_cost_usd:.4f} |",
        f"| Total Tool Calls | {flow_metrics.total_tool_calls} |",
        "",
        "## Per-Node Breakdown",
        "",
        "| Node | Agent | Duration | LLM Time | Tool Time | Tokens | Cost | Status |",
        "|------|-------|----------|----------|-----------|--------|------|--------|",
    ]

    for node in sorted(flow_metrics.nodes, key=lambda n: n.order_index):
        tokens = node.input_tokens + node.output_tokens
        cost = node.agent_metrics.total_estimated_cost_usd if node.agent_metrics else 0
        llm_t = node.agent_metrics.llm_time_ms if node.agent_metrics else 0
        tool_t = node.agent_metrics.tool_execution_time_ms if node.agent_metrics else 0
        is_bn = " 🔥" if node.node_id == flow_metrics.bottleneck_node else ""

        lines.append(
            f"| {node.node_id}{is_bn} | {node.agent_name} | "
            f"{node.duration_ms:.0f}ms | {llm_t:.0f}ms | {tool_t:.0f}ms | "
            f"{tokens:,} | ${cost:.4f} | {node.status} |"
        )

    lines.extend([
        "",
        "## Bottleneck Analysis",
        "",
        f"**Bottleneck Node:** `{flow_metrics.bottleneck_node}`",
        f"**Primary Cause:** {flow_metrics.bottleneck_reason}",
        "",
    ])

    # Model performance comparison within the flow
    lines.extend([
        "## Model Performance in This Flow",
        "",
        "| Agent | Model | Latency | OTPS | Input Tokens | Output Tokens |",
        "|-------|-------|---------|------|-------------|--------------|",
    ])

    for node in flow_metrics.nodes:
        if node.agent_metrics and node.agent_metrics.model_invocations:
            for mi in node.agent_metrics.model_invocations[:1]:  # First invocation per agent
                otps = f"{mi.output_tokens_per_second:.1f}" if mi.output_tokens_per_second > 0 else "N/A"
                lines.append(
                    f"| {node.agent_name} | {mi.model_id} | "
                    f"{mi.total_latency_ms:.0f}ms | {otps} tok/s | "
                    f"{mi.input_tokens:,} | {mi.output_tokens:,} |"
                )

    lines.extend([
        "",
        "## Optimization Recommendations",
        "",
    ])

    graph = generate_flow_graph_json(flow_metrics)
    for i, bn in enumerate(graph["bottlenecks"], 1):
        lines.append(f"{i}. **{bn['agent_name']}** ({bn['duration_ms']:.0f}ms) — {bn['recommendation']}")

    return "\n".join(lines)
