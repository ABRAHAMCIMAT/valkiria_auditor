"""
Launches one QLoRA job per agent on SageMaker. Without --execute it only prints
the plan and its estimated cost, so nothing is billed by accident.

Usage:
    python launch_training.py --agent controls_a7 --role-arn <arn> --train-s3 s3://bucket/fine-tuning/datasets
    python launch_training.py --agent controls_a7 --role-arn <arn> --train-s3 s3://... --execute
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents import AGENTS  # noqa: E402

INSTANCE_TYPE = "ml.g5.2xlarge"
INSTANCE_USD_PER_HOUR = 1.515  # On-demand us-east-1: confirm before budgeting
MAX_RUN_HOURS = 6
FRAMEWORK_VERSION = "2.6.0"
PY_VERSION = "py312"
SOURCE_DIR = Path(__file__).resolve().parent / "training"


def job_plan(agent: str, train_s3: str) -> dict:
    return {
        "agent": agent,
        "base_name": f"iso27001-{agent.replace('_', '-')}-ft",
        "hyperparameters": {"model_id": AGENTS[agent]["base_model"]},
        "train_uri": f"{train_s3.rstrip('/')}/{agent}/",
        "max_cost_usd": round(MAX_RUN_HOURS * INSTANCE_USD_PER_HOUR, 2),
    }


def launch(plan: dict, role_arn: str) -> str:
    from sagemaker.pytorch import PyTorch

    estimator = PyTorch(
        entry_point="train_qlora.py",
        source_dir=str(SOURCE_DIR),
        role=role_arn,
        instance_type=INSTANCE_TYPE,
        instance_count=1,
        framework_version=FRAMEWORK_VERSION,
        py_version=PY_VERSION,
        hyperparameters=plan["hyperparameters"],
        base_job_name=plan["base_name"],
        max_run=MAX_RUN_HOURS * 3600,
        volume_size=100,
    )
    estimator.fit({"train": plan["train_uri"]}, wait=False)
    return estimator.latest_training_job.name


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True, choices=sorted(AGENTS) + ["all"])
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--train-s3", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    agents = sorted(AGENTS) if args.agent == "all" else [args.agent]
    plans = [job_plan(agent, args.train_s3) for agent in agents]
    for plan in plans:
        print(f"[INFO] {plan['base_name']}: {plan['hyperparameters']['model_id']} "
              f"on {INSTANCE_TYPE}, data {plan['train_uri']}, at most ${plan['max_cost_usd']}")
    print(f"[INFO] Maximum total: ${sum(p['max_cost_usd'] for p in plans):.2f}")

    if not args.execute:
        print("[INFO] Plan only. Add --execute to launch.")
        return

    for plan in plans:
        print(f"[INFO] Started job: {launch(plan, args.role_arn)}")


if __name__ == "__main__":
    main()
