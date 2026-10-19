"""
Strands Agents — Multi-Agent ISO 27001 Audit Orchestrator.

Uses the "Agents as Tools" pattern where specialized sub-agents are wrapped
as @tool functions and invoked by a central orchestrator agent.

Flow:
1. planning_agent → Generates audit plan (scope, schedule, controls)
2. evidence_agent → Collects evidence for in-scope controls via RAG
3. organizational_controls_agent → Evaluates A.5 controls (parallel)
4. people_controls_agent → Evaluates A.6 controls (parallel)
5. physical_controls_agent → Evaluates A.7 controls (parallel)
6. technological_controls_agent → Evaluates A.8 controls (parallel)
7. Orchestrator consolidates → Verifies consistency, generates report

Framework: strands-agents==1.20.0
Model: Configurable via backend.models.registry (default: GPT OSS 120B)
"""

import os

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

from backend.observability.collector import ObservabilityCollector
from backend.observability.flow_tracker import FlowTracker
from backend.agentcore.shared.memory import (
    create_consolidation_memory,
    create_planning_memory,
    create_evidence_memory,
    create_domain_agent_memory,
)


# ─────────────────────────────────────────────────────────────────────────────
# MODEL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

REGION = os.environ.get("AWS_REGION", "us-east-1")
PRIMARY_MODEL_ID = os.environ.get("PRIMARY_MODEL_ID", "openai.gpt-oss-120b-1:0")
FAST_MODEL_ID = os.environ.get("FAST_MODEL_ID", "qwen.qwen3-32b-v1:0")


