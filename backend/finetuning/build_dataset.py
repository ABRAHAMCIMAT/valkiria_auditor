"""
Builds the training datasets from human-reviewed examples.

Input: data/curated/<agent>.jsonl, one reviewed example per line.
Output: <out>/<agent>/train.jsonl and val.jsonl in chat format.

The build refuses unreviewed examples, labels outside the schema, overlap with
the evaluation sets, and datasets too small to train on. A label must come from a
person reviewing a real source: a model trained on invented labels learns noise.

Usage:
    python build_dataset.py --out build/datasets [--agent controls_a5]
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import AGENTS, ANNEX_A_2022, system_prompt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
CURATED_DIR = Path(__file__).resolve().parent / "data" / "curated"
HOLDOUT_FILES = [
    REPO_ROOT / "testsets" / "iso27001_controls_assessment.json",
    REPO_ROOT / "deliverables" / "Avance5.dev" / "evaluation-sets" / "gov_eval_set.json",
]

CONFORMITY_LEVELS = {
    "conforming",
    "minor_nonconformity",
    "major_nonconformity",
    "opportunity_for_improvement",
}
REQUIRED_FIELDS = {
    "id", "control_id", "evidence", "conformity_level", "maturity_score",
    "finding", "recommendation", "source_document", "review_status", "reviewed_by",
}
MIN_TRAIN_EXAMPLES = 100
MIN_EXAMPLES_PER_LABEL = 10
MIN_EVIDENCE_LENGTH = 40
VALIDATION_BUCKETS = 10  # 1 in 10 source documents goes to validation


class DatasetError(Exception):
    pass


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def holdout_fingerprints() -> set[str]:
    """Evidence texts in the evaluation sets, which must never reach training."""
    texts = set()
    for path in HOLDOUT_FILES:
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data["requirements"] if isinstance(data, dict) else data
        for record in records:
            if "evidence" in record:
                texts.add(record["evidence"])
            for context in record.get("retrieved_context", []):
                texts.add(context.get("content", ""))
    return {normalize_text(text) for text in texts if text}


def validate_example(example: dict, agent: str, holdout: set[str]) -> None:
    missing = REQUIRED_FIELDS - example.keys()
    if missing:
        raise DatasetError(f"missing fields: {sorted(missing)}")
    if example["review_status"] != "approved":
        raise DatasetError(f"review_status is {example['review_status']}, expected approved")
    if not str(example["reviewed_by"]).strip():
        raise DatasetError("reviewed_by is empty")
    if example["conformity_level"] not in CONFORMITY_LEVELS:
        raise DatasetError(f"unknown conformity_level: {example['conformity_level']}")
    if example["control_id"] not in ANNEX_A_2022:
        raise DatasetError(f"control not in Annex A 2022: {example['control_id']}")
    domain = AGENTS[agent].get("domain")
    if domain and not example["control_id"].startswith(f"{domain}."):
        raise DatasetError(f"control {example['control_id']} does not belong to {agent}")
    score = example["maturity_score"]
    if not isinstance(score, int) or not 0 <= score <= 5:
        raise DatasetError(f"maturity_score must be an integer from 0 to 5: {score}")
    if len(str(example["evidence"]).strip()) < MIN_EVIDENCE_LENGTH:
        raise DatasetError("evidence is too short")
    if normalize_text(example["evidence"]) in holdout:
        raise DatasetError("evidence overlaps with an evaluation set")


def to_chat(example: dict, prompt: str) -> dict:
    answer = {
        "control_id": example["control_id"],
        "conformity_level": example["conformity_level"],
        "maturity_score": example["maturity_score"],
        "finding": example["finding"],
        "recommendation": example["recommendation"],
    }
    user = (
        f"Evalúa la siguiente evidencia contra el control {example['control_id']}.\n\n"
        f"EVIDENCIA:\n{example['evidence']}\n\n"
        "Responde únicamente con el hallazgo en formato JSON."
    )
    return {
        "id": example["id"],
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
            {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
        ],
    }


def is_validation_document(source_document: str) -> bool:
    """Split by source document, so passages of one report never land on both sides."""
    digest = hashlib.sha256(source_document.encode("utf-8")).hexdigest()
    return int(digest, 16) % VALIDATION_BUCKETS == 0


def build_agent_dataset(agent: str, curated_path: Path, holdout: set[str]) -> tuple[list[dict], list[dict]]:
    examples = []
    seen = set()
    for number, line in enumerate(curated_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            example = json.loads(line)
            validate_example(example, agent, holdout)
        except (json.JSONDecodeError, DatasetError) as exc:
            raise DatasetError(f"{curated_path.name}:{number}: {exc}") from exc
        fingerprint = normalize_text(example["evidence"])
        if fingerprint in seen:
            raise DatasetError(f"{curated_path.name}:{number}: duplicate evidence")
        seen.add(fingerprint)
        examples.append(example)

    prompt = system_prompt(agent)
    train = [to_chat(e, prompt) for e in examples if not is_validation_document(e["source_document"])]
    val = [to_chat(e, prompt) for e in examples if is_validation_document(e["source_document"])]

    if len(train) < MIN_TRAIN_EXAMPLES:
        raise DatasetError(f"{agent}: {len(train)} training examples, at least {MIN_TRAIN_EXAMPLES} are required")
    if not val:
        raise DatasetError(f"{agent}: no validation examples, add more source documents")

    train_ids = {e["id"] for e in train}
    labels = [e["conformity_level"] for e in examples if e["id"] in train_ids]
    for level in CONFORMITY_LEVELS:
        if labels.count(level) < MIN_EXAMPLES_PER_LABEL:
            raise DatasetError(
                f"{agent}: {labels.count(level)} training examples of {level}, "
                f"at least {MIN_EXAMPLES_PER_LABEL} are required"
            )
    return train, val


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--agent", choices=sorted(AGENTS))
    parser.add_argument("--curated-dir", type=Path, default=CURATED_DIR)
    args = parser.parse_args()

    holdout = holdout_fingerprints()
    failed = False
    for agent in ([args.agent] if args.agent else sorted(AGENTS)):
        curated = args.curated_dir / f"{agent}.jsonl"
        if not curated.exists():
            print(f"[ERROR] {agent}: no curated data at {curated}")
            failed = True
            continue
        try:
            train, val = build_agent_dataset(agent, curated, holdout)
        except DatasetError as exc:
            print(f"[ERROR] {exc}")
            failed = True
            continue
        write_jsonl(args.out / agent / "train.jsonl", train)
        write_jsonl(args.out / agent / "val.jsonl", val)
        print(f"[INFO] {agent}: {len(train)} train, {len(val)} val")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
