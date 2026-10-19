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
│   Model: us.amazon.nova-pro-v1:0 │ Temp: 0.0 │ Memory: STM + LTM       │
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
| 1 | Planificación | `planning_agent/` | Nova Pro | Generate audit plan: scope, schedule, criteria, team |
| 2 | Recopilación de Evidencia | `evidence_agent/` | Nova Pro | Retrieve and organize documentary evidence via RAG |
| 3 | Controles Organizacionales | `organizational_controls_agent/` | Nova Pro | Evaluate 37 controls (A.5.x) |
| 4 | Controles de Personas | `people_controls_agent/` | Nova Pro | Evaluate 8 controls (A.6.x) |
| 5 | Controles Tecnológicos | `technological_controls_agent/` | Nova Pro | Evaluate 34 controls (A.8.x) |
| 6 | Consolidación | `consolidation_agent/` | Nova Pro | Orchestrate, verify, consolidate final audit report |

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
# Install toolkit
pip install bedrock-agentcore-starter-toolkit

# Navigate to an agent
cd backend/agentcore/consolidation_agent

# Start local dev server
agentcore dev

# Test locally
agentcore invoke --dev '{"prompt": "Generate an audit plan for organization X", "session_id": "audit_001", "actor_id": "auditor_1"}'

# Deploy to cloud
agentcore configure --entrypoint src/main.py --non-interactive
agentcore launch
```

## Environment Variables

Each agent requires these environment variables (set via `.env` or `agentcore dev --env`):

| Variable | Description |
|----------|-------------|
| `KNOWLEDGE_BASE_ID` | Bedrock Knowledge Base ID for RAG queries |
| `AWS_REGION` | AWS region (default: us-east-1) |
| `AGENTCORE_MEMORY_ID` | Memory resource ID (created once via CLI) |
| `GATEWAY_MCP_URL` | AgentCore Gateway MCP endpoint |
| `GATEWAY_CLIENT_ID` | Cognito client ID for Gateway OAuth2 |
| `GATEWAY_CLIENT_SECRET` | Cognito client secret |
| `GATEWAY_TOKEN_ENDPOINT` | Cognito token endpoint |
| `GATEWAY_SCOPE` | Gateway scope (e.g., `AuditGateway/invoke`) |
| `DOCUMENTS_TABLE` | DynamoDB Documents table name |
| `AUDITS_TABLE` | DynamoDB Audits table name |
| `BUCKET_NAME` | S3 bucket for document storage |

## ISO 27001:2022 Control Coverage

- **A.5 Organizational Controls** (37 controls) → `organizational_controls_agent`
- **A.6 People Controls** (8 controls) → `people_controls_agent`
- **A.7 Physical Controls** (14 controls) → addressed within organizational assessment
- **A.8 Technological Controls** (34 controls) → `technological_controls_agent`

Total: 93 Annex A controls evaluated across specialized agents.
