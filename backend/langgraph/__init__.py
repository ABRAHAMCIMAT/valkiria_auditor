"""
LangGraph implementation of the ISO 27001 multi-agent audit orchestration.

Pattern: StateGraph with conditional edges and parallel fan-out
- Typed state flows through graph nodes
- Each node wraps a specialized agent invocation
- Parallel execution of domain evaluators via fan-out
- Conditional routing based on evidence sufficiency

Framework: langgraph==0.4.x (latest stable)
"""
