"""
Organizational Controls Agent (A.5) — Evaluates 37 organizational controls.
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
from shared.tools.dynamodb_tools import save_audit_finding
from shared.tools.s3_tools import save_report_to_s3
from shared.prompts.organizational_controls import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# AGENT-SPECIFIC TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def evaluate_control(
    control_id: str,
    control_name: str,
    evidence_summary: str,
    organization_context: str = "",
) -> dict:
    """
    Evaluate a single organizational control based on evidence.
    Produces a conformity assessment with maturity scoring.

    Args:
        control_id: ISO 27001:2022 control ID (e.g., 'A.5.1').
        control_name: Human-readable control name.
        evidence_summary: Summary of evidence available for this control.
        organization_context: Additional context about the organization.

    Returns:
        Dict with conformity_level, maturity_score, gaps, and finding if applicable.
    """
    # This tool provides structure — the LLM reasoning handles the actual assessment
    return {
        "control_id": control_id,
        "control_name": control_name,
        "evidence_provided": bool(evidence_summary),
        "instruction": (
            "Based on the evidence summary, determine:\n"
            "1. conformity_level: conforming|minor_nonconformity|major_nonconformity|opportunity_for_improvement|not_applicable\n"
            "2. maturity_score: 0-5 (CMM scale)\n"
            "3. gaps_identified: list of specific gaps\n"
            "4. finding: structured finding if non-conforming\n"
            "Use the evidence_summary and RAG tools to make your assessment."
        ),
    }


@tool
def get_a5_controls_checklist() -> dict:
    """
    Get the complete A.5 organizational controls checklist with evaluation criteria.

    Returns:
        Dict with all 37 A.5 controls and their key evaluation points.
    """
    controls = {
        "A.5.1": {"name": "Policies for information security", "key_criteria": ["Policy exists", "Approved by management", "Communicated to personnel", "Reviewed periodically"]},
        "A.5.2": {"name": "Information security roles and responsibilities", "key_criteria": ["Roles defined", "Responsibilities documented", "Communicated", "Adequate resources"]},
        "A.5.3": {"name": "Segregation of duties", "key_criteria": ["Conflicting duties identified", "Separation implemented", "Compensating controls where separation not possible"]},
        "A.5.4": {"name": "Management responsibilities", "key_criteria": ["Management commitment documented", "Security in business processes", "Adequate resources allocated"]},
        "A.5.5": {"name": "Contact with authorities", "key_criteria": ["Relevant authorities identified", "Contact procedures defined", "Reporting obligations known"]},
        "A.5.6": {"name": "Contact with special interest groups", "key_criteria": ["Relevant groups identified", "Participation documented", "Knowledge sharing active"]},
        "A.5.7": {"name": "Threat intelligence", "key_criteria": ["Sources identified", "Collection process defined", "Analysis performed", "Actions taken"]},
        "A.5.8": {"name": "Information security in project management", "key_criteria": ["Security integrated in PM methodology", "Risk assessment per project", "Security requirements defined"]},
        "A.5.9": {"name": "Inventory of information and associated assets", "key_criteria": ["Inventory complete", "Owners assigned", "Classification applied", "Regular review"]},
        "A.5.10": {"name": "Acceptable use of information and assets", "key_criteria": ["Policy defined", "Acknowledged by users", "Covers all asset types", "Enforcement mechanism"]},
        "A.5.11": {"name": "Return of assets", "key_criteria": ["Process defined", "Applied at termination", "Records maintained"]},
        "A.5.12": {"name": "Classification of information", "key_criteria": ["Scheme defined", "Applied consistently", "Includes handling rules"]},
        "A.5.13": {"name": "Labelling of information", "key_criteria": ["Labelling procedures", "Aligned with classification", "Digital and physical"]},
        "A.5.14": {"name": "Information transfer", "key_criteria": ["Transfer policies", "Secure methods defined", "Agreements in place"]},
        "A.5.15": {"name": "Access control", "key_criteria": ["Access policy", "Business requirements basis", "Need-to-know principle"]},
        "A.5.16": {"name": "Identity management", "key_criteria": ["Unique IDs", "Lifecycle management", "Identity verification"]},
        "A.5.17": {"name": "Authentication information", "key_criteria": ["Password policy", "MFA where appropriate", "Secure distribution"]},
        "A.5.18": {"name": "Access rights", "key_criteria": ["Provisioning process", "Review cycle", "Revocation on change/termination"]},
        "A.5.19": {"name": "Information security in supplier relationships", "key_criteria": ["Risk assessment", "Security requirements defined", "Agreements include security"]},
        "A.5.20": {"name": "Addressing security in supplier agreements", "key_criteria": ["Security clauses", "Right to audit", "Incident notification"]},
        "A.5.21": {"name": "Managing security in ICT supply chain", "key_criteria": ["Supply chain risks identified", "Propagation of requirements", "Monitoring"]},
        "A.5.22": {"name": "Monitoring and review of supplier services", "key_criteria": ["Regular reviews", "Performance against SLAs", "Change management"]},
        "A.5.23": {"name": "Information security for cloud services", "key_criteria": ["Cloud security policy", "Shared responsibility clear", "Exit strategy"]},
        "A.5.24": {"name": "Incident management planning", "key_criteria": ["Response plan", "Roles defined", "Communication plan", "Testing performed"]},
        "A.5.25": {"name": "Assessment of security events", "key_criteria": ["Classification criteria", "Triage process", "Escalation paths"]},
        "A.5.26": {"name": "Response to incidents", "key_criteria": ["Response procedures", "Containment actions", "Eradication steps"]},
        "A.5.27": {"name": "Learning from incidents", "key_criteria": ["Post-incident reviews", "Lessons documented", "Improvements implemented"]},
        "A.5.28": {"name": "Collection of evidence", "key_criteria": ["Procedures defined", "Chain of custody", "Forensic readiness"]},
        "A.5.29": {"name": "Security during disruption", "key_criteria": ["Continuity plans", "Security maintained during disruption"]},
        "A.5.30": {"name": "ICT readiness for business continuity", "key_criteria": ["BIA performed", "Recovery objectives defined", "Testing conducted"]},
        "A.5.31": {"name": "Legal, statutory requirements", "key_criteria": ["Requirements identified", "Compliance approach defined", "Regular review"]},
        "A.5.32": {"name": "Intellectual property rights", "key_criteria": ["IPR policy", "License management", "Open source governance"]},
        "A.5.33": {"name": "Protection of records", "key_criteria": ["Retention schedule", "Protection measures", "Disposal procedures"]},
        "A.5.34": {"name": "Privacy and PII protection", "key_criteria": ["Privacy policy", "DPA compliance", "Data subject rights"]},
        "A.5.35": {"name": "Independent review", "key_criteria": ["Scheduled reviews", "Independent reviewers", "Findings actioned"]},
        "A.5.36": {"name": "Compliance with policies", "key_criteria": ["Compliance checks", "Technical verification", "Management reporting"]},
        "A.5.37": {"name": "Documented operating procedures", "key_criteria": ["Procedures documented", "Current versions", "Accessible to personnel"]},
    }
    return {"domain": "A.5", "total_controls": 37, "controls": controls}


# ─────────────────────────────────────────────────────────────────────────────
# AGENTCORE APP
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Organizational Controls Agent entrypoint."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    session_id = payload.get("session_id", f"org_{datetime.now().strftime('%Y%m%d%H%M%S')}")
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
        model=load_model(temperature=0.0),  # Deterministic for audit assessments
        system_prompt=SYSTEM_PROMPT,
        tools=[
            query_knowledge_base,
            retrieve_control_evidence,
            evaluate_control,
            get_a5_controls_checklist,
            save_audit_finding,
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
        "agent": "organizational_controls_agent",
    }


if __name__ == "__main__":
    app.run()
