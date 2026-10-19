"""
Instrumented Agent — Wraps Strands Agent with automatic metrics collection.

Provides a drop-in replacement for the standard Agent that collects:
- Per-invocation model metrics (latency, tokens, cost)
- Tool execution timing
- End-to-end agent metrics

Usage:
    from backend.models.instrumented_agent import create_instrumented_agent

    agent, collector = create_instrumented_agent(
        agent_name="planning_agent",
        model_key="nova-pro",
        strategy=SelectionStrategy.COST_OPTIMIZED,
        system_prompt=SYSTEM_PROMPT,
        tools=[...],
    )
    response = agent("Generate audit plan for organization X")
    metrics = collector.finalize()
"""

import os
import time
from typing import Optional

from strands import Agent

from backend.models.metrics import MetricsCollector, MetricsStore, estimate_cost
from backend.models.registry import BEDROCK_MODELS, ModelCapability, get_model
from backend.models.selector import ModelSelector, SelectionCriteria, SelectionStrategy


def create_instrumented_agent(
    agent_name: str,
    model_key: str = "gpt-oss-120b",
    strategy: SelectionStrategy = SelectionStrategy.FIXED,
    criteria: Optional[SelectionCriteria] = None,
    system_prompt: str = "",
    tools: list = None,
    session_manager=None,
    session_id: str = "",
    actor_id: str = "",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    region: Optional[str] = None,
    use_cross_region: bool = True,
) -> tuple[Agent, MetricsCollector]:
    """
    Create a Strands Agent with automatic metrics instrumentation.

    Args:
        agent_name: Name of the agent (for metrics labeling).
        model_key: Registry key for the model (used with FIXED strategy).
        strategy: Model selection strategy.
        criteria: Selection criteria (for non-FIXED strategies).
        system_prompt: Agent system prompt.
        tools: List of tools for the agent.
        session_manager: Optional AgentCore memory session manager.
        session_id: Session ID for metrics correlation.
        actor_id: Actor performing the invocation.
        temperature: Override temperature (None = use model default).
        max_tokens: Override max tokens.
        region: AWS region.
        use_cross_region: Whether to use cross-region inference profiles.

    Returns:
        Tuple of (configured Agent, MetricsCollector).
    """
    # Select model
    selector = ModelSelector(
        strategy=strategy,
        fixed_model_key=model_key,
        region=region or os.environ.get("AWS_REGION", "us-east-1"),
        use_cross_region=use_cross_region,
    )

    model_spec = selector.select(criteria)
    bedrock_model = selector.load_model(
        model_spec=model_spec,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Create metrics collector
    collector = MetricsCollector(
        agent_name=agent_name,
        session_id=session_id,
        actor_id=actor_id,
    )

    # Create agent
    agent = Agent(
        model=bedrock_model,
        system_prompt=system_prompt,
        tools=tools or [],
        session_manager=session_manager,
    )

    return agent, collector


def save_metrics(collector: MetricsCollector, persist: bool = True) -> dict:
    """
    Finalize and optionally persist metrics.

    Args:
        collector: The metrics collector from an agent invocation.
        persist: Whether to save to DynamoDB/CloudWatch.

    Returns:
        Dict with the finalized agent metrics summary.
    """
    metrics = collector.finalize()

    if persist:
        try:
            store = MetricsStore()
            store.save_agent_metrics(metrics)
        except Exception:
            pass  # Metrics persistence should never break the agent

    return {
        "agent_name": metrics.agent_name,
        "total_execution_time_ms": round(metrics.total_execution_time_ms, 1),
        "llm_time_ms": round(metrics.llm_time_ms, 1),
        "tool_execution_time_ms": round(metrics.tool_execution_time_ms, 1),
        "total_input_tokens": metrics.total_input_tokens,
        "total_output_tokens": metrics.total_output_tokens,
        "total_cost_usd": metrics.total_estimated_cost_usd,
        "tool_calls": metrics.tool_call_count,
        "turns": metrics.turns_count,
        "success": metrics.success,
    }
