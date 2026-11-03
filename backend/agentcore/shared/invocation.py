"""
Sub-agent invocation for the orchestrator.

In AgentCore each sub-agent is a runtime reached with a SigV4-signed
InvokeAgentRuntime call, addressed by the ARN in <KEY>_AGENT_ARN. In local dev
(LOCAL_DEV=1) sub-agents run on separate ports and are reached over plain HTTP.
"""

import json
import os
import uuid

import boto3
import httpx
from botocore.config import Config


# Port assignment documented in IMPLEMENTATION.md (section 5.4)
LOCAL_PORTS = {
    "PLANNING": 8081,
    "EVIDENCE": 8082,
    "ORG_CONTROLS": 8083,
    "PEOPLE_CONTROLS": 8084,
    "PHYSICAL_CONTROLS": 8085,
    "TECH_CONTROLS": 8086,
}

# A domain evaluation can run for many minutes. Retries stay off because
# repeating a call would duplicate model spend and saved findings.
SUB_AGENT_TIMEOUT_SECONDS = 900
MIN_RUNTIME_SESSION_ID_LENGTH = 33

_client = None


def _agentcore_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "bedrock-agentcore",
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
            config=Config(
                read_timeout=SUB_AGENT_TIMEOUT_SECONDS,
                retries={"max_attempts": 0},
            ),
        )
    return _client


def runtime_session_id(session_id: str, agent_key: str) -> str:
    """Build a per-sub-agent session id that meets the API minimum length."""
    base = f"{session_id or uuid.uuid4().hex}-{agent_key.lower()}"
    return base.ljust(MIN_RUNTIME_SESSION_ID_LENGTH, "0")


def _invoke_runtime(agent_arn: str, agent_key: str, payload: dict) -> dict:
    response = _agentcore_client().invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=runtime_session_id(payload.get("session_id", ""), agent_key),
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(payload).encode("utf-8"),
    )
    return json.loads(response["response"].read())


def _invoke_local(agent_key: str, payload: dict) -> dict:
    default_url = f"http://localhost:{LOCAL_PORTS[agent_key]}/invocations"
    url = os.environ.get(f"{agent_key}_AGENT_ENDPOINT", default_url)
    response = httpx.post(url, json=payload, timeout=float(SUB_AGENT_TIMEOUT_SECONDS))
    response.raise_for_status()
    return response.json()


def invoke_sub_agent(agent_key: str, payload: dict) -> dict:
    """
    Invoke a sub-agent and return its response.

    A failure returns an explicit error telling the orchestrator to report the
    domain as not evaluated, so a failed domain cannot turn into invented findings.

    Args:
        agent_key: One of the LOCAL_PORTS keys.
        payload: Body for the sub-agent entrypoint (prompt, session_id, actor_id).
    """
    try:
        agent_arn = os.environ.get(f"{agent_key}_AGENT_ARN", "")
        if agent_arn:
            return _invoke_runtime(agent_arn, agent_key, payload)
        if os.environ.get("LOCAL_DEV", "0") == "1":
            return _invoke_local(agent_key, payload)
        raise RuntimeError(f"{agent_key}_AGENT_ARN is not configured")
    except Exception as exc:
        print(f"[ERROR] Sub-agent {agent_key} failed: {exc}")
        return {
            "status": "error",
            "agent": agent_key,
            "error": f"Sub-agent invocation failed: {exc}",
            "instruction": (
                "Report this domain as NOT EVALUATED in the final report. "
                "Do not produce findings for its controls."
            ),
        }
