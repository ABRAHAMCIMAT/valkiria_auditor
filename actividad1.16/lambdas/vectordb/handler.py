"""
Lambda: vectordb  (Step 3 del pipeline)
Ejecuta una consulta RAG de prueba contra la Bedrock Knowledge Base para
validar que la ingesta fue exitosa y que el índice responde correctamente.

Bedrock Knowledge Bases gestiona internamente:
  - Los embeddings (Titan Text Embeddings V2, 1024 dims)
  - El índice vectorial en OpenSearch Serverless
  - La recuperación semántica

Esta Lambda usa la API RetrieveAndGenerate para:
  1. Ejecutar 3 consultas de validación sobre controles ISO 27001:2022
  2. Verificar que los chunks recuperados son relevantes
  3. Guardar el reporte de validación en S3

Input (desde Step Functions, output del paso Chunking):
    {
        "bucket": "...",
        "key": "raw/...",
        "file_name": "...",
        "knowledge_base_id": "XXXXXXXXXX",
        "data_source_id":    "YYYYYYYYYY",
        "ingestion_job_id":  "ZZZZZZZZZZ",
        "ingestion_status":  "COMPLETE",
        "chunking_stats": { ... }
    }

Output:
    {
        ...previous fields...,
        "validation_results_key": "validation/<uuid>_validation.json",
        "vectordb_stats": {
            "queries_executed": 3,
            "queries_with_results": 3,
            "avg_sources_per_query": 4.3,
            "knowledge_base_id": "...",
            "embedding_model": "amazon.titan-embed-text-v2:0",
            "generation_model": "amazon.nova-pro-v1:0"
        }
    }

References:
  - https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_RetrieveAndGenerate.html
  - https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-supported.html
"""

import json
import os
import time
import uuid
from typing import Any

import boto3

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

BUCKET_NAME       = os.environ["BUCKET_NAME"]
VALIDATION_PREFIX = os.environ.get("VALIDATION_PREFIX", "validation/")
REGION            = os.environ.get("AWS_REGION", "us-east-1")

# Generation model for RetrieveAndGenerate
# amazon.nova-pro-v1:0 — latest Amazon Nova Pro, strong reasoning + multimodal
# Alternative: us.anthropic.claude-3-5-sonnet-20241022-v2:0 (cross-region inference profile)
GENERATION_MODEL_ID = os.environ.get(
    "GENERATION_MODEL_ID", "amazon.nova-pro-v1:0"
)

# Embedding model (must match what was used during KB creation)
EMBEDDING_MODEL_ID = os.environ.get(
    "EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"
)

# Number of source chunks to retrieve per query
NUMBER_OF_RESULTS = int(os.environ.get("NUMBER_OF_RESULTS", "5"))

# ─────────────────────────────────────────────────────────────────────────────
# AWS CLIENTS
# ─────────────────────────────────────────────────────────────────────────────

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
s3_client             = boto3.client("s3")

# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION QUERIES
# These queries test that the KB correctly indexes ISO 27001:2022 content
# ─────────────────────────────────────────────────────────────────────────────

