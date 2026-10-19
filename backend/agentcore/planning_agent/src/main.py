"""
Planning Agent — Generates ISO 27001:2022 audit plans.
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
from shared.tools.s3_tools import save_report_to_s3
from shared.prompts.planning import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# AGENT-SPECIFIC TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_iso27001_controls_list(domain: str = "all") -> dict:
    """
    Get the list of ISO 27001:2022 Annex A controls for planning purposes.

    Args:
        domain: Control domain to retrieve - 'A.5', 'A.6', 'A.7', 'A.8', or 'all'.

    Returns:
        Dict with control IDs and names per domain.
    """
    controls = {
        "A.5": {
            "name": "Organizational Controls",
            "count": 37,
            "range": "A.5.1 – A.5.37",
            "description": "Policies, roles, responsibilities, supplier management, incident response",
        },
        "A.6": {
            "name": "People Controls",
            "count": 8,
            "range": "A.6.1 – A.6.8",
            "description": "Screening, employment terms, awareness, remote working",
        },
        "A.7": {
            "name": "Physical Controls",
            "count": 14,
            "range": "A.7.1 – A.7.14",
            "description": "Physical perimeters, entry controls, equipment security",
        },
        "A.8": {
            "name": "Technological Controls",
            "count": 34,
            "range": "A.8.1 – A.8.34",
            "description": "Access control, cryptography, network security, secure development",
        },
    }

    if domain == "all":
        return {
            "total_controls": 93,
            "domains": controls,
        }
    elif domain in controls:
        return {"domain": domain, **controls[domain]}
    else:
        return {"error": f"Unknown domain: {domain}. Use 'A.5', 'A.6', 'A.7', 'A.8', or 'all'."}


@tool
def generate_audit_schedule(
    organization_size: str,
    controls_in_scope: list[str],
    audit_type: str = "internal",
) -> dict:
    """
    Generate a suggested audit schedule based on organization size and scope.

    Args:
        organization_size: One of 'small' (<50 employees), 'medium' (50-500), 'large' (>500).
        controls_in_scope: List of control domain IDs in scope (e.g., ['A.5', 'A.6', 'A.8']).
        audit_type: 'internal', 'certification', or 'surveillance'.

    Returns:
        Dict with proposed schedule phases and estimated durations.
    """
    # Base durations by org size (days)
    base_durations = {
        "small": {"planning": 1, "per_domain": 1, "consolidation": 1},
        "medium": {"planning": 2, "per_domain": 2, "consolidation": 2},
        "large": {"planning": 3, "per_domain": 3, "consolidation": 3},
    }

    duration = base_durations.get(organization_size, base_durations["medium"])
    total_domain_days = duration["per_domain"] * len(controls_in_scope)

    schedule = [
        {
            "phase": "Phase 1 — Planning & Preparation",
            "duration_days": duration["planning"],
            "activities": [
                "Define scope and objectives",
                "Review previous audit findings",
                "Prepare audit checklist",
                "Request documentary evidence",
            ],
        },
        {
            "phase": "Phase 2 — Evidence Collection",
            "duration_days": duration["planning"],
            "activities": [
                "Collect policies and procedures",
                "Retrieve system configurations and logs",
                "Gather training and awareness records",
                "Review risk assessment documentation",
            ],
        },
        {
            "phase": "Phase 3 — Domain Assessment",
            "duration_days": total_domain_days,
            "activities": [
                f"Evaluate {d} controls" for d in controls_in_scope
            ],
        },
        {
            "phase": "Phase 4 — Consolidation & Reporting",
            "duration_days": duration["consolidation"],
            "activities": [
                "Cross-reference findings",
                "Verify consistency",
                "Generate consolidated report",
                "Prepare management presentation",
            ],
        },
    ]

    total_days = (
        duration["planning"] * 2 + total_domain_days + duration["consolidation"]
    )

    return {
        "audit_type": audit_type,
        "organization_size": organization_size,
        "controls_in_scope": controls_in_scope,
        "total_estimated_days": total_days,
        "schedule": schedule,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENTCORE APP
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Planning Agent entrypoint."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    session_id = payload.get("session_id", f"plan_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    actor_id = payload.get("actor_id", "system")

    # Configure memory if available
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

    # Create agent with tools
    agent = Agent(
        model=load_model(temperature=0.2),
        system_prompt=SYSTEM_PROMPT,
        tools=[
            query_knowledge_base,
            retrieve_control_evidence,
            get_iso27001_controls_list,
            generate_audit_schedule,
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
        "agent": "planning_agent",
    }


if __name__ == "__main__":
    app.run()
