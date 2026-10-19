"""
Unit tests for individual agent logic (checklists, evaluation tools, prompts).
"""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestOrganizationalControlsAgent:
    """Tests for the A.5 Organizational Controls Agent."""

    def test_get_a5_controls_checklist_returns_37_controls(self):
        """Checklist tool returns exactly 37 A.5 controls."""
        from backend.agentcore.organizational_controls_agent.src.main import get_a5_controls_checklist
        result = get_a5_controls_checklist._tool_func()

        assert result["domain"] == "A.5"
        assert result["total_controls"] == 37
        assert len(result["controls"]) == 37
        assert "A.5.1" in result["controls"]
        assert "A.5.37" in result["controls"]

    def test_a5_controls_have_required_fields(self):
        """Each control has name and key_criteria."""
        from backend.agentcore.organizational_controls_agent.src.main import get_a5_controls_checklist
        result = get_a5_controls_checklist._tool_func()

        for control_id, control in result["controls"].items():
            assert "name" in control, f"Missing 'name' in {control_id}"
            assert "key_criteria" in control, f"Missing 'key_criteria' in {control_id}"
            assert len(control["key_criteria"]) > 0, f"Empty criteria in {control_id}"

    def test_evaluate_control_tool_structure(self):
        """evaluate_control returns proper instruction structure."""
        from backend.agentcore.organizational_controls_agent.src.main import evaluate_control
        result = evaluate_control._tool_func(
            control_id="A.5.1",
            control_name="Policies for information security",
            evidence_summary="Policy exists but not reviewed in 2 years.",
        )

        assert result["control_id"] == "A.5.1"
        assert result["evidence_provided"] is True
        assert "instruction" in result


class TestPeopleControlsAgent:
    """Tests for the A.6 People Controls Agent."""

    def test_get_a6_controls_checklist_returns_8_controls(self):
        """Checklist tool returns exactly 8 A.6 controls."""
        from backend.agentcore.people_controls_agent.src.main import get_a6_controls_checklist
        result = get_a6_controls_checklist._tool_func()

        assert result["domain"] == "A.6"
        assert result["total_controls"] == 8
        assert len(result["controls"]) == 8
        assert "A.6.1" in result["controls"]
        assert "A.6.8" in result["controls"]

    def test_a6_controls_have_evidence_types(self):
        """Each A.6 control includes expected evidence types."""
        from backend.agentcore.people_controls_agent.src.main import get_a6_controls_checklist
        result = get_a6_controls_checklist._tool_func()

        for control_id, control in result["controls"].items():
            assert "evidence_types" in control, f"Missing evidence_types in {control_id}"
            assert len(control["evidence_types"]) > 0

    def test_assess_training_effectiveness(self):
        """Training effectiveness tool returns assessment framework."""
        from backend.agentcore.people_controls_agent.src.main import assess_training_effectiveness
        result = assess_training_effectiveness._tool_func(
            training_records_summary="85% completion rate, annual program",
            personnel_count=200,
        )

        assert result["control_id"] == "A.6.3"
        assert result["training_data_provided"] is True
        assert result["personnel_count"] == 200
        assert len(result["assessment_framework"]) == 5


class TestPhysicalControlsAgent:
    """Tests for the A.7 Physical Controls Agent."""

    def test_get_a7_controls_checklist_returns_14_controls(self):
        """Checklist tool returns exactly 14 A.7 controls."""
        from backend.agentcore.physical_controls_agent.src.main import get_a7_controls_checklist
        result = get_a7_controls_checklist._tool_func()

        assert result["domain"] == "A.7"
        assert result["total_controls"] == 14
        assert len(result["controls"]) == 14
        assert "A.7.1" in result["controls"]
        assert "A.7.14" in result["controls"]

    def test_a7_controls_cover_all_domains(self):
        """All 14 physical controls are named correctly."""
        from backend.agentcore.physical_controls_agent.src.main import get_a7_controls_checklist
        result = get_a7_controls_checklist._tool_func()

        expected_names = [
            "Physical security perimeters",
            "Physical entry",
            "Securing offices, rooms and facilities",
            "Physical security monitoring",
            "Protecting against physical and environmental threats",
            "Working in secure areas",
            "Clear desk and clear screen",
            "Equipment siting and protection",
            "Security of assets off-premises",
            "Storage media",
            "Supporting utilities",
            "Cabling security",
            "Equipment maintenance",
            "Secure disposal or re-use of equipment",
        ]
        actual_names = [c["name"] for c in result["controls"].values()]
        assert actual_names == expected_names

    def test_assess_physical_site_security_shared_facility(self):
        """Site security assessment flags multi-tenant risks."""
        from backend.agentcore.physical_controls_agent.src.main import assess_physical_site_security
        result = assess_physical_site_security._tool_func(
            site_description="Office building floor 3, shared reception",
            has_data_center=False,
            is_shared_facility=True,
        )

        assert result["is_shared_facility"] is True
        assert len(result["risk_factors"]) >= 2
        assert any("Multi-tenant" in r for r in result["risk_factors"])

    def test_assess_physical_site_with_data_center(self):
        """Site assessment flags data center requirements."""
        from backend.agentcore.physical_controls_agent.src.main import assess_physical_site_security
        result = assess_physical_site_security._tool_func(
            site_description="Corporate HQ with server room",
            has_data_center=True,
            is_shared_facility=False,
        )

        assert result["has_data_center"] is True
        assert any("Data center" in r for r in result["risk_factors"])

    def test_evaluate_environmental_controls_full_protection(self):
        """Full protection scores high maturity."""
        from backend.agentcore.physical_controls_agent.src.main import evaluate_environmental_controls
        result = evaluate_environmental_controls._tool_func(
            fire_suppression_type="gas",
            ups_capacity_minutes=30,
            hvac_monitored=True,
            generator_available=True,
        )

        assert result["fire_maturity"] == 5
        assert result["power_maturity"] == 5
        assert result["hvac_maturity"] == 4
        assert result["overall_maturity"] >= 4.0
        assert len(result["gaps_identified"]) == 0

    def test_evaluate_environmental_controls_no_protection(self):
        """No protection scores low with many gaps."""
        from backend.agentcore.physical_controls_agent.src.main import evaluate_environmental_controls
        result = evaluate_environmental_controls._tool_func(
            fire_suppression_type="none",
            ups_capacity_minutes=0,
            hvac_monitored=False,
            generator_available=False,
        )

        assert result["fire_maturity"] == 0
        assert result["power_maturity"] == 0
        assert result["overall_maturity"] < 2.0
        assert len(result["gaps_identified"]) >= 3