def _get_model(model_id: str = None, temperature: float = 0.2) -> BedrockModel:
    """Get a configured Bedrock model."""
    return BedrockModel(
        model_id=model_id or PRIMARY_MODEL_ID,
        region_name=REGION,
        temperature=temperature,
        max_tokens=4096,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SUB-AGENT DEFINITIONS (wrapped as tools)
# ─────────────────────────────────────────────────────────────────────────────

PLANNING_PROMPT = """You are an ISO 27001:2022 audit planning specialist.
Generate a structured audit plan with: scope, objectives, criteria, schedule, team roles, and controls in scope.
Follow ISO 19011:2018 methodology. Output structured JSON."""

EVIDENCE_PROMPT = """You are an ISO 27001:2022 evidence collection specialist.
Retrieve and organize documentary evidence for the specified controls using the knowledge base.
Assess evidence sufficiency and identify gaps. Output structured findings per control."""

ORG_CONTROLS_PROMPT = """You are an ISO 27001:2022 auditor for Organizational Controls (A.5).
Evaluate each specified A.5 control for conformity based on the provided evidence.
Assign maturity scores (0-5 CMM scale) and generate findings for non-conformities."""

PEOPLE_CONTROLS_PROMPT = """You are an ISO 27001:2022 auditor for People Controls (A.6).
Evaluate each specified A.6 control for conformity based on the provided evidence.
Assess screening, training effectiveness, remote working controls, and event reporting."""

TECH_CONTROLS_PROMPT = """You are an ISO 27001:2022 auditor for Technological Controls (A.8).
Evaluate each specified A.8 control for conformity based on the provided evidence.
Assess access control, vulnerability management, secure development, and network security."""

PHYSICAL_CONTROLS_PROMPT = """You are an ISO 27001:2022 auditor for Physical Controls (A.7).
Evaluate each specified A.7 control for conformity based on the provided evidence.
Assess physical security perimeters, entry controls, environmental protection, equipment security,
clear desk/screen policies, and secure disposal of equipment."""

ORCHESTRATOR_PROMPT = """You are the lead ISO 27001:2022 audit orchestrator.
Coordinate the audit by invoking sub-agents in sequence:
1. Call plan_audit to generate the audit plan
2. Call collect_evidence for controls in scope
3. Call evaluate_organizational_controls, evaluate_people_controls, evaluate_physical_controls, and evaluate_technological_controls
4. Verify consistency across all domain results
5. Generate a consolidated final audit report with executive summary

Always invoke all steps. The final report must include:
- Executive summary with verdict
- Per-domain findings
- Prioritized recommendations
- Overall maturity score"""


# ─────────────────────────────────────────────────────────────────────────────
# SUB-AGENT TOOL FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def plan_audit(organization_context: str, audit_type: str = "internal") -> str:
    """
    Generate an ISO 27001:2022 audit plan for the given organization.

    Args:
        organization_context: Description of the organization (size, sector, scope).
        audit_type: Type of audit - 'internal', 'certification', or 'surveillance'.

    Returns:
        Structured audit plan with scope, schedule, criteria, and controls in scope.
    """
    memory = create_planning_memory(session_id="planning_sub", actor_id="orchestrator")
    planning_agent = Agent(
        model=_get_model(PRIMARY_MODEL_ID, temperature=0.2),
        system_prompt=PLANNING_PROMPT,
        session_manager=memory,
    )
    result = planning_agent(
        f"Generate an audit plan for: {organization_context}. Audit type: {audit_type}. "
        f"Include all applicable Annex A controls (A.5, A.6, A.7, A.8)."
    )
    return str(result)


@tool
def collect_evidence(controls_in_scope: str, organization_context: str = "") -> str:
    """
    Collect documentary evidence for the specified controls via RAG knowledge base.

    Args:
        controls_in_scope: Comma-separated list of control IDs or domains (e.g., 'A.5,A.6,A.7,A.8').
        organization_context: Additional context about the organization.

    Returns:
        Evidence collection report with sufficiency assessment per control domain.
    """
    evidence_agent = Agent(
        model=_get_model(FAST_MODEL_ID, temperature=0.1),
        system_prompt=EVIDENCE_PROMPT,
    )
    result = evidence_agent(
        f"Collect evidence for controls: {controls_in_scope}. "
        f"Organization: {organization_context}. "
        f"Assess sufficiency and identify gaps."
    )
    return str(result)


@tool
def evaluate_organizational_controls(evidence_summary: str, controls: str = "A.5.1-A.5.37") -> str:
    """
    Evaluate ISO 27001:2022 Organizational Controls (A.5) based on collected evidence.

    Args:
        evidence_summary: Summary of evidence available for A.5 controls.
        controls: Control range to evaluate (default: all 37 A.5 controls).

    Returns:
        Domain report with conformity assessments, maturity scores, and findings.
    """
    org_agent = Agent(
        model=_get_model(PRIMARY_MODEL_ID, temperature=0.0),
        system_prompt=ORG_CONTROLS_PROMPT,
    )
    result = org_agent(
        f"Evaluate organizational controls ({controls}) with this evidence:\n{evidence_summary}\n"
        f"For each control provide: conformity_level, maturity_score, gaps, and findings."
    )
    return str(result)


@tool
def evaluate_people_controls(evidence_summary: str, controls: str = "A.6.1-A.6.8") -> str:
    """
    Evaluate ISO 27001:2022 People Controls (A.6) based on collected evidence.

    Args:
        evidence_summary: Summary of evidence available for A.6 controls.
        controls: Control range to evaluate (default: all 8 A.6 controls).

    Returns:
        Domain report with conformity assessments, maturity scores, and findings.
    """
    people_agent = Agent(
        model=_get_model(FAST_MODEL_ID, temperature=0.0),
        system_prompt=PEOPLE_CONTROLS_PROMPT,
    )
    result = people_agent(
        f"Evaluate people controls ({controls}) with this evidence:\n{evidence_summary}\n"
        f"For each control provide: conformity_level, maturity_score, gaps, and findings."
    )
    return str(result)


@tool
def evaluate_physical_controls(evidence_summary: str, controls: str = "A.7.1-A.7.14") -> str:
    """
    Evaluate ISO 27001:2022 Physical Controls (A.7) based on collected evidence.

    Args:
        evidence_summary: Summary of evidence available for A.7 controls.
        controls: Control range to evaluate (default: all 14 A.7 controls).

    Returns:
        Domain report with conformity assessments, maturity scores, and findings.
    """
    physical_agent = Agent(
        model=_get_model(PRIMARY_MODEL_ID, temperature=0.0),
        system_prompt=PHYSICAL_CONTROLS_PROMPT,
    )
    result = physical_agent(
        f"Evaluate physical controls ({controls}) with this evidence:\n{evidence_summary}\n"
        f"For each control provide: conformity_level, maturity_score, gaps, and findings."
    )
    return str(result)


@tool
def evaluate_technological_controls(evidence_summary: str, controls: str = "A.8.1-A.8.34") -> str:
    """
    Evaluate ISO 27001:2022 Technological Controls (A.8) based on collected evidence.

    Args:
        evidence_summary: Summary of evidence available for A.8 controls.
        controls: Control range to evaluate (default: all 34 A.8 controls).

    Returns:
        Domain report with conformity assessments, maturity scores, and findings.
    """
    tech_agent = Agent(
        model=_get_model(PRIMARY_MODEL_ID, temperature=0.0),
        system_prompt=TECH_CONTROLS_PROMPT,
    )
    result = tech_agent(
        f"Evaluate technological controls ({controls}) with this evidence:\n{evidence_summary}\n"
        f"For each control provide: conformity_level, maturity_score, gaps, and findings."
    )
    return str(result)


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

def run_audit(
    organization_context: str,
    audit_type: str = "internal",
    audit_id: str = "",
    session_id: str = "",
    actor_id: str = "lead_auditor",
) -> dict:
    """
    Execute a complete ISO 27001:2022 audit using Strands Agents orchestration.

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

    # Create memory session for orchestrator
    memory_session = create_consolidation_memory(session_id=session_id, actor_id=actor_id)

    # Create orchestrator agent with sub-agents as tools
    orchestrator = Agent(
        model=_get_model(PRIMARY_MODEL_ID, temperature=0.0),
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=[
            plan_audit,
            collect_evidence,
            evaluate_organizational_controls,
            evaluate_people_controls,
            evaluate_physical_controls,
            evaluate_technological_controls,
        ],
        session_manager=memory_session,
    )

    # Execute the orchestration
    prompt = (
        f"Perform a complete ISO 27001:2022 {audit_type} audit for:\n"
        f"{organization_context}\n\n"
        f"Execute all steps in order and produce the consolidated report."
    )

    with tracker.node("orchestration", agent_name="consolidation_agent", model_id=PRIMARY_MODEL_ID) as node:
        result = orchestrator(prompt)
        node.set_result(
            input_tokens=0,  # Strands handles internally
            output_tokens=0,
            tool_calls=6,
        )

    flow_summary = tracker.finalize()

    # Persist report to S3
    from backend.observability.s3_store import S3MetricsStore
    s3_store = S3MetricsStore()
    s3_store.save_audit_report(audit_id, "strands-agents", str(result), flow_summary)

    return {
        "framework": "strands-agents",
        "version": "1.20.0",
        "audit_id": audit_id,
        "report": str(result),
        "flow_metrics": flow_summary,
        "mermaid_diagram": tracker.mermaid_diagram(),
    }


if __name__ == "__main__":
    result = run_audit(
        organization_context="ACME Corp, a technology company with 200 employees handling financial data.",
        audit_type="internal",
        audit_id="strands_audit_001",
        session_id="strands_session_001",
    )
    print(result["report"][:2000])
