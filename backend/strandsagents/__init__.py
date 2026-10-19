"""
Strands Agents SDK implementation of the ISO 27001 multi-agent audit orchestration.

Pattern: Agents as Tools (hierarchical delegation)
- Orchestrator agent wraps sub-agents as @tool functions
- Each sub-agent has its own system prompt, tools, and model
- Orchestrator coordinates the flow: Plan → Evidence → Domain Eval → Consolidation
"""
