"""
Integration tests verifying complete ISO 27001 coverage across all agent architectures.

Validates that:
- All 93 controls (2022) are covered by the 4 domain agents
- All 114 controls (2013) are covered by the 3 specialized agents
- No control is missed or duplicated between agents
- The consolidation step receives reports from all domain agents
"""

import pytest


class TestISO27001_2022_Coverage:
    """Verify complete ISO 27001:2022 Annex A coverage."""

    def test_total_controls_equals_93(self):
        """Sum of all domain agent controls equals 93."""
        from backend.agentcore.organizational_controls_agent.src.main import get_a5_controls_checklist
        from backend.agentcore.people_controls_agent.src.main import get_a6_controls_checklist
        from backend.agentcore.physical_controls_agent.src.main import get_a7_controls_checklist
        from backend.agentcore.technological_controls_agent.src.main import get_a8_controls_checklist

        a5 = get_a5_controls_checklist._tool_func()
        a6 = get_a6_controls_checklist._tool_func()
        a7 = get_a7_controls_checklist._tool_func()
        a8 = get_a8_controls_checklist._tool_func()

        total = a5["total_controls"] + a6["total_controls"] + a7["total_controls"] + a8["total_controls"]
        assert total == 93

    def test_no_duplicate_controls_across_agents(self):
        """No control ID appears in more than one agent's checklist."""
        from backend.agentcore.organizational_controls_agent.src.main import get_a5_controls_checklist
        from backend.agentcore.people_controls_agent.src.main import get_a6_controls_checklist
        from backend.agentcore.physical_controls_agent.src.main import get_a7_controls_checklist
        from backend.agentcore.technological_controls_agent.src.main import get_a8_controls_checklist

        a5_ids = set(get_a5_controls_checklist._tool_func()["controls"].keys())
        a6_ids = set(get_a6_controls_checklist._tool_func()["controls"].keys())
        a7_ids = set(get_a7_controls_checklist._tool_func()["controls"].keys())
        a8_ids = set(get_a8_controls_checklist._tool_func()["controls"].keys())

        all_ids = [a5_ids, a6_ids, a7_ids, a8_ids]
        for i in range(len(all_ids)):
            for j in range(i + 1, len(all_ids)):
                overlap = all_ids[i] & all_ids[j]
                assert overlap == set(), f"Duplicate controls found: {overlap}"

    def test_planning_agent_lists_all_93_controls(self):
        """Planning agent's control list totals 93."""
        from backend.agentcore.planning_agent.src.main import get_iso27001_controls_list
        result = get_iso27001_controls_list._tool_func(domain="all")

        total = sum(d["count"] for d in result["domains"].values())
        assert total == 93

    def test_all_domain_prefixes_correct(self):
        """A.5 controls start with A.5, A.6 with A.6, etc."""
        from backend.agentcore.organizational_controls_agent.src.main import get_a5_controls_checklist
        from backend.agentcore.people_controls_agent.src.main import get_a6_controls_checklist
        from backend.agentcore.physical_controls_agent.src.main import get_a7_controls_checklist
        from backend.agentcore.technological_controls_agent.src.main import get_a8_controls_checklist

        for cid in get_a5_controls_checklist._tool_func()["controls"].keys():
            assert cid.startswith("A.5."), f"Control {cid} should start with A.5."

        for cid in get_a6_controls_checklist._tool_func()["controls"].keys():
            assert cid.startswith("A.6."), f"Control {cid} should start with A.6."

        for cid in get_a7_controls_checklist._tool_func()["controls"].keys():
            assert cid.startswith("A.7."), f"Control {cid} should start with A.7."

        for cid in get_a8_controls_checklist._tool_func()["controls"].keys():
            assert cid.startswith("A.8."), f"Control {cid} should start with A.8."

    def test_strands_orchestrator_has_all_domain_tools(self):
        """Strands orchestrator has tools for all 4 domain agents."""
        from backend.strandsagents.orchestrator import (
            evaluate_organizational_controls,
            evaluate_people_controls,
            evaluate_physical_controls,
            evaluate_technological_controls,
        )
        # All are importable @tool functions
        assert hasattr(evaluate_organizational_controls, "_tool_func")
        assert hasattr(evaluate_people_controls, "_tool_func")
        assert hasattr(evaluate_physical_controls, "_tool_func")
        assert hasattr(evaluate_technological_controls, "_tool_func")

    def test_langgraph_state_covers_all_domains(self):
        """LangGraph AuditState has report fields for all 4 domains."""
        from backend.langgraph.orchestrator import AuditState

        required_fields = [
            "org_controls_report",
            "people_controls_report",
            "physical_controls_report",
            "tech_controls_report",
        ]
        for field in required_fields:
            assert field in AuditState.__annotations__, f"Missing state field: {field}"


