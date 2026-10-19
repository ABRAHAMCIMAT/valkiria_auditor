"""
CloudWatch Alarms — Defines alerting rules for model and agent performance anomalies.

Alert categories:
1. Latency degradation (model response time exceeds SLA)
2. Error rate spikes (agent or model failure rate above threshold)
3. Cost anomaly (per-audit cost exceeds budget)
4. Throttling (model invocations being rate-limited)
5. Bottleneck persistence (same node is bottleneck repeatedly)
"""

import os
from typing import Optional

import boto3


NAMESPACE = "AgentCore/ISO27001Audit"
REGION = os.environ.get("AWS_REGION", "us-east-1")
SNS_TOPIC_ARN = os.environ.get("ALERTS_SNS_TOPIC_ARN", "")


class AlertManager:
    """
    Creates and manages CloudWatch alarms for the audit system.

    Usage:
        manager = AlertManager()
        manager.create_all_alarms()
    """

    def __init__(self, region: str = None, sns_topic_arn: str = None):
        self.region = region or REGION
        self.sns_topic_arn = sns_topic_arn or SNS_TOPIC_ARN
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client("cloudwatch", region_name=self.region)
        return self._client

    def _create_alarm(
        self,
        alarm_name: str,
        metric_name: str,
        dimensions: list[dict],
        threshold: float,
        comparison: str = "GreaterThanThreshold",
        period: int = 300,
        evaluation_periods: int = 2,
        statistic: str = "Average",
        description: str = "",
        treat_missing: str = "notBreaching",
    ):
        """Create a single CloudWatch alarm."""
        params = {
            "AlarmName": alarm_name,
            "AlarmDescription": description,
            "Namespace": NAMESPACE,
            "MetricName": metric_name,
            "Dimensions": dimensions,
            "Statistic": statistic,
            "Period": period,
            "EvaluationPeriods": evaluation_periods,
            "Threshold": threshold,
            "ComparisonOperator": comparison,
            "TreatMissingData": treat_missing,
        }

        if self.sns_topic_arn:
            params["AlarmActions"] = [self.sns_topic_arn]
            params["OKActions"] = [self.sns_topic_arn]

        self.client.put_metric_alarm(**params)

    # ─────────────────────────────────────────────────────────────────────
    # LATENCY ALARMS
    # ─────────────────────────────────────────────────────────────────────

    def create_model_latency_alarms(self, threshold_ms: float = 30000.0):
        """Alert when any model's average latency exceeds threshold."""
        models = [
            ("gpt-oss-120b", "openai.gpt-oss-120b-1:0"),
            ("qwen3-32b", "qwen.qwen3-32b-v1:0"),
            ("claude-haiku-4.5", "anthropic.claude-haiku-4-5-20250514-v1:0"),
            ("claude-sonnet-4.6", "anthropic.claude-sonnet-4-6-20250514-v1:0"),
            ("llama-4-maverick", "meta.llama4-maverick-17b-instruct-v1:0"),
            ("mistral-large", "mistral.mistral-large-2407-v1:0"),
            ("deepseek-r1", "deepseek.deepseek-r1-v1:0"),
        ]

        for name, model_id in models:
            self._create_alarm(
                alarm_name=f"ISO27001-ModelLatency-{name}",
                metric_name="ModelLatency",
                dimensions=[{"Name": "ModelId", "Value": model_id}],
                threshold=threshold_ms,
                description=f"Model {name} avg latency > {threshold_ms}ms over 2 consecutive 5-min periods",
            )

    def create_agent_execution_time_alarms(self, threshold_ms: float = 120000.0):
        """Alert when agent execution time exceeds 2 minutes."""
        agents = [
            "planning_agent",
            "evidence_agent",
            "organizational_controls_agent",
            "people_controls_agent",
            "technological_controls_agent",
            "consolidation_agent",
        ]

        for agent in agents:
            self._create_alarm(
                alarm_name=f"ISO27001-AgentTime-{agent}",
                metric_name="AgentExecutionTime",
                dimensions=[{"Name": "AgentName", "Value": agent}],
                threshold=threshold_ms,
                description=f"Agent {agent} execution time > {threshold_ms}ms",
            )

    # ─────────────────────────────────────────────────────────────────────
    # ERROR RATE ALARMS
    # ─────────────────────────────────────────────────────────────────────

    def create_agent_error_rate_alarms(self, threshold: float = 0.2):
        """Alert when agent success rate drops below 80%."""
        agents = [
            "planning_agent",
            "evidence_agent",
            "organizational_controls_agent",
            "people_controls_agent",
            "technological_controls_agent",
            "consolidation_agent",
        ]

        for agent in agents:
            self._create_alarm(
                alarm_name=f"ISO27001-AgentErrors-{agent}",
                metric_name="AgentSuccess",
                dimensions=[{"Name": "AgentName", "Value": agent}],
                threshold=1.0 - threshold,
                comparison="LessThanThreshold",
                description=f"Agent {agent} success rate < {(1-threshold)*100}%",
            )

    def create_model_error_alarms(self):
        """Alert when model success rate drops below 90%."""
        models = [
            ("gpt-oss-120b", "openai.gpt-oss-120b-1:0"),
            ("qwen3-32b", "qwen.qwen3-32b-v1:0"),
        ]

        for name, model_id in models:
            self._create_alarm(
                alarm_name=f"ISO27001-ModelErrors-{name}",
                metric_name="ModelSuccess",
                dimensions=[{"Name": "ModelId", "Value": model_id}],
                threshold=0.9,
                comparison="LessThanThreshold",
                description=f"Model {name} success rate < 90%",
            )

    # ─────────────────────────────────────────────────────────────────────
    # COST ALARMS
    # ─────────────────────────────────────────────────────────────────────

    def create_cost_alarm(self, per_audit_threshold_usd: float = 5.0):
        """Alert when a single audit flow exceeds cost threshold."""
        self._create_alarm(
            alarm_name="ISO27001-FlowCostAnomaly",
            metric_name="FlowTotalCost",
            dimensions=[{"Name": "FlowType", "Value": "audit_orchestration"}],
            threshold=per_audit_threshold_usd,
            statistic="Maximum",
            description=f"Audit flow cost > ${per_audit_threshold_usd}",
        )

    # ─────────────────────────────────────────────────────────────────────
    # THROTTLING ALARMS
    # ─────────────────────────────────────────────────────────────────────

    def create_throttling_alarms(self):
        """Alert on model throttling."""
        models = [
            ("gpt-oss-120b", "openai.gpt-oss-120b-1:0"),
            ("qwen3-32b", "qwen.qwen3-32b-v1:0"),
        ]

        for name, model_id in models:
            self._create_alarm(
                alarm_name=f"ISO27001-Throttle-{name}",
                metric_name="ModelThrottles",
                dimensions=[{"Name": "ModelId", "Value": model_id}],
                threshold=5.0,
                statistic="Sum",
                description=f"Model {name} throttled > 5 times in 5 min",
            )

    # ─────────────────────────────────────────────────────────────────────
    # ORCHESTRATION ALARMS
    # ─────────────────────────────────────────────────────────────────────

    def create_flow_time_alarm(self, threshold_ms: float = 600000.0):
        """Alert when full orchestration flow exceeds 10 minutes."""
        self._create_alarm(
            alarm_name="ISO27001-FlowTotalTime",
            metric_name="FlowTotalTime",
            dimensions=[{"Name": "FlowType", "Value": "audit_orchestration"}],
            threshold=threshold_ms,
            description=f"Orchestration flow > {threshold_ms/1000}s",
        )

    def create_flow_failure_alarm(self):
        """Alert on any orchestration flow failure."""
        self._create_alarm(
            alarm_name="ISO27001-FlowFailure",
            metric_name="FlowSuccess",
            dimensions=[{"Name": "FlowType", "Value": "audit_orchestration"}],
            threshold=1.0,
            comparison="LessThanThreshold",
            statistic="Minimum",
            evaluation_periods=1,
            description="Orchestration flow failed (any node failure)",
        )

    # ─────────────────────────────────────────────────────────────────────
    # DEPLOY ALL
    # ─────────────────────────────────────────────────────────────────────

    def create_all_alarms(self):
        """Create all monitoring alarms."""
        self.create_model_latency_alarms()
        self.create_agent_execution_time_alarms()
        self.create_agent_error_rate_alarms()
        self.create_model_error_alarms()
        self.create_cost_alarm()
        self.create_throttling_alarms()
        self.create_flow_time_alarm()
        self.create_flow_failure_alarm()
