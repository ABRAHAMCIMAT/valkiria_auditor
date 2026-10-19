"""
Technological Controls Agent (A.8) — Evaluates 34 technological controls.
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
from shared.tools.s3_tools import get_document_content, save_report_to_s3
from shared.prompts.technological_controls import SYSTEM_PROMPT


# ─────────────────────────────────────────────────────────────────────────────
# AGENT-SPECIFIC TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def get_a8_controls_checklist() -> dict:
    """
    Get the complete A.8 technological controls checklist with evaluation criteria.

    Returns:
        Dict with all 34 A.8 controls and their key evaluation points.
    """
    controls = {
        "A.8.1": {"name": "User endpoint devices", "key_criteria": ["Device management policy", "MDM/UEM deployed", "Encryption at rest", "Remote wipe capability"]},
        "A.8.2": {"name": "Privileged access rights", "key_criteria": ["PAM solution", "Privileged accounts inventoried", "Session recording", "Just-in-time access"]},
        "A.8.3": {"name": "Information access restriction", "key_criteria": ["RBAC implemented", "Data access policies", "Application-level controls"]},
        "A.8.4": {"name": "Access to source code", "key_criteria": ["Repository access controls", "Branch protection", "Code review requirements"]},
        "A.8.5": {"name": "Secure authentication", "key_criteria": ["MFA enforced", "Password complexity", "Account lockout", "SSO where applicable"]},
        "A.8.6": {"name": "Capacity management", "key_criteria": ["Monitoring active", "Thresholds defined", "Forecasting performed", "Auto-scaling where possible"]},
        "A.8.7": {"name": "Protection against malware", "key_criteria": ["AV/EDR deployed", "Signatures updated", "Real-time protection", "Behavioral analysis"]},
        "A.8.8": {"name": "Management of technical vulnerabilities", "key_criteria": ["Vulnerability scanning", "Patch management SLAs", "Risk-based prioritization", "Remediation tracking"]},
        "A.8.9": {"name": "Configuration management", "key_criteria": ["Baselines defined (CIS/NIST)", "Drift detection", "Change control", "Hardening applied"]},
        "A.8.10": {"name": "Information deletion", "key_criteria": ["Deletion policy", "Secure deletion methods", "Verification performed"]},
        "A.8.11": {"name": "Data masking", "key_criteria": ["Masking rules defined", "Applied in non-prod", "PII protection"]},
        "A.8.12": {"name": "Data leakage prevention", "key_criteria": ["DLP tools deployed", "Policies configured", "Monitoring active", "Incident response"]},
        "A.8.13": {"name": "Information backup", "key_criteria": ["Backup policy (3-2-1)", "Regular testing", "Encryption of backups", "Offsite storage"]},
        "A.8.14": {"name": "Redundancy of processing facilities", "key_criteria": ["HA architecture", "Failover tested", "RTO/RPO defined"]},
        "A.8.15": {"name": "Logging", "key_criteria": ["Centralized logging", "Retention policy", "Integrity protection", "Coverage sufficient"]},
        "A.8.16": {"name": "Monitoring activities", "key_criteria": ["SIEM deployed", "Alerts configured", "24/7 monitoring or SOC", "Incident correlation"]},
        "A.8.17": {"name": "Clock synchronization", "key_criteria": ["NTP configured", "All systems synchronized", "Accuracy verified"]},
        "A.8.18": {"name": "Use of privileged utility programs", "key_criteria": ["Utilities restricted", "Usage logged", "Authorization required"]},
        "A.8.19": {"name": "Installation of software", "key_criteria": ["Whitelist/approval process", "Admin rights restricted", "Software inventory"]},
        "A.8.20": {"name": "Networks security", "key_criteria": ["Network architecture documented", "Firewall rules", "IDS/IPS deployed"]},
        "A.8.21": {"name": "Security of network services", "key_criteria": ["SLAs defined", "Security requirements in contracts", "Monitoring"]},
        "A.8.22": {"name": "Segregation of networks", "key_criteria": ["VLANs/subnets", "DMZ configured", "Microsegmentation"]},
        "A.8.23": {"name": "Web filtering", "key_criteria": ["URL filtering", "Category blocking", "SSL inspection where appropriate"]},
        "A.8.24": {"name": "Use of cryptography", "key_criteria": ["Encryption standards", "Key management", "TLS 1.2+ enforced", "Certificate management"]},
        "A.8.25": {"name": "Secure development life cycle", "key_criteria": ["SSDLC defined", "Security requirements in sprints", "Threat modeling"]},
        "A.8.26": {"name": "Application security requirements", "key_criteria": ["Security requirements gathered", "OWASP Top 10 addressed", "Input validation"]},
        "A.8.27": {"name": "Secure system architecture", "key_criteria": ["Security architecture documented", "Defense in depth", "Zero trust principles"]},
        "A.8.28": {"name": "Secure coding", "key_criteria": ["Coding standards", "SAST integrated", "Developer training", "Code review"]},
        "A.8.29": {"name": "Security testing in development", "key_criteria": ["SAST/DAST/SCA", "Penetration testing", "Acceptance criteria"]},
        "A.8.30": {"name": "Outsourced development", "key_criteria": ["Security requirements in contracts", "Code ownership", "Testing requirements"]},
        "A.8.31": {"name": "Separation of environments", "key_criteria": ["Dev/test/prod separated", "Access controls per environment", "Data sanitization"]},
        "A.8.32": {"name": "Change management", "key_criteria": ["Change process documented", "CAB/approval workflow", "Rollback procedures", "Testing before deployment"]},
        "A.8.33": {"name": "Test information", "key_criteria": ["Test data sanitized", "No production data in test", "Data generation tools"]},
        "A.8.34": {"name": "Protection during audit testing", "key_criteria": ["Audit access controlled", "Minimal impact on operations", "Audit tools secured"]},
    }
    return {"domain": "A.8", "total_controls": 34, "controls": controls}


@tool
def analyze_sast_findings(
    sast_report_s3_key: str,
) -> dict:
    """
    Analyze SAST (Static Application Security Testing) findings for controls A.8.25–A.8.34.
    Retrieves SAST report from S3 and categorizes findings by severity and control mapping.

    Args:
        sast_report_s3_key: S3 key of the SAST findings report (JSON format).

    Returns:
        Dict with categorized findings, severity distribution, and control mappings.
    """
    import json
    import boto3

    bucket = os.environ.get("BUCKET_NAME", "")
    if not bucket:
        return {"error": "BUCKET_NAME not configured"}

    s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))

    try:
        response = s3.get_object(Bucket=bucket, Key=sast_report_s3_key)
        report = json.loads(response["Body"].read().decode("utf-8"))
    except Exception as exc:
        return {"error": f"Failed to retrieve SAST report: {exc}"}

    # Map SAST finding categories to ISO 27001 controls
    category_to_control = {
        "injection": "A.8.26",
        "authentication": "A.8.5",
        "cryptography": "A.8.24",
        "configuration": "A.8.9",
        "access_control": "A.8.3",
        "input_validation": "A.8.26",
        "error_handling": "A.8.28",
        "logging": "A.8.15",
        "data_exposure": "A.8.12",
        "dependency": "A.8.8",
    }

    findings = report.get("findings", [])
    severity_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    control_findings = {}

    for finding in findings:
        severity = finding.get("severity", "medium").lower()
        severity_dist[severity] = severity_dist.get(severity, 0) + 1

        category = finding.get("category", "").lower()
        mapped_control = category_to_control.get(category, "A.8.28")  # Default to secure coding

        if mapped_control not in control_findings:
            control_findings[mapped_control] = []
        control_findings[mapped_control].append({
            "title": finding.get("title", ""),
            "severity": severity,
            "file": finding.get("file", ""),
        })

    return {
        "total_findings": len(findings),
        "severity_distribution": severity_dist,
        "control_mappings": control_findings,
        "controls_affected": list(control_findings.keys()),
        "recommendation": (
            "Critical and high severity findings directly impact conformity assessment "
            "for the mapped controls."
        ),
    }


@tool
def evaluate_vulnerability_management(
    scan_frequency: str = "unknown",
    patch_sla_days: int = 0,
    open_vulnerabilities: int = 0,
    critical_open: int = 0,
) -> dict:
    """
    Evaluate vulnerability management maturity for control A.8.8.

    Args:
        scan_frequency: How often vulnerability scans run ('weekly', 'monthly', 'quarterly', 'unknown').
        patch_sla_days: Days allowed for patching (0 if not defined).
        open_vulnerabilities: Total open vulnerabilities count.
        critical_open: Number of critical open vulnerabilities.

    Returns:
        Dict with maturity assessment and conformity recommendation.
    """
    maturity_indicators = {
        "scanning": {
            "weekly": 4,
            "monthly": 3,
            "quarterly": 2,
            "unknown": 0,
        },
        "patching": {
            "sla_defined": patch_sla_days > 0,
            "sla_days": patch_sla_days,
            "industry_benchmark": 30,  # 30 days for critical
        },
    }

    scan_maturity = maturity_indicators["scanning"].get(scan_frequency, 1)

    # Patching maturity
    if patch_sla_days == 0:
        patch_maturity = 0
    elif patch_sla_days <= 14:
        patch_maturity = 5
    elif patch_sla_days <= 30:
        patch_maturity = 4
    elif patch_sla_days <= 60:
        patch_maturity = 3
    else:
        patch_maturity = 2

    # Risk assessment
    if critical_open > 10:
        risk = "critical"
        conformity = "major_nonconformity"
    elif critical_open > 0:
        risk = "high"
        conformity = "minor_nonconformity"
    elif open_vulnerabilities > 50:
        risk = "medium"
        conformity = "minor_nonconformity"
    else:
        risk = "low"
        conformity = "conforming"

    overall_maturity = round((scan_maturity + patch_maturity) / 2, 1)

    return {
        "control_id": "A.8.8",
        "scan_frequency": scan_frequency,
        "scan_maturity": scan_maturity,
        "patch_sla_days": patch_sla_days,
        "patch_maturity": patch_maturity,
        "open_vulnerabilities": open_vulnerabilities,
        "critical_open": critical_open,
        "overall_maturity": overall_maturity,
        "risk_level": risk,
        "suggested_conformity": conformity,
    }


# ─────────────────────────────────────────────────────────────────────────────
# AGENTCORE APP
# ─────────────────────────────────────────────────────────────────────────────

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """Technological Controls Agent entrypoint."""
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    session_id = payload.get("session_id", f"tech_{datetime.now().strftime('%Y%m%d%H%M%S')}")
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
            get_a8_controls_checklist,
            analyze_sast_findings,
            evaluate_vulnerability_management,
            get_document_content,
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
        "agent": "technological_controls_agent",
    }


if __name__ == "__main__":
    app.run()
