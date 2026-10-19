# Observability Module

## Overview

Complete observability stack for the AgentCore multi-agent ISO 27001 audit system. Covers three metric levels with structured logging, CloudWatch metrics, dashboards, alerting, and distributed tracing.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Agent Code (per agent)                         │
│                                                                    │
│   ObservabilityCollector   ─── track_model() / track_tool()       │
│           │                                                        │
│           ├── StructuredLogger  → stdout (JSON)  → CW Logs        │
│           └── CloudWatchPublisher → CW Metrics → Dashboards       │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│                  FlowTracker (orchestration level)                 │
│                                                                    │
│   node("planning") → node("evidence") → node("org_controls")...  │
│           │                                                        │
│           ├── Per-node CW Metrics                                  │
│           ├── Flow-level CW Metrics                                │
│           └── Mermaid diagram output                               │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│                   CloudWatch                                       │
│                                                                    │
│   Namespace: AgentCore/ISO27001Audit                               │
│   ├── Dashboards (model, agent, orchestration)                    │
│   ├── Alarms (latency, errors, cost, throttles)                   │
│   └── Logs Insights (pre-built queries)                           │
└──────────────────────────────────────────────────────────────────┘
```

## Components

| File | Purpose |
|------|---------|
| `logging.py` | Structured JSON logging + TraceContext for distributed tracing |
| `cloudwatch.py` | CloudWatch custom metrics publisher (3 levels) |
| `collector.py` | Unified collector combining logging + metrics for agents |
| `flow_tracker.py` | Orchestration flow tracking with DAG, bottleneck detection |
| `dashboards.py` | IaC-ready CloudWatch dashboard definitions |
| `alerts.py` | CloudWatch alarm definitions for anomaly detection |
| `queries.py` | Pre-built CloudWatch Logs Insights queries |

## Usage

### Per-Agent Instrumentation

```python
from backend.observability.collector import ObservabilityCollector

obs = ObservabilityCollector(
    agent_name="organizational_controls_agent",
    audit_id="audit_001",
    session_id="session_xyz",
    actor_id="auditor_1",
)

# Track model invocations
with obs.track_model("openai.gpt-oss-120b-1:0") as model:
    response = agent(prompt)
    model.set_tokens(input_tokens=200, output_tokens=800)
    model.set_ttft(ttft_ms=450.0)

# Track tool calls
with obs.track_tool("retrieve_control_evidence") as tool:
    result = retrieve_control_evidence(control_id="A.5.1")
    tool.set_rag_result(sources=5, relevance=0.85)

# Finalize
summary = obs.finalize()
# → Logs JSON summary, publishes all CW metrics
```

### Orchestration Flow

```python
from backend.observability.flow_tracker import FlowTracker

tracker = FlowTracker(audit_id="audit_001", session_id="session_xyz")

with tracker.node("planning", agent_name="planning_agent", model_id="openai.gpt-oss-120b-1:0") as node:
    result = invoke_planning_agent(...)
    node.set_result(input_tokens=300, output_tokens=1200, tool_calls=3, cost=0.002, llm_time_ms=5000)

with tracker.node("evidence", agent_name="evidence_agent", model_id="qwen.qwen3-32b-v1:0") as node:
    result = invoke_evidence_agent(...)
    node.set_result(input_tokens=500, output_tokens=2000, tool_calls=8, cost=0.001, llm_time_ms=3000)

# Parallel nodes
with tracker.node("org_controls", agent_name="organizational_controls_agent", model_id="openai.gpt-oss-120b-1:0") as node:
    ...

summary = tracker.finalize()
diagram = tracker.mermaid_diagram()
```

### Distributed Tracing

```python
from backend.observability.logging import TraceContext

# Create root trace
ctx = TraceContext(audit_id="audit_001", session_id="s1", actor_id="auditor_1")

# Pass to sub-agent via HTTP headers
headers = ctx.child_span().to_headers()
# → {"X-Trace-Id": "abc123...", "X-Span-Id": "def456...", ...}

