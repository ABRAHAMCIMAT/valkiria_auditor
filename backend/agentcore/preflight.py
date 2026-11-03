"""
Checks what a deployment needs before spending on it: credentials, model access,
tool calling on the model, and the knowledge base. Makes one small Converse call.

Usage:
    python preflight.py --knowledge-base-id <id>
"""

import argparse
import os
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
# Every agent depends on tool calling, so a model answering text only is not enough
PROBE_TOOL = {
    "toolSpec": {
        "name": "get_control",
        "description": "Get an ISO 27001 control by id",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {"control_id": {"type": "string"}},
            "required": ["control_id"],
        }},
    },
}


def check_model(client, model_id: str) -> str | None:
    """Return a problem description, or None if the model can call tools."""
    try:
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "You must use the get_control tool to fetch control A.5.1."}]}],
            toolConfig={"tools": [PROBE_TOOL], "toolChoice": {"auto": {}}},
            # The same sampling parameters the agents send
            inferenceConfig={"maxTokens": 300, "temperature": 0.0},
        )
    except (ClientError, BotoCoreError) as exc:
        return str(exc)
    content = response["output"]["message"]["content"]
    if not any("toolUse" in block for block in content):
        return "did not call the tool"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "us-east-1"))
    parser.add_argument("--model", default=MODEL_ID)
    args = parser.parse_args()

    problems = []

    try:
        identity = boto3.client("sts", region_name=args.region).get_caller_identity()
        print(f"[INFO] Account {identity['Account']}, region {args.region}")
    except (ClientError, BotoCoreError) as exc:
        print(f"[ERROR] No usable AWS credentials: {exc}")
        return 1

    runtime = boto3.client("bedrock-runtime", region_name=args.region)
    problem = check_model(runtime, args.model)
    if problem:
        problems.append(f"model {args.model}: {problem}")
    else:
        print(f"[INFO] Model {args.model}: calls tools")

    try:
        kb = boto3.client("bedrock-agent", region_name=args.region).get_knowledge_base(
            knowledgeBaseId=args.knowledge_base_id
        )["knowledgeBase"]
        print(f"[INFO] Knowledge base {kb['name']}: {kb['status']}")
        if kb["status"] != "ACTIVE":
            problems.append(f"knowledge base status is {kb['status']}")
    except (ClientError, BotoCoreError) as exc:
        problems.append(f"knowledge base {args.knowledge_base_id}: {exc}")

    for problem in problems:
        print(f"[ERROR] {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
