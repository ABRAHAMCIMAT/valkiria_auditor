"""
Dynamic Model Selector — Enables AgentCore agents to choose among available
Bedrock models based on task requirements, latency constraints, and cost budget.

Implements selection strategies:
- FIXED: Always use a specific model (default behavior)
- COST_OPTIMIZED: Choose cheapest model that meets capability requirements
- LATENCY_OPTIMIZED: Choose fastest model that meets capability requirements
- QUALITY_OPTIMIZED: Choose highest-capability model within budget
- ADAPTIVE: Select based on historical performance metrics (requires metrics data)
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from strands.models.bedrock import BedrockModel

from backend.models.registry import (
    BEDROCK_MODELS,
    CostTier,
    LatencyProfile,
    ModelCapability,
    ModelSpec,
    get_model,
    get_recommended_models_for_agent,
)


class SelectionStrategy(str, Enum):
    """Model selection strategy."""
    FIXED = "fixed"
    COST_OPTIMIZED = "cost_optimized"
    LATENCY_OPTIMIZED = "latency_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    ADAPTIVE = "adaptive"


@dataclass
class SelectionCriteria:
    """Criteria for model selection."""
    required_capabilities: list[ModelCapability] = None
    max_cost_tier: CostTier = CostTier.PREMIUM
    max_latency_profile: LatencyProfile = LatencyProfile.SLOW
    min_context_tokens: int = 0
    min_output_tokens: int = 0
    requires_tool_use: bool = True
    requires_streaming: bool = False
    agent_role: Optional[str] = None

    def __post_init__(self):
        if self.required_capabilities is None:
            self.required_capabilities = []


# Cost tier ordering for comparison
_COST_ORDER = {CostTier.LOW: 0, CostTier.MEDIUM: 1, CostTier.HIGH: 2, CostTier.PREMIUM: 3}
_LATENCY_ORDER = {LatencyProfile.FAST: 0, LatencyProfile.BALANCED: 1, LatencyProfile.SLOW: 2}


class ModelSelector:
    """
    Selects the optimal Bedrock model based on strategy and criteria.

    Usage:
        selector = ModelSelector(strategy=SelectionStrategy.COST_OPTIMIZED)
        model_spec = selector.select(
            criteria=SelectionCriteria(
                required_capabilities=[ModelCapability.REASONING, ModelCapability.AGENTIC],
                max_cost_tier=CostTier.MEDIUM,
                requires_tool_use=True,
            )
        )
        bedrock_model = selector.load_model(model_spec)
    """

    def __init__(
        self,
        strategy: SelectionStrategy = SelectionStrategy.FIXED,
        fixed_model_key: str = "gpt-oss-120b",
        region: Optional[str] = None,
        use_cross_region: bool = False,
    ):
        self.strategy = strategy
        self.fixed_model_key = fixed_model_key
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.use_cross_region = use_cross_region

    def select(self, criteria: Optional[SelectionCriteria] = None) -> ModelSpec:
        """
        Select the best model based on strategy and criteria.

        Args:
            criteria: Selection criteria (required capabilities, cost/latency constraints).

        Returns:
            ModelSpec of the selected model.
        """
        if self.strategy == SelectionStrategy.FIXED:
            return get_model(self.fixed_model_key)

        if criteria is None:
            criteria = SelectionCriteria()

        # Filter candidates based on hard requirements
        candidates = self._filter_candidates(criteria)

        if not candidates:
            # Fallback: relax constraints and return default
            return get_model(self.fixed_model_key)

        # Rank candidates based on strategy
        if self.strategy == SelectionStrategy.COST_OPTIMIZED:
            return self._select_cheapest(candidates)
        elif self.strategy == SelectionStrategy.LATENCY_OPTIMIZED:
            return self._select_fastest(candidates)
        elif self.strategy == SelectionStrategy.QUALITY_OPTIMIZED:
            return self._select_highest_quality(candidates)
        elif self.strategy == SelectionStrategy.ADAPTIVE:
            return self._select_adaptive(candidates, criteria)
        else:
            return candidates[0]

    def _filter_candidates(self, criteria: SelectionCriteria) -> list[ModelSpec]:
        """Filter models that meet all hard requirements."""
        candidates = []
        for model in BEDROCK_MODELS.values():
            # Capability check
            if criteria.required_capabilities:
                if not all(cap in model.capabilities for cap in criteria.required_capabilities):
                    continue

            # Cost check
            if _COST_ORDER[model.cost_tier] > _COST_ORDER[criteria.max_cost_tier]:
                continue

            # Latency check
            if _LATENCY_ORDER[model.latency_profile] > _LATENCY_ORDER[criteria.max_latency_profile]:
                continue

            # Context window check
            if model.max_context_tokens < criteria.min_context_tokens:
                continue

            # Output token check
            if model.max_output_tokens < criteria.min_output_tokens:
                continue

            # Tool use check
            if criteria.requires_tool_use and not model.supports_tool_use:
                continue

            # Streaming check
            if criteria.requires_streaming and not model.supports_streaming:
                continue

            candidates.append(model)

        # If agent_role specified, reorder by recommendation
        if criteria.agent_role:
            recommended = get_recommended_models_for_agent(criteria.agent_role)
            # Sort: recommended models first, in priority order
            def priority_key(m: ModelSpec):
                for key, spec in BEDROCK_MODELS.items():
                    if spec.model_id == m.model_id and key in recommended:
                        return recommended.index(key)
                return len(recommended)
            candidates.sort(key=priority_key)

        return candidates

    def _select_cheapest(self, candidates: list[ModelSpec]) -> ModelSpec:
        """Select the lowest-cost model from candidates."""
        return min(candidates, key=lambda m: _COST_ORDER[m.cost_tier])

    def _select_fastest(self, candidates: list[ModelSpec]) -> ModelSpec:
        """Select the lowest-latency model from candidates."""
        return min(candidates, key=lambda m: _LATENCY_ORDER[m.latency_profile])

    def _select_highest_quality(self, candidates: list[ModelSpec]) -> ModelSpec:
        """Select the model with most capabilities and largest context."""
        def quality_score(m: ModelSpec) -> float:
            return len(m.capabilities) * 10 + m.max_context_tokens / 100_000
        return max(candidates, key=quality_score)

    def _select_adaptive(self, candidates: list[ModelSpec], criteria: SelectionCriteria) -> ModelSpec:
        """
        Select based on historical performance metrics.
        Falls back to quality_optimized if no metrics are available.
        """
        # Adaptive selection uses metrics from the MetricsCollector.
        # If no historical data, fall back to quality-optimized.
        try:
            from backend.models.metrics import MetricsStore
            store = MetricsStore()
            best_model_id = store.get_best_model_for_agent(criteria.agent_role or "default")
            if best_model_id:
                for m in candidates:
                    if m.model_id == best_model_id:
                        return m
        except Exception:
            pass

        return self._select_highest_quality(candidates)

    def load_model(
        self,
        model_spec: Optional[ModelSpec] = None,
        criteria: Optional[SelectionCriteria] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BedrockModel:
        """
        Select and instantiate a BedrockModel ready for agent use.

        Args:
            model_spec: Specific model to load. If None, selection is performed.
            criteria: Selection criteria (used if model_spec is None).
            temperature: Override temperature (uses model's recommended if None).
            max_tokens: Override max tokens.

        Returns:
            Configured BedrockModel instance.
        """
        if model_spec is None:
            model_spec = self.select(criteria)

        # Use cross-region ID if configured and available
        model_id = model_spec.model_id
        if self.use_cross_region and model_spec.cross_region_id:
            model_id = model_spec.cross_region_id

        return BedrockModel(
            model_id=model_id,
            region_name=self.region,
            temperature=temperature if temperature is not None else model_spec.recommended_temperature,
            max_tokens=max_tokens or model_spec.max_output_tokens,
        )
