"""
Consolidation/Orchestrator Agent — Coordinates all sub-agents and produces
the final consolidated ISO 27001:2022 audit report.
Deployed as an independent AgentCore runtime instance.

This is the primary entry point for the multi-agent audit system.
It uses the "Agents as Tools" pattern to invoke specialized sub-agents.
"""

import json
import os
from datetime import datetime

import httpx
from strands import Agent, tool
from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.model_loader import load_model
from shared.tools.rag_tools import query_knowledge_base
from shared.tools.dynamodb_tools import save_audit_finding, list_audit_findings
from shared.tools.s3_tools import save_report_to_s3
from shared.prompts.consolidation import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# SUB-AGENT INVOCATION TOOLS
# Uses AgentCore invoke to call deployed sub-agents
# ─────────────────────────────────────────────────────────────────────────────

def _invoke_sub_agent(agent_endpoint: str, payload: dict) -> dict:
    """
    Internal helper to invoke a deployed sub-agent via HTTP.
    In production, this uses the AgentCore runtime endpoint.
    In local dev, routes to localhost with different ports.
    """
    is_local = os.environ.get("LOCAL_DEV", "0") == "1"

    if is_local:
        # Local dev: sub-agents run on different ports
        url = agent_endpoint
    else:
        # Production: use AgentCore runtime invoke
        url = f"{agent_endpoint}/invocations"

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=120.0,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        return {"error": f"Sub-agent invocation failed: {exc}"}


@tool
def invoke_planning_agent(
    prompt: str,
    session_id: str = "",
    actor_id: str = "orchestrator",
) -> dict:
    """
    Invoke the Planning Agent to generate an ISO 27001:2022 audit plan.
    The planning agent determines scope, schedule, criteria, and team composition.

    Args:
        prompt: Instructions for the planning agent (e.g., organization context, audit type).
        session_id: Session ID for continuity.
        actor_id: Actor performing the action.

    Returns:
        Dict with the planning agent's response including audit plan details.
    """
    endpoint = os.environ.get("PLANNING_AGENT_ENDPOINT", "http://localhost:8081/invocations")
    return _invoke_sub_agent(endpoint, {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": actor_id,
    })


@tool
def invoke_evidence_agent(
    prompt: str,
    session_id: str = "",
    actor_id: str = "orchestrator",
) -> dict:
    """
    Invoke the Evidence Collection Agent to retrieve and organize documentary evidence.
    The evidence agent queries the RAG knowledge base and assesses evidence sufficiency.

    Args:
        prompt: Instructions specifying which controls need evidence (e.g., "Collect evidence for A.5.1 through A.5.10").
        session_id: Session ID for continuity.
        actor_id: Actor performing the action.

    Returns:
        Dict with evidence collection results, sufficiency assessment, and gaps.
    """
    endpoint = os.environ.get("EVIDENCE_AGENT_ENDPOINT", "http://localhost:8082/invocations")
    return _invoke_sub_agent(endpoint, {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": actor_id,
    })


@tool
def invoke_organizational_controls_agent(
    prompt: str,
    session_id: str = "",
    actor_id: str = "orchestrator",
) -> dict:
    """
    Invoke the Organizational Controls Agent (A.5) to evaluate 37 organizational controls.
    Assesses policies, roles, supplier management, incident response, and compliance controls.

    Args:
        prompt: Instructions and context for A.5 control evaluation (include evidence summary).
        session_id: Session ID for continuity.
        actor_id: Actor performing the action.

    Returns:
        Dict with conformity assessments, findings, and maturity scores for A.5 controls.
    """
    endpoint = os.environ.get("ORG_CONTROLS_AGENT_ENDPOINT", "http://localhost:8083/invocations")
    return _invoke_sub_agent(endpoint, {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": actor_id,
    })


@tool
def invoke_people_controls_agent(
    prompt: str,
    session_id: str = "",
    actor_id: str = "orchestrator",
) -> dict:
    """
    Invoke the People Controls Agent (A.6) to evaluate 8 people-related controls.
    Assesses screening, training, employment terms, remote working, and event reporting.

    Args:
        prompt: Instructions and context for A.6 control evaluation (include evidence summary).
        session_id: Session ID for continuity.
        actor_id: Actor performing the action.

    Returns:
        Dict with conformity assessments, findings, and maturity scores for A.6 controls.
    """
    endpoint = os.environ.get("PEOPLE_CONTROLS_AGENT_ENDPOINT", "http://localhost:8084/invocations")
    return _invoke_sub_agent(endpoint, {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": actor_id,
    })