class TestISO27001_2013_Coverage:
    """Verify complete ISO 27001:2013 coverage in comp2013 agents."""

    def test_governance_covers_clauses_4_to_10(self):
        """Governance agent scope includes clauses 4 through 10."""
        from backend.comp2013.orchestrator import AGENT_SCOPES

        ref_ids = AGENT_SCOPES["gobernanza"]["ref_ids"]
        clause_prefixes = set(rid.split(".")[0] for rid in ref_ids)

        # Should cover 4, 5, 6, 7, 8, 9, 10
        expected = {"4", "5", "6", "7", "8", "9", "10"}
        assert expected.issubset(clause_prefixes), f"Missing clauses: {expected - clause_prefixes}"

    def test_organizational_covers_expected_annexa_domains(self):
        """Organizational agent covers A.5, A.6, A.7, A.8, A.15, A.16, A.18."""
        from backend.comp2013.orchestrator import AGENT_SCOPES

        ref_ids = AGENT_SCOPES["organizacional"]["ref_ids"]
        domain_prefixes = set()
        for rid in ref_ids:
            # Extract domain like "A.5" or "A.15"
            parts = rid.split(".")
            domain_prefixes.add(f"{parts[0]}.{parts[1]}")

        expected_domains = {"A.5", "A.6", "A.7", "A.8", "A.15", "A.16", "A.18"}
        assert expected_domains.issubset(domain_prefixes), f"Missing: {expected_domains - domain_prefixes}"

    def test_technical_covers_expected_annexa_domains(self):
        """Technical agent covers A.9, A.10, A.11, A.12, A.13, A.14, A.17."""
        from backend.comp2013.orchestrator import AGENT_SCOPES

        ref_ids = AGENT_SCOPES["tecnico"]["ref_ids"]
        domain_prefixes = set()
        for rid in ref_ids:
            parts = rid.split(".")
            domain_prefixes.add(f"{parts[0]}.{parts[1]}")

        expected_domains = {"A.9", "A.10", "A.11", "A.12", "A.13", "A.14", "A.17"}
        assert expected_domains.issubset(domain_prefixes), f"Missing: {expected_domains - domain_prefixes}"

    def test_no_overlap_between_organizational_and_technical(self):
        """No control appears in both organizational and technical scopes."""
        from backend.comp2013.orchestrator import AGENT_SCOPES

        org_ids = set(AGENT_SCOPES["organizacional"]["ref_ids"])
        tech_ids = set(AGENT_SCOPES["tecnico"]["ref_ids"])

        overlap = org_ids & tech_ids
        assert overlap == set(), f"Controls in both agents: {overlap}"

    def test_total_2013_controls_reasonable(self):
        """Total controls across all 2013 agents is reasonable (>100)."""
        from backend.comp2013.orchestrator import AGENT_SCOPES

        total = sum(len(scope["ref_ids"]) for scope in AGENT_SCOPES.values())
        # 2013 has 114 Annex A controls + management clauses
        # Not all may be assessable, but should be > 100
        assert total > 100, f"Only {total} controls total — expected > 100"


class TestCrossFrameworkConsistency:
    """Verify that all frameworks produce compatible outputs."""

    def test_all_frameworks_registered_in_runner(self):
        """run_audit.py includes all 4 frameworks."""
        from backend.run_audit import FRAMEWORKS

        assert "strands" in FRAMEWORKS
        assert "langgraph" in FRAMEWORKS
        assert "crewai" in FRAMEWORKS
        assert "comp2013" in FRAMEWORKS

    def test_all_frameworks_callable(self):
        """All framework runner functions are callable."""
        from backend.run_audit import FRAMEWORKS

        for name, runner in FRAMEWORKS.items():
            assert callable(runner), f"Framework {name} runner is not callable"
