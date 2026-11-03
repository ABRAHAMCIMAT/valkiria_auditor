"""
Runs a model over the holdout evaluation set and writes its predictions, for
comparing an adapter against the Phase 1 baseline with promotion_gate.py.

The model comes from the same environment variables the agents use: MODEL_ID for
Bedrock, or SAGEMAKER_ENDPOINT_NAME for a fine-tuned adapter.

Usage:
    MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0 python evaluate_model.py --out baseline.jsonl
    SAGEMAKER_ENDPOINT_NAME=<endpoint> python evaluate_model.py --out adapter.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import AGENTS, system_prompt  # noqa: E402

HOLDOUT_PATH = REPO_ROOT / "testsets" / "iso27001_controls_assessment.json"
LABEL_ALIASES = {
    "minor_non_conformity": "minor_nonconformity",
    "major_non_conformity": "major_nonconformity",
}
DOMAIN_AGENTS = {config["domain"]: name for name, config in AGENTS.items() if "domain" in config}
MAX_TOKENS = 1024


def load_holdout(path: Path = HOLDOUT_PATH) -> list[dict]:
    requirements = json.loads(path.read_text(encoding="utf-8"))["requirements"]
    return [
        {
            "control_id": r["ref_id"],
            "agent": DOMAIN_AGENTS[r["domain"]],
            "evidence": r["evidence"],
            "conformity_level": LABEL_ALIASES.get(r["conformity"], r["conformity"]),
            "maturity_score": r["maturity_level"],
        }
        for r in requirements
    ]


def parse_prediction(answer: str) -> dict | None:
    text = answer.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    sys.path.insert(0, str(REPO_ROOT / "backend" / "agentcore"))
    from shared.model_loader import load_model
    from strands import Agent

    with args.out.open("w", encoding="utf-8") as f:
        for item in load_holdout():
            agent = Agent(
                model=load_model(temperature=0.0, max_tokens=MAX_TOKENS),
                system_prompt=system_prompt(item["agent"]),
                callback_handler=None,
            )
            prompt = (
                f"Evalúa la siguiente evidencia contra el control {item['control_id']}.\n\n"
                f"EVIDENCIA:\n{item['evidence']}\n\n"
                "Responde únicamente con el hallazgo en formato JSON con los campos "
                "control_id, conformity_level, maturity_score, finding y recommendation."
            )
            prediction = parse_prediction(str(agent(prompt)))
            f.write(json.dumps({"control_id": item["control_id"], "prediction": prediction}, ensure_ascii=False) + "\n")
            print(f"[INFO] {item['control_id']}: {(prediction or {}).get('conformity_level', 'invalid')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
