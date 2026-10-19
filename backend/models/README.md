# Model Performance & Evaluation Module

## Overview

This module enables AgentCore to dynamically select among available Bedrock foundation models and comprehensively measure performance at three levels:

1. **Level 1 — Model (LLM) Performance**: Latency, token utilization, throughput, cost per invocation
2. **Level 2 — Per-Agent Performance**: Execution time, tool usage, RAG quality, success rate
3. **Level 3 — Orchestration Flow Performance**: End-to-end timing, bottleneck detection, visual DAG with per-node metrics

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Orchestration Tracker                        │
│    (Level 3: Flow metrics, DAG visualization, bottlenecks)   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Instrumented Agent / Metrics Collector           │
│    (Level 2: Per-agent execution, tools, RAG quality)        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│           Model Selector + Registry + Evaluation             │
│    (Level 1: Model selection, latency, tokens, cost)         │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Persistence: DynamoDB (historical) + CloudWatch (real-time)  │
└─────────────────────────────────────────────────────────────┘
```

## Available Bedrock Models

The registry includes models optimized for different agent roles:

| Model | Provider | Cost Tier | Latency | Best For |
|-------|----------|-----------|---------|----------|
| GPT OSS 120B | OpenAI | Medium | Balanced | Production reasoning (open-weight, 128K ctx) |
| Qwen3 32B Dense | Qwen | Low | Fast | Low-latency, consistent, hybrid thinking |
| Claude Haiku 4.5 | Anthropic | Low | Fast | Evidence retrieval, classification |
| Claude Sonnet 4.6 | Anthropic | Medium | Balanced | Structured analysis, tool use |
| Llama 4 Maverick | Meta | Low | Fast | Budget sub-agents, MoE efficient |
| Mistral Large | Mistral | Medium | Balanced | Strong tool use, audit evaluations |
| DeepSeek R1 | DeepSeek | Medium | Slow | Chain-of-thought, complex consolidation |

## Selection Strategies

```python
from backend.models.selector import ModelSelector, SelectionStrategy, SelectionCriteria
from backend.models.registry import ModelCapability, CostTier

# Fixed: always use a specific model
selector = ModelSelector(strategy=SelectionStrategy.FIXED, fixed_model_key="gpt-oss-120b")

# Cost-optimized: cheapest model meeting requirements
selector = ModelSelector(strategy=SelectionStrategy.COST_OPTIMIZED)
model = selector.select(SelectionCriteria(
    required_capabilities=[ModelCapability.REASONING, ModelCapability.AGENTIC],
    max_cost_tier=CostTier.MEDIUM,
    requires_tool_use=True,
))

# Latency-optimized: fastest response time
selector = ModelSelector(strategy=SelectionStrategy.LATENCY_OPTIMIZED)

# Quality-optimized: best model within budget
selector = ModelSelector(strategy=SelectionStrategy.QUALITY_OPTIMIZED)

# Adaptive: uses historical performance data
selector = ModelSelector(strategy=SelectionStrategy.ADAPTIVE)
```

## Metrics Collection

### Level 1: Model Metrics

Captured per LLM invocation:
- `total_latency_ms` — End-to-end time from request to last token
- `time_to_first_token_ms` — Time until first streaming token received
- `output_tokens_per_second` — Throughput (derived)
- `input_tokens` / `output_tokens` / `total_tokens`
- `cache_read_tokens` / `cache_write_tokens` — Prompt caching efficiency
- `estimated_cost_usd` — Cost based on published pricing
- `was_throttled` — Whether the request was rate-limited

### Level 2: Agent Metrics

Captured per agent invocation:
- `total_execution_time_ms` — Total wall-clock time
- `llm_time_ms` — Time spent in LLM calls
- `tool_execution_time_ms` — Time spent in tool calls
- `overhead_time_ms` — Orchestration overhead (total - llm - tools)
- `tools_called` — List of tools invoked
- `tool_call_count` / `tool_success_count` / `tool_error_count`
- `rag_queries_made` / `rag_sources_retrieved` / `avg_rag_relevance_score`
- `turns_count` — Number of LLM reasoning turns
- `total_estimated_cost_usd` — Aggregated cost

### Level 3: Orchestration Flow Metrics

Captured for the full audit flow:
- `total_flow_time_ms` — End-to-end orchestration time
- `critical_path_time_ms` — Longest sequential dependency chain
- Per-node: `duration_ms`, `wait_time_ms`, `start_time_ms`, `end_time_ms`
- `bottleneck_node` — Node with highest duration
- `bottleneck_reason` — `"llm_latency"` or `"tool_execution"`
- Aggregated: total tokens, total cost, agents invoked, tool calls

## CloudWatch Metrics Published

Under namespace `AgentCore/ISO27001Audit`:

| Metric | Dimensions | Unit |
|--------|-----------|------|
| AgentExecutionTime | AgentName | Milliseconds |
| AgentLLMTime | AgentName | Milliseconds |
| AgentToolTime | AgentName | Milliseconds |
| AgentInputTokens | AgentName | Count |
| AgentOutputTokens | AgentName | Count |
| AgentToolCalls | AgentName | Count |
| AgentCostUSD | AgentName | None |
| AgentSuccess | AgentName | Count |
| OrchestrationFlowTime | FlowType | Milliseconds |
| OrchestrationTotalTokens | FlowType | Count |
| OrchestrationTotalCost | FlowType | None |
| OrchestrationAgentsInvoked | FlowType | Count |
| OrchestrationSuccess | FlowType | Count |

## Model Evaluation (Bedrock Evaluations)

### Built-in ISO 27001 Benchmark

```python
from backend.models.evaluation import ModelEvaluator, create_iso27001_evaluation_dataset

