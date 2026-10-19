"""
LangGraph — Multi-Agent ISO 27001 Audit Orchestrator.

Uses a StateGraph with typed state, conditional edges, and parallel fan-out
for domain evaluators. Each node is a function that invokes a specialized
Bedrock model with domain-specific prompting.

Flow (as a graph):
    START → planning → evidence → fan_out_evaluators → consolidation → END
                                       │
                              ┌─────────┼──────────────────┐
                              ▼         ▼         ▼        ▼
                         org_eval  people_eval phys_eval tech_eval
                              │         │         │        │
                              └─────────┼──────────────────┘
                                        ▼
                                  consolidation

Framework: langgraph==0.4.7 + langchain-aws==0.2.17
Model: Configurable (default: GPT OSS 120B via Bedrock)
"""

import os
import operator
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage, SystemMessage

from backend.observability.flow_tracker import FlowTracker


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

REGION = os.environ.get("AWS_REGION", "us-east-1")
PRIMARY_MODEL_ID = os.environ.get("PRIMARY_MODEL_ID", "openai.gpt-oss-120b-1:0")
FAST_MODEL_ID = os.environ.get("FAST_MODEL_ID", "qwen.qwen3-32b-v1:0")


def _get_llm(model_id: str = None, temperature: float = 0.2) -> ChatBedrock:
    """Get a configured ChatBedrock model."""
    return ChatBedrock(
        model_id=model_id or PRIMARY_MODEL_ID,
        region_name=REGION,
        model_kwargs={"temperature": temperature, "max_tokens": 4096},
    )


# ─────────────────────────────────────────────────────────────────────────────
# STATE DEFINITION
# ─────────────────────────────────────────────────────────────────────────────

class AuditState(TypedDict):
    """Typed state that flows through the audit graph."""
    # Input
    organization_context: str
    audit_type: str
    audit_id: str
    session_id: str
    actor_id: str

    # Intermediate results (appended by each node)
    audit_plan: str
    evidence_report: str
    org_controls_report: str
    people_controls_report: str
    physical_controls_report: str
    tech_controls_report: str

    # Final output
    consolidated_report: str
    executive_summary: str
    success: bool


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH NODES
# ─────────────────────────────────────────────────────────────────────────────

def planning_node(state: AuditState) -> dict:
    """Node: Generate audit plan."""
    llm = _get_llm(PRIMARY_MODEL_ID, temperature=0.2)
    messages = [
        SystemMessage(content=(
            "You are an ISO 27001:2022 audit planning specialist. "
            "Generate a structured audit plan following ISO 19011:2018. "
            "Include: scope, objectives, criteria, schedule, team roles, controls in scope."
        )),
        HumanMessage(content=(
            f"Generate an audit plan for:\n{state['organization_context']}\n"
            f"Audit type: {state['audit_type']}\n"
            f"Include all applicable Annex A controls (A.5, A.6, A.7, A.8)."
        )),
    ]
    response = llm.invoke(messages)
    return {"audit_plan": response.content}


def evidence_node(state: AuditState) -> dict:
    """Node: Collect evidence for in-scope controls."""
    llm = _get_llm(FAST_MODEL_ID, temperature=0.1)
    messages = [
        SystemMessage(content=(
            "You are an ISO 27001:2022 evidence collection specialist. "
            "Retrieve and organize evidence for controls based on the audit plan. "
            "Assess sufficiency and identify gaps per control domain."
        )),
        HumanMessage(content=(
            f"Based on this audit plan:\n{state['audit_plan'][:2000]}\n\n"
            f"Collect evidence for controls A.5, A.6, A.7, and A.8. "
            f"Organization: {state['organization_context']}"
        )),
    ]
    response = llm.invoke(messages)
    return {"evidence_report": response.content}


