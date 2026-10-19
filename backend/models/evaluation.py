"""
Model Evaluation — Integrates with Amazon Bedrock Evaluations to measure
model quality for audit-specific tasks.

Uses LLM-as-a-judge pattern and built-in metrics to compare model performance
on ISO 27001 audit tasks (control evaluation, evidence analysis, report generation).

Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-built-in-metrics.html
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import boto3


REGION = os.environ.get("AWS_REGION", "us-east-1")
EVALUATION_BUCKET = os.environ.get("EVALUATION_BUCKET", "")
EVALUATION_ROLE_ARN = os.environ.get("EVALUATION_ROLE_ARN", "")


@dataclass
class EvaluationTask:
    """A single evaluation prompt with expected output."""
    prompt: str
    reference_answer: str = ""  # Ground truth for comparison
    category: str = ""  # e.g., "control_evaluation", "evidence_retrieval"
    control_id: str = ""  # ISO control reference if applicable
    metadata: dict = field(default_factory=dict)


@dataclass
class EvaluationDataset:
    """Collection of evaluation tasks for benchmarking models."""
    name: str
    description: str
    tasks: list[EvaluationTask] = field(default_factory=list)
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_jsonl(self) -> str:
        """Convert to JSONL format required by Bedrock Evaluations."""
        lines = []
        for task in self.tasks:
            entry = {"prompt": task.prompt}
            if task.reference_answer:
                entry["referenceResponse"] = task.reference_answer
            if task.category:
                entry["category"] = task.category
            lines.append(json.dumps(entry, ensure_ascii=False))
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# PRE-BUILT EVALUATION DATASETS
# ─────────────────────────────────────────────────────────────────────────────

def create_iso27001_evaluation_dataset() -> EvaluationDataset:
    """
    Create a benchmark dataset for evaluating models on ISO 27001 audit tasks.
    Covers: control evaluation, evidence analysis, finding generation, report quality.
    """
    tasks = [
        # ── Control Evaluation Tasks ──
        EvaluationTask(
            prompt=(
                "Evaluate control A.5.1 (Policies for information security) for an organization "
                "that has a security policy document last updated 3 years ago, not communicated to "
                "new employees in the past year. Provide: conformity level, maturity score (0-5), "
                "and a structured finding if non-conforming."
            ),
            reference_answer=(
                "conformity_level: minor_nonconformity\n"
                "maturity_score: 2\n"
                "Finding: The information security policy exists (A.5.1 partially met) but has not "
                "been reviewed within the organization's defined review cycle (3 years exceeds "
                "recommended annual review). Additionally, the lack of communication to new "
                "employees in the past year indicates a gap in the 'communicated to relevant "
                "personnel' requirement. Recommendation: Conduct immediate policy review and update, "
                "establish annual review schedule, integrate policy acknowledgment into onboarding."
            ),
            category="control_evaluation",
            control_id="A.5.1",
        ),
        EvaluationTask(
            prompt=(
                "Assess control A.8.7 (Protection against malware) for an organization running "
                "Windows endpoints with Microsoft Defender enabled, centrally managed, real-time "
                "protection active, definitions updated daily, but no Linux server coverage and "
                "no mobile device protection."
            ),
            reference_answer=(
                "conformity_level: minor_nonconformity\n"
                "maturity_score: 3\n"
                "Finding: Windows endpoint protection is well-implemented and centrally managed "
                "(automated updates, real-time scanning). However, the scope gap for Linux servers "
                "and mobile devices represents incomplete implementation. Modern malware protection "
                "must cover all endpoint types. Recommendation: Extend EDR/anti-malware to Linux "
                "servers (CrowdStrike/CarbonBlack) and implement MDM with threat protection for "
                "mobile devices within 60 days."
            ),
            category="control_evaluation",
            control_id="A.8.7",
        ),
        EvaluationTask(
            prompt=(
                "Evaluate control A.6.3 (Information security awareness, education and training) "
                "for an organization with: annual security awareness training (85% completion rate), "
                "no phishing simulations, no role-based training for developers or admins, "
                "training content not updated since 2023."
            ),
            reference_answer=(
                "conformity_level: minor_nonconformity\n"
                "maturity_score: 2\n"
                "Finding: A basic awareness program exists with reasonable completion rates. "
                "However, three significant gaps: (1) No role-based training for personnel with "
                "elevated security responsibilities (developers, system admins), (2) No behavioral "
                "testing (phishing simulations) to measure effectiveness, (3) Outdated content does "
                "not reflect current threat landscape. ISO 27001:2022 A.6.3 requires training "
                "appropriate to roles AND measured effectiveness."
            ),
            category="control_evaluation",
            control_id="A.6.3",
        ),

        # ── Evidence Analysis Tasks ──
        EvaluationTask(
            prompt=(
                "Given the following evidence for A.5.15 (Access control): "
                "1. Access Control Policy v2.1 (last review: Jan 2025), "
                "2. Active Directory group membership export, "
                "3. Quarterly access review reports (Q1-Q3 2025). "
                "Assess evidence sufficiency for audit evaluation."
            ),
            reference_answer=(
                "Evidence is SUFFICIENT for a conformity assessment.\n"
                "- Policy documentation: Present and current (reviewed within 12 months)\n"
                "- Implementation evidence: AD export demonstrates technical implementation\n"
                "- Maintenance evidence: Quarterly reviews demonstrate ongoing management\n"
                "Potential gap: No evidence of access provisioning/deprovisioning process logs "
                "or evidence of least-privilege enforcement. Recommend requesting joiner/mover/leaver "
                "process documentation for complete assessment."
            ),
            category="evidence_analysis",
            control_id="A.5.15",
        ),

        # ── Report Generation Tasks ──
        EvaluationTask(
            prompt=(
                "Generate an executive summary for an ISO 27001 audit with: "
                "79 controls assessed, 5 major non-conformities (A.5.7, A.5.24, A.8.8, A.8.15, A.8.25), "
                "15 minor non-conformities, 8 opportunities for improvement, "
                "average maturity score 2.8/5. Organization: financial services, 300 employees."
            ),
            reference_answer=(
                "Executive Summary: The ISO 27001:2022 ISMS audit identified significant gaps "
                "requiring remediation before certification recommendation. Five major non-conformities "
                "were identified in critical areas: threat intelligence (A.5.7), incident management "
                "planning (A.5.24), vulnerability management (A.8.8), logging (A.8.15), and secure "
                "development lifecycle (A.8.25). The overall maturity of 2.8/5 indicates the ISMS "
                "is at a 'Defined' but inconsistently managed level. For a financial services "
                "organization handling sensitive data, these gaps represent material risk. "
                "Certification is NOT recommended until major non-conformities are resolved. "
                "Estimated remediation timeline: 90-120 days with dedicated resources."
            ),
            category="report_generation",
        ),

        # ── Reasoning / Cross-Reference Tasks ──
        EvaluationTask(
            prompt=(
                "Identify systemic issues if the following findings exist simultaneously:\n"
                "- A.5.7 (Threat intelligence): No threat intelligence program\n"
                "- A.8.8 (Vulnerability management): Scanning only quarterly, no prioritization\n"
                "- A.8.16 (Monitoring): No SIEM, only basic OS logging\n"
                "- A.5.24 (Incident management): Plan exists but never tested\n"
                "Are these independent findings or indicative of a systemic issue?"
            ),
            reference_answer=(
                "SYSTEMIC ISSUE IDENTIFIED: These findings are interconnected and indicate a "
                "fundamental gap in the organization's security detection and response capability.\n"
                "Root cause: Absent proactive security operations function (no SOC or equivalent).\n"
                "The chain: Without threat intelligence (A.5.7), vulnerability prioritization lacks "
                "context (A.8.8). Without monitoring (A.8.16), threats cannot be detected. Without "
                "tested incident response (A.5.24), even detected incidents cannot be handled.\n"
                "Recommendation: Address as a unified security operations program rather than "
                "individual control gaps. Consider SOC implementation or MDR service."
            ),
            category="reasoning",
        ),
    ]

    return EvaluationDataset(
        name="iso27001_audit_benchmark_v1",
        description="Benchmark dataset for evaluating LLM performance on ISO 27001:2022 audit tasks",
        tasks=tasks,
    )


# ─────────────────────────────────────────────────────────────────────────────
# BEDROCK EVALUATION JOB MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

class ModelEvaluator:
    """
    Manages model evaluation jobs using Amazon Bedrock Evaluations.

    Supports:
    - Automated evaluation with built-in metrics (accuracy, robustness, toxicity)
    - LLM-as-a-judge evaluation for audit quality assessment
    - Custom metric evaluation via prompt datasets
    """

    def __init__(self, region: str = None):
        self.region = region or REGION
        self._bedrock = boto3.client("bedrock", region_name=self.region)
        self._s3 = boto3.client("s3", region_name=self.region)

    def upload_dataset(self, dataset: EvaluationDataset, bucket: str = None) -> str:
        """
        Upload evaluation dataset to S3 in JSONL format.

        Returns:
            S3 URI of the uploaded dataset.
        """
        bucket = bucket or EVALUATION_BUCKET
        if not bucket:
            raise ValueError("EVALUATION_BUCKET must be configured")

        key = f"evaluation-datasets/{dataset.name}/{dataset.version}/dataset.jsonl"
        content = dataset.to_jsonl()

        self._s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="application/jsonl",
        )

        return f"s3://{bucket}/{key}"

    def create_evaluation_job(
        self,
        job_name: str,
        model_ids: list[str],
        dataset_s3_uri: str,
        evaluation_type: str = "LLM_AS_JUDGE",
        judge_model_id: str = "amazon.nova-pro-v1:0",
        output_bucket: str = None,
        metrics: list[str] = None,
    ) -> dict:
        """
        Create a Bedrock model evaluation job.

        Args:
            job_name: Unique job name.
            model_ids: List of model IDs to evaluate.
            dataset_s3_uri: S3 URI of the evaluation dataset (JSONL).
            evaluation_type: 'LLM_AS_JUDGE' or 'AUTOMATED'.
            judge_model_id: Model to use as judge (for LLM_AS_JUDGE type).
            output_bucket: S3 bucket for evaluation results.
            metrics: List of built-in metric names to compute.

        Returns:
            Dict with job ARN and status.
        """
        output_bucket = output_bucket or EVALUATION_BUCKET
        if not output_bucket:
            raise ValueError("Output bucket must be configured")

        if metrics is None:
            metrics = [
                "Builtin.Accuracy",
                "Builtin.Completeness",
                "Builtin.FollowingInstructions",
                "Builtin.ProfessionalStyleAndTone",
            ]

        # Build evaluation config based on type
        if evaluation_type == "LLM_AS_JUDGE":
            evaluation_config = {
                "automated": {
                    "datasetMetricConfigs": [
                        {
                            "taskType": "General",
                            "metricNames": metrics,
                            "dataset": {
                                "name": job_name,
                                "datasetLocation": {
                                    "s3Uri": dataset_s3_uri,
                                },
                            },
                        }
                    ]
                }
            }
        else:
            evaluation_config = {
                "automated": {
                    "datasetMetricConfigs": [
                        {
                            "taskType": "General",
                            "metricNames": metrics,
                            "dataset": {
                                "name": job_name,
                                "datasetLocation": {
                                    "s3Uri": dataset_s3_uri,
                                },
                            },
                        }
                    ]
                }
            }

        # Build inference configs for each model
        inference_configs = []
        for model_id in model_ids:
            inference_configs.append({
                "bedrockModel": {
                    "modelIdentifier": model_id,
                    "inferenceParams": json.dumps({
                        "temperature": 0.2,
                        "maxTokens": 2048,
                        "topP": 0.9,
                    }),
                }
            })

        try:
            response = self._bedrock.create_evaluation_job(
                jobName=job_name,
                jobDescription=f"ISO 27001 audit model evaluation - {datetime.now(timezone.utc).strftime('%Y%m%d')}",
                roleArn=EVALUATION_ROLE_ARN,
                evaluationConfig=evaluation_config,
                inferenceConfig={"modelConfigs": inference_configs},
                outputDataConfig={
                    "s3Uri": f"s3://{output_bucket}/evaluation-results/{job_name}/",
                },
            )

            return {
                "job_arn": response["jobArn"],
                "status": "created",
                "models_evaluated": model_ids,
                "metrics": metrics,
            }
        except Exception as exc:
            return {"error": str(exc), "status": "failed"}

    def get_evaluation_results(self, job_arn: str) -> dict:
        """
        Get results from a completed evaluation job.

        Args:
            job_arn: ARN of the evaluation job.

        Returns:
            Dict with job status and metric results.
        """
        try:
            response = self._bedrock.get_evaluation_job(jobIdentifier=job_arn)
            return {
                "job_name": response.get("jobName"),
                "status": response.get("status"),
                "model_results": response.get("evaluationResults", {}),
                "output_uri": response.get("outputDataConfig", {}).get("s3Uri", ""),
            }
        except Exception as exc:
            return {"error": str(exc)}

    def run_local_benchmark(
        self,
        model_ids: list[str],
        dataset: EvaluationDataset,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> dict:
        """
        Run a local (non-Bedrock Evaluations) benchmark by invoking each model
        on the dataset tasks and measuring latency + token metrics.

        This is useful for quick comparisons without creating a formal evaluation job.

        Args:
            model_ids: Models to benchmark.
            dataset: Evaluation dataset.
            temperature: Temperature for all invocations.
            max_tokens: Max tokens for all invocations.

        Returns:
            Dict with per-model metrics (latency, tokens, cost).
        """
        import time
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=self.region)
        results = {}

        for model_id in model_ids:
            model_results = {
                "model_id": model_id,
                "tasks_completed": 0,
                "tasks_failed": 0,
                "total_latency_ms": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "avg_latency_ms": 0.0,
                "avg_output_tokens_per_second": 0.0,
                "estimated_total_cost_usd": 0.0,
                "per_task_results": [],
            }

            for task in dataset.tasks:
                start = time.perf_counter()
                try:
                    response = bedrock_runtime.converse(
                        modelId=model_id,
                        messages=[{"role": "user", "content": [{"text": task.prompt}]}],
                        inferenceConfig={
                            "temperature": temperature,
                            "maxTokens": max_tokens,
                        },
                    )

                    latency = (time.perf_counter() - start) * 1000
                    usage = response.get("usage", {})
                    input_tokens = usage.get("inputTokens", 0)
                    output_tokens = usage.get("outputTokens", 0)

                    model_results["tasks_completed"] += 1
                    model_results["total_latency_ms"] += latency
                    model_results["total_input_tokens"] += input_tokens
                    model_results["total_output_tokens"] += output_tokens

                    model_results["per_task_results"].append({
                        "category": task.category,
                        "control_id": task.control_id,
                        "latency_ms": round(latency, 1),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "output_text": response["output"]["message"]["content"][0]["text"][:500],
                    })

                except Exception as exc:
                    model_results["tasks_failed"] += 1
                    model_results["per_task_results"].append({
                        "category": task.category,
                        "error": str(exc),
                    })

            # Compute averages
            completed = model_results["tasks_completed"]
            if completed > 0:
                model_results["avg_latency_ms"] = round(model_results["total_latency_ms"] / completed, 1)
                total_seconds = model_results["total_latency_ms"] / 1000
                if total_seconds > 0:
                    model_results["avg_output_tokens_per_second"] = round(
                        model_results["total_output_tokens"] / total_seconds, 1
                    )

            from backend.models.metrics import estimate_cost
            model_results["estimated_total_cost_usd"] = estimate_cost(
                model_id, model_results["total_input_tokens"], model_results["total_output_tokens"]
            )

            results[model_id] = model_results

        return {
            "benchmark_name": dataset.name,
            "models_evaluated": len(model_ids),
            "tasks_per_model": len(dataset.tasks),
            "results": results,
        }
