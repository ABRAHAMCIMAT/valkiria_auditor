"""
CrewAI — Multi-Agent ISO 27001 Audit Orchestrator.

Uses the role-based crew pattern with:
- Agents defined by role, goal, and backstory
- Tasks with explicit expected_output and context chaining
- Sequential process for ordered execution
- Hierarchical process alternative with manager delegation

Flow:
1. Planning Agent → Task: Generate audit plan
2. Evidence Agent → Task: Collect evidence (context: audit plan)
3. Org Controls Agent → Task: Evaluate A.5 (context: evidence)
4. People Controls Agent → Task: Evaluate A.6 (context: evidence)
5. Physical Controls Agent → Task: Evaluate A.7 (context: evidence)
6. Tech Controls Agent → Task: Evaluate A.8 (context: evidence)
7. Consolidation Agent → Task: Generate final report (context: all evaluations)

Framework: crewai==1.2.0
Model: Configurable via LiteLLM model strings (Bedrock)
"""

import os
from typing import Optional

from crewai import Agent, Crew, Task, Process
from crewai.llm import LLM

from backend.observability.flow_tracker import FlowTracker


# ─────────────────────────────────────────────────────────────────────────────
# MODEL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

REGION = os.environ.get("AWS_REGION", "us-east-1")
PRIMARY_MODEL_ID = os.environ.get("PRIMARY_MODEL_ID", "openai.gpt-oss-120b-1:0")
FAST_MODEL_ID = os.environ.get("FAST_MODEL_ID", "qwen.qwen3-32b-v1:0")


