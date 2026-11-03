"""
Builds the ARN that RetrieveAndGenerate expects for a model.

Claude Sonnet 4.5 is invoked through a cross-region inference profile, whose ARN
includes the account, unlike a foundation model ARN.
"""

import os
from functools import lru_cache

import boto3


CROSS_REGION_PREFIXES = ("us", "eu", "apac", "global")


@lru_cache(maxsize=1)
def _account_id() -> str:
    return boto3.client("sts", region_name=os.environ.get("AWS_REGION", "us-east-1")).get_caller_identity()["Account"]


def model_arn(model_id: str, region: str) -> str:
    """Return the inference profile ARN for a cross-region ID, else the foundation model ARN."""
    if model_id.split(".", 1)[0] in CROSS_REGION_PREFIXES:
        return f"arn:aws:bedrock:{region}:{_account_id()}:inference-profile/{model_id}"
    return f"arn:aws:bedrock:{region}::foundation-model/{model_id}"
