# AgentCore — Multi-Agent ISO 27001 Audit System

## Overview

This directory contains the Bedrock AgentCore implementation for the multi-agent ISO 27001:2022 audit system. Each agent is deployed independently via AgentCore runtime and coordinated by the **Consolidation Orchestrator** using the "Agents as Tools" pattern (Strands SDK).

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        AgentCore Gateway (MCP)                            │
│         OAuth2 + Cognito │ Centralized Tool Routing                      │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────────────────────┐
│                    consolidation_agent (Orchestrator)                     │
│   Model: Claude Sonnet 4.5       │ Temp: 0.0 │ Memory: STM + LTM       │
│   Coordinates all sub-agents, verifies consistency, generates report     │
└───┬──────────┬──────────┬──────────┬──────────┬─────────────────────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│planning││evidence││org_ctrl││people  ││tech    │
│_agent  ││_agent  ││_agent  ││_ctrl   ││_ctrl   │
│        ││        ││(A.5)   ││_agent  ││_agent  │
│        ││        ││        ││(A.6)   ││(A.8)   │
└────────┘└────────┘└────────┘└────────┘└────────┘
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│              Bedrock Knowledge Bases (RAG)                                │
│  OpenSearch Serverless │ Titan Embeddings V2 │ Semantic Chunking          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Agent Inventory

| # | Agent | Directory | Model | Role |
|---|-------|-----------|-------|------|
| 1 | Planificación | `planning_agent/` | Claude Sonnet 4.5 | Generate audit plan: scope, schedule, criteria, team |
| 2 | Recopilación de Evidencia | `evidence_agent/` | Claude Sonnet 4.5 | Retrieve and organize documentary evidence via RAG |
| 3 | Controles Organizacionales | `organizational_controls_agent/` | Claude Sonnet 4.5 | Evaluate 37 controls (A.5.x) |
| 4 | Controles de Personas | `people_controls_agent/` | Claude Sonnet 4.5 | Evaluate 8 controls (A.6.x) |
| 5 | Controles Físicos | `physical_controls_agent/` | Claude Sonnet 4.5 | Evaluate 14 controls (A.7.x) |
| 6 | Controles Tecnológicos | `technological_controls_agent/` | Claude Sonnet 4.5 | Evaluate 34 controls (A.8.x) |
| 7 | Consolidación | `consolidation_agent/` | Claude Sonnet 4.5 | Orchestrate, verify, consolidate final audit report |

## Shared Components

- `shared/` — Common tools, utilities, model loader, RAG client
- `shared/tools/` — Reusable @tool-decorated functions (RAG queries, DynamoDB access, S3 operations)
- `shared/prompts/` — System prompt templates per agent role
- `shared/models.py` — Pydantic models for structured outputs (findings, controls, reports)

## AgentCore Primitives Used

| Primitive | Purpose |
|-----------|---------|
| **Runtime** | Deploy each agent as an independent serverless endpoint |
| **Memory (STM)** | Conversation persistence within an audit session |
| **Memory (LTM)** | Long-term knowledge: past audit findings, organizational context |
| **Gateway** | MCP endpoint routing tool calls to Lambda targets (RAG, DynamoDB, S3) |

## Development Workflow

```bash
# Deployment: CDK stack in backend/cdk/lib/agentcore-stack.ts, driven by backend/deploy.sh
python preflight.py --knowledge-base-id <id>   # Model access and tool calling
../deploy.sh

# Build and run one agent locally
docker build --build-arg AGENT_DIR=planning_agent -t planning .
docker run -p 8080:8080 planning
curl localhost:8080/ping
```

Each agent's image installs from `requirements.lock`, with hashes for Linux ARM64. After changing a `requirements.txt`, regenerate it with `./lock_requirements.sh`.

See `IMPLEMENTATION.md` for details and current status.
