# CLAUDE.md

## Project Overview

Multi-agent ISO 27001 audit system using RAG (Retrieval-Augmented Generation). Built as a graduate capstone project (ITESM MNA, Team #16). The system ingests a curated knowledge base of ISO standards, real audit reports, and organizational policies to generate ISMS audit findings and reports.

**Development language:** Python 3.14+ with Jupyter notebooks. Documentation and deliverables are in Spanish.

## Important instructions
- Do not read, display, or reference any .env file or its contents
**Development language:** Python 3.12+ with Jupyter notebooks. Documentation and deliverables are in Spanish.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r deliverables/requirements.txt
jupyter notebook              # Launch notebook server
```

## Running Notebooks

Deliverables are Jupyter notebooks in `deliverables/`. Run from the project root so relative paths resolve correctly.

## Architecture

The system follows a multi-agent RAG pipeline implemented with **Amazon Bedrock Knowledge Bases** and **Amazon S3 Vectors**.

### Data Pipeline (CRISP-ML(Q) — Data Engineering Phase)

1. **Document ingestion** — 35+ documents in 7 categories parsed from PDF, DOCX, XLSX, YAML, MD formats.
2. **Chunking** — Semantic chunking (maxTokens=512, bufferSize=1, breakpointPercentileThreshold=95, overlap=20%) via Bedrock Knowledge Bases. Hierarchical chunking for structured documents (SOA, Risk Register).
3. **Embedding** — Amazon Titan Text Embeddings V2 (1024d, normalized L2). Production target: 512d (99% precision retained, 50% storage savings).
4. **Vector storage** — Amazon S3 Vectors (Avance 3) / OpenSearch Serverless (Avance 2 design).
5. **Metadata filtering** — Validated via Chi-squared and ANOVA: `document_type`, `source_category`, `compliance_domain`, `iso_control_reference`, `temporal_relevance`.

### Multi-Agent System

Specialized agents coordinated by a consolidator follow the "Agents as Tools" pattern (Strands Agents SDK). Phase 1 uses Bedrock API models; Phase 2 adds QLoRA fine-tuning on SageMaker.

| # | Agent | Model (API) | Model (Fine-tuned) | Role |
|---|-------|-------------|--------------------|----- |
| 1 | Planificación | Nova Pro | Ministral 3 8B | Generate audit plan: scope, schedule, criteria, team |
| 2 | Recopilación de Evidencia | Nova Pro | Ministral 3 8B | Retrieve and organize relevant documentary evidence |
| 3 | Controles Organizacionales (A.5) | Nova Pro | Ministral 3 8B | Evaluate 37 organizational controls |
| 4 | Controles de Personas (A.6) | Nova Pro | Ministral 3 8B | Evaluate 8 people controls |
| 5 | Controles Físicos (A.7) | Nova Pro | Ministral 3 8B | Evaluate 14 physical and environmental controls |
| 6 | Controles Tecnológicos (A.8) | Nova Pro | Ministral 3 8B | Evaluate 34 technological controls |
| 7 | Consolidación (Orchestrator) | GPT-OSS-120B (OpenAI vía Bedrock) | DeepSeek-R1-0528-Qwen3-8B | Verify consistency, consolidate, generate final report |

### AWS Services

- **Amazon Bedrock** — Foundation models: Nova Pro (parsing/generation), Titan Text Embeddings V2 (embeddings)
- **Bedrock Knowledge Bases** — Managed RAG with semantic chunking and metadata filtering
- **S3 Vectors** — Vector store (cosine distance, 1024d float32)
- **S3** — Document storage (`raw/`, `processed/`, `eda_results/`, `validation/`, `fine-tuning/`)
- **SageMaker** — QLoRA fine-tuning jobs (ml.g5.2xlarge instances)
- **Step Functions** — Pipeline orchestration (EDA → Chunking/KB Ingestion → RAG Validation)
- **Lambda** — Serverless compute (Python 3.12 runtime)
- **API Gateway** — REST API for presigned URL generation and pipeline status

## Knowledge Base Structure

| Directory | Files | Format | Purpose |
|---|---|---|---|
| `knowledge-base/iso27001/` | 1 | PDF | ISO/IEC 27001:2013 full text — RAG citation source |
| `knowledge-base/audit-examples/` | 8 | PDF, DOCX | Real audit reports — training data for finding structure/language |
| `knowledge-base/audit-methodology/` | 4 | PDF | ISO 19011, maturity models — audit planning frameworks |
| `knowledge-base/ciso-assistant-community/` | 5 | YAML | ISO 27001:2022, ISO 22301, ISO 42001 — machine-readable controls |
| `knowledge-base/non-conformities/` | 1 | MD | Common NC patterns — agent domain knowledge |
| `knowledge-base/sponsor-documents/` | 8 | PDF, DOCX | Organizational policies — real evidence for gap analysis |

Additionally, an **ISO 27001:2022 Toolkit** (`ISO-27001-2022-Toolkit/`) provides templates: Gap Assessment Plan, SOA, Risk Register, Scope and Context, Asset Inventory, BCP/DRP, Security Policy, Training Plan, Management Review, ISMS Checklists, Internal Audit, ROI.

The YAML standards files use `ref_id` fields (e.g., `A.5.1`) for control lookups and support multilingual translations (EN, ES, FR, DE, etc.).

## Notebook Conventions

When a Python library is needed in a notebook, first check cell 0 (the imports cell). If the library is not already imported, add it there rather than importing it inline in the working cell.

## Style Preferences

When writing lists, use a colon (not a dash) to separate a term from its description:
```
1. Concept: explanation
```
Not:
```
1. Concept — explanation
```

When writing lists (numbered or bulleted), do not add blank lines between items:
```
1. ABC
2. DEF
```
Not:
```
1. ABC

2. DEF
```

### ISO 27001:2022 Control Domains (Annex A)

- **A.5** — Organizational Controls (37 controls): policies, roles, responsibilities
- **A.6** — People Controls (8 controls): competence, awareness, training
- **A.7** — Physical Controls (14 controls): physical/environmental security
- **A.8** — Technological Controls (34 controls): systems and data security

## Feature Engineering (Avance 2)

Key metadata characteristics validated statistically for RAG retrieval:

| Metadata | Validation | Impact |
|----------|-----------|--------|
| `document_type` | χ²=45.23, p<0.001 | +15% Precision@5 |
| `source_category` | χ²=38.67, p<0.001 | Discriminative filter |
| `compliance_domain` | χ²=52.89, p<0.001 | Priority filter |
| `keyword_density` | F=23.67, p<0.001 | Predictive feature |
| `chunk_length` | F=8.45, p=0.003 | Retained for analysis |

Chunking comparison (selected: **Semantic**):
- Fixed 300: Recall@5=0.72, MRR=0.58
- Fixed 512: Recall@5=0.78, MRR=0.64
- **Semantic: Recall@5=0.85, MRR=0.71**
- Hierarchical: Recall@5=0.82, MRR=0.69

RAG baseline metrics: Recall@5=0.85, Precision@5=0.89, MRR=0.71, Latency=68ms.

## Common Commands

```bash
# Python environment setup
python -m venv .venv
.venv\Scripts\activate
pip install -r deliverables/requirements.txt

# Run notebooks
jupyter notebook

# CDK deployment (from actividad1.16/cdk/)
npm install
npx cdk bootstrap
npx cdk deploy
```

## Conventions

- Lambda handlers use `lambda_handler(event, context)` entry point
- Environment variables configure all Lambda behavior (bucket names, model IDs, prefixes)
- Logging uses `print(f"[INFO|WARN|ERROR] ...")` pattern
- Each Lambda has its own `requirements.txt` for isolated dependencies
- CDK uses a single shared IAM role for pipeline Lambdas
- Deliverables follow naming convention `Avance{N}.16.{ext}` (N = milestone, 16 = team number)
- Methodology: CRISP-ML(Q) (Studer et al., 2021)
