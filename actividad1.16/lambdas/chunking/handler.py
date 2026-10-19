"""
Lambda: chunking  (Step 2 del pipeline)
Crea o actualiza la Bedrock Knowledge Base y su Data Source con:

  - Parsing strategy : BEDROCK_FOUNDATION_MODEL
      Modelo: amazon.nova-pro-v1:0  (vision model, ideal para PDFs con tablas/imágenes)
      Prompt personalizado para documentos de auditoría ISO 27001

  - Chunking strategy: SEMANTIC
      bufferSize=1, breakpointPercentileThreshold=95
      (agrupa oraciones semánticamente similares; ideal para controles ISO)

  - Embedding model : amazon.titan-embed-text-v2:0  (1024 dims, float32)

El flujo es:
  1. Verificar si ya existe una KB con el nombre configurado; si no, crearla.
  2. Verificar si ya existe el Data Source S3; si no, crearlo con la config de parsing/chunking.
  3. Disparar start_ingestion_job para sincronizar el bucket S3 → KB.
  4. Esperar (polling) hasta que el job termine o falle (max 12 min).

Input (desde Step Functions, output del paso EDA):
    {
        "bucket": "iso27001-compliance-rag-<account>",
        "key":    "raw/<uuid>_file.pdf",
        "file_name": "...",
        "eda_results_key": "...",
        "eda_summary": { ... }
    }

Output:
    {
        ...previous fields...,
        "knowledge_base_id": "XXXXXXXXXX",
        "data_source_id":    "YYYYYYYYYY",
        "ingestion_job_id":  "ZZZZZZZZZZ",
        "ingestion_status":  "COMPLETE",
        "chunking_stats": { ... }
    }

References:
  - https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_ChunkingConfiguration.html
  - https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_ParsingConfiguration.html
  - https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-supported.html
"""

import json
import os
import time
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION  (all overridable via Lambda environment variables)
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME       = os.environ["BUCKET_NAME"]
RAW_PREFIX        = os.environ.get("RAW_PREFIX", "raw/")
KB_NAME           = os.environ.get("KB_NAME", "iso27001-compliance-kb")
KB_DESCRIPTION    = os.environ.get("KB_DESCRIPTION",
                                   "ISO 27001:2022 compliance evaluation knowledge base")
KB_ROLE_ARN       = os.environ["KB_ROLE_ARN"]          # IAM role Bedrock assumes for KB
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", "")
OPENSEARCH_INDEX  = os.environ.get("OPENSEARCH_INDEX", "iso27001-controls-index")
REGION            = os.environ.get("AWS_REGION", "us-east-1")

# ── Embedding model ──────────────────────────────────────────────────────────
# amazon.titan-embed-text-v2:0 supports 256/512/1024 dims, float32 + binary
# Supported in us-east-1, us-west-2, eu-central-1, ap-northeast-1 and more
EMBEDDING_MODEL_ID = os.environ.get(
    "EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
)
EMBEDDING_DIMS = int(os.environ.get("EMBEDDING_DIMENSIONS", "1024"))

# ── Parsing model ─────────────────────────────────────────────────────────────
# Foundation model parsing supports: Claude vision, Nova vision, LLaMA 4 vision
# amazon.nova-pro-v1:0 is a Nova vision model — excellent for PDFs with tables/images
# Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-supported.html
PARSING_MODEL_ID = os.environ.get(
    "PARSING_MODEL_ID", "amazon.nova-pro-v1:0"
)

# ── Chunking ──────────────────────────────────────────────────────────────────
# SEMANTIC chunking uses NLP to group semantically similar sentences.
# bufferSize=1 means adjacent sentences are considered for grouping.
# breakpointPercentileThreshold=95 means only very strong semantic breaks
# create new chunks — keeps ISO controls together.
CHUNKING_STRATEGY              = os.environ.get("CHUNKING_STRATEGY", "SEMANTIC")
SEMANTIC_BUFFER_SIZE           = int(os.environ.get("SEMANTIC_BUFFER_SIZE", "1"))
SEMANTIC_BREAKPOINT_PERCENTILE = int(os.environ.get("SEMANTIC_BREAKPOINT_PERCENTILE", "95"))

# Max wait for ingestion job (seconds)
MAX_WAIT_SECONDS = int(os.environ.get("MAX_WAIT_SECONDS", "720"))
POLL_INTERVAL    = int(os.environ.get("POLL_INTERVAL_SECONDS", "15"))

# ─────────────────────────────────────────────────────────────────────────────
# AWS CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)


# ─────────────────────────────────────────────────────────────────────────────
# PARSING PROMPT
# Customizes how Nova Pro interprets audit documents during ingestion.
# ─────────────────────────────────────────────────────────────────────────────

