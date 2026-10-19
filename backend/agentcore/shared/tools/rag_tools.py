"""
RAG tools for querying Bedrock Knowledge Bases.
Used by all agents to retrieve ISO 27001 context and evidence.
"""

import os

import boto3
from strands import tool


REGION = os.environ.get("AWS_REGION", "us-east-1")
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "")
GENERATION_MODEL_ID = os.environ.get("GENERATION_MODEL_ID", "openai.gpt-oss-120b-1:0")
NUMBER_OF_RESULTS = int(os.environ.get("RAG_NUMBER_OF_RESULTS", "5"))

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)


@tool
def query_knowledge_base(question: str, num_results: int = 5) -> dict:
    """
    Query the ISO 27001 knowledge base using RetrieveAndGenerate.
    Returns an AI-generated answer grounded in the knowledge base documents,
    along with source citations.

    Args:
        question: The audit-related question to answer using RAG.
        num_results: Number of source chunks to retrieve (default 5).

    Returns:
        Dict with 'answer', 'sources' (list of source URIs and excerpts),
        and 'source_count'.
    """
    kb_id = KNOWLEDGE_BASE_ID
    if not kb_id:
        return {"error": "KNOWLEDGE_BASE_ID not configured", "answer": "", "sources": [], "source_count": 0}

    response = bedrock_agent_runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": f"arn:aws:bedrock:{REGION}::foundation-model/{GENERATION_MODEL_ID}",
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": num_results,
                        "overrideSearchType": "SEMANTIC",
                    }
                },
                "generationConfiguration": {
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            "maxTokens": 2048,
                            "temperature": 0.0,
                            "topP": 0.9,
                        }
                    },
                },
            },
        },
    )

    answer = response["output"]["text"]
    sources = []
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            loc = ref.get("location", {}).get("s3Location", {})
            sources.append({
                "uri": loc.get("uri", ""),
                "excerpt": ref.get("content", {}).get("text", "")[:300],
            })

    return {
        "answer": answer,
        "sources": sources,
        "source_count": len(sources),
    }


@tool
def retrieve_control_evidence(control_id: str, organization_context: str = "") -> dict:
    """
    Retrieve evidence and requirements for a specific ISO 27001:2022 control.
    Combines RAG retrieval with a structured prompt to extract control-specific
    audit evidence requirements.

    Args:
        control_id: ISO 27001:2022 control reference (e.g., 'A.5.1', 'A.8.7').
        organization_context: Optional context about the organization being audited.

    Returns:
        Dict with 'control_id', 'requirements', 'evidence_types',
        'common_findings', and 'sources'.
    """
    kb_id = KNOWLEDGE_BASE_ID
    if not kb_id:
        return {"error": "KNOWLEDGE_BASE_ID not configured"}

    question = (
        f"For ISO 27001:2022 control {control_id}, provide:\n"
        f"1. The control objective and requirements\n"
        f"2. Types of evidence an auditor should request\n"
        f"3. Common non-conformities found during audits\n"
        f"4. Evaluation criteria for conformity assessment\n"
    )
    if organization_context:
        question += f"\nOrganization context: {organization_context}"

    response = bedrock_agent_runtime.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": f"arn:aws:bedrock:{REGION}::foundation-model/{GENERATION_MODEL_ID}",
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": NUMBER_OF_RESULTS,
                        "overrideSearchType": "SEMANTIC",
                    }
                },
                "generationConfiguration": {
                    "promptTemplate": {
                        "textPromptTemplate": (
                            "You are an expert ISO 27001:2022 auditor. "
                            "Based on the retrieved context, provide a structured assessment "
                            "for the requested control. Be specific about evidence requirements "
                            "and common non-conformities.\n\n"
                            "$search_results$\n\n"
                            "Question: $query$"
                        )
                    },
                    "inferenceConfig": {
                        "textInferenceConfig": {
                            "maxTokens": 2048,
                            "temperature": 0.0,
                            "topP": 0.9,
                        }
                    },
                },
            },
        },
    )

    answer = response["output"]["text"]
    sources = []
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            loc = ref.get("location", {}).get("s3Location", {})
            sources.append(loc.get("uri", ""))

    return {
        "control_id": control_id,
        "assessment_details": answer,
        "sources": list(set(sources)),
        "source_count": len(set(sources)),
    }
