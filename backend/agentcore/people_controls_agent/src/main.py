"""
People Controls Agent (A.6) — Evaluates 8 people-related controls.
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
from shared.prompts.people_controls import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# AGENT-SPECIFIC TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_a6_controls_checklist() -> dict:
    """
    Get the complete A.6 people controls checklist with evaluation criteria.

    Returns:
        Dict with all 8 A.6 controls and their key evaluation points.
    """
    controls = {
        "A.6.1": {
            "name": "Screening",
            "key_criteria": [
                "Background checks performed",
                "Proportional to role sensitivity",
                "References verified",
                "Qualifications confirmed",
                "Process documented and consistent",
            ],
            "evidence_types": ["HR procedures", "Screening records", "Background check reports"],
        },
        "A.6.2": {
            "name": "Terms and conditions of employment",
            "key_criteria": [
                "Security responsibilities in contracts",
                "Acceptable use acknowledged",
                "Confidentiality obligations stated",
                "Post-employment obligations included",
            ],
            "evidence_types": ["Employment contracts", "Onboarding checklists", "Signed acknowledgments"],
        },
        "A.6.3": {
            "name": "Information security awareness, education and training",
            "key_criteria": [
                "Awareness program exists and is active",
                "Role-based training for security personnel",
                "Training records maintained",
                "Effectiveness measured",
                "Regular updates on new threats",
                "Phishing simulation results",
            ],
            "evidence_types": ["Training materials", "Attendance records", "Quiz/test results", "Awareness campaign evidence"],
        },
        "A.6.4": {
            "name": "Disciplinary process",
            "key_criteria": [
                "Formal process documented",
                "Known to all personnel",
                "Proportionate sanctions defined",
                "Applied consistently",
                "Evidence of enforcement when needed",
            ],
            "evidence_types": ["Disciplinary policy", "HR records", "Communication evidence"],
        },
        "A.6.5": {
            "name": "Responsibilities after termination or change of employment",
            "key_criteria": [
                "Exit procedures documented",
                "Asset return checklist",
                "Access revocation within defined SLA",
                "Post-employment obligations communicated",
                "Knowledge transfer process",
            ],
            "evidence_types": ["Offboarding checklists", "Access revocation logs", "Exit interview records"],
        },
        "A.6.6": {
            "name": "Confidentiality or non-disclosure agreements",
            "key_criteria": [
                "NDA requirements identified",
                "Templates current and legally reviewed",
                "Applied to employees and contractors",
                "Third-party NDAs in place",
                "Regular review of obligations",
            ],
            "evidence_types": ["NDA templates", "Signed agreements", "Legal review records"],
        },
        "A.6.7": {
            "name": "Remote working",
            "key_criteria": [
                "Remote working policy exists",
                "Security measures defined (VPN, encryption)",
                "Physical security of remote location addressed",
                "Communication security ensured",
                "Equipment security managed",
                "Monitoring capability maintained",
            ],
            "evidence_types": ["Remote work policy", "VPN config evidence", "Endpoint protection records"],
        },
        "A.6.8": {
            "name": "Information security event reporting",
            "key_criteria": [
                "Reporting mechanism accessible",
                "Personnel aware of obligations",
                "No-blame culture encouraged",
                "Timely reporting monitored",
                "Process tested periodically",
            ],
            "evidence_types": ["Reporting procedures", "Incident logs", "Awareness communications"],
        },
    }
    return {"domain": "A.6", "total_controls": 8, "controls": controls}


@tool
def assess_training_effectiveness(
    training_records_summary: str,
    personnel_count: int = 0,
) -> dict:
    """
    Assess the effectiveness of the security awareness training program (A.6.3).

    Args:
        training_records_summary: Summary of available training records and results.
        personnel_count: Total number of personnel in scope (0 if unknown).

    Returns:
        Dict with effectiveness assessment and identified gaps.
    """
    effectiveness_criteria = [
        {"criterion": "Coverage", "description": "Percentage of personnel who completed training"},
        {"criterion": "Frequency", "description": "Training conducted at least annually"},
        {"criterion": "Relevance", "description": "Content updated for current threats"},
        {"criterion": "Measurement", "description": "Knowledge assessment (quiz/test) performed"},
        {"criterion": "Behavioral Change", "description": "Measurable improvement (e.g., phishing click rates)"},
    ]

    return {
        "control_id": "A.6.3",
        "assessment_framework": effectiveness_criteria,
        "training_data_provided": bool(training_records_summary),
        "personnel_count": personnel_count,
        "instruction": (
            "Use the training records and RAG knowledge base to evaluate "
            "each effectiveness criterion. Provide a maturity score (0-5) "
            "and identify specific gaps."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENTCORE APP
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """People Controls Agent entrypoint."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    session_id = payload.get("session_id", f"people_{datetime.now().strftime('%Y%m%d%H%M%S')}")
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
        model=load_model(temperature=0.0),
        system_prompt=SYSTEM_PROMPT,
        tools=[
            query_knowledge_base,
            retrieve_control_evidence,
            get_a6_controls_checklist,
            assess_training_effectiveness,
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
        "agent": "people_controls_agent",
    }


if __name__ == "__main__":
    app.run()