def org_controls_node(state: AuditState) -> dict:
    """Node: Evaluate A.5 Organizational Controls."""
    llm = _get_llm(PRIMARY_MODEL_ID, temperature=0.0)
    messages = [
        SystemMessage(content=(
            "You are an ISO 27001:2022 auditor for Organizational Controls (A.5). "
            "Evaluate the 37 controls for conformity. Assign maturity scores (CMM 0-5). "
            "Generate findings for non-conformities with root cause and recommendations."
        )),
        HumanMessage(content=(
            f"Evaluate A.5 controls with this evidence:\n{state['evidence_report'][:3000]}\n\n"
            f"Provide: conformity_level, maturity_score, gaps, findings per control."
        )),
    ]
    response = llm.invoke(messages)
    return {"org_controls_report": response.content}


def people_controls_node(state: AuditState) -> dict:
    """Node: Evaluate A.6 People Controls."""
    llm = _get_llm(FAST_MODEL_ID, temperature=0.0)
    messages = [
        SystemMessage(content=(
            "You are an ISO 27001:2022 auditor for People Controls (A.6). "
            "Evaluate the 8 controls: screening, training, remote working, event reporting. "
            "Assess conformity and assign maturity scores."
        )),
        HumanMessage(content=(
            f"Evaluate A.6 controls with this evidence:\n{state['evidence_report'][:2000]}\n\n"
            f"Provide: conformity_level, maturity_score, gaps, findings per control."
        )),
    ]
    response = llm.invoke(messages)
    return {"people_controls_report": response.content}


def physical_controls_node(state: AuditState) -> dict:
    """Node: Evaluate A.7 Physical Controls."""
    llm = _get_llm(PRIMARY_MODEL_ID, temperature=0.0)
    messages = [
        SystemMessage(content=(
            "You are an ISO 27001:2022 auditor for Physical Controls (A.7). "
            "Evaluate the 14 controls: perimeters, entry, monitoring, environmental, "
            "equipment security, clear desk, and secure disposal."
        )),
        HumanMessage(content=(
            f"Evaluate A.7 controls with this evidence:\n{state['evidence_report'][:3000]}\n\n"
            f"Provide: conformity_level, maturity_score, gaps, findings per control."
        )),
    ]
    response = llm.invoke(messages)
    return {"physical_controls_report": response.content}


def tech_controls_node(state: AuditState) -> dict:
    """Node: Evaluate A.8 Technological Controls."""
    llm = _get_llm(PRIMARY_MODEL_ID, temperature=0.0)
    messages = [
        SystemMessage(content=(
            "You are an ISO 27001:2022 auditor for Technological Controls (A.8). "
            "Evaluate the 34 controls: access, crypto, network, secure development. "
            "Consider SAST findings and vulnerability management data."
        )),
        HumanMessage(content=(
            f"Evaluate A.8 controls with this evidence:\n{state['evidence_report'][:3000]}\n\n"
            f"Provide: conformity_level, maturity_score, gaps, findings per control."
        )),
    ]
    response = llm.invoke(messages)
    return {"tech_controls_report": response.content}