evaluator = ModelEvaluator()
dataset = create_iso27001_evaluation_dataset()

# Option A: Quick local benchmark (direct invocations)
results = evaluator.run_local_benchmark(
    model_ids=["openai.gpt-oss-120b-1:0", "qwen.qwen3-32b-v1:0"],
    dataset=dataset,
)

# Option B: Formal Bedrock Evaluation Job (LLM-as-judge)
s3_uri = evaluator.upload_dataset(dataset, bucket="my-eval-bucket")
job = evaluator.create_evaluation_job(
    job_name="iso27001_model_comparison_v1",
    model_ids=["openai.gpt-oss-120b-1:0", "qwen.qwen3-32b-v1:0", "mistral.mistral-large-2407-v1:0"],
    dataset_s3_uri=s3_uri,
    evaluation_type="LLM_AS_JUDGE",
    judge_model_id="anthropic.claude-sonnet-4-6-20250514-v1:0",
)
```

### Evaluation Metrics

- **Accuracy**: How correctly the model evaluates ISO 27001 controls
- **Completeness**: Whether all required assessment elements are covered
- **FollowingInstructions**: Adherence to structured output format
- **ProfessionalStyleAndTone**: Appropriate audit language

## Orchestration Flow Visualization

### Mermaid Diagram

```python
from backend.models.orchestration_tracker import OrchestrationTracker

tracker = OrchestrationTracker(audit_id="audit_001")
# ... track nodes ...
print(tracker.get_mermaid_diagram())
```

Produces a diagram with per-node metrics (time, tokens, cost, tool calls) and highlights the bottleneck node.

### JSON Graph (for frontend)

```python
graph = tracker.get_flow_graph()
# Returns: { nodes: [...], edges: [...], summary: {...}, bottlenecks: [...] }
```

Each node includes:
- Agent identification
- LLM metrics (model, latency, TTFT, OTPS)
- Agent metrics (execution time, tools, cost)
- Flow metrics (wait time, is_bottleneck flag)
- Optimization recommendations

### Bottleneck Report

```python
report = tracker.get_bottleneck_report()
# Markdown report with per-node table, analysis, and recommendations
```

## Usage in AgentCore Agents

```python
# In any agent's src/main.py:
from backend.models.instrumented_agent import create_instrumented_agent, save_metrics
from backend.models.selector import SelectionStrategy

agent, collector = create_instrumented_agent(
    agent_name="organizational_controls_agent",
    model_key="gpt-oss-120b",
    strategy=SelectionStrategy.COST_OPTIMIZED,
    system_prompt=SYSTEM_PROMPT,
    tools=[...],
    session_id="audit_001",
)

response = agent("Evaluate A.5.1 control...")
metrics = save_metrics(collector, persist=True)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region | `us-east-1` |
| `METRICS_TABLE` | DynamoDB table for metrics storage | `AgentCoreMetrics` |
| `EVALUATION_BUCKET` | S3 bucket for evaluation datasets/results | — |
| `EVALUATION_ROLE_ARN` | IAM role ARN for Bedrock Evaluation jobs | — |
| `MODEL_ID` | Default model ID | `openai.gpt-oss-120b-1:0` |
