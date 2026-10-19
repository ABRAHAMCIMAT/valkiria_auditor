"""
Unified Observability Collector — Wires structured logging, CloudWatch metrics,
and trace context into a single entry point for agent instrumentation.

This is the primary integration point that agents use to emit observability data.
It combines:
- StructuredLogger (JSON logs → CloudWatch Logs)
- CloudWatchPublisher (custom metrics → CloudWatch Metrics)
- TraceContext (distributed tracing headers)

Usage in an agent:

    from backend.observability.collector import ObservabilityCollector

    obs = ObservabilityCollector(
        agent_name="organizational_controls_agent",
        audit_id="audit_001",
        session_id="session_xyz",
        actor_id="auditor_1",
    )

    # Track a model invocation
    with obs.track_model("openai.gpt-oss-120b-1:0") as model:
        response = bedrock_model.invoke(...)
        model.set_tokens(input_tokens=200, output_tokens=800)

    # Track a tool call
    with obs.track_tool("query_knowledge_base") as tool:
        result = query_knowledge_base(question="...")
        tool.set_rag_result(sources=5, relevance=0.85)

    # Finalize and publish all metrics
    summary = obs.finalize()
"""

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from backend.observability.logging import StructuredLogger, TraceContext
from backend.observability.cloudwatch import CloudWatchPublisher
from backend.observability.s3_store import S3MetricsStore
from backend.models.metrics import estimate_cost


@dataclass
class _ModelInvocationRecord:
    """Internal record for a single model call."""
    model_id: str = ""
    start_time: float = 0.0
    latency_ms: float = 0.0
    ttft_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    success: bool = True
    error_type: str = ""
    throttled: bool = False


@dataclass
class _ToolCallRecord:
    """Internal record for a tool execution."""
    tool_name: str = ""
    start_time: float = 0.0
    duration_ms: float = 0.0
    success: bool = True
    error: str = ""
    rag_sources: int = 0
    rag_relevance: float = 0.0


