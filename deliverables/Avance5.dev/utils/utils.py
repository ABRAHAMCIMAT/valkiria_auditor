from pathlib import Path
import json
import re
import time
import boto3
import yaml
from dotenv import load_dotenv


def get_bedrock_client(env_path: str | Path = ".env"):
    """Load AWS credentials from .env and return a Bedrock Runtime client."""
    load_dotenv(Path(env_path))
    return boto3.client("bedrock-runtime")


def load_prompt(path: str | Path) -> str:
    """Load a prompt file and return its contents as a string."""
    prompt_path = Path(path)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def validate_models(models: dict, bedrock_client) -> list[dict]:
    """Ping each model with a minimal converse() call and return a status list."""
    results = []
    total = len(models)
    for i, (name, endpoint) in enumerate(models.items(), start=1):
        print(f"[{i}/{total}] {name} ({endpoint}) ... ", end="", flush=True)
        try:
            resp = bedrock_client.converse(
                modelId=endpoint,
                messages=[{"role": "user", "content": [{"text": "Reply with OK."}]}],
                inferenceConfig={"maxTokens": 16},
            )
            blocks = resp["output"]["message"]["content"]
            text = next((b["text"] for b in blocks if "text" in b), "").strip()
            print("OK")
            results.append({"model": name, "status": "OK", "detail": text[:60]})
        except Exception as e:
            print(f"ERROR\n", e)
            results.append({"model": name, "status": "ERROR", "detail": str(e)[:80]})
    return results


def load_config(path: str | Path) -> dict:
    """Load a YAML file and return its contents as a dictionary."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_assessable_nodes(yaml_path: str | Path, ref_id_prefix: str | None = None) -> dict[str, str]:
    """Return a {ref_id: name} catalog of all assessable clauses in an ISO 27001 YAML file.

    Args:
        yaml_path: Path to the ISO 27001 YAML file.
        ref_id_prefix: Optional filter. Only clauses whose ref_id starts with this
                       string are included (e.g. "4", "9", "A.9", "A.1").
                       Pass None to return all assessable clauses.

    Returns:
        Ordered dict mapping ref_id (str) to clause name (str).
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    nodes = data["objects"]["framework"]["requirement_nodes"]
    result = {}
    for node in nodes:
        if not node.get("assessable"):
            continue
        ref_id = str(node.get("ref_id", ""))
        if ref_id_prefix is not None and not ref_id.startswith(ref_id_prefix):
            continue
        result[ref_id] = node.get("name", "").strip()

    return result


def _get_node(yaml_path: str | Path, ref_id: str) -> dict:
    """Return the full node dict for a given ref_id from an ISO 27001 YAML file."""
    yaml_path = Path(yaml_path)
    with yaml_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    nodes = data["objects"]["framework"]["requirement_nodes"]
    for node in nodes:
        if str(node.get("ref_id", "")) == ref_id:
            return node
    raise KeyError(f"ref_id '{ref_id}' not found in {yaml_path}")


def build_clause_text(yaml_path: str | Path, ref_id: str) -> str:
    """Build a clause_to_evaluate string for a given ref_id.

    Looks up the full node from the ISO 27001 YAML file and combines ref_id,
    name, description, and components into a single block of text ready to be
    injected into the {{CLAUSE_TO_EVALUATE}} placeholder.

    Args:
        yaml_path: Path to the ISO 27001 YAML file.
        ref_id: Clause identifier to look up (e.g. "9.3", "6.1.2", "A.9.1.1").

    Returns:
        Formatted string with the clause identifier, description, and atomic
        sub-requirements (components) when available.

    Raises:
        KeyError: If ref_id is not found in the YAML file.
    """
    node = _get_node(yaml_path, ref_id)
    name = node.get("name", "").strip()
    description = node.get("description", "").strip()
    components = node.get("components", [])

    lines = [f"Clausula {ref_id} - {name}"]
    if description:
        lines.append(description)
    if components:
        lines.append("Requisitos especificos:")
        lines.extend(components)

    return "\n".join(lines)


def build_agent_message(record: dict, prompt: str) -> tuple[str, str]:
    """Split an agent prompt and fill placeholders from a single eval record.

    Splits the prompt on '### MENSAJE DEL USUARIO', then replaces
    {{RETRIEVED_CONTEXT}} and {{CLAUSE_TO_EVALUATE}} with the record values.

    Returns:
        (system_prompt, user_message) as a tuple of strings.
    """
    system_prompt, user_template = prompt.split("### MENSAJE DEL USUARIO")
    user_message = (
        user_template.strip()
        .replace(
            "{{RETRIEVED_CONTEXT}}",
            json.dumps(record["retrieved_context"], ensure_ascii=False, indent=2),
        )
        .replace("{{CLAUSE_TO_EVALUATE}}", record["clause_to_evaluate"])
    )
    return '\n'.join([system_prompt.strip(), user_message])


def build_eval_batch(records: list[dict], prompt: str) -> list[dict]:
    """Build a list of ready-to-invoke message pairs from an eval dataset.

    Calls build_agent_message for each record and attaches eval metadata.

    Returns:
        List of dicts with keys: system_prompt, user_message,
        clause_to_evaluate, expected_severity.
    """
    return [
        {
            "message": build_agent_message(record, prompt),
            "clause_to_evaluate": record["clause_to_evaluate"],
            "expected_severity": record["expected_severity"],
        }
        for record in records
    ]
