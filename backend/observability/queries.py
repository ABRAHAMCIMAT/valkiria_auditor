"""
CloudWatch Logs Insights Queries — Pre-built queries for analyzing
model, agent, and orchestration performance from structured logs.

These queries target the JSON-structured logs emitted by StructuredLogger.
Run them via CloudWatch Logs Insights console or programmatically via boto3.
"""


# ─────────────────────────────────────────────────────────────────────────────
# LEVEL 1: Model Performance Queries
# ─────────────────────────────────────────────────────────────────────────────

MODEL_LATENCY_PERCENTILES = """
filter metric_type = "model_invocation"
| stats
    avg(latency_ms) as avg_latency,
    pct(latency_ms, 50) as p50,
    pct(latency_ms, 90) as p90,
    pct(latency_ms, 99) as p99,
    count(*) as invocations
    by model_id
| sort avg_latency desc
"""

MODEL_TOKEN_UTILIZATION = """
filter metric_type = "model_invocation"
| stats
    avg(input_tokens) as avg_input,
    avg(output_tokens) as avg_output,
    sum(input_tokens + output_tokens) as total_tokens,
    avg(output_tokens_per_second) as avg_otps
    by model_id
| sort total_tokens desc
"""

MODEL_COST_BREAKDOWN = """
filter metric_type = "model_invocation"
| stats
    sum(estimated_cost_usd) as total_cost,
    avg(estimated_cost_usd) as avg_cost_per_call,
    count(*) as invocations
    by model_id
| sort total_cost desc
"""

MODEL_ERROR_RATE = """
filter metric_type = "model_invocation"
| stats
    count(*) as total,
    sum(case when success = 0 then 1 else 0 end) as errors,
    (sum(case when success = 0 then 1 else 0 end) / count(*)) * 100 as error_rate_pct
    by model_id
| sort error_rate_pct desc
"""

MODEL_COMPARISON_BY_AGENT = """
filter metric_type = "model_invocation"
| stats
    avg(latency_ms) as avg_latency,
    avg(output_tokens_per_second) as avg_otps,
    avg(estimated_cost_usd) as avg_cost
    by model_id, agent_name
| sort agent_name, avg_latency
"""


# ─────────────────────────────────────────────────────────────────────────────
# LEVEL 2: Agent Performance Queries
# ─────────────────────────────────────────────────────────────────────────────

AGENT_EXECUTION_BREAKDOWN = """
filter metric_type = "agent_complete"
| stats
    avg(total_execution_time_ms) as avg_total,
    avg(llm_time_ms) as avg_llm,
    avg(tool_execution_time_ms) as avg_tool,
    avg(overhead_time_ms) as avg_overhead,
    avg(total_tokens) as avg_tokens,
    avg(estimated_cost_usd) as avg_cost
    by agent_name
| sort avg_total desc
"""

AGENT_TOOL_USAGE = """
filter metric_type = "tool_call"
| stats
    count(*) as total_calls,
    sum(case when success = 1 then 1 else 0 end) as successes,
    sum(case when success = 0 then 1 else 0 end) as failures,
    avg(duration_ms) as avg_duration
    by agent_name, tool_name
| sort total_calls desc
"""

AGENT_SUCCESS_RATE = """
filter metric_type = "agent_complete"
| stats
    count(*) as total,
    sum(case when success = 1 then 1 else 0 end) as successes,
    (sum(case when success = 1 then 1 else 0 end) / count(*)) * 100 as success_rate_pct
    by agent_name
| sort success_rate_pct asc
"""

AGENT_LLM_EFFICIENCY = """
filter metric_type = "agent_complete"
| stats
    avg(llm_time_ms / total_execution_time_ms) as llm_ratio,
    avg(tool_execution_time_ms / total_execution_time_ms) as tool_ratio,
    avg(turns_count) as avg_turns
    by agent_name
| sort llm_ratio desc
"""


# ─────────────────────────────────────────────────────────────────────────────
# LEVEL 3: Orchestration Flow Queries
# ─────────────────────────────────────────────────────────────────────────────

FLOW_SUMMARY = """
filter message = "Orchestration flow completed"
| stats
    avg(total_flow_time_ms) as avg_flow_time,
    avg(total_tokens) as avg_tokens,
    avg(total_cost_usd) as avg_cost,
    count(*) as total_flows,
    sum(case when success = 1 then 1 else 0 end) as successes
    by bin(1h)
| sort @timestamp desc
"""

FLOW_BOTTLENECK_FREQUENCY = """
filter message = "Orchestration flow completed"
| stats count(*) as occurrences by bottleneck_node, bottleneck_reason
| sort occurrences desc
"""

NODE_DURATION_COMPARISON = """
filter level = "INFO" and ispresent(node_id) and ispresent(duration_ms)
| stats
    avg(duration_ms) as avg_duration,
    pct(duration_ms, 90) as p90_duration,
    max(duration_ms) as max_duration
    by node_id
| sort avg_duration desc
"""

TRACE_FULL_FLOW = """
filter trace_id = "{trace_id}"
| sort @timestamp asc
| fields @timestamp, agent_name, message, level, duration_ms, model_id, tool_name
"""


# ─────────────────────────────────────────────────────────────────────────────
# ERROR INVESTIGATION
# ─────────────────────────────────────────────────────────────────────────────

RECENT_ERRORS = """
filter level = "ERROR"
| sort @timestamp desc
| limit 50
| fields @timestamp, agent_name, message, error_type, error_message, trace_id
"""

FAILED_FLOWS = """
filter message = "Orchestration flow completed" and success = 0
| sort @timestamp desc
| limit 20
| fields @timestamp, flow_id, audit_id, total_flow_time_ms, failed_nodes
"""


def get_query(query_name: str) -> str:
    """Get a pre-built query by name."""
    queries = {
        "model_latency": MODEL_LATENCY_PERCENTILES,
        "model_tokens": MODEL_TOKEN_UTILIZATION,
        "model_cost": MODEL_COST_BREAKDOWN,
        "model_errors": MODEL_ERROR_RATE,
        "model_by_agent": MODEL_COMPARISON_BY_AGENT,
        "agent_breakdown": AGENT_EXECUTION_BREAKDOWN,
        "agent_tools": AGENT_TOOL_USAGE,
        "agent_success": AGENT_SUCCESS_RATE,
        "agent_efficiency": AGENT_LLM_EFFICIENCY,
        "flow_summary": FLOW_SUMMARY,
        "flow_bottlenecks": FLOW_BOTTLENECK_FREQUENCY,
        "node_duration": NODE_DURATION_COMPARISON,
        "recent_errors": RECENT_ERRORS,
        "failed_flows": FAILED_FLOWS,
    }
    if query_name not in queries:
        raise ValueError(f"Unknown query: {query_name}. Available: {list(queries.keys())}")
    return queries[query_name]
