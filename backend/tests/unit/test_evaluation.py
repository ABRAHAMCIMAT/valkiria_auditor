"""Tests for the Bedrock model evaluation job builder."""

from unittest.mock import MagicMock

import pytest

from backend.models import evaluation


@pytest.fixture
def evaluator(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    instance = evaluation.ModelEvaluator(region="us-east-1")
    instance._bedrock = MagicMock()
    instance._bedrock.create_evaluation_job.return_value = {"jobArn": "arn:job"}
    return instance


def create(evaluator, evaluation_type):
    return evaluator.create_evaluation_job(
        job_name="job",
        model_ids=["us.anthropic.claude-sonnet-4-5-20250929-v1:0"],
        dataset_s3_uri="s3://bucket/dataset.jsonl",
        evaluation_type=evaluation_type,
        output_bucket="bucket",
    )


@pytest.mark.parametrize("evaluation_type", sorted(evaluation.EVALUATION_TYPES))
def test_supported_types_create_a_job(evaluator, evaluation_type):
    create(evaluator, evaluation_type)
    evaluator._bedrock.create_evaluation_job.assert_called_once()


def test_unknown_type_is_rejected_before_calling_bedrock(evaluator):
    with pytest.raises(ValueError, match="evaluation_type"):
        create(evaluator, "HUMAN")
    evaluator._bedrock.create_evaluation_job.assert_not_called()


def test_claude_models_are_not_sent_top_p(evaluator):
    create(evaluator, "AUTOMATED")
    configs = evaluator._bedrock.create_evaluation_job.call_args.kwargs["inferenceConfig"]["modelConfigs"]
    assert "topP" not in configs[0]["bedrockModel"]["inferenceParams"]
