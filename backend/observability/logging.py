"""
Structured Logging — JSON-formatted logs with correlation IDs for cross-agent tracing.

All log entries include:
- trace_id: Unique per audit execution (propagated across all agents)
- span_id: Unique per agent invocation within a trace
- agent_name: Which agent emitted the log
- model_id: Which LLM was active
- Timing and token metrics inline

Outputs to stdout in JSON format for CloudWatch Logs ingestion.
"""

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    METRIC = "METRIC"


@dataclass
class TraceContext:
    """Distributed trace context propagated across agent invocations."""
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_span_id: str = ""
    audit_id: str = ""
    session_id: str = ""
    actor_id: str = ""

    def child_span(self) -> "TraceContext":
        """Create a child span for sub-agent invocation."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=self.span_id,
            audit_id=self.audit_id,
            session_id=self.session_id,
            actor_id=self.actor_id,
        )

    def to_headers(self) -> dict[str, str]:
        """Serialize to HTTP headers for cross-agent propagation."""
        return {
            "X-Trace-Id": self.trace_id,
            "X-Span-Id": self.span_id,
            "X-Parent-Span-Id": self.parent_span_id,
            "X-Audit-Id": self.audit_id,
            "X-Session-Id": self.session_id,
            "X-Actor-Id": self.actor_id,
        }

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "TraceContext":
        """Deserialize from HTTP headers received by a sub-agent."""
        return cls(
            trace_id=headers.get("X-Trace-Id", uuid.uuid4().hex),
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=headers.get("X-Span-Id", ""),
            audit_id=headers.get("X-Audit-Id", ""),
            session_id=headers.get("X-Session-Id", ""),
            actor_id=headers.get("X-Actor-Id", ""),
        )

    @classmethod
    def from_payload(cls, payload: dict) -> "TraceContext":
        """Extract trace context from an agent invocation payload."""
        return cls(
            trace_id=payload.get("trace_id", uuid.uuid4().hex),
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=payload.get("parent_span_id", ""),
            audit_id=payload.get("audit_id", ""),
            session_id=payload.get("session_id", ""),
            actor_id=payload.get("actor_id", ""),
        )


class StructuredLogger:
    """
    JSON-structured logger with automatic trace context injection.

    Usage:
        ctx = TraceContext(audit_id="audit_001")
        logger = StructuredLogger(agent_name="planning_agent", trace_ctx=ctx)

        logger.info("Starting audit plan generation", controls_in_scope=37)
        logger.metric("model_invocation", model_id="openai.gpt-oss-120b-1:0", latency_ms=1200)

        with logger.timed_operation("rag_query"):
            result = query_knowledge_base(...)
    """

    def __init__(
        self,
        agent_name: str,
        trace_ctx: Optional[TraceContext] = None,
        model_id: str = "",
    ):
        self.agent_name = agent_name
        self.trace_ctx = trace_ctx or TraceContext()
        self.model_id = model_id
        self._operation_stack: list[dict] = []

    def _emit(self, level: LogLevel, message: str, **kwargs):
        """Emit a structured JSON log line to stdout."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "agent_name": self.agent_name,
            "message": message,
            "trace_id": self.trace_ctx.trace_id,
            "span_id": self.trace_ctx.span_id,
            "parent_span_id": self.trace_ctx.parent_span_id,
            "audit_id": self.trace_ctx.audit_id,
            "session_id": self.trace_ctx.session_id,
        }
        if self.model_id:
            entry["model_id"] = self.model_id
        entry.update(kwargs)

        print(json.dumps(entry, default=str), flush=True)

    def debug(self, message: str, **kwargs):
        if os.environ.get("LOG_LEVEL", "INFO") == "DEBUG":
            self._emit(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._emit(LogLevel.INFO, message, **kwargs)

    def warn(self, message: str, **kwargs):
        self._emit(LogLevel.WARN, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._emit(LogLevel.ERROR, message, **kwargs)

    def metric(self, metric_name: str, **kwargs):
        """Emit a metric-type log entry (for CloudWatch Logs Insights queries)."""
        self._emit(LogLevel.METRIC, metric_name, metric_type=metric_name, **kwargs)

    def set_model(self, model_id: str):
        """Update the active model ID for subsequent log entries."""
        self.model_id = model_id

    @contextmanager
    def timed_operation(self, operation_name: str, **extra):
        """Context manager that logs operation start/end with duration."""
        start = time.perf_counter()
        self.debug(f"Starting {operation_name}", operation=operation_name, **extra)
        try:
            yield
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            self.error(
                f"Failed {operation_name}",
                operation=operation_name,
                duration_ms=round(duration_ms, 2),
                error_type=type(exc).__name__,
                error_message=str(exc)[:200],
                **extra,
            )
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            self.info(
                f"Completed {operation_name}",
                operation=operation_name,
                duration_ms=round(duration_ms, 2),
                **extra,
            )

    def log_model_invocation(
        self,
        model_id: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        ttft_ms: float = 0.0,
        success: bool = True,
        error_type: str = "",
        cost_usd: float = 0.0,
    ):
        """Log a model invocation with standard metrics."""
        otps = output_tokens / (latency_ms / 1000.0) if latency_ms > 0 and output_tokens > 0 else 0
        self.metric(
            "model_invocation",
            model_id=model_id,
            latency_ms=round(latency_ms, 2),
            ttft_ms=round(ttft_ms, 2),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            output_tokens_per_second=round(otps, 1),
            success=success,
            error_type=error_type,
            estimated_cost_usd=round(cost_usd, 6),
        )

    def log_tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool = True,
        error: str = "",
    ):
        """Log a tool execution with timing."""
        self.metric(
            "tool_call",
            tool_name=tool_name,
            duration_ms=round(duration_ms, 2),
            success=success,
            error=error[:200] if error else "",
        )

    def log_agent_complete(
        self,
        total_time_ms: float,
        llm_time_ms: float,
        tool_time_ms: float,
        total_tokens: int,
        tool_calls: int,
        turns: int,
        success: bool = True,
        cost_usd: float = 0.0,
    ):
        """Log agent invocation completion summary."""
        self.metric(
            "agent_complete",
            total_execution_time_ms=round(total_time_ms, 2),
            llm_time_ms=round(llm_time_ms, 2),
            tool_execution_time_ms=round(tool_time_ms, 2),
            overhead_time_ms=round(max(0, total_time_ms - llm_time_ms - tool_time_ms), 2),
            total_tokens=total_tokens,
            tool_call_count=tool_calls,
            turns_count=turns,
            success=success,
            estimated_cost_usd=round(cost_usd, 6),
        )