class TestTechnologicalControlsAgent:
    """Tests for the A.8 Technological Controls Agent."""

    def test_get_a8_controls_checklist_returns_34_controls(self):
        """Checklist tool returns exactly 34 A.8 controls."""
        from backend.agentcore.technological_controls_agent.src.main import get_a8_controls_checklist
        result = get_a8_controls_checklist._tool_func()

        assert result["domain"] == "A.8"
        assert result["total_controls"] == 34
        assert len(result["controls"]) == 34
        assert "A.8.1" in result["controls"]
        assert "A.8.34" in result["controls"]

    def test_evaluate_vulnerability_management_critical_exposure(self):
        """Critical vulnerabilities trigger major non-conformity."""
        from backend.agentcore.technological_controls_agent.src.main import evaluate_vulnerability_management
        result = evaluate_vulnerability_management._tool_func(
            scan_frequency="quarterly",
            patch_sla_days=90,
            open_vulnerabilities=100,
            critical_open=15,
        )

        assert result["risk_level"] == "critical"
        assert result["suggested_conformity"] == "major_nonconformity"
        assert result["scan_maturity"] == 2

    def test_evaluate_vulnerability_management_healthy(self):
        """Good vulnerability management scores conforming."""
        from backend.agentcore.technological_controls_agent.src.main import evaluate_vulnerability_management
        result = evaluate_vulnerability_management._tool_func(
            scan_frequency="weekly",
            patch_sla_days=14,
            open_vulnerabilities=5,
            critical_open=0,
        )

        assert result["risk_level"] == "low"
        assert result["suggested_conformity"] == "conforming"
        assert result["overall_maturity"] >= 4.0


class TestPlanningAgent:
    """Tests for the Planning Agent tools."""

    def test_get_iso27001_controls_list_all(self):
        """Returns all 93 controls across 4 domains."""
        from backend.agentcore.planning_agent.src.main import get_iso27001_controls_list
        result = get_iso27001_controls_list._tool_func(domain="all")

        assert result["total_controls"] == 93
        assert "A.5" in result["domains"]
        assert "A.6" in result["domains"]
        assert "A.7" in result["domains"]
        assert "A.8" in result["domains"]
        assert result["domains"]["A.5"]["count"] == 37
        assert result["domains"]["A.6"]["count"] == 8
        assert result["domains"]["A.7"]["count"] == 14
        assert result["domains"]["A.8"]["count"] == 34

    def test_get_iso27001_controls_list_single_domain(self):
        """Returns single domain info when specified."""
        from backend.agentcore.planning_agent.src.main import get_iso27001_controls_list
        result = get_iso27001_controls_list._tool_func(domain="A.7")

        assert result["domain"] == "A.7"
        assert result["count"] == 14
        assert "Physical" in result["name"]

    def test_get_iso27001_controls_list_invalid_domain(self):
        """Returns error for invalid domain."""
        from backend.agentcore.planning_agent.src.main import get_iso27001_controls_list
        result = get_iso27001_controls_list._tool_func(domain="A.99")

        assert "error" in result

    def test_generate_audit_schedule_small_org(self):
        """Schedule for small org is shorter."""
        from backend.agentcore.planning_agent.src.main import generate_audit_schedule
        result = generate_audit_schedule._tool_func(
            organization_size="small",
            controls_in_scope=["A.5", "A.6", "A.7", "A.8"],
            audit_type="internal",
        )

        assert result["organization_size"] == "small"
        assert result["total_estimated_days"] <= 10
        assert len(result["schedule"]) == 4

    def test_generate_audit_schedule_large_org(self):
        """Schedule for large org is longer."""
        from backend.agentcore.planning_agent.src.main import generate_audit_schedule
        result = generate_audit_schedule._tool_func(
            organization_size="large",
            controls_in_scope=["A.5", "A.6", "A.7", "A.8"],
            audit_type="certification",
        )

        assert result["total_estimated_days"] > 10
        assert result["audit_type"] == "certification"