@tool
def invoke_technological_controls_agent(
    prompt: str,
    session_id: str = "",
    actor_id: str = "orchestrator",
) -> dict:
    """
    Invoke the Technological Controls Agent (A.8) to evaluate 34 technology controls.
    Assesses access control, cryptography, network security, secure development, and operations.

    Args:
        prompt: Instructions and context for A.8 control evaluation (include evidence summary and SAST results if available).
        session_id: Session ID for continuity.
        actor_id: Actor performing the action.

    Returns:
        Dict with conformity assessments, findings, and maturity scores for A.8 controls.
    """
    endpoint = os.environ.get("TECH_CONTROLS_AGENT_ENDPOINT", "http://localhost:8085/invocations")
    return _invoke_sub_agent(endpoint, {
        "prompt": prompt,
        "session_id": session_id,
        "actor_id": actor_id,
    })


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR-SPECIFIC TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def verify_findings_consistency(findings_json: str) -> dict:
    """
    Verify consistency across findings from different domain agents.
    Checks for contradictions, duplicate findings, and maturity/conformity alignment.

    Args:
        findings_json: JSON string containing all findings from domain agents.

    Returns:
        Dict with consistency checks, identified issues, and recommendations.
    """
    try:
        findings = json.loads(findings_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON input"}

    issues = []
    controls_seen = {}

    for finding in findings:
        control_id = finding.get("control_id", "")
        conformity = finding.get("conformity_level", "")
        maturity = finding.get("maturity_score", 0)

        # Check maturity/conformity alignment
        if conformity == "conforming" and maturity < 3:
            issues.append({
                "type": "alignment_mismatch",
                "control_id": control_id,
                "issue": f"Conforming but maturity={maturity} (expected ≥3)",
            })
        elif conformity == "major_nonconformity" and maturity > 2:
            issues.append({
                "type": "alignment_mismatch",
                "control_id": control_id,
                "issue": f"Major NC but maturity={maturity} (expected ≤2)",
            })

        # Check for duplicates
        if control_id in controls_seen:
            prev = controls_seen[control_id]
            if prev["conformity_level"] != conformity:
                issues.append({
                    "type": "contradiction",
                    "control_id": control_id,
                    "issue": f"Conflicting assessments: '{prev['conformity_level']}' vs '{conformity}'",
                })
        controls_seen[control_id] = finding

    return {
        "total_findings": len(findings),
        "controls_assessed": len(controls_seen),
        "issues_found": len(issues),
        "issues": issues,
        "is_consistent": len(issues) == 0,
    }


@tool
def generate_executive_summary(
    total_controls: int,
    major_nc: int,
    minor_nc: int,
    opportunities: int,
    conforming: int,
    average_maturity: float,
    critical_domains: list[str] = [],
) -> dict:
    """
    Generate executive summary data for the consolidated audit report.

    Args:
        total_controls: Total number of controls assessed.
        major_nc: Number of major non-conformities.
        minor_nc: Number of minor non-conformities.
        opportunities: Number of opportunities for improvement.
        conforming: Number of conforming controls.
        average_maturity: Overall average maturity score.
        critical_domains: Domains with critical gaps.

    Returns:
        Dict with executive summary statistics and overall assessment.
    """
    # Calculate conformity rate
    conformity_rate = round(conforming / max(total_controls, 1) * 100, 1)

    # Overall verdict
    if major_nc > 5:
        verdict = "CERTIFICATION NOT RECOMMENDED — Significant gaps require systemic remediation"
    elif major_nc > 0:
        verdict = "CONDITIONAL CERTIFICATION — Major non-conformities must be resolved within 90 days"
    elif minor_nc > 10:
        verdict = "CERTIFICATION RECOMMENDED WITH CONDITIONS — Minor non-conformities require corrective action plan"
    else:
        verdict = "CERTIFICATION RECOMMENDED — ISMS demonstrates effective implementation"

    return {
        "summary_stats": {
            "total_controls_assessed": total_controls,
            "conforming": conforming,
            "major_nonconformities": major_nc,
            "minor_nonconformities": minor_nc,
            "opportunities_for_improvement": opportunities,
            "conformity_rate_percent": conformity_rate,
            "average_maturity_score": average_maturity,
        },
        "verdict": verdict,
        "critical_domains": critical_domains,
        "maturity_assessment": (
            "Optimized" if average_maturity >= 4.5
            else "Managed" if average_maturity >= 3.5
            else "Defined" if average_maturity >= 2.5
            else "Repeatable" if average_maturity >= 1.5
            else "Initial"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENTCORE APP
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Consolidation Orchestrator Agent entrypoint."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    session_id = payload.get("session_id", f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    actor_id = payload.get("actor_id", "lead_auditor")

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
        model=load_model(temperature=0.0, max_tokens=8192),
        system_prompt=SYSTEM_PROMPT,
        tools=[
            # Sub-agent invocation tools
            invoke_planning_agent,
            invoke_evidence_agent,
            invoke_organizational_controls_agent,
            invoke_people_controls_agent,
            invoke_technological_controls_agent,
            # Orchestrator tools
            verify_findings_consistency,
            generate_executive_summary,
            # Shared tools
            query_knowledge_base,
            save_audit_finding,
            list_audit_findings,
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
        "agent": "consolidation_agent",
    }


if __name__ == "__main__":
    app.run()
