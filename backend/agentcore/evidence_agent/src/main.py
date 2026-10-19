"""
Evidence Collection Agent — Retrieves and organizes documentary evidence for audit.
Deployed as an independent AgentCore runtime instance.
"""

import os
from datetime import datetime

from strands import Agent, tool
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.model_loader import load_model
from shared.tools.rag_tools import query_knowledge_base, retrieve_control_evidence
from shared.tools.s3_tools import get_document_content, save_report_to_s3
from shared.tools.dynamodb_tools import get_document_metadata
from shared.prompts.evidence import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# AGENT-SPECIFIC TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def collect_evidence_for_controls(
    control_ids: list[str],
    organization_context: str = "",
) -> dict:
    """
    Batch evidence collection for multiple controls.
    Queries the knowledge base for each control and aggregates results.

    Args:
        control_ids: List of ISO 27001:2022 control IDs to collect evidence for (e.g., ['A.5.1', 'A.5.2']).
        organization_context: Description of the organization being audited.

    Returns:
        Dict with 'evidence_packages' per control and summary statistics.
    """
    import boto3

    kb_id = os.environ.get("KNOWLEDGE_BASE_ID", "")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not kb_id:
        return {"error": "KNOWLEDGE_BASE_ID not configured"}

    client = boto3.client("bedrock-agent-runtime", region_name=region)
    model_id = os.environ.get("GENERATION_MODEL_ID", "amazon.nova-pro-v1:0")
    results = []

    for control_id in control_ids:
        question = (
            f"Retrieve all available documentary evidence related to ISO 27001:2022 "
            f"control {control_id}. Include policies, procedures, records, and any "
            f"implementation evidence."
        )
        if organization_context:
            question += f" Organization: {organization_context}"

        try:
            response = client.retrieve_and_generate(
                input={"text": question},
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "knowledgeBaseId": kb_id,
                        "modelArn": f"arn:aws:bedrock:{region}::foundation-model/{model_id}",
                        "retrievalConfiguration": {
                            "vectorSearchConfiguration": {
                                "numberOfResults": 5,
                                "overrideSearchType": "SEMANTIC",
                            }
                        },
                    },
                },
            )

            sources = []
            for citation in response.get("citations", []):
                for ref in citation.get("retrievedReferences", []):
                    loc = ref.get("location", {}).get("s3Location", {})
                    sources.append({
                        "uri": loc.get("uri", ""),
                        "excerpt": ref.get("content", {}).get("text", "")[:200],
                    })

            results.append({
                "control_id": control_id,
                "evidence_found": len(sources) > 0,
                "evidence_count": len(sources),
                "sources": sources,
                "summary": response["output"]["text"][:500],
            })

        except Exception as exc:
            results.append({
                "control_id": control_id,
                "evidence_found": False,
                "evidence_count": 0,
                "error": str(exc),
            })

    controls_with_evidence = sum(1 for r in results if r.get("evidence_found"))

    return {
        "total_controls_queried": len(control_ids),
        "controls_with_evidence": controls_with_evidence,
        "controls_without_evidence": len(control_ids) - controls_with_evidence,
        "evidence_packages": results,
    }


@tool
def assess_evidence_sufficiency(
    control_id: str,
    evidence_items: list[str],
) -> dict:
    """
    Assess whether collected evidence is sufficient for auditing a given control.

    Args:
        control_id: ISO 27001:2022 control reference (e.g., 'A.5.1').
        evidence_items: List of evidence descriptions or document references found.

    Returns:
        Dict with sufficiency assessment, gaps, and recommendations.
    """
    # Evidence type requirements per control category
    required_evidence_types = {
        "A.5": ["policy", "procedure", "review_records", "implementation_evidence"],
        "A.6": ["hr_records", "training_records", "agreements", "procedures"],
        "A.7": ["physical_security_plan", "access_logs", "maintenance_records"],
        "A.8": ["technical_config", "scan_results", "architecture_docs", "procedures"],
    }

    domain = control_id[:3]  # e.g., "A.5"
    required = required_evidence_types.get(domain, ["documentation"])

    # Simple heuristic: check what types of evidence were found
    found_types = []
    for item in evidence_items:
        item_lower = item.lower()
        if any(word in item_lower for word in ["policy", "política"]):
            found_types.append("policy")
        if any(word in item_lower for word in ["procedure", "procedimiento", "process"]):
            found_types.append("procedure")
        if any(word in item_lower for word in ["record", "log", "registro"]):
            found_types.append("review_records")
        if any(word in item_lower for word in ["config", "scan", "technical"]):
            found_types.append("technical_config")
        if any(word in item_lower for word in ["training", "capacitación", "awareness"]):
            found_types.append("training_records")

    found_types = list(set(found_types))
    missing = [r for r in required if r not in found_types]
    sufficiency_score = len(found_types) / max(len(required), 1)

    return {
        "control_id": control_id,
        "evidence_items_count": len(evidence_items),
        "evidence_types_found": found_types,
        "evidence_types_required": required,
        "missing_evidence_types": missing,
        "sufficiency_score": round(sufficiency_score, 2),
        "is_sufficient": sufficiency_score >= 0.75,
        "recommendation": (
            "Evidence is sufficient for assessment."
            if sufficiency_score >= 0.75
            else f"Additional evidence needed: {', '.join(missing)}"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENTCORE APP
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Evidence Agent entrypoint."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    session_id = payload.get("session_id", f"evidence_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    actor_id = payload.get("actor_id", "system")

    session_manager = None
    if memory_id:
        config = AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=session_id,
            actor_id=actor_id,
        )
        session_manager = AgentCoreMemorySessionManager(
            agentcore_memory_config=config,
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )

    agent = Agent(
        model=load_model(temperature=0.1),
        system_prompt=SYSTEM_PROMPT,
        tools=[
            query_knowledge_base,
            retrieve_control_evidence,
            get_document_content,
            get_document_metadata,
            collect_evidence_for_controls,
            assess_evidence_sufficiency,
            save_report_to_s3,
        ],
        session_manager=session_manager,
    )

    prompt = payload.get("prompt", "")
    response = agent(prompt)

    return {
        "response": str(response),
        "session_id": session_id,
        "actor_id": actor_id,
        "agent": "evidence_agent",
    }


if __name__ == "__main__":
    app.run()
