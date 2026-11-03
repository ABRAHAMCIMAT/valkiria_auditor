"""
Decides whether a fine-tuned adapter replaces the Phase 1 model, comparing the
predictions of both over the same holdout. Exit code 0 means promote.

Usage:
    python promotion_gate.py --baseline baseline.jsonl --candidate adapter.jsonl
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_model import load_holdout  # noqa: E402
from safe_paths import resolve_in_workspace  # noqa: E402

MIN_CONCORDANCE_GAIN = 0.05
MIN_VALID_RATE = 0.95
MAX_MAE_INCREASE = 0.0


def score(predictions: dict, holdout: list[dict]) -> dict:
    """Score predictions, counting anything missing or malformed as wrong."""
    valid = correct = 0
    errors = []
    for item in holdout:
        prediction = predictions.get(item["control_id"]) or {}
        level = prediction.get("conformity_level")
        maturity = prediction.get("maturity_score")
        if level is None or not isinstance(maturity, (int, float)) or isinstance(maturity, bool):
            continue
        valid += 1
        correct += level == item["conformity_level"]
        errors.append(abs(maturity - item["maturity_score"]))
    total = len(holdout)
    return {
        "valid_rate": valid / total,
        "concordance": correct / total,
        "maturity_mae": sum(errors) / len(errors) if errors else float("inf"),
    }


def decide(baseline: dict, candidate: dict) -> list[str]:
    """Return the reasons not to promote. Empty means promote."""
    reasons = []
    if candidate["valid_rate"] < MIN_VALID_RATE:
        reasons.append(f"valid_rate {candidate['valid_rate']:.2f} < {MIN_VALID_RATE}")
    if candidate["concordance"] < baseline["concordance"] + MIN_CONCORDANCE_GAIN:
        reasons.append(
            f"concordance {candidate['concordance']:.2f} does not beat baseline "
            f"{baseline['concordance']:.2f} by {MIN_CONCORDANCE_GAIN}"
        )
    if candidate["maturity_mae"] > baseline["maturity_mae"] + MAX_MAE_INCREASE:
        reasons.append(f"maturity_mae {candidate['maturity_mae']:.2f} worse than {baseline['maturity_mae']:.2f}")
    return reasons


def load_predictions(path: Path) -> dict:
    text = resolve_in_workspace(path).read_text(encoding="utf-8")
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    return {row["control_id"]: row.get("prediction") for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()

    holdout = load_holdout()
    baseline = score(load_predictions(args.baseline), holdout)
    candidate = score(load_predictions(args.candidate), holdout)
    print(f"[INFO] Baseline: {baseline}")
    print(f"[INFO] Candidate: {candidate}")

    reasons = decide(baseline, candidate)
    for reason in reasons:
        print(f"[WARN] Not promoted: {reason}")
    if not reasons:
        print("[INFO] Promote: the adapter beats the baseline on the holdout")
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
