"""
CrewAI implementation of the ISO 27001 multi-agent audit orchestration.

Pattern: Role-based crew with sequential process and hierarchical delegation
- Agents defined by role, goal, and backstory
- Tasks define the work with expected outputs
- Crew orchestrates agents in sequential order
- Manager agent handles delegation and quality control

Framework: crewai==1.x (latest stable GA)
"""