PARSING_PROMPT = """You are an expert in information security and ISO 27001:2022 auditing.
Extract ALL content from this document page, including:
- Text paragraphs, headings, and bullet points
- Tables (preserve structure as markdown tables)
- Figures and charts (describe their content and key data points)
- Audit findings, control references (e.g. A.5.1, A.8.7), and compliance statuses
- Recommendations and remediation actions

For each ISO 27001 control reference found, explicitly note the control ID.
Preserve the hierarchical structure of the document.
Output the extracted content in clean, structured markdown."""


# ─────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _find_existing_kb(name: str) -> str | None:
    """Return the knowledgeBaseId of an existing KB with the given name, or None."""
    paginator = bedrock_agent.get_paginator("list_knowledge_bases")
    for page in paginator.paginate():
        for kb in page.get("knowledgeBaseSummaries", []):
            if kb["name"] == name and kb["status"] in ("ACTIVE", "CREATING"):
                return kb["knowledgeBaseId"]
    return None


def _create_knowledge_base() -> str:
    """Create a new Bedrock Knowledge Base backed by OpenSearch Serverless."""
    print(f"[INFO] Creating Knowledge Base '{KB_NAME}'")

    response = bedrock_agent.create_knowledge_base(
        name=KB_NAME,
        description=KB_DESCRIPTION,
        roleArn=KB_ROLE_ARN,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": (
                    f"arn:aws:bedrock:{REGION}::foundation-model/{EMBEDDING_MODEL_ID}"
                ),
                "embeddingModelConfiguration": {
                    "bedrockEmbeddingModelConfiguration": {
                        "dimensions": EMBEDDING_DIMS,
                        # FLOAT32 for maximum precision; use BINARY for cost reduction
                        "embeddingDataType": "FLOAT32",
                    }
                },
            },
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": os.environ["OPENSEARCH_COLLECTION_ARN"],
                "vectorIndexName": OPENSEARCH_INDEX,
                "fieldMapping": {
                    "vectorField":   "embedding",
                    "textField":     "text",
                    "metadataField": "metadata",
                },
            },
        },
    )

    kb_id = response["knowledgeBase"]["knowledgeBaseId"]
    print(f"[INFO] Knowledge Base created: {kb_id}")

    # Wait until ACTIVE
    for _ in range(20):
        kb = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]
        if kb["status"] == "ACTIVE":
            break
        if kb["status"] == "FAILED":
            raise RuntimeError(f"Knowledge Base creation failed: {kb.get('failureReasons')}")
        time.sleep(10)

    return kb_id


# ─────────────────────────────────────────────────────────────────────────────
# DATA SOURCE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def _find_existing_data_source(kb_id: str, ds_name: str) -> str | None:
    """Return the dataSourceId of an existing data source, or None."""
    paginator = bedrock_agent.get_paginator("list_data_sources")
    for page in paginator.paginate(knowledgeBaseId=kb_id):
        for ds in page.get("dataSourceSummaries", []):
            if ds["name"] == ds_name and ds["status"] in ("AVAILABLE", "CREATING"):
                return ds["dataSourceId"]
    return None


def _create_data_source(kb_id: str) -> str:
    """
    Create an S3 data source with:
      - BEDROCK_FOUNDATION_MODEL parsing (Nova Pro) for PDF extraction
      - SEMANTIC chunking (NLP-based sentence grouping)
    """
    ds_name = f"{KB_NAME}-s3-source"
    print(f"[INFO] Creating Data Source '{ds_name}' for KB {kb_id}")

    # Build chunking configuration
    if CHUNKING_STRATEGY == "SEMANTIC":
        chunking_config = {
            "chunkingStrategy": "SEMANTIC",
            "semanticChunkingConfiguration": {
                "bufferSize": SEMANTIC_BUFFER_SIZE,
                "breakpointPercentileThreshold": SEMANTIC_BREAKPOINT_PERCENTILE,
                # maxTokens: max tokens per chunk (default 300)
                "maxTokens": 500,
            },
        }
    elif CHUNKING_STRATEGY == "HIERARCHICAL":
        # Alternative: hierarchical chunking (large parent + small child chunks)
        # Good for documents where context from parent improves retrieval
        chunking_config = {
            "chunkingStrategy": "HIERARCHICAL",
            "hierarchicalChunkingConfiguration": {
                "levelConfigurations": [
                    {"maxTokens": 1500},  # parent chunk
                    {"maxTokens": 300},   # child chunk
                ],
                "overlapTokens": 60,
            },
        }
    else:
        # FIXED_SIZE fallback
        chunking_config = {
            "chunkingStrategy": "FIXED_SIZE",
            "fixedSizeChunkingConfiguration": {
                "maxTokens": 500,
                "overlapPercentage": 20,
            },
        }

    response = bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name=ds_name,
        description="ISO 27001:2022 audit documents and reference data",
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": f"arn:aws:s3:::{BUCKET_NAME}",
                "inclusionPrefixes": [RAW_PREFIX],
            },
        },
        # ── PARSING CONFIGURATION ─────────────────────────────────────────
        # BEDROCK_FOUNDATION_MODEL: uses a vision-capable FM to parse PDFs.
        # This extracts tables, figures, and images — critical for audit PDFs.
        # Falls back to default parser if FM parsing fails.
        # Ref: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_ParsingConfiguration.html
        vectorIngestionConfiguration={
            "chunkingConfiguration": chunking_config,
            "parsingConfiguration": {
                "parsingStrategy": "BEDROCK_FOUNDATION_MODEL",
                "bedrockFoundationModelConfiguration": {
                    "modelArn": (
                        f"arn:aws:bedrock:{REGION}::foundation-model/{PARSING_MODEL_ID}"
                    ),
                    "parsingPrompt": {
                        "parsingPromptText": PARSING_PROMPT,
                    },
                },
            },
        },
    )

    ds_id = response["dataSource"]["dataSourceId"]
    print(f"[INFO] Data Source created: {ds_id}")
    return ds_id


