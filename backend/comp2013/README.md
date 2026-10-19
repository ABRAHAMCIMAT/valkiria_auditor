# comp2013 — ISO 27001:2013 Audit Agents for AWS Deployment

## Overview

This module adapts the evaluation-validated agent architecture from `deliverables/Avance5.dev/` into production-ready AWS components compatible with the existing backend infrastructure.

The Avance5 notebook validated three specialized agents against 11 Bedrock models using ISO 27001:2013. This directory packages those agents for deployment as Lambda functions behind the same API Gateway used by the 2022 agents.

## Agent Mapping

| Agent | ISO 27001:2013 Scope | Controls |
|-------|---------------------|----------|
| **Gobernanza** | Clauses 4–10 (ISMS Management) | 26 assessable clauses |
| **Organizacional** | Annex A: A.5–A.8, A.15, A.16, A.18 | 45 controls |
| **Técnico** | Annex A: A.9–A.14, A.17 | 69 controls |

## Architecture

```
API Gateway
    │
    POST /audit/comp2013
    │
    ▼
┌─────────────────────────────────────┐
│   comp2013 Lambda Orchestrator      │
│   (orchestrator.py → handler.py)    │
└──────┬──────────┬──────────┬────────┘
       │          │          │
       ▼          ▼          ▼
  Gobernanza  Organizacional  Técnico
  (Cls 4-10)  (A.5-A.8,A.15) (A.9-A.14,A.17)
```

## Relationship to Existing Backend

- Reuses the same **S3 bucket**, **DynamoDB tables**, **Lambda layer**, and **IAM role** from the existing `BackendStack`
- Uses the same **vector store** (S3 Vectors) with the 2013 YAML as source
- Shares the **observability infrastructure** (CloudWatch, metrics)
- Adds a new `/audit/comp2013` API endpoint

## Deployment

This module is deployed as part of the existing CDK backend stack via `comp2013-stack.ts`. No separate deployment is needed.

```bash
cd backend/cdk
npx cdk deploy
```

## Configuration

Environment variables (same pattern as existing orchestrators):

| Variable | Description |
|----------|-------------|
| `PRIMARY_MODEL_ID` | Best model from Avance5 evaluation |
| `JUDGE_MODEL_ID` | LLM judge model (claude-sonnet-4-5) |
| `KNOWLEDGE_BASE_ID` | Bedrock KB with 2013 standard docs |
| `BUCKET_NAME` | Shared S3 bucket |
| `VECTOR_STORE_BUCKET` | S3 Vectors bucket name |
| `VECTOR_STORE_INDEX` | S3 Vectors index name |