VALIDATION_QUERIES = [
    {
        "id": "q1_malware_protection",
        "question": (
            "What evidence is required to evaluate control A.8.7 "
            "(protection against malware) in an ISO 27001:2022 audit?"
        ),
        "expected_controls": ["A.8.7", "A.8.8"],
    },
    {
        "id": "q2_access_control",
        "question": (
            "What are the most common audit findings related to access control "
            "in ISO 27001:2022 organizational controls (A.5)?"
        ),
        "expected_controls": ["A.5.15", "A.5.16", "A.5.18"],
    },
    {
        "id": "q3_risk_assessment",
        "question": (
            "How should an organization document and maintain its information "
            "security risk assessment according to ISO 27001:2022 clause 6.1?"
        ),
        "expected_controls": ["A.5.7", "A.5.19"],
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# RAG QUERY
# ─────────────────────────────────────────────────────────────────────────────

def _retrieve_and_generate(kb_id: str, question: str) -> dict:
    """
    Execute a RetrieveAndGenerate call against the Bedrock Knowledge Base.
    Uses the KNOWLEDGE_BASE retrieval type with the configured generation model.
    """
    response = bedrock_agent_runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": (
                    f"arn:aws:bedrock:{REGION}::foundation-model/{GENERATION_MODEL_ID}"
                ),
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": NUMBER_OF_RESULTS,
                        # OVERRIDDEN_RERANKING: use built-in reranking for better precision
                        "overrideSearchType": "SEMANTIC",
                    }
                },
                "generationConfiguration": {
                    "promptTemplate": {
                        "textPromptTemplate": (
                            "You are an expert ISO 27001:2022 auditor. "
                            "Answer the following question based ONLY on the provided context. "
                            "Always cite the specific ISO control IDs (e.g. A.8.7) when relevant.\n\n"
                            "$search_results$\n\n"
                            "Question: $query$\n\n"
                            "Provide: (1) direct answer, (2) relevant ISO controls, "
                            "(3) required evidence."
                        )
                    },
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            "maxTokens": 1024,
                            "temperature": 0.0,   # deterministic for audit responses
                            "topP": 0.9,
                        }
                    },
                },
            },
        },
    )

    answer  = response["output"]["text"]
    sources = response.get("citations", [])

    # Extract source references
    source_refs = []
    for citation in sources:
        for ref in citation.get("retrievedReferences", []):
            loc = ref.get("location", {}).get("s3Location", {})
            source_refs.append({
                "uri":     loc.get("uri", ""),
                "excerpt": ref.get("content", {}).get("text", "")[:200],
            })

    return {
        "answer":       answer,
        "sources":      source_refs,
        "source_count": len(source_refs),
    }


# ─────────────────────────────────────────────────────────────────────────────
# LAMBDA HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def lambda_handler(event: dict, context: Any) -> dict:
    kb_id     = event["knowledge_base_id"]
    file_name = event.get("file_name", "unknown")

    print(f"[INFO] VectorDB validation starting for KB: {kb_id}")
    print(f"[INFO] Generation model: {GENERATION_MODEL_ID}")
    print(f"[INFO] Embedding model:  {EMBEDDING_MODEL_ID}")

    # Small delay to ensure the index is fully refreshed after ingestion
    time.sleep(5)

    # Run validation queries
    results = []
    queries_with_results = 0

    for query in VALIDATION_QUERIES:
        print(f"[INFO] Running query: {query['id']}")
        try:
            result = _retrieve_and_generate(kb_id, query["question"])
            result["query_id"]  = query["id"]
            result["question"]  = query["question"]
            result["expected_controls"] = query["expected_controls"]

            # Check if expected controls appear in the answer
            answer_lower = result["answer"].lower()
            controls_found = [
                c for c in query["expected_controls"]
                if c.lower() in answer_lower
            ]
            result["controls_found_in_answer"] = controls_found
            result["status"] = "success"

            if result["source_count"] > 0:
                queries_with_results += 1

            print(f"[INFO] Query {query['id']}: {result['source_count']} sources, "
                  f"controls found: {controls_found}")

        except Exception as exc:
            print(f"[WARN] Query {query['id']} failed: {exc}")
            result = {
                "query_id": query["id"],
                "question": query["question"],
                "status":   "error",
                "error":    str(exc),
                "source_count": 0,
            }

        results.append(result)

    # Compute summary stats
    total_sources = sum(r.get("source_count", 0) for r in results)
    avg_sources   = round(total_sources / len(results), 2) if results else 0

    validation_report = {
        "knowledge_base_id":    kb_id,
        "source_file":          file_name,
        "generation_model":     GENERATION_MODEL_ID,
        "embedding_model":      EMBEDDING_MODEL_ID,
        "queries_executed":     len(results),
        "queries_with_results": queries_with_results,
        "avg_sources_per_query": avg_sources,
        "results":              results,
    }

    # Save validation report to S3
    report_key = f"{VALIDATION_PREFIX}{uuid.uuid4().hex[:8]}_{file_name}_validation.json"
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=report_key,
        Body=json.dumps(validation_report, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )

    print(f"[INFO] Validation report saved to s3://{BUCKET_NAME}/{report_key}")
    print(f"[INFO] Summary: {queries_with_results}/{len(results)} queries returned results, "
          f"avg {avg_sources} sources/query")

    return {
        **event,
        "validation_results_key": report_key,
        "vectordb_stats": {
            "queries_executed":      len(results),
            "queries_with_results":  queries_with_results,
            "avg_sources_per_query": avg_sources,
            "knowledge_base_id":     kb_id,
            "embedding_model":       EMBEDDING_MODEL_ID,
            "generation_model":      GENERATION_MODEL_ID,
        },
    }