def _get_llm(model_id: str = None, temperature: float = 0.2) -> LLM:
    """Get a CrewAI-compatible LLM via Bedrock."""
    mid = model_id or PRIMARY_MODEL_ID
    return LLM(
        model=f"bedrock/{mid}",
        temperature=temperature,
        max_tokens=4096,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AGENT DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

def _create_agents() -> dict[str, Agent]:
    """Create all specialized agents for the ISO 27001 audit crew."""

    planning_agent = Agent(
        role="ISO 27001 Audit Planner",
        goal="Generate comprehensive audit plans following ISO 19011:2018 methodology",
        backstory=(
            "You are a senior audit planning specialist with 15+ years of experience "
            "in ISMS implementations and certifications. You specialize in risk-based "
            "audit planning for ISO 27001:2022, determining scope, criteria, and schedules."
        ),
        llm=_get_llm(PRIMARY_MODEL_ID, temperature=0.2),
        verbose=False,
        allow_delegation=False,
    )

    evidence_agent = Agent(
        role="ISO 27001 Evidence Collector",
        goal="Retrieve and assess documentary evidence from the knowledge base for audit evaluation",
        backstory=(
            "You are an experienced audit evidence specialist. You systematically "
            "collect policies, procedures, records, and logs relevant to each control. "
            "You assess evidence sufficiency and flag gaps that require additional collection."
        ),
        llm=_get_llm(FAST_MODEL_ID, temperature=0.1),
        verbose=False,
        allow_delegation=False,
    )

    org_controls_agent = Agent(
        role="Organizational Controls Auditor (A.5)",
        goal="Evaluate 37 organizational controls for conformity and assign maturity scores",
        backstory=(
            "You are a specialist in ISO 27001:2022 organizational controls (A.5). "
            "You evaluate policies, roles, supplier management, incident response, "
            "and compliance controls with rigorous evidence-based methodology."
        ),
        llm=_get_llm(PRIMARY_MODEL_ID, temperature=0.0),
        verbose=False,
        allow_delegation=False,
    )

    people_controls_agent = Agent(
        role="People Controls Auditor (A.6)",
        goal="Evaluate 8 people-related controls for conformity and assess HR security practices",
        backstory=(
            "You specialize in A.6 controls: screening, employment terms, security awareness "
            "training effectiveness, remote working security, and incident reporting culture. "
            "You understand both technical and human factors in information security."
        ),
        llm=_get_llm(FAST_MODEL_ID, temperature=0.0),
        verbose=False,
        allow_delegation=False,
    )

    tech_controls_agent = Agent(
        role="Technological Controls Auditor (A.8)",
        goal="Evaluate 34 technological controls covering access, crypto, networks, and secure development",
        backstory=(
            "You are a senior technical security auditor with expertise in A.8 controls. "
            "You evaluate endpoint security, vulnerability management, network architecture, "
            "cryptography, SDLC security, and change management with hands-on technical depth."
        ),
        llm=_get_llm(PRIMARY_MODEL_ID, temperature=0.0),
        verbose=False,
        allow_delegation=False,
    )

    physical_controls_agent = Agent(
        role="Physical Controls Auditor (A.7)",
        goal="Evaluate 14 physical and environmental controls covering perimeters, entry, monitoring, and equipment security",
        backstory=(
            "You are a specialist in ISO 27001:2022 physical controls (A.7). "
            "You evaluate physical security perimeters, entry controls, CCTV monitoring, "
            "environmental protections, clear desk/screen policies, equipment siting, "
            "and secure disposal with practical site security expertise."
        ),
        llm=_get_llm(PRIMARY_MODEL_ID, temperature=0.0),
        verbose=False,
        allow_delegation=False,
    )

    consolidation_agent = Agent(
        role="Lead Auditor and Report Consolidator",
        goal="Verify consistency across domains and produce the final consolidated audit report",
        backstory=(
            "You are the lead auditor responsible for the final quality of the audit report. "
            "You cross-reference findings across domains, identify systemic issues, "
            "verify maturity/conformity alignment, and produce the executive summary "
            "with certification recommendation."
        ),
        llm=_get_llm(PRIMARY_MODEL_ID, temperature=0.0),
        verbose=False,
        allow_delegation=False,
    )

    return {
        "planning": planning_agent,
        "evidence": evidence_agent,
        "org_controls": org_controls_agent,
        "people_controls": people_controls_agent,
        "physical_controls": physical_controls_agent,
        "tech_controls": tech_controls_agent,
        "consolidation": consolidation_agent,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TASK DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

def _create_tasks(agents: dict[str, Agent], organization_context: str, audit_type: str) -> list[Task]:
    """Create the sequential task chain for the audit crew."""

    planning_task = Task(
        description=(
            f"Generate an ISO 27001:2022 {audit_type} audit plan for:\n"
            f"{organization_context}\n\n"
            f"Include: scope definition, audit objectives, criteria (standards and policies), "
            f"phased schedule, team roles, and list of Annex A controls in scope (A.5, A.6, A.7, A.8)."
        ),
        expected_output=(
            "A structured audit plan document with sections: "
            "Scope, Objectives, Criteria, Schedule (phased), Team, Controls in Scope."
        ),
        agent=agents["planning"],
    )

    evidence_task = Task(
        description=(
            "Based on the audit plan, collect documentary evidence for all controls in scope. "
            "For each control domain (A.5, A.6, A.7, A.8), identify available evidence and assess sufficiency. "
            "Flag controls where evidence is missing or outdated."
        ),
        expected_output=(
            "Evidence collection report organized by domain (A.5, A.6, A.7, A.8) with: "
            "evidence items found, sufficiency assessment (sufficient/insufficient), "
            "and gaps requiring additional collection."
        ),
        agent=agents["evidence"],
        context=[planning_task],
    )

    org_controls_task = Task(
        description=(
            "Evaluate all 37 Organizational Controls (A.5.1–A.5.37) based on the collected evidence. "
            "For each control determine: conformity level (conforming/minor NC/major NC/opportunity/N-A), "
            "maturity score (CMM 0-5), gaps identified, and structured finding if non-conforming."
        ),
        expected_output=(
            "Domain report for A.5 with: per-control assessment table, "
            "summary statistics (conforming count, NC count), average maturity, "
            "and detailed findings with recommendations."
        ),
        agent=agents["org_controls"],
        context=[evidence_task],
    )

    people_controls_task = Task(
        description=(
            "Evaluate all 8 People Controls (A.6.1–A.6.8) based on the collected evidence. "
            "Assess screening, training effectiveness, remote working, and event reporting. "
            "For each control: conformity level, maturity score, gaps, and findings."
        ),
        expected_output=(
            "Domain report for A.6 with: per-control assessment, "
            "training effectiveness evaluation, and findings with recommendations."
        ),
        agent=agents["people_controls"],
        context=[evidence_task],
    )

    tech_controls_task = Task(
        description=(
            "Evaluate all 34 Technological Controls (A.8.1–A.8.34) based on collected evidence. "
            "Cover access control, vulnerability management, cryptography, network security, "
            "and secure development. For each: conformity level, maturity score, gaps, findings."
        ),
        expected_output=(
            "Domain report for A.8 with: per-control assessment, "
            "SAST/vulnerability correlation, and findings with technical recommendations."
        ),
        agent=agents["tech_controls"],
        context=[evidence_task],
    )

    physical_controls_task = Task(
        description=(
            "Evaluate all 14 Physical Controls (A.7.1–A.7.14) based on collected evidence. "
            "Cover physical security perimeters, entry controls, monitoring, environmental protection, "
            "clear desk/screen, equipment siting, and secure disposal. "
            "For each: conformity level, maturity score, gaps, findings."
        ),
        expected_output=(
            "Domain report for A.7 with: per-control assessment, "
            "site security evaluation, and findings with physical security recommendations."
        ),
        agent=agents["physical_controls"],
        context=[evidence_task],
    )

    consolidation_task = Task(
        description=(
            "Consolidate all domain reports (A.5, A.6, A.7, A.8) into the final audit report. "
            "Verify consistency (no contradicting findings), identify systemic issues, "
            "compute overall maturity score, and produce executive summary with "
            "certification recommendation (recommended/conditional/not recommended)."
        ),
        expected_output=(
            "Final consolidated audit report with:\n"
            "1. Executive Summary (max 500 words) with verdict\n"
            "2. Scope and methodology\n"
            "3. Per-domain summaries\n"
            "4. All findings sorted by severity\n"
            "5. Systemic issues identified\n"
            "6. Overall maturity score (0-5)\n"
            "7. Prioritized recommendations\n"
            "8. Certification recommendation with conditions\n"
            "9. Next steps and timeline"
        ),
        agent=agents["consolidation"],
        context=[org_controls_task, people_controls_task, physical_controls_task, tech_controls_task],
    )

    return [
        planning_task,
        evidence_task,
        org_controls_task,
        people_controls_task,
        physical_controls_task,
        tech_controls_task,
        consolidation_task,
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CREW ASSEMBLY & EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def build_audit_crew(
    organization_context: str,
    audit_type: str = "internal",
) -> Crew:
    """
    Build the CrewAI crew for the ISO 27001 audit.

    Args:
        organization_context: Description of the organization to audit.
        audit_type: 'internal', 'certification', or 'surveillance'.

    Returns:
        Configured Crew ready for kickoff.
    """
    agents = _create_agents()
    tasks = _create_tasks(agents, organization_context, audit_type)

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
        memory=False,  # Disable for deterministic audit outputs
    )

    return crew


def run_audit(
    organization_context: str,
    audit_type: str = "internal",
    audit_id: str = "",
    session_id: str = "",
    actor_id: str = "lead_auditor",
) -> dict:
    """
    Execute a complete ISO 27001:2022 audit using CrewAI orchestration.

    Args:
        organization_context: Description of the organization to audit.
        audit_type: 'internal', 'certification', or 'surveillance'.
        audit_id: Unique audit identifier.
        session_id: Session identifier for tracing.
        actor_id: The auditor performing the evaluation.

    Returns:
        Dict with audit report and observability metrics.
    """
    # Initialize observability
    tracker = FlowTracker(audit_id=audit_id, session_id=session_id, actor_id=actor_id)

    # Build crew
    crew = build_audit_crew(organization_context, audit_type)

    # Execute
    with tracker.node("crew_execution", agent_name="crewai_orchestrator", model_id=PRIMARY_MODEL_ID) as node:
        result = crew.kickoff()
        node.set_result(
            input_tokens=int(result.token_usage.total_tokens * 0.4) if hasattr(result, "token_usage") else 0,
            output_tokens=int(result.token_usage.total_tokens * 0.6) if hasattr(result, "token_usage") else 0,
            tool_calls=7,
        )

    flow_summary = tracker.finalize()

    # Persist report to S3
    from backend.observability.s3_store import S3MetricsStore
    s3_store = S3MetricsStore()
    s3_store.save_audit_report(audit_id, "crewai", str(result), flow_summary)

    return {
        "framework": "crewai",
        "version": "1.2.0",
        "audit_id": audit_id,
        "report": str(result),
        "flow_metrics": flow_summary,
        "mermaid_diagram": tracker.mermaid_diagram(),
    }


if __name__ == "__main__":
    result = run_audit(
        organization_context="ACME Corp, a technology company with 200 employees handling financial data.",
        audit_type="internal",
        audit_id="crewai_audit_001",
        session_id="crewai_session_001",
    )
    print(result["report"][:2000])