# ─────────────────────────────────────────────────────────────────────────────
# INGESTION JOB
# ─────────────────────────────────────────────────────────────────────────────

def _start_ingestion_job(kb_id: str, ds_id: str) -> str:
    """Start a sync ingestion job and return the jobId."""
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        description=f"Ingestion triggered by pipeline at {time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
    )
    job_id = response["ingestionJob"]["ingestionJobId"]
    print(f"[INFO] Ingestion job started: {job_id}")
    return job_id


def _wait_for_ingestion(kb_id: str, ds_id: str, job_id: str) -> dict:
    """Poll until the ingestion job reaches a terminal state."""
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id,
        )
        job = response["ingestionJob"]
        status = job["status"]
        stats  = job.get("statistics", {})

        print(f"[INFO] Ingestion job {job_id} status={status} "
              f"scanned={stats.get('numberOfDocumentsScanned', 0)} "
              f"indexed={stats.get('numberOfNewDocumentsIndexed', 0)} "
              f"failed={stats.get('numberOfDocumentsFailed', 0)}")

        if status in ("COMPLETE", "FAILED", "STOPPED"):
            return job

        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    raise TimeoutError(
        f"Ingestion job {job_id} did not complete within {MAX_WAIT_SECONDS}s"
    )


# ─────────────────────────────────────────────────────────────────────────────
# LAMBDA HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context: Any) -> dict:
    bucket    = event["bucket"]
    key       = event["key"]
    file_name = event.get("file_name", key.split("/")[-1])

    print(f"[INFO] Chunking/KB ingestion starting for s3://{bucket}/{key}")
    print(f"[INFO] Parsing model: {PARSING_MODEL_ID}")
    print(f"[INFO] Chunking strategy: {CHUNKING_STRATEGY}")
    print(f"[INFO] Embedding model: {EMBEDDING_MODEL_ID} ({EMBEDDING_DIMS} dims)")

    # 1. Get or create Knowledge Base
    kb_id = _find_existing_kb(KB_NAME)
    if kb_id:
        print(f"[INFO] Reusing existing Knowledge Base: {kb_id}")
    else:
        kb_id = _create_knowledge_base()

    # 2. Get or create Data Source
    ds_name = f"{KB_NAME}-s3-source"
    ds_id = _find_existing_data_source(kb_id, ds_name)
    if ds_id:
        print(f"[INFO] Reusing existing Data Source: {ds_id}")
    else:
        ds_id = _create_data_source(kb_id)

    # 3. Start ingestion job (syncs S3 raw/ prefix → KB)
    job_id = _start_ingestion_job(kb_id, ds_id)

    # 4. Wait for completion
    job = _wait_for_ingestion(kb_id, ds_id, job_id)
    stats = job.get("statistics", {})

    if job["status"] == "FAILED":
        failure_reasons = job.get("failureReasons", [])
        print(f"[ERROR] Ingestion job failed: {failure_reasons}")
        raise RuntimeError(f"Ingestion job {job_id} failed: {failure_reasons}")

    print(f"[INFO] Ingestion complete. Stats: {json.dumps(stats)}")

    return {
        **event,
        "knowledge_base_id": kb_id,
        "data_source_id":    ds_id,
        "ingestion_job_id":  job_id,
        "ingestion_status":  job["status"],
        "chunking_stats": {
            "parsing_model":           PARSING_MODEL_ID,
            "chunking_strategy":       CHUNKING_STRATEGY,
            "embedding_model":         EMBEDDING_MODEL_ID,
            "embedding_dimensions":    EMBEDDING_DIMS,
            "documents_scanned":       stats.get("numberOfDocumentsScanned", 0),
            "documents_indexed":       stats.get("numberOfNewDocumentsIndexed", 0),
            "documents_updated":       stats.get("numberOfModifiedDocumentsIndexed", 0),
            "documents_deleted":       stats.get("numberOfDocumentsDeleted", 0),
            "documents_failed":        stats.get("numberOfDocumentsFailed", 0),
        },
    }