class ObservabilityCollector:
    """
    Unified observability for a single agent invocation.
    Combines logging, metrics, and tracing in one API.
    """

    def __init__(
        self,
        agent_name: str,
        audit_id: str = "",
        session_id: str = "",
        actor_id: str = "",
        trace_ctx: Optional[TraceContext] = None,
        publish_metrics: bool = True,
    ):
        self.agent_name = agent_name
        self.publish_metrics = publish_metrics

        # Trace context (create or inherit)
        self.trace_ctx = trace_ctx or TraceContext(
            audit_id=audit_id,
            session_id=session_id,
            actor_id=actor_id,
        )

        # Logger
        self.logger = StructuredLogger(
            agent_name=agent_name,
            trace_ctx=self.trace_ctx,
        )

        # CloudWatch publisher
        self._publisher = CloudWatchPublisher() if publish_metrics else None

        # S3 persistence
        self._s3_store = S3MetricsStore() if publish_metrics else None

        # Internal tracking
        self._start_time = time.perf_counter()
        self._model_records: list[_ModelInvocationRecord] = []
        self._tool_records: list[_ToolCallRecord] = []

        self.logger.info("Agent invocation started")

    @contextmanager
    def track_model(self, model_id: str):
        """
        Track a model invocation with automatic timing and cost estimation.

        Usage:
            with obs.track_model("openai.gpt-oss-120b-1:0") as model:
                response = invoke_model(...)
                model.set_tokens(input_tokens=100, output_tokens=500)
        """
        record = _ModelInvocationRecord(
            model_id=model_id,
            start_time=time.perf_counter(),
        )
        self.logger.set_model(model_id)

        class _ModelCtx:
            def set_tokens(self_inner, input_tokens: int, output_tokens: int):
                record.input_tokens = input_tokens
                record.output_tokens = output_tokens

            def set_ttft(self_inner, ttft_ms: float):
                record.ttft_ms = ttft_ms

            def set_throttled(self_inner):
                record.throttled = True

            def set_error(self_inner, error_type: str):
                record.success = False
                record.error_type = error_type

        ctx = _ModelCtx()
        try:
            yield ctx
        except Exception as exc:
            record.success = False
            record.error_type = type(exc).__name__
            raise
        finally:
            record.latency_ms = (time.perf_counter() - record.start_time) * 1000
            record.cost_usd = estimate_cost(model_id, record.input_tokens, record.output_tokens)
            self._model_records.append(record)

            # Emit log
            self.logger.log_model_invocation(
                model_id=model_id,
                latency_ms=record.latency_ms,
                input_tokens=record.input_tokens,
                output_tokens=record.output_tokens,
                ttft_ms=record.ttft_ms,
                success=record.success,
                error_type=record.error_type,
                cost_usd=record.cost_usd,
            )

            # Publish to CloudWatch
            if self._publisher:
                otps = (
                    record.output_tokens / (record.latency_ms / 1000.0)
                    if record.latency_ms > 0 and record.output_tokens > 0
                    else 0.0
                )
                self._publisher.publish_model_metrics(
                    model_id=model_id,
                    agent_name=self.agent_name,
                    latency_ms=record.latency_ms,
                    ttft_ms=record.ttft_ms,
                    input_tokens=record.input_tokens,
                    output_tokens=record.output_tokens,
                    output_tokens_per_second=otps,
                    cost_usd=record.cost_usd,
                    success=record.success,
                    throttled=record.throttled,
                )

    @contextmanager
    def track_tool(self, tool_name: str):
        """
        Track a tool call with automatic timing.

        Usage:
            with obs.track_tool("query_knowledge_base") as tool:
                result = query_knowledge_base(...)
                tool.set_rag_result(sources=5, relevance=0.85)
        """
        record = _ToolCallRecord(
            tool_name=tool_name,
            start_time=time.perf_counter(),
        )

        class _ToolCtx:
            def set_rag_result(self_inner, sources: int = 0, relevance: float = 0.0):
                record.rag_sources = sources
                record.rag_relevance = relevance

            def set_error(self_inner, error: str):
                record.success = False
                record.error = error

        ctx = _ToolCtx()
        try:
            yield ctx
        except Exception as exc:
            record.success = False
            record.error = str(exc)[:200]
            raise
        finally:
            record.duration_ms = (time.perf_counter() - record.start_time) * 1000
            self._tool_records.append(record)

            self.logger.log_tool_call(
                tool_name=tool_name,
                duration_ms=record.duration_ms,
                success=record.success,
                error=record.error,
            )

    def child_context(self) -> TraceContext:
        """Create a child trace context for sub-agent invocation."""
        return self.trace_ctx.child_span()

    def finalize(self) -> dict:
        """
        Finalize collection, compute aggregates, publish agent-level metrics,
        and return a summary dict.
        """
        total_time_ms = (time.perf_counter() - self._start_time) * 1000

        # Aggregate model metrics
        total_llm_time = sum(r.latency_ms for r in self._model_records)
        total_input_tokens = sum(r.input_tokens for r in self._model_records)
        total_output_tokens = sum(r.output_tokens for r in self._model_records)
        total_cost = sum(r.cost_usd for r in self._model_records)
        turns = len(self._model_records)

        # Aggregate tool metrics
        total_tool_time = sum(r.duration_ms for r in self._tool_records)
        tool_count = len(self._tool_records)
        tool_errors = sum(1 for r in self._tool_records if not r.success)
        rag_queries = sum(1 for r in self._tool_records if r.rag_sources > 0)

        overhead = max(0, total_time_ms - total_llm_time - total_tool_time)
        success = all(r.success for r in self._model_records) if self._model_records else True

        # Log summary
        self.logger.log_agent_complete(
            total_time_ms=total_time_ms,
            llm_time_ms=total_llm_time,
            tool_time_ms=total_tool_time,
            total_tokens=total_input_tokens + total_output_tokens,
            tool_calls=tool_count,
            turns=turns,
            success=success,
            cost_usd=total_cost,
        )

        # Publish agent-level CloudWatch metrics
        if self._publisher:
            self._publisher.publish_agent_metrics(
                agent_name=self.agent_name,
                total_execution_time_ms=total_time_ms,
                llm_time_ms=total_llm_time,
                tool_time_ms=total_tool_time,
                overhead_time_ms=overhead,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                tool_call_count=tool_count,
                tool_error_count=tool_errors,
                turns_count=turns,
                rag_queries=rag_queries,
                cost_usd=total_cost,
                success=success,
            )
            self._publisher.flush()

        # Persist to S3
        summary = {
            "agent_name": self.agent_name,
            "trace_id": self.trace_ctx.trace_id,
            "span_id": self.trace_ctx.span_id,
            "audit_id": self.trace_ctx.audit_id,
            "session_id": self.trace_ctx.session_id,
            "actor_id": self.trace_ctx.actor_id,
            "total_execution_time_ms": round(total_time_ms, 2),
            "llm_time_ms": round(total_llm_time, 2),
            "tool_time_ms": round(total_tool_time, 2),
            "overhead_time_ms": round(overhead, 2),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "estimated_cost_usd": round(total_cost, 6),
            "model_invocations": turns,
            "tool_calls": tool_count,
            "tool_errors": tool_errors,
            "rag_queries": rag_queries,
            "success": success,
            "models_used": list(set(r.model_id for r in self._model_records)),
            "model_details": [
                {
                    "model_id": r.model_id,
                    "latency_ms": round(r.latency_ms, 2),
                    "ttft_ms": round(r.ttft_ms, 2),
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": round(r.cost_usd, 6),
                    "success": r.success,
                }
                for r in self._model_records
            ],
            "tool_details": [
                {
                    "tool_name": r.tool_name,
                    "duration_ms": round(r.duration_ms, 2),
                    "success": r.success,
                    "rag_sources": r.rag_sources,
                }
                for r in self._tool_records
            ],
        }

        if self._s3_store:
            self._s3_store.save_agent_metrics(self.agent_name, summary)
            # Save per-model metrics individually
            for r in self._model_records:
                self._s3_store.save_model_metrics(r.model_id, {
                    "invocation_id": uuid.uuid4().hex[:12],
                    "model_id": r.model_id,
                    "agent_name": self.agent_name,
                    "latency_ms": round(r.latency_ms, 2),
                    "ttft_ms": round(r.ttft_ms, 2),
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "cost_usd": round(r.cost_usd, 6),
                    "success": r.success,
                    "trace_id": self.trace_ctx.trace_id,
                })

        return summary
