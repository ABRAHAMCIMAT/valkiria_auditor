"""
Model loader for Bedrock foundation models.
Centralizes model configuration for all agents.
"""

import os

from strands.models import Model
from strands.models.bedrock import BedrockModel


# Default model configuration
DEFAULT_MODEL_ID = "openai.gpt-oss-120b-1:0"
DEFAULT_REGION = "us-east-1"
DEFAULT_TEMPERATURE = 0.2  # Deterministic for audit outputs
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TOP_P = 0.9


def load_model(
    model_id: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    region: str | None = None,
) -> Model:
    """
    Load the model for agent use: a Bedrock model (Phase 1), or the fine-tuned
    SageMaker endpoint named by SAGEMAKER_ENDPOINT_NAME when set (Phase 2).

    Args:
        model_id: Bedrock model ARN or ID. Defaults to Nova Pro.
        temperature: Sampling temperature. Defaults to 0.2 for deterministic outputs.
        max_tokens: Max tokens in response. Defaults to 4096.
        region: AWS region. Defaults to env var or us-east-1.

    Returns:
        Configured model instance.
    """
    endpoint_name = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "")
    if endpoint_name:
        return _load_sagemaker_model(endpoint_name, temperature, max_tokens, region)

    resolved_model_id = model_id or os.environ.get("MODEL_ID", DEFAULT_MODEL_ID)

    # Claude models on Bedrock reject temperature and top_p in the same request
    sampling = {}
    if "anthropic." not in resolved_model_id:
        sampling["top_p"] = float(os.environ.get("MODEL_TOP_P", str(DEFAULT_TOP_P)))

    return BedrockModel(
        model_id=resolved_model_id,
        region_name=region or os.environ.get("AWS_REGION", DEFAULT_REGION),
        temperature=temperature if temperature is not None else float(
            os.environ.get("MODEL_TEMPERATURE", str(DEFAULT_TEMPERATURE))
        ),
        max_tokens=max_tokens or int(
            os.environ.get("MODEL_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))
        ),
        **sampling,
    )


def _load_sagemaker_model(
    endpoint_name: str,
    temperature: float | None,
    max_tokens: int | None,
    region: str | None,
) -> Model:
    """Load a fine-tuned adapter served by vLLM on a SageMaker endpoint."""
    from strands.models.sagemaker import SageMakerAIModel

    return SageMakerAIModel(
        endpoint_config={
            "endpoint_name": endpoint_name,
            "region_name": region or os.environ.get("AWS_REGION", DEFAULT_REGION),
        },
        payload_config={
            "max_tokens": max_tokens or int(os.environ.get("MODEL_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
            "temperature": temperature if temperature is not None else float(
                os.environ.get("MODEL_TEMPERATURE", str(DEFAULT_TEMPERATURE))
            ),
            "stream": False,
        },
    )
