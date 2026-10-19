"""
Unified Audit Runner — Execute the ISO 27001 audit using any of the three
orchestration frameworks and compare results.

Usage:
    python -m backend.run_audit --framework strands --org "ACME Corp, 200 employees, fintech"
    python -m backend.run_audit --framework langgraph --org "ACME Corp, 200 employees, fintech"
    python -m backend.run_audit --framework crewai --org "ACME Corp, 200 employees, fintech"
    python -m backend.run_audit --framework all --org "ACME Corp, 200 employees, fintech"
"""

import argparse
import json
import time
from typing import Callable


def _run_strands(org: str, audit_type: str, audit_id: str) -> dict:
    from backend.strandsagents.orchestrator import run_audit
    return run_audit(
        organization_context=org,
        audit_type=audit_type,
        audit_id=f"strands_{audit_id}",
        session_id=f"strands_session_{audit_id}",
    )


def _run_langgraph(org: str, audit_type: str, audit_id: str) -> dict:
    from backend.langgraph.orchestrator import run_audit
    return run_audit(
        organization_context=org,
        audit_type=audit_type,
        audit_id=f"langgraph_{audit_id}",
        session_id=f"langgraph_session_{audit_id}",
    )


def _run_crewai(org: str, audit_type: str, audit_id: str) -> dict:
    from backend.crewai.orchestrator import run_audit
    return run_audit(
        organization_context=org,
        audit_type=audit_type,
        audit_id=f"crewai_{audit_id}",
        session_id=f"crewai_session_{audit_id}",
    )


def _run_comp2013(org: str, audit_type: str, audit_id: str) -> dict:
    from backend.comp2013.orchestrator import run_audit
    return run_audit(
        organization_context=org,
        audit_type=audit_type,
        audit_id=f"comp2013_{audit_id}",
        session_id=f"comp2013_session_{audit_id}",
    )


FRAMEWORKS: dict[str, Callable] = {
    "strands": _run_strands,
    "langgraph": _run_langgraph,
    "crewai": _run_crewai,
    "comp2013": _run_comp2013,
}


def run_comparison(org: str, audit_type: str = "internal", audit_id: str = "001") -> dict:
    """Run all three frameworks and compare execution metrics."""
    results = {}

    for name, runner in FRAMEWORKS.items():
        print(f"\n{'='*60}")
        print(f"  Running: {name.upper()}")
        print(f"{'='*60}\n")

        start = time.perf_counter()
        try:
            result = runner(org, audit_type, audit_id)
            result["wall_time_seconds"] = round(time.perf_counter() - start, 2)
            result["error"] = None
            results[name] = result
        except Exception as exc:
            results[name] = {
                "framework": name,
                "error": str(exc),
                "wall_time_seconds": round(time.perf_counter() - start, 2),
            }

    # Print comparison summary
    print(f"\n{'='*60}")
    print("  COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"{'Framework':<12} {'Time (s)':<10} {'Success':<10} {'Report Len':<12}")
    print("-" * 44)
    for name, res in results.items():
        t = res.get("wall_time_seconds", 0)
        success = "✅" if not res.get("error") else "❌"
        report_len = len(res.get("report", ""))
        print(f"{name:<12} {t:<10} {success:<10} {report_len:<12}")

    return results


def main():
    parser = argparse.ArgumentParser(description="ISO 27001 Multi-Agent Audit Runner")
    parser.add_argument("--framework", choices=["strands", "langgraph", "crewai", "comp2013", "all"], default="all")
    parser.add_argument("--org", required=True, help="Organization context description")
    parser.add_argument("--type", choices=["internal", "certification", "surveillance"], default="internal")
    parser.add_argument("--id", default="001", help="Audit identifier")
    args = parser.parse_args()

    if args.framework == "all":
        results = run_comparison(args.org, args.type, args.id)
    else:
        runner = FRAMEWORKS[args.framework]
        result = runner(args.org, args.type, args.id)
        print(json.dumps(result.get("flow_metrics", {}), indent=2))
        print(f"\nReport length: {len(result.get('report', ''))} chars")


if __name__ == "__main__":
    main()
