"""Persistencia del resultado de un request, incluso tras una excepción."""

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from ..llm.providers.base import Provider
from ..llm.providers.mock_provider import MockProvider
from ..llm.usage import TokenUsage, summarize_usage
from .config import ROOT, Settings
from .metrics import append_metric
from .pricing import cost_metrics


def record_request(
    settings: Settings,
    provider: Provider | None,
    *,
    injected: bool,
    status: str,
    failure_code: str | None,
    attempts: int,
    started: float,
    usage_by_attempt: list[TokenUsage],
) -> None:
    usage_metrics = summarize_usage(usage_by_attempt)
    if usage_metrics["usage_status"] == "unavailable" and isinstance(
        provider, MockProvider
    ):
        usage_metrics["usage_status"] = "unavailable_mock"
    append_metric(
        ROOT / settings.metrics_path,
        {
            "request_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": "injected_test_double" if injected else settings.provider,
            "simulated": injected or settings.provider == "mock",
            "prompt_version": settings.prompt,
            "status": status,
            "failure_stage": None if status == "ok" else status,
            "failure_code": failure_code,
            "attempts": attempts,
            "latency_seconds": perf_counter() - started,
            **usage_metrics,
            **cost_metrics(
                usage_by_attempt,
                provider=settings.provider,
                model=settings.model,
                pricing_path=ROOT / settings.pricing_path
                if settings.pricing_path
                else None,
                allow_fixture=injected,
            ),
        },
    )
