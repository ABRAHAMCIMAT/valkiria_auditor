"""
CloudWatch Dashboard Definitions — IaC-ready JSON templates for monitoring
the multi-agent ISO 27001 audit system.

Dashboards:
1. Model Performance Dashboard — Per-model latency, tokens, cost, OTPS
2. Agent Performance Dashboard — Per-agent execution breakdown
3. Orchestration Flow Dashboard — End-to-end flow with bottleneck tracking

These JSON definitions can be deployed via CDK (aws_cloudwatch.CfnDashboard)
or via AWS CLI (aws cloudwatch put-dashboard).
"""

import json

NAMESPACE = "AgentCore/ISO27001Audit"
REGION = "us-east-1"

# The 7 models in the registry
MODELS = [
    "openai.gpt-oss-120b-1:0",
    "qwen.qwen3-32b-v1:0",
    "anthropic.claude-haiku-4-5-20250514-v1:0",
    "anthropic.claude-sonnet-4-6-20250514-v1:0",
    "meta.llama4-maverick-17b-instruct-v1:0",
    "mistral.mistral-large-2407-v1:0",
    "deepseek.deepseek-r1-v1:0",
]

# The 6 agents
AGENTS = [
    "planning_agent",
    "evidence_agent",
    "organizational_controls_agent",
    "people_controls_agent",
    "technological_controls_agent",
    "consolidation_agent",
]


def _metric_widget(title: str, metrics_list: list, width: int = 12, height: int = 6, stat: str = "Average") -> dict:
    """Helper to build a CloudWatch metric widget."""
    return {
        "type": "metric",
        "width": width,
        "height": height,
        "properties": {
            "title": title,
            "region": REGION,
            "metrics": metrics_list,
            "stat": stat,
            "period": 300,
            "view": "timeSeries",
        },
    }


def generate_model_performance_dashboard() -> dict:
    """
    Level 1: Model Performance Dashboard.

    Shows per-model:
    - Latency (p50, p90, p99)
    - Token throughput (OTPS)
    - Input/Output token distribution
    - Cost per invocation
    - Success rate and throttle count
    """
    widgets = []

    # Row 1: Latency comparison across models
    latency_metrics = [
        [NAMESPACE, "ModelLatency", "ModelId", model_id]
        for model_id in MODELS
    ]
    widgets.append(_metric_widget(
        "Model Latency Comparison (avg ms)",
        latency_metrics,
        width=24,
    ))

    # Row 2: TTFT comparison
    ttft_metrics = [
        [NAMESPACE, "ModelTTFT", "ModelId", model_id]
        for model_id in MODELS
    ]
    widgets.append(_metric_widget(
        "Time to First Token (avg ms)",
        ttft_metrics,
        width=12,
    ))

    # OTPS comparison
    otps_metrics = [
        [NAMESPACE, "ModelOTPS", "ModelId", model_id]
        for model_id in MODELS
    ]
    widgets.append(_metric_widget(
        "Output Tokens Per Second",
        otps_metrics,
        width=12,
    ))

    # Row 3: Token utilization
    input_token_metrics = [
        [NAMESPACE, "ModelInputTokens", "ModelId", model_id]
        for model_id in MODELS
    ]
    widgets.append(_metric_widget(
        "Input Tokens Per Invocation",
        input_token_metrics,
        width=12,
        stat="Sum",
    ))

    output_token_metrics = [
        [NAMESPACE, "ModelOutputTokens", "ModelId", model_id]
        for model_id in MODELS
    ]
    widgets.append(_metric_widget(
        "Output Tokens Per Invocation",
        output_token_metrics,
        width=12,
        stat="Sum",
    ))

    # Row 4: Cost and success
    cost_metrics = [
        [NAMESPACE, "ModelCostUSD", "ModelId", model_id]
        for model_id in MODELS
    ]
    widgets.append(_metric_widget(
        "Cost Per Invocation (USD)",
        cost_metrics,
        width=12,
        stat="Sum",
    ))

    success_metrics = [
        [NAMESPACE, "ModelSuccess", "ModelId", model_id]
        for model_id in MODELS
    ]
    widgets.append(_metric_widget(
        "Model Success Rate",
        success_metrics,
        width=12,
        stat="Average",
    ))

    return {
        "widgets": widgets,
    }