def consolidation_node(state: AuditState) -> dict:
    """Node: Consolidate all domain reports into final audit report."""
    llm = _get_llm(PRIMARY_MODEL_ID, temperature=0.0)
    messages = [
        SystemMessage(content=(
            "You are the lead ISO 27001:2022 auditor producing the final consolidated report. "
            "Verify consistency across domains, identify systemic issues, "
            "and generate an executive summary with certification recommendation."
        )),
        HumanMessage(content=(
            f"Consolidate these domain reports into a final audit report:\n\n"
            f"AUDIT PLAN:\n{state['audit_plan'][:1000]}\n\n"
            f"ORGANIZATIONAL CONTROLS (A.5):\n{state['org_controls_report'][:2000]}\n\n"
            f"PEOPLE CONTROLS (A.6):\n{state['people_controls_report'][:1500]}\n\n"
            f"PHYSICAL CONTROLS (A.7):\n{state['physical_controls_report'][:1500]}\n\n"
            f"TECHNOLOGICAL CONTROLS (A.8):\n{state['tech_controls_report'][:2000]}\n\n"
            f"Produce: executive summary, consolidated findings (by severity), "
            f"overall maturity score, certification recommendation, and next steps."
        )),
    ]
    response = llm.invoke(messages)
    return {
        "consolidated_report": response.content,
        "executive_summary": response.content[:500],
        "success": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH CONSTRUCTION
# ─────────────────────────────────────────────────────────────────────────────

def build_audit_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for the ISO 27001 audit flow.

    Graph structure:
        START → planning → evidence → [org_eval, people_eval, physical_eval, tech_eval] → consolidation → END

    The four domain evaluation nodes run as a parallel fan-out from evidence,
    then fan-in to consolidation.
    """
    graph = StateGraph(AuditState)

    # Add nodes
    graph.add_node("planning", planning_node)
    graph.add_node("evidence", evidence_node)
    graph.add_node("org_controls", org_controls_node)
    graph.add_node("people_controls", people_controls_node)
    graph.add_node("physical_controls", physical_controls_node)
    graph.add_node("tech_controls", tech_controls_node)
    graph.add_node("consolidation", consolidation_node)

    # Sequential: START → planning → evidence
    graph.add_edge(START, "planning")
    graph.add_edge("planning", "evidence")

    # Fan-out: evidence → [org, people, physical, tech] (parallel)
    graph.add_edge("evidence", "org_controls")
    graph.add_edge("evidence", "people_controls")
    graph.add_edge("evidence", "physical_controls")
    graph.add_edge("evidence", "tech_controls")

    # Fan-in: [org, people, physical, tech] → consolidation
    graph.add_edge("org_controls", "consolidation")
    graph.add_edge("people_controls", "consolidation")
    graph.add_edge("physical_controls", "consolidation")
    graph.add_edge("tech_controls", "consolidation")

    # End
    graph.add_edge("consolidation", END)

    return graph


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def run_audit(
    organization_context: str,
    audit_type: str = "internal",
    audit_id: str = "",
    session_id: str = "",
    actor_id: str = "lead_auditor",
) -> dict:
    """
    Execute a complete ISO 27001:2022 audit using LangGraph orchestration.

    Args:
        organization_context: Description of the organization to audit.
        audit_type: 'internal', 'certification', or 'surveillance'.
        audit_id: Unique audit identifier.
        session_id: Session identifier for tracing.
        actor_id: The auditor performing the evaluation.

    Returns:
        Dict with audit report and observability metrics.
    """
    # Build and compile graph
    graph = build_audit_graph()
    app = graph.compile()

    # Initialize observability
    tracker = FlowTracker(audit_id=audit_id, session_id=session_id, actor_id=actor_id)

    # Prepare initial state
    initial_state: AuditState = {
        "organization_context": organization_context,
        "audit_type": audit_type,
        "audit_id": audit_id,
        "session_id": session_id,
        "actor_id": actor_id,
        "audit_plan": "",
        "evidence_report": "",
        "org_controls_report": "",
        "people_controls_report": "",
        "physical_controls_report": "",
        "tech_controls_report": "",
        "consolidated_report": "",
        "executive_summary": "",
        "success": False,
    }

    # Execute the graph
    with tracker.node("full_graph", agent_name="langgraph_orchestrator", model_id=PRIMARY_MODEL_ID) as node:
        final_state = app.invoke(initial_state)
        node.set_result(
            input_tokens=0,
            output_tokens=0,
            tool_calls=7,  # 7 nodes executed
        )

    flow_summary = tracker.finalize()

    # Persist report to S3
    from backend.observability.s3_store import S3MetricsStore
    s3_store = S3MetricsStore()
    s3_store.save_audit_report(audit_id, "langgraph", final_state.get("consolidated_report", ""), flow_summary)

    return {
        "framework": "langgraph",
        "version": "0.4.7",
        "audit_id": audit_id,
        "report": final_state.get("consolidated_report", ""),
        "executive_summary": final_state.get("executive_summary", ""),
        "success": final_state.get("success", False),
        "flow_metrics": flow_summary,
        "mermaid_diagram": tracker.mermaid_diagram(),
    }


if __name__ == "__main__":
    result = run_audit(
        organization_context="ACME Corp, a technology company with 200 employees handling financial data.",
        audit_type="internal",
        audit_id="langgraph_audit_001",
        session_id="langgraph_session_001",
    )
    print(result["report"][:2000])