# Sub-agent receives and continues the trace
child_ctx = TraceContext.from_headers(request.headers)
obs = ObservabilityCollector(agent_name="sub_agent", trace_ctx=child_ctx)
```

## CloudWatch Metrics Published

### Level 1: Model Metrics (Dimension: ModelId)

| Metric | Unit | Description |
|--------|------|-------------|
| ModelLatency | Milliseconds | End-to-end model invocation time |
| ModelTTFT | Milliseconds | Time to first token |
| ModelOTPS | Count/Second | Output tokens per second |
| ModelInputTokens | Count | Tokens in prompt |
| ModelOutputTokens | Count | Tokens in response |
| ModelCostUSD | None | Estimated cost per invocation |
| ModelInvocations | Count | Total invocation count |
| ModelSuccess | Count | 1 if success, 0 if failure |
| ModelThrottles | Count | Rate-limit occurrences |

### Level 2: Agent Metrics (Dimension: AgentName)

| Metric | Unit | Description |
|--------|------|-------------|
| AgentExecutionTime | Milliseconds | Total wall-clock time |
| AgentLLMTime | Milliseconds | Time in LLM calls |
| AgentToolTime | Milliseconds | Time in tool calls |
| AgentOverheadTime | Milliseconds | Framework overhead |
| AgentInputTokens | Count | Total input tokens |
| AgentOutputTokens | Count | Total output tokens |
| AgentToolCalls | Count | Number of tool invocations |
| AgentToolErrors | Count | Failed tool calls |
| AgentTurns | Count | LLM reasoning turns |
| AgentRAGQueries | Count | Knowledge base queries |
| AgentCostUSD | None | Total estimated cost |
| AgentSuccess | Count | 1/0 success indicator |
| AgentLLMTimeRatio | None | LLM time / total time |

### Level 3: Orchestration Metrics (Dimension: FlowType)

| Metric | Unit | Description |
|--------|------|-------------|
| FlowTotalTime | Milliseconds | End-to-end audit flow time |
| FlowCriticalPathTime | Milliseconds | Longest sequential chain |
| FlowAgentsInvoked | Count | Agents that completed |
| FlowTotalTokens | Count | All tokens consumed |
| FlowTotalCost | None | Total flow cost (USD) |
| FlowTotalToolCalls | Count | All tool calls across agents |
| FlowSuccess | Count | 1/0 flow success |
| FlowFailedNodes | Count | Number of failed nodes |
| FlowParallelismRatio | None | Critical path / total time |

### Per-Node Metrics (Dimensions: AgentName + FlowNode)

| Metric | Unit | Description |
|--------|------|-------------|
| NodeDuration | Milliseconds | Node execution time |
| NodeWaitTime | Milliseconds | Time waiting for dependencies |
| NodeLLMTime | Milliseconds | LLM time within node |
| NodeToolTime | Milliseconds | Tool time within node |
| NodeTokens | Count | Tokens consumed by node |
| NodeCost | None | Node cost (USD) |

## Alarms

| Alarm | Condition | Action |
|-------|-----------|--------|
| Model Latency | avg > 30s for 2 periods | SNS notification |
| Agent Execution Time | avg > 120s for 2 periods | SNS notification |
| Agent Error Rate | success rate < 80% | SNS notification |
| Model Error Rate | success rate < 90% | SNS notification |
| Flow Cost Anomaly | max > $5 per audit | SNS notification |
| Model Throttling | > 5 throttles in 5 min | SNS notification |
| Flow Total Time | avg > 10 min | SNS notification |
| Flow Failure | any success=0 | SNS notification |

## Deploy Dashboards

```bash
# Export and deploy via AWS CLI
python -c "
from backend.observability.dashboards import export_dashboard_json
import json

for name in ['model', 'agent', 'orchestration']:
    body = export_dashboard_json(name)
    print(f'Deploying {name} dashboard...')
    # aws cloudwatch put-dashboard --dashboard-name ISO27001-{name} --dashboard-body '{body}'
"
```

## Deploy Alarms

```python
from backend.observability.alerts import AlertManager

manager = AlertManager(sns_topic_arn="arn:aws:sns:us-east-1:123456789:audit-alerts")
manager.create_all_alarms()
```

## Log Queries (CloudWatch Logs Insights)

```python
from backend.observability.queries import get_query

# Get pre-built queries
print(get_query("model_latency"))      # Latency percentiles by model
print(get_query("agent_breakdown"))    # Execution time breakdown per agent
print(get_query("flow_bottlenecks"))   # Most common bottleneck nodes
print(get_query("recent_errors"))      # Last 50 errors across all agents
```
