"""
Pydantic models for structured agent outputs.
Defines the data contracts between agents and the orchestrator.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConformityLevel(str, Enum):
    """ISO 27001 conformity assessment levels."""
    CONFORMING = "conforming"
    MINOR_NC = "minor_nonconformity"
    MAJOR_NC = "major_nonconformity"
    OPPORTUNITY = "opportunity_for_improvement"
    NOT_APPLICABLE = "not_applicable"


class RiskLevel(str, Enum):
    """Risk severity levels for findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ControlDomain(str, Enum):
    """ISO 27001:2022 Annex A control domains."""
    ORGANIZATIONAL = "A.5"
    PEOPLE = "A.6"
    PHYSICAL = "A.7"
    TECHNOLOGICAL = "A.8"


class AuditFinding(BaseModel):
    """A single audit finding (non-conformity or observation)."""
    finding_id: str = Field(description="Unique finding identifier (e.g., NC-001)")
    control_id: str = Field(description="ISO 27001:2022 control reference (e.g., A.5.1)")
    control_name: str = Field(description="Control name in Spanish")
    conformity_level: ConformityLevel
    risk_level: RiskLevel
    description: str = Field(description="Detailed finding description")
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence references")
    root_cause: Optional[str] = Field(default=None, description="Root cause analysis")
    recommendation: str = Field(description="Corrective action recommendation")
    remediation_timeline: Optional[str] = Field(default=None, description="Suggested remediation timeline")
    rag_sources: list[str] = Field(default_factory=list, description="RAG source URIs used")


class ControlAssessment(BaseModel):
    """Assessment result for a single ISO 27001 control."""
    control_id: str
    control_name: str
    domain: ControlDomain
    conformity_level: ConformityLevel
    maturity_score: float = Field(ge=0, le=5, description="CMM maturity level (0-5)")
    evidence_reviewed: list[str] = Field(default_factory=list)
    gaps_identified: list[str] = Field(default_factory=list)
    findings: list[AuditFinding] = Field(default_factory=list)


class AuditPlan(BaseModel):
    """Structured audit plan output from the planning agent."""
    audit_id: str
    organization_name: str
    scope: str = Field(description="Audit scope definition")
    objectives: list[str] = Field(description="Audit objectives")
    criteria: list[str] = Field(description="Audit criteria (standards, policies)")
    schedule: list[dict] = Field(description="Audit schedule (phases, dates, activities)")
    team_roles: list[dict] = Field(description="Audit team composition and roles")
    controls_in_scope: list[str] = Field(description="List of control IDs to evaluate")
    methodology: str = Field(default="ISO 19011:2018")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EvidencePackage(BaseModel):
    """Evidence collection result from the evidence agent."""
    control_id: str
    evidence_items: list[dict] = Field(description="Retrieved evidence documents")
    rag_query_used: str = Field(description="RAG query that retrieved this evidence")
    relevance_score: float = Field(ge=0, le=1)
    source_documents: list[str] = Field(description="Source document URIs")
    gaps: list[str] = Field(default_factory=list, description="Missing evidence identified")


class DomainReport(BaseModel):
    """Report from a domain-specific control evaluation agent."""
    domain: ControlDomain
    domain_name: str
    total_controls: int
    controls_assessed: list[ControlAssessment]
    summary_findings: list[AuditFinding]
    conformity_stats: dict = Field(description="Counts by conformity level")
    average_maturity: float = Field(ge=0, le=5)
    critical_gaps: list[str] = Field(default_factory=list)


class ConsolidatedAuditReport(BaseModel):
    """Final consolidated audit report from the orchestrator."""
    audit_id: str
    organization_name: str
    audit_date: datetime = Field(default_factory=datetime.utcnow)
    auditor_id: str
    scope: str
    methodology: str
    executive_summary: str
    domain_reports: list[DomainReport]
    all_findings: list[AuditFinding]
    total_nonconformities: int
    major_nonconformities: int
    minor_nonconformities: int
    opportunities_for_improvement: int
    overall_maturity_score: float = Field(ge=0, le=5)
    recommendations_priority: list[dict] = Field(description="Prioritized recommendations")
    conclusion: str
    next_steps: list[str]
