"""
Physical Controls Agent (A.7) — Evaluates 14 physical and environmental controls.
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
from shared.prompts.physical_controls import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# AGENT-SPECIFIC TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_a7_controls_checklist() -> dict:
    """
    Get the complete A.7 physical controls checklist with evaluation criteria.

    Returns:
        Dict with all 14 A.7 controls and their key evaluation points.
    """
    controls = {
        "A.7.1": {
            "name": "Physical security perimeters",
            "key_criteria": [
                "Security perimeters clearly defined",
                "Walls, barriers, and fences adequate",
                "Perimeter continuously monitored",
                "Entry points limited and controlled",
            ],
            "evidence_types": ["Floor plans", "Perimeter diagrams", "CCTV coverage maps", "Security assessments"],
        },
        "A.7.2": {
            "name": "Physical entry",
            "key_criteria": [
                "Access control mechanisms in place (badges, biometrics)",
                "Visitor management procedures defined",
                "Access logs maintained and reviewed",
                "After-hours access restricted and monitored",
            ],
            "evidence_types": ["Access control logs", "Visitor logs", "Badge system reports", "Entry procedures"],
        },
        "A.7.3": {
            "name": "Securing offices, rooms and facilities",
            "key_criteria": [
                "Sensitive areas identified and classified",
                "Rooms locked when unoccupied",
                "Internal directories not publicly visible",
                "Windows and doors secured appropriately",
            ],
            "evidence_types": ["Room classification records", "Lock audit reports", "Facility security policy"],
        },
        "A.7.4": {
            "name": "Physical security monitoring",
            "key_criteria": [
                "CCTV or equivalent monitoring deployed",
                "Coverage includes critical areas",
                "Recordings retained per policy",
                "Monitoring reviewed regularly",
            ],
            "evidence_types": ["CCTV coverage maps", "Retention policy", "Monitoring review records", "Alarm system logs"],
        },
        "A.7.5": {
            "name": "Protecting against physical and environmental threats",
            "key_criteria": [
                "Risk assessment for natural disasters performed",
                "Fire suppression systems installed and maintained",
                "Environmental controls in data centers",
                "Business continuity for physical threats addressed",
            ],
            "evidence_types": ["Environmental risk assessment", "Fire system inspection reports", "BCP documents", "Insurance policies"],
        },
        "A.7.6": {
            "name": "Working in secure areas",
            "key_criteria": [
                "Rules for working in secure areas defined",
                "Supervised access for visitors/contractors",
                "Unattended secure areas locked",
                "Photography/recording restrictions communicated",
            ],
            "evidence_types": ["Secure area policy", "Visitor escort logs", "Signage photos", "Training records"],
        },
        "A.7.7": {
            "name": "Clear desk and clear screen",
            "key_criteria": [
                "Clear desk policy defined and communicated",
                "Clear screen policy enforced (auto-lock)",
                "Sensitive documents secured when not in use",
                "Compliance checks performed periodically",
            ],
            "evidence_types": ["Clear desk policy", "Screen lock config evidence", "Spot check records", "Awareness materials"],
        },
        "A.7.8": {
            "name": "Equipment siting and protection",
            "key_criteria": [
                "Equipment located to reduce unauthorized access",
                "Protection from environmental hazards",
                "Food and drink policies near equipment",
                "Cable routing to prevent damage",
            ],
            "evidence_types": ["Data center layout plans", "Equipment placement guidelines", "Environmental monitoring logs"],
        },
        "A.7.9": {
            "name": "Security of assets off-premises",
            "key_criteria": [
                "Policy for off-site equipment use",
                "Encryption on portable devices",
                "Transport security procedures",
                "Insurance or risk coverage for off-site assets",
            ],
            "evidence_types": ["Off-premises asset policy", "Encryption verification reports", "Asset register (off-site)"],
        },
        "A.7.10": {
            "name": "Storage media",
            "key_criteria": [
                "Media handling procedures (classification-based)",
                "Secure disposal methods defined",
                "Media tracking and inventory maintained",
                "Secure transport of media",
            ],
            "evidence_types": ["Media handling policy", "Media inventory", "Disposal certificates", "Transport logs"],
        },
        "A.7.11": {
            "name": "Supporting utilities",
            "key_criteria": [
                "UPS/backup power for critical systems",
                "Power supply redundancy",
                "HVAC and water supply maintained",
                "Utility failure procedures documented",
            ],
            "evidence_types": ["UPS test reports", "Generator maintenance logs", "HVAC monitoring records", "Utility BCP"],
        },
        "A.7.12": {
            "name": "Cabling security",
            "key_criteria": [
                "Power and telecom cables protected",
                "Cables routed to avoid interception",
                "Network cables separated from power cables",
                "Cable access points secured",
            ],
            "evidence_types": ["Cabling diagrams", "Physical inspection reports", "Data center design standards"],
        },
        "A.7.13": {
            "name": "Equipment maintenance",
            "key_criteria": [
                "Maintenance schedule defined and followed",
                "Only authorized personnel perform maintenance",
                "Maintenance logs maintained",
                "Data sanitized before external maintenance",
            ],
            "evidence_types": ["Maintenance schedules", "Service contracts", "Maintenance logs", "Data sanitization records"],
        },
        "A.7.14": {
            "name": "Secure disposal or re-use of equipment",
            "key_criteria": [
                "Secure disposal procedures for end-of-life equipment",
                "Data wiping verified before disposal or re-use",
                "Certificates of destruction obtained",
                "Third-party disposal providers assessed",
            ],
            "evidence_types": ["Disposal policy", "Certificates of destruction", "Data wiping verification reports", "Vendor assessments"],
        },
    }
    return {"domain": "A.7", "total_controls": 14, "controls": controls}


@tool
def assess_physical_site_security(
    site_description: str,
    has_data_center: bool = False,
    is_shared_facility: bool = False,
) -> dict:
    """
    Assess physical site security posture for controls A.7.1–A.7.6.
    Provides a structured framework for evaluating site-level physical security.

    Args:
        site_description: Description of the physical site(s) in scope.
        has_data_center: Whether the site contains a data center or server room.
        is_shared_facility: Whether the organization operates in a multi-tenant building.

    Returns:
        Dict with assessment framework and risk factors.
    """
    risk_factors = []
    if is_shared_facility:
        risk_factors.append("Multi-tenant facility increases perimeter control complexity")
        risk_factors.append("Shared access points require additional visitor controls")
    if has_data_center:
        risk_factors.append("Data center requires enhanced environmental controls")
        risk_factors.append("24/7 monitoring required for critical infrastructure")

    assessment_areas = [
        {"area": "Perimeter Security (A.7.1)", "critical": True, "key_question": "Are physical boundaries clearly defined and enforced?"},
        {"area": "Entry Controls (A.7.2)", "critical": True, "key_question": "Are all entry points controlled with authentication and logging?"},
        {"area": "Room Security (A.7.3)", "critical": has_data_center, "key_question": "Are sensitive rooms classified and secured?"},
        {"area": "Monitoring (A.7.4)", "critical": True, "key_question": "Is physical monitoring continuous and recordings retained?"},
        {"area": "Environmental Protection (A.7.5)", "critical": has_data_center, "key_question": "Are fire, flood, and environmental risks mitigated?"},
        {"area": "Secure Area Rules (A.7.6)", "critical": has_data_center, "key_question": "Are rules for working in secure areas enforced?"},
    ]

    return {
        "site_description": site_description,
        "has_data_center": has_data_center,
        "is_shared_facility": is_shared_facility,
        "risk_factors": risk_factors,
        "assessment_areas": assessment_areas,
        "instruction": (
            "Use the site description, risk factors, and RAG knowledge base to evaluate "
            "each assessment area. Consider the shared facility and data center context "
            "when determining maturity and conformity levels."
        ),
    }


@tool
def evaluate_environmental_controls(
    fire_suppression_type: str = "unknown",
    ups_capacity_minutes: int = 0,
    hvac_monitored: bool = False,
    generator_available: bool = False,
) -> dict:
    """
    Evaluate environmental protection controls for A.7.5 and A.7.11.

    Args:
        fire_suppression_type: Type of fire suppression ('gas', 'water', 'foam', 'none', 'unknown').
        ups_capacity_minutes: UPS backup duration in minutes (0 if unknown/none).
        hvac_monitored: Whether HVAC is monitored with alerting.
        generator_available: Whether backup generator is available.

    Returns:
        Dict with environmental maturity assessment.
    """
    # Fire suppression maturity
    fire_maturity = {
        "gas": 5,        # Gas-based (FM-200, Novec) — best for data centers
        "water": 3,      # Sprinkler — adequate but risky for equipment
        "foam": 4,       # Foam — good compromise
        "none": 0,       # No suppression
        "unknown": 1,    # Not assessed
    }.get(fire_suppression_type, 1)

    # Power resilience maturity
    if ups_capacity_minutes >= 30 and generator_available:
        power_maturity = 5
    elif ups_capacity_minutes >= 15 and generator_available:
        power_maturity = 4
    elif ups_capacity_minutes >= 10:
        power_maturity = 3
    elif ups_capacity_minutes > 0:
        power_maturity = 2
    else:
        power_maturity = 0

    # HVAC maturity
    hvac_maturity = 4 if hvac_monitored else 2

    overall_maturity = round((fire_maturity + power_maturity + hvac_maturity) / 3, 1)

    gaps = []
    if fire_suppression_type in ("none", "unknown"):
        gaps.append("Fire suppression not implemented or not assessed")
    if ups_capacity_minutes == 0:
        gaps.append("No UPS backup power available")
    if not generator_available:
        gaps.append("No backup generator for extended outages")
    if not hvac_monitored:
        gaps.append("HVAC not monitored — risk of undetected environmental degradation")

    return {
        "controls_assessed": ["A.7.5", "A.7.11"],
        "fire_suppression_type": fire_suppression_type,
        "fire_maturity": fire_maturity,
        "ups_capacity_minutes": ups_capacity_minutes,
        "power_maturity": power_maturity,
        "hvac_monitored": hvac_monitored,
        "hvac_maturity": hvac_maturity,
        "generator_available": generator_available,
        "overall_maturity": overall_maturity,
        "gaps_identified": gaps,
        "recommendation": (
            "Data centers should target gas-based fire suppression, 30+ min UPS with "
            "generator failover, and 24/7 HVAC monitoring with alerting."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENTCORE APP
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Physical Controls Agent entrypoint."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    session_id = payload.get("session_id", f"physical_{datetime.now().strftime('%Y%m%d%H%M%S')}")
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
            get_a7_controls_checklist,
            assess_physical_site_security,
            evaluate_environmental_controls,
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
        "agent": "physical_controls_agent",
    }


if __name__ == "__main__":
    app.run()
