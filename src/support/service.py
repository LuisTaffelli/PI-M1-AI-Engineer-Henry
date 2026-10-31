"""Orquesta el flujo offline. No hay SDKs ni acceso a red."""

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from ..runtime.config import ROOT, Settings
from .guardrails import check_input, check_output
from ..runtime.metrics import append_metric
from ..llm.prompts import load_prompt
from ..llm.providers.base import Provider
from ..llm.providers.mock_provider import MockProvider
from .schemas import SupportResponse


def simulate_response(
    query: str, provider: Provider | None = None, *, settings: Settings | None = None
) -> SupportResponse:
    # Invocaciones programáticas no registran métricas salvo pedido explícito.
    settings = settings if settings is not None else Settings()
    started = perf_counter()
    attempts = 0
    status = "rejected_input"
    injected = provider is not None
    try:
        check_input(query, settings.max_query_chars)
        status = "configuration_error"
        prompt = load_prompt(settings.prompt)
        if provider is None:
            provider = MockProvider(settings.mock_scenario)
        for attempt in range(1, settings.max_attempts + 1):
            attempts = attempt
            status = "provider_error"
            raw_text = provider.generate(prompt.render(), query)
            status = "invalid_response"
            try:
                response = SupportResponse.model_validate_json(raw_text)
            except ValidationError:
                if attempt == settings.max_attempts:
                    raise
                continue
            status = "rejected_output"
            check_output(response)
            status = "ok"
            return response
        raise RuntimeError("No se ejecutó ningún intento.")
    finally:
        if settings.log_metrics:
            append_metric(ROOT / settings.metrics_path, {
                "request_id": str(uuid4()),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "provider": "injected_test_double" if injected else settings.provider,
                "simulated": True,
                "prompt_version": settings.prompt,
                "status": status,
                "attempts": attempts,
                "latency_seconds": perf_counter() - started,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "cost_usd": None,
                "usage_status": "unavailable_mock",
            })
