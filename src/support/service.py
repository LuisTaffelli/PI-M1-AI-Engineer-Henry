"""Orquesta validación, proveedor y retry; el mock sigue siendo predeterminado."""

from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from ..llm.prompts import load_prompt
from ..llm.providers.base import GenerationResult, Provider, ProviderError
from ..llm.providers.gemini_provider import GeminiProvider
from ..llm.providers.mock_provider import MockProvider
from ..llm.providers.ollama_provider import OllamaProvider
from ..llm.providers.openai_provider import OpenAIProvider
from ..llm.usage import TokenUsage, summarize_usage
from ..runtime.config import ROOT, Settings
from ..runtime.metrics import append_metric
from ..runtime.pricing import cost_metrics
from .guardrails import check_input, check_output
from .schemas import SupportResponse, validation_failure_code


def _validation_feedback(error: ValidationError) -> str:
    """Resumir hasta tres fallas sin copiar valores, mensajes o claves externas."""
    rules = {
        "answer": "answer: usá texto no vacío.",
        "confidence": "confidence: usá un número finito entre 0 y 1.",
        "category": "category: elegí billing, technical, account u other.",
        "actions": "actions: usá una lista de textos no vacíos; puede estar vacía.",
    }
    summaries = []
    for issue in error.errors(
        include_input=False, include_context=False, include_url=False
    ):
        location = issue["loc"]
        field = location[0] if location else None
        if issue["type"] == "json_invalid":
            summary = "La salida debe ser JSON válido y completo, sin texto adicional."
        elif issue["type"] == "extra_forbidden":
            summary = "Eliminá campos adicionales: sólo answer, confidence, category y actions."
        elif field in rules:
            summary = rules[field]
            if issue["type"] == "missing":
                summary = f"Falta el campo {field}. {summary}"
        else:
            summary = (
                "Devolvé un objeto JSON que cumpla los tipos y campos del contrato."
            )
        if summary not in summaries:
            summaries.append(summary)
        if len(summaries) == 3:
            break
    return (
        "Corrección de salida anterior:\n"
        + "\n".join(f"- {summary}" for summary in summaries)
        + "\nGenerá de nuevo la respuesta completa para la consulta original, sólo en JSON."
    )


def simulate_response(
    query: str, provider: Provider | None = None, *, settings: Settings | None = None
) -> SupportResponse:
    # Invocaciones programáticas no registran métricas salvo pedido explícito.
    settings = settings if settings is not None else Settings()
    started = perf_counter()
    attempts = 0
    status = "rejected_input"
    failure_code = None
    usage_by_attempt: list[TokenUsage] = []
    injected = provider is not None
    try:
        check_input(query, settings.max_query_chars)
        status = "configuration_error"
        prompt = load_prompt(settings.prompt)
        base_instructions = prompt.render()
        instructions = base_instructions
        if provider is None:
            if settings.provider == "mock":
                provider = MockProvider(settings.mock_scenario)
            elif settings.provider == "openai":
                provider = OpenAIProvider(
                    model=settings.model or "",
                    max_output_tokens=settings.openai_max_output_tokens,
                )
            elif settings.provider == "gemini":
                provider = GeminiProvider(
                    model=settings.model or "",
                    max_output_tokens=settings.gemini_max_output_tokens,
                    response_schema=SupportResponse.model_json_schema(),
                )
            else:
                provider = OllamaProvider(
                    model=settings.model or "",
                    base_url=settings.ollama_base_url,
                    max_output_tokens=settings.ollama_max_output_tokens,
                    num_ctx=settings.ollama_num_ctx,
                    timeout_seconds=settings.ollama_timeout_seconds,
                    response_schema=SupportResponse.model_json_schema(),
                )
        for attempt in range(1, settings.max_attempts + 1):
            attempts = attempt
            status = "provider_error"
            usage_by_attempt.append(TokenUsage())
            try:
                result = provider.generate(instructions, query)
                if not isinstance(result, GenerationResult):
                    raise ProviderError("El proveedor incumple el contrato interno.")
                usage_by_attempt[-1] = result.usage
            except ProviderError as error:
                usage_by_attempt[-1] = error.usage
                raise
            raw_text = result.text
            status = "invalid_response"
            try:
                response = SupportResponse.model_validate_json(raw_text)
            except ValidationError as error:
                if attempt == settings.max_attempts:
                    raise
                # Sólo el resumen del último error: sin salida cruda ni historial acumulado.
                instructions = f"{base_instructions}\n\n{_validation_feedback(error)}"
                continue
            status = "rejected_output"
            check_output(response)
            status = "ok"
            return response
        raise RuntimeError("No se ejecutó ningún intento.")
    except ProviderError as error:
        failure_code = error.code
        raise
    except ValidationError as error:
        # Settings/prompts también usan Pydantic: no confundirlos con salida del modelo.
        failure_code = (
            validation_failure_code(error)
            if status == "invalid_response"
            else "configuration_invalid"
        )
        raise
    finally:
        if settings.log_metrics:
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
                    "provider": "injected_test_double"
                    if injected
                    else settings.provider,
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
