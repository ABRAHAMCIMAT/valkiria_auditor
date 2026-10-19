"""
AgentCore Memory Integration — Provides STM and LTM for audit agents.

Memory enables:
- STM (Short-Term Memory): Conversation persistence within an audit session
- LTM (Long-Term Memory): Knowledge retention across sessions (past findings,
  organizational context, auditor preferences)

Memory Strategies:
- Summary: Session summaries for quick context recall
- Semantic: Factual extraction (e.g., "Organization X has 200 employees")
- User Preference: Auditor preferences (language, report format)

Usage:
    from backend.agentcore.shared.memory import create_memory_session, MemoryConfig

    config = MemoryConfig(
        memory_id="<from-agentcore-memory-create>",
        session_id="audit_001",
        actor_id="auditor_david",
    )
    session_manager = create_memory_session(config)

    agent = Agent(
        model=load_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=[...],
        session_manager=session_manager,
    )
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

REGION = os.environ.get("AWS_REGION", "us-east-1")
DEFAULT_MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")


@dataclass
class MemoryConfig:
    """Configuration for AgentCore Memory."""
    memory_id: str = ""
    session_id: str = ""
    actor_id: str = ""
    region: str = ""
    mode: str = "STM_ONLY"  # STM_ONLY, STM_AND_LTM, NO_MEMORY

    def __post_init__(self):
        if not self.memory_id:
            self.memory_id = DEFAULT_MEMORY_ID
        if not self.region:
            self.region = REGION


@dataclass
class LTMRetrievalConfig:
    """Configuration for Long-Term Memory retrieval."""
    namespace: str = ""
    top_k: int = 5
    relevance_score: float = 0.5


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY SESSION FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def create_memory_session(
    config: MemoryConfig,
    ltm_configs: Optional[list[LTMRetrievalConfig]] = None,
) -> Optional[AgentCoreMemorySessionManager]:
    """
    Create an AgentCore Memory session manager for a Strands agent.

    Args:
        config: Memory configuration (memory_id, session_id, actor_id).
        ltm_configs: Optional LTM retrieval configurations for semantic/preference namespaces.

    Returns:
        AgentCoreMemorySessionManager instance, or None if memory is disabled.
    """
    if config.mode == "NO_MEMORY" or not config.memory_id:
        return None

    # Build retrieval config for LTM namespaces
    retrieval_config = None
    if ltm_configs and config.mode == "STM_AND_LTM":
        from bedrock_agentcore.memory.integrations.strands.config import RetrievalConfig
        retrieval_config = {}
        for ltm in ltm_configs:
            retrieval_config[ltm.namespace] = RetrievalConfig(
                top_k=ltm.top_k,
                relevance_score=ltm.relevance_score,
            )

    agentcore_config = AgentCoreMemoryConfig(
        memory_id=config.memory_id,
        session_id=config.session_id,
        actor_id=config.actor_id,
        retrieval_config=retrieval_config,
    )

    return AgentCoreMemorySessionManager(
        agentcore_memory_config=agentcore_config,
        region_name=config.region,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PRE-CONFIGURED MEMORY FACTORIES PER AGENT ROLE
# ─────────────────────────────────────────────────────────────────────────────

def create_planning_memory(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    """Create memory for the Planning Agent (STM only — session context)."""
    config = MemoryConfig(
        session_id=session_id,
        actor_id=actor_id,
        mode="STM_ONLY",
    )
    return create_memory_session(config)


def create_evidence_memory(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    """Create memory for the Evidence Agent (STM — evidence tracking within session)."""
    config = MemoryConfig(
        session_id=session_id,
        actor_id=actor_id,
        mode="STM_ONLY",
    )
    return create_memory_session(config)


def create_domain_agent_memory(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    """Create memory for domain evaluation agents (STM + LTM for past findings)."""
    config = MemoryConfig(
        session_id=session_id,
        actor_id=actor_id,
        mode="STM_AND_LTM",
    )
    ltm_configs = [
        LTMRetrievalConfig(
            namespace="/facts/{actorId}",
            top_k=10,
            relevance_score=0.3,
        ),
        LTMRetrievalConfig(
            namespace="/summaries/{actorId}/{sessionId}",
            top_k=3,
            relevance_score=0.5,
        ),
    ]
    return create_memory_session(config, ltm_configs)


def create_consolidation_memory(session_id: str, actor_id: str) -> Optional[AgentCoreMemorySessionManager]:
    """
    Create memory for the Consolidation Agent (STM + full LTM).
    The orchestrator benefits from all memory strategies:
    - Session summaries for audit context
    - Semantic facts for organizational knowledge
    - Preferences for report formatting
    """
    config = MemoryConfig(
        session_id=session_id,
        actor_id=actor_id,
        mode="STM_AND_LTM",
    )
    ltm_configs = [
        LTMRetrievalConfig(
            namespace="/summaries/{actorId}/{sessionId}",
            top_k=5,
            relevance_score=0.5,
        ),
        LTMRetrievalConfig(
            namespace="/facts/{actorId}",
            top_k=15,
            relevance_score=0.3,
        ),
        LTMRetrievalConfig(
            namespace="/preferences/{actorId}",
            top_k=5,
            relevance_score=0.7,
        ),
    ]
    return create_memory_session(config, ltm_configs)


# ─────────────────────────────────────────────────────────────────────────────
# MEMORY RESOURCE CREATION HELPER (CLI wrapper)
# ─────────────────────────────────────────────────────────────────────────────

def get_memory_creation_command(memory_name: str = "iso27001_audit_memory") -> str:
    """
    Get the CLI command to create the AgentCore Memory resource.
    Run this ONCE during initial setup.

    Returns:
        Shell command string.
    """
    strategies = [
        {
            "summaryMemoryStrategy": {
                "name": "AuditSessionSummary",
                "namespaces": ["/summaries/{actorId}/{sessionId}"],
            }
        },
        {
            "semanticMemoryStrategy": {
                "name": "OrganizationalFacts",
                "namespaces": ["/facts/{actorId}"],
            }
        },
        {
            "userPreferenceMemoryStrategy": {
                "name": "AuditorPreferences",
                "namespaces": ["/preferences/{actorId}"],
            }
        },
    ]

    import json
    strategies_json = json.dumps(strategies)

    return (
        f"agentcore memory create {memory_name} "
        f"--description 'Memory for ISO 27001 multi-agent audit system' "
        f"--strategies '{strategies_json}' "
        f"--region {REGION} "
        f"--wait"
    )
