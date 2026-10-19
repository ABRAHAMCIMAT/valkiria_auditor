"""
ISO 27001:2013 Audit Orchestrator — Adapted from Avance5.dev evaluation.

Executes the three specialized agents (Gobernanza, Organizacional, Técnico) sequentially,
retrieves evidence from S3 Vectors, and consolidates findings into a unified report.

Architecture:
    1. Parse audit request → determine clauses/controls in scope
    2. For each clause/control: retrieve evidence via S3 Vectors → invoke specialist agent
    3. Optionally run LLM judge for quality scoring
    4. Consolidate all findings into audit report

Compatible with the existing backend infrastructure (same IAM role, S3 bucket, DynamoDB).
"""

import json
import os
import time
from datetime import datetime, timezone

import boto3

from backend.comp2013.prompts.governance import SYSTEM_PROMPT as GOV_PROMPT
from backend.comp2013.prompts.organizational import SYSTEM_PROMPT as ORG_PROMPT
from backend.comp2013.prompts.technical import SYSTEM_PROMPT as TECH_PROMPT
from backend.comp2013.prompts.judge import SYSTEM_PROMPT as JUDGE_PROMPT
from backend.observability.flow_tracker import FlowTracker


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

REGION = os.environ.get("AWS_REGION", "us-east-1")
PRIMARY_MODEL_ID = os.environ.get("PRIMARY_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
JUDGE_MODEL_ID = os.environ.get("JUDGE_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
VECTOR_STORE_BUCKET = os.environ.get("VECTOR_STORE_BUCKET", "iso27001-vectors-e16")
VECTOR_STORE_INDEX = os.environ.get("VECTOR_STORE_INDEX", "iso27001-compliance-index")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "amazon.titan-embed-text-v2:0")
TOP_K = int(os.environ.get("TOP_K", "3"))
BUCKET_NAME = os.environ.get("BUCKET_NAME", "")

# Agent scope definitions (from Avance5 config.yaml)
AGENT_SCOPES = {
    "gobernanza": {
        "prompt": GOV_PROMPT,
        "description": "Clausulas de Gestión 4-10",
        "ref_ids": [
            "4.1", "4.2", "4.3", "4.4",
            "5.1", "5.2", "5.3",
            "6.1.1", "6.1.2", "6.1.3", "6.2",
            "7.2", "7.3", "7.4", "7.5.1", "7.5.2", "7.5.3",
            "8.1", "9.1", "9.2", "9.3", "10.1",
        ],
    },
    "organizacional": {
        "prompt": ORG_PROMPT,
        "description": "Anexo A: A.5-A.8, A.15, A.16, A.18",
        "ref_ids": [
            "A.5.1.1", "A.5.1.2",
            "A.6.1.1", "A.6.1.2", "A.6.1.3", "A.6.1.4", "A.6.1.5",
            "A.6.2.1", "A.6.2.2",
            "A.7.1.1", "A.7.1.2", "A.7.2.1", "A.7.2.2", "A.7.2.3", "A.7.3.1",
            "A.8.1.1", "A.8.1.2", "A.8.1.3", "A.8.1.4",
            "A.8.2.1", "A.8.2.2", "A.8.2.3",
            "A.8.3.1", "A.8.3.2", "A.8.3.3",
            "A.15.1.1", "A.15.1.2", "A.15.1.3", "A.15.2.1", "A.15.2.2",
            "A.16.1.1", "A.16.1.2", "A.16.1.3", "A.16.1.4", "A.16.1.5", "A.16.1.6", "A.16.1.7",
            "A.18.1.1", "A.18.1.2", "A.18.1.3", "A.18.1.4", "A.18.1.5",
            "A.18.2.1", "A.18.2.2", "A.18.2.3",
        ],
    },
    "tecnico": {
        "prompt": TECH_PROMPT,
        "description": "Anexo A: A.9-A.14, A.17",
        "ref_ids": [
            "A.9.1.1", "A.9.1.2", "A.9.2.1", "A.9.2.2", "A.9.2.3", "A.9.2.4", "A.9.2.5", "A.9.2.6",
            "A.9.3.1", "A.9.4.1", "A.9.4.2", "A.9.4.3", "A.9.4.4", "A.9.4.5",
            "A.10.1.1", "A.10.1.2",
            "A.11.1.1", "A.11.1.2", "A.11.1.3", "A.11.1.4", "A.11.1.5", "A.11.1.6",
            "A.11.2.1", "A.11.2.2", "A.11.2.3", "A.11.2.4", "A.11.2.5", "A.11.2.6", "A.11.2.7", "A.11.2.8", "A.11.2.9",
            "A.12.1.1", "A.12.1.2", "A.12.1.3", "A.12.1.4",
            "A.12.2.1", "A.12.3.1",
            "A.12.4.1", "A.12.4.2", "A.12.4.3", "A.12.4.4",
            "A.12.5.1", "A.12.6.1", "A.12.6.2", "A.12.7.1",
            "A.13.1.1", "A.13.1.2", "A.13.1.3", "A.13.2.1", "A.13.2.2", "A.13.2.3", "A.13.2.4",
            "A.14.1.1", "A.14.1.2", "A.14.1.3",
            "A.14.2.1", "A.14.2.2", "A.14.2.3", "A.14.2.4", "A.14.2.5", "A.14.2.6", "A.14.2.7", "A.14.2.8", "A.14.2.9",
            "A.14.3.1",
            "A.17.1.1", "A.17.1.2", "A.17.1.3", "A.17.2.1",
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# EVIDENCE RETRIEVAL (S3 Vectors)
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_evidence(clause_text: str, bedrock_client) -> list[dict]:
    """
    Retrieve relevant evidence from S3 Vectors using semantic search.

    Args:
        clause_text: The clause or control text to search for.
        bedrock_client: Boto3 bedrock-runtime client.

    Returns:
        List of dicts with 'document' and 'content' keys.
    """
    s3v_client = boto3.client("s3vectors", region_name=REGION)

    # Generate embedding for the query
    embed_response = bedrock_client.invoke_model(
        modelId=EMBEDDING_MODEL,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({"inputText": clause_text}),
    )
    embedding = json.loads(embed_response["body"].read())["embedding"]

    # Query S3 Vectors
    try:
        response = s3v_client.query_vectors(
            vectorBucketName=VECTOR_STORE_BUCKET,
            indexName=VECTOR_STORE_INDEX,
            queryVector=embedding,
            topK=TOP_K,
            metadataFilter={},
        )

        results = []
        for hit in response.get("vectors", []):
            metadata = hit.get("metadata", {})
            results.append({
                "document": metadata.get("source_document", metadata.get("document_name", "unknown")),
                "content": metadata.get("text", metadata.get("content", "")),
            })
        return results

    except Exception as exc:
        print(f"[WARN] S3 Vectors query failed: {exc}. Returning empty context.")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# AGENT INVOCATION
# ─────────────────────────────────────────────────────────────────────────────

def invoke_agent(
    system_prompt: str,
    clause_text: str,
    retrieved_context: list[dict],
    model_id: str,
    bedrock_client,
) -> dict:
    """
    Invoke a specialist agent using Bedrock converse API.

    Args:
        system_prompt: The agent's system prompt.
        clause_text: The clause/control to evaluate.
        retrieved_context: List of evidence documents.
        model_id: Bedrock model to use.
        bedrock_client: Boto3 bedrock-runtime client.

    Returns:
        Dict with agent response, latency, and token metrics.
    """
    user_message = (
        f"<retrieved_context>\n"
        f"{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}\n"
        f"</retrieved_context>\n\n"
        f"<clause_to_evaluate>\n{clause_text}\n</clause_to_evaluate>"
    )

    start = time.perf_counter()

    response = bedrock_client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
        inferenceConfig={"temperature": 0.0, "maxTokens": 2048},
    )

    latency_ms = (time.perf_counter() - start) * 1000
    usage = response.get("usage", {})
    output_blocks = response["output"]["message"]["content"]
    output_text = next((b["text"] for b in output_blocks if "text" in b), "")

    # Parse JSON response
    try:
        # Handle markdown code blocks
        cleaned = output_text.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:-1])
        finding = json.loads(cleaned)
    except json.JSONDecodeError:
        finding = {"raw_response": output_text, "parse_error": True}

    return {
        "finding": finding,
        "latency_ms": round(latency_ms, 1),
        "input_tokens": usage.get("inputTokens", 0),
        "output_tokens": usage.get("outputTokens", 0),
    }


def invoke_judge(
    clause_text: str,
    retrieved_context: list[dict],
    agent_response: str,
    bedrock_client,
) -> dict:
    """
    Invoke the LLM judge to evaluate agent response quality.

    Returns:
        Dict with precision_score and per-criterion scores.
    """
    user_message = (
        f"<clause_to_evaluate>\n{clause_text}\n</clause_to_evaluate>\n\n"
        f"<retrieved_context>\n{json.dumps(retrieved_context, ensure_ascii=False, indent=2)}\n</retrieved_context>\n\n"
        f"<agent_response>\n{agent_response}\n</agent_response>"
    )

    try:
        response = bedrock_client.converse(
            modelId=JUDGE_MODEL_ID,
            system=[{"text": JUDGE_PROMPT}],
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            inferenceConfig={"temperature": 0.0, "maxTokens": 1024},
        )

        output_blocks = response["output"]["message"]["content"]
        output_text = next((b["text"] for b in output_blocks if "text" in b), "")

        cleaned = output_text.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:-1])

        return json.loads(cleaned)
    except Exception as exc:
        return {"precision_score": 0, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATION
# ─────────────────────────────────────────────────────────────────────────────

def run_audit(
    organization_context: str,
    audit_type: str = "internal",
    audit_id: str = "",
    session_id: str = "",
    actor_id: str = "lead_auditor",
    agents_in_scope: list[str] = None,
    controls_in_scope: list[str] = None,
    run_judge: bool = False,
) -> dict:
    """
    Execute an ISO 27001:2013 audit using the three specialized agents.

    Args:
        organization_context: Description of the organization.
        audit_type: 'internal', 'certification', or 'surveillance'.
        audit_id: Unique audit identifier.
        session_id: Session identifier.
        actor_id: Auditor identifier.
        agents_in_scope: Which agents to run ('gobernanza', 'organizacional', 'tecnico'). Default: all.
        controls_in_scope: Specific control ref_ids to evaluate. Default: all for selected agents.
        run_judge: Whether to run the LLM judge on each finding.

    Returns:
        Dict with all findings, metrics, and consolidated summary.
    """
    if not audit_id:
        audit_id = f"comp2013_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if not session_id:
        session_id = f"session_{audit_id}"

    if agents_in_scope is None:
        agents_in_scope = ["gobernanza", "organizacional", "tecnico"]

    # Initialize
    bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    tracker = FlowTracker(audit_id=audit_id, session_id=session_id, actor_id=actor_id)

    all_findings = []
    agent_metrics = {}

    for agent_name in agents_in_scope:
        if agent_name not in AGENT_SCOPES:
            continue

        scope = AGENT_SCOPES[agent_name]
        ref_ids = controls_in_scope if controls_in_scope else scope["ref_ids"]
        # Filter to only ref_ids that belong to this agent
        valid_ids = [rid for rid in ref_ids if rid in scope["ref_ids"]]

        if not valid_ids:
            continue

        agent_findings = []
        agent_latency_total = 0.0
        agent_input_tokens = 0
        agent_output_tokens = 0

        with tracker.node(f"{agent_name}_evaluation", agent_name=agent_name, model_id=PRIMARY_MODEL_ID) as node:
            for ref_id in valid_ids:
                # Build clause text (simplified — in production, load from YAML)
                clause_text = f"Control {ref_id} — Evaluar el cumplimiento de este control según ISO 27001:2013."

                # Retrieve evidence
                evidence = retrieve_evidence(
                    f"{clause_text} {organization_context}",
                    bedrock,
                )

                # Invoke specialist agent
                result = invoke_agent(
                    system_prompt=scope["prompt"],
                    clause_text=clause_text,
                    retrieved_context=evidence,
                    model_id=PRIMARY_MODEL_ID,
                    bedrock_client=bedrock,
                )

                finding_record = {
                    "agent": agent_name,
                    "ref_id": ref_id,
                    "finding": result["finding"],
                    "evidence_count": len(evidence),
                    "latency_ms": result["latency_ms"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                }

                # Optional: run judge
                if run_judge and not result["finding"].get("parse_error"):
                    judge_result = invoke_judge(
                        clause_text=clause_text,
                        retrieved_context=evidence,
                        agent_response=json.dumps(result["finding"], ensure_ascii=False),
                        bedrock_client=bedrock,
                    )
                    finding_record["judge_score"] = judge_result.get("precision_score", 0)
                    finding_record["judge_detail"] = judge_result

                agent_findings.append(finding_record)
                agent_latency_total += result["latency_ms"]
                agent_input_tokens += result["input_tokens"]
                agent_output_tokens += result["output_tokens"]

            node.set_result(
                input_tokens=agent_input_tokens,
                output_tokens=agent_output_tokens,
                tool_calls=len(valid_ids),
            )

        all_findings.extend(agent_findings)
        agent_metrics[agent_name] = {
            "controls_evaluated": len(agent_findings),
            "total_latency_ms": round(agent_latency_total, 1),
            "avg_latency_ms": round(agent_latency_total / max(len(agent_findings), 1), 1),
            "total_input_tokens": agent_input_tokens,
            "total_output_tokens": agent_output_tokens,
        }

    # Consolidate
    severity_counts = {"No conformidad mayor": 0, "No conformidad menor": 0, "Conforme": 0,
                       "No se puede evaluar": 0, "Oportunidad de Mejora": 0}
    for f in all_findings:
        ranking = f.get("finding", {}).get("ranking", "")
        if ranking in severity_counts:
            severity_counts[ranking] += 1

    flow_summary = tracker.finalize()

    # Persist to S3
    if BUCKET_NAME:
        try:
            s3 = boto3.client("s3", region_name=REGION)
            report_key = f"metrics/comp2013/{audit_id}/report.json"
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=report_key,
                Body=json.dumps({
                    "audit_id": audit_id,
                    "framework": "comp2013",
                    "standard": "ISO/IEC 27001:2013",
                    "findings": all_findings,
                    "severity_counts": severity_counts,
                    "agent_metrics": agent_metrics,
                    "flow_metrics": flow_summary,
                }, ensure_ascii=False, default=str).encode("utf-8"),
                ContentType="application/json",
            )
        except Exception as exc:
            print(f"[WARN] Failed to persist report to S3: {exc}")

    return {
        "framework": "comp2013",
        "standard": "ISO/IEC 27001:2013",
        "version": "1.0.0",
        "audit_id": audit_id,
        "total_controls_evaluated": len(all_findings),
        "severity_counts": severity_counts,
        "agent_metrics": agent_metrics,
        "findings": all_findings,
        "flow_metrics": flow_summary,
    }


if __name__ == "__main__":
    result = run_audit(
        organization_context="ACME Corp, empresa tecnológica con 200 empleados que maneja datos financieros.",
        audit_type="internal",
        audit_id="comp2013_test_001",
        agents_in_scope=["gobernanza"],
        controls_in_scope=["9.3"],
        run_judge=True,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str)[:3000])