def generate_agent_performance_dashboard() -> dict:
    """
    Level 2: Agent Performance Dashboard.

    Shows per-agent:
    - Total execution time breakdown (LLM vs Tool vs Overhead)
    - Token consumption
    - Tool call count and error rate
    - RAG query count
    - Cost accumulation
    - Success rate
    """
    widgets = []

    # Row 1: Execution time breakdown per agent
    exec_metrics = [
        [NAMESPACE, "AgentExecutionTime", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Agent Execution Time (avg ms)",
        exec_metrics,
        width=24,
    ))

    # Row 2: LLM time vs Tool time
    llm_metrics = [
        [NAMESPACE, "AgentLLMTime", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Agent LLM Time (avg ms)",
        llm_metrics,
        width=12,
    ))

    tool_metrics = [
        [NAMESPACE, "AgentToolTime", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Agent Tool Execution Time (avg ms)",
        tool_metrics,
        width=12,
    ))

    # Row 3: Token usage and cost
    token_metrics = [
        [NAMESPACE, "AgentInputTokens", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Agent Input Tokens",
        token_metrics,
        width=12,
        stat="Sum",
    ))

    cost_metrics = [
        [NAMESPACE, "AgentCostUSD", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Agent Cost (USD)",
        cost_metrics,
        width=12,
        stat="Sum",
    ))

    # Row 4: Tool calls and errors
    tool_call_metrics = [
        [NAMESPACE, "AgentToolCalls", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Tool Calls Per Agent",
        tool_call_metrics,
        width=12,
        stat="Sum",
    ))

    tool_error_metrics = [
        [NAMESPACE, "AgentToolErrors", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Tool Errors Per Agent",
        tool_error_metrics,
        width=12,
        stat="Sum",
    ))

    # Row 5: Success rate and LLM ratio
    success_metrics = [
        [NAMESPACE, "AgentSuccess", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Agent Success Rate",
        success_metrics,
        width=12,
        stat="Average",
    ))

    ratio_metrics = [
        [NAMESPACE, "AgentLLMTimeRatio", "AgentName", agent]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "LLM Time Ratio (LLM / Total)",
        ratio_metrics,
        width=12,
        stat="Average",
    ))

    return {
        "widgets": widgets,
    }


def generate_orchestration_flow_dashboard() -> dict:
    """
    Level 3: Orchestration Flow Dashboard.

    Shows:
    - End-to-end flow time trend
    - Critical path vs total time (parallelism efficiency)
    - Per-node duration breakdown
    - Bottleneck frequency
    - Total cost per audit
    - Success/failure rate
    """
    widgets = []

    # Row 1: Flow-level timing
    widgets.append(_metric_widget(
        "Orchestration Flow Total Time (ms)",
        [[NAMESPACE, "FlowTotalTime", "FlowType", "audit_orchestration"]],
        width=12,
    ))
    widgets.append(_metric_widget(
        "Critical Path Time (ms)",
        [[NAMESPACE, "FlowCriticalPathTime", "FlowType", "audit_orchestration"]],
        width=12,
    ))

    # Row 2: Cost and tokens
    widgets.append(_metric_widget(
        "Total Cost Per Audit (USD)",
        [[NAMESPACE, "FlowTotalCost", "FlowType", "audit_orchestration"]],
        width=12,
        stat="Sum",
    ))
    widgets.append(_metric_widget(
        "Total Tokens Per Audit",
        [[NAMESPACE, "FlowTotalTokens", "FlowType", "audit_orchestration"]],
        width=12,
        stat="Sum",
    ))

    # Row 3: Per-node duration comparison
    node_metrics = [
        [NAMESPACE, "NodeDuration", "AgentName", agent, "FlowNode", agent.replace("_agent", "")]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Per-Node Duration (ms)",
        node_metrics,
        width=24,
    ))

    # Row 4: Node wait times (queuing/dependency delay)
    wait_metrics = [
        [NAMESPACE, "NodeWaitTime", "AgentName", agent, "FlowNode", agent.replace("_agent", "")]
        for agent in AGENTS
    ]
    widgets.append(_metric_widget(
        "Per-Node Wait Time (ms)",
        wait_metrics,
        width=12,
    ))

    # Parallelism ratio
    widgets.append(_metric_widget(
        "Parallelism Ratio (lower = more parallel)",
        [[NAMESPACE, "FlowParallelismRatio", "FlowType", "audit_orchestration"]],
        width=12,
    ))

    # Row 5: Success and failures
    widgets.append(_metric_widget(
        "Flow Success Rate",
        [[NAMESPACE, "FlowSuccess", "FlowType", "audit_orchestration"]],
        width=12,
        stat="Average",
    ))
    widgets.append(_metric_widget(
        "Failed Nodes Per Flow",
        [[NAMESPACE, "FlowFailedNodes", "FlowType", "audit_orchestration"]],
        width=12,
        stat="Sum",
    ))

    return {
        "widgets": widgets,
    }


def export_dashboard_json(dashboard_name: str) -> str:
    """
    Export a dashboard definition as JSON string ready for AWS CLI or CDK.

    Args:
        dashboard_name: One of 'model', 'agent', 'orchestration'.

    Returns:
        JSON string for aws cloudwatch put-dashboard --dashboard-body.
    """
    generators = {
        "model": generate_model_performance_dashboard,
        "agent": generate_agent_performance_dashboard,
        "orchestration": generate_orchestration_flow_dashboard,
    }

    if dashboard_name not in generators:
        raise ValueError(f"Unknown dashboard: {dashboard_name}. Use: {list(generators.keys())}")

    body = generators[dashboard_name]()
    return json.dumps(body, indent=2)
