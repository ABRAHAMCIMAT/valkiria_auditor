"""
Bedrock Model Registry — Available foundation models for AgentCore agents.

Provides a catalog of available models with their characteristics (context window,
cost tier, latency profile) to enable dynamic model selection based on task needs.

Source: https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ModelProvider(str, Enum):
    """Model providers available on Amazon Bedrock."""
    OPENAI = "openai"
    QWEN = "qwen"
    ANTHROPIC = "anthropic"
    META = "meta"
    MISTRAL = "mistral"
    DEEPSEEK = "deepseek"


class ModelCapability(str, Enum):
    """Model capabilities relevant for agent task selection."""
    TEXT_GENERATION = "text_generation"
    REASONING = "reasoning"
    CODE = "code"
    MULTIMODAL = "multimodal"
    EMBEDDING = "embedding"
    LONG_CONTEXT = "long_context"
    AGENTIC = "agentic"


class CostTier(str, Enum):
    """Relative cost tier for budget-aware selection."""
    LOW = "low"           # < $0.5/M input tokens
    MEDIUM = "medium"     # $0.5 - $3/M input tokens
    HIGH = "high"         # $3 - $10/M input tokens
    PREMIUM = "premium"   # > $10/M input tokens


class LatencyProfile(str, Enum):
    """Expected latency characteristics."""
    FAST = "fast"         # TTFT < 500ms, high throughput
    BALANCED = "balanced" # TTFT 500-2000ms
    SLOW = "slow"         # TTFT > 2000ms, highest quality


@dataclass
class ModelSpec:
    """Specification for a Bedrock foundation model."""
    model_id: str
    display_name: str
    provider: ModelProvider
    capabilities: list[ModelCapability] = field(default_factory=list)
    max_context_tokens: int = 128_000
    max_output_tokens: int = 4_096
    cost_tier: CostTier = CostTier.MEDIUM
    latency_profile: LatencyProfile = LatencyProfile.BALANCED
    supports_streaming: bool = True
    supports_tool_use: bool = True
    recommended_temperature: float = 0.2
    notes: str = ""
    # Cross-region inference profile ID (for multi-region deployment)
    cross_region_id: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# MODEL CATALOG
# Available models for the ISO 27001 audit multi-agent system
# ─────────────────────────────────────────────────────────────────────────────

BEDROCK_MODELS: dict[str, ModelSpec] = {
    # ───── OpenAI GPT Family ─────
    "gpt-oss-120b": ModelSpec(
        model_id="openai.gpt-oss-120b-1:0",
        display_name="GPT OSS 120B",
        provider=ModelProvider.OPENAI,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.REASONING,
            ModelCapability.CODE,
        ],
        max_context_tokens=128_000,
        max_output_tokens=8_192,
        cost_tier=CostTier.MEDIUM,
        latency_profile=LatencyProfile.BALANCED,
        supports_tool_use=False,
        recommended_temperature=0.2,
        notes="120B open-weight model. Production-grade reasoning. Uses <reasoning> tags.",
    ),

    # ───── Qwen3 Family (Alibaba) ─────
    "qwen3-32b": ModelSpec(
        model_id="qwen.qwen3-32b-v1:0",
        display_name="Qwen3 32B Dense",
        provider=ModelProvider.QWEN,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.REASONING,
            ModelCapability.CODE,
        ],
        max_context_tokens=128_000,
        max_output_tokens=8_192,
        cost_tier=CostTier.LOW,
        latency_profile=LatencyProfile.FAST,
        supports_tool_use=True,
        recommended_temperature=0.3,
        notes="Dense 32B. Consistent performance, low latency. Hybrid thinking modes.",
    ),

    # ───── Anthropic Claude Family ─────
    "claude-sonnet-4.6": ModelSpec(
        model_id="anthropic.claude-sonnet-4-6-20250514-v1:0",
        display_name="Claude Sonnet 4.6",
        provider=ModelProvider.ANTHROPIC,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.REASONING,
            ModelCapability.CODE,
            ModelCapability.AGENTIC,
        ],
        max_context_tokens=200_000,
        max_output_tokens=16_000,
        cost_tier=CostTier.MEDIUM,
        latency_profile=LatencyProfile.BALANCED,
        recommended_temperature=0.2,
        cross_region_id="us.anthropic.claude-sonnet-4-6-20250514-v1:0",
        notes="Strong structured analysis and tool use. Good for audit evaluations.",
    ),
    "claude-haiku-4.5": ModelSpec(
        model_id="anthropic.claude-haiku-4-5-20250514-v1:0",
        display_name="Claude Haiku 4.5",
        provider=ModelProvider.ANTHROPIC,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CODE,
            ModelCapability.AGENTIC,
        ],
        max_context_tokens=200_000,
        max_output_tokens=8_192,
        cost_tier=CostTier.LOW,
        latency_profile=LatencyProfile.FAST,
        recommended_temperature=0.3,
        cross_region_id="us.anthropic.claude-haiku-4-5-20250514-v1:0",
        notes="Fast and cost-effective. Good for evidence retrieval and classification.",
    ),

    # ───── Meta Llama Family ─────
    "llama-4-maverick": ModelSpec(
        model_id="meta.llama4-maverick-17b-instruct-v1:0",
        display_name="Llama 4 Maverick 17B",
        provider=ModelProvider.META,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.REASONING,
            ModelCapability.MULTIMODAL,
        ],
        max_context_tokens=128_000,
        max_output_tokens=4_096,
        cost_tier=CostTier.LOW,
        latency_profile=LatencyProfile.FAST,
        supports_tool_use=True,
        recommended_temperature=0.3,
        cross_region_id="us.meta.llama4-maverick-17b-instruct-v1:0",
        notes="Efficient MoE architecture. Good price-performance for sub-agents.",
    ),

    # ───── Mistral Family ─────
    "mistral-large": ModelSpec(
        model_id="mistral.mistral-large-2407-v1:0",
        display_name="Mistral Large",
        provider=ModelProvider.MISTRAL,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.REASONING,
            ModelCapability.CODE,
            ModelCapability.AGENTIC,
        ],
        max_context_tokens=128_000,
        max_output_tokens=8_192,
        cost_tier=CostTier.MEDIUM,
        latency_profile=LatencyProfile.BALANCED,
        recommended_temperature=0.2,
        notes="Strong tool use. Good for structured audit evaluations.",
    ),

    # ───── DeepSeek ─────
    "deepseek-r1": ModelSpec(
        model_id="deepseek.deepseek-r1-v1:0",
        display_name="DeepSeek R1",
        provider=ModelProvider.DEEPSEEK,
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.REASONING,
            ModelCapability.CODE,
        ],
        max_context_tokens=128_000,
        max_output_tokens=8_192,
        cost_tier=CostTier.MEDIUM,
        latency_profile=LatencyProfile.SLOW,
        supports_tool_use=False,
        recommended_temperature=0.1,
        cross_region_id="us.deepseek.deepseek-r1-v1:0",
        notes="Exceptional reasoning with chain-of-thought. For complex analysis and consolidation.",
    ),
}


def get_model(key: str) -> ModelSpec:
    """Get a model spec by registry key."""
    if key not in BEDROCK_MODELS:
        raise ValueError(f"Unknown model key '{key}'. Available: {list(BEDROCK_MODELS.keys())}")
    return BEDROCK_MODELS[key]


def list_models_by_capability(capability: ModelCapability) -> list[ModelSpec]:
    """Filter models that support a given capability."""
    return [m for m in BEDROCK_MODELS.values() if capability in m.capabilities]


def list_models_by_cost_tier(tier: CostTier) -> list[ModelSpec]:
    """Filter models by cost tier."""
    return [m for m in BEDROCK_MODELS.values() if m.cost_tier == tier]


def list_models_by_latency(profile: LatencyProfile) -> list[ModelSpec]:
    """Filter models by latency profile."""
    return [m for m in BEDROCK_MODELS.values() if m.latency_profile == profile]


def get_recommended_models_for_agent(agent_role: str) -> list[str]:
    """
    Get recommended model keys for a specific agent role.

    Args:
        agent_role: One of 'planning', 'evidence', 'organizational',
                    'people', 'technological', 'consolidation'.

    Returns:
        List of model registry keys in priority order.
    """
    recommendations = {
        "planning": ["gpt-oss-120b", "claude-sonnet-4.6", "mistral-large", "qwen3-32b"],
        "evidence": ["qwen3-32b", "claude-haiku-4.5", "llama-4-maverick", "gpt-oss-120b"],
        "organizational": ["gpt-oss-120b", "claude-sonnet-4.6", "mistral-large", "qwen3-32b"],
        "people": ["qwen3-32b", "claude-sonnet-4.6", "gpt-oss-120b", "llama-4-maverick"],
        "technological": ["gpt-oss-120b", "claude-sonnet-4.6", "mistral-large", "qwen3-32b"],
        "consolidation": ["deepseek-r1", "gpt-oss-120b", "claude-sonnet-4.6", "mistral-large"],
    }
    return recommendations.get(agent_role, ["gpt-oss-120b", "qwen3-32b"])
