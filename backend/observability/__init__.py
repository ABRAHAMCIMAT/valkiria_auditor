"""
Observability module for the AgentCore multi-agent ISO 27001 audit system.

Provides:
- Structured logging with correlation IDs for tracing across agents
- CloudWatch metrics publishing (model, agent, orchestration levels)
- CloudWatch dashboard definitions (IaC-ready JSON)
- Alerting and anomaly detection rules
- OpenTelemetry-compatible trace context propagation
- Performance reporting and aggregation utilities
"""
