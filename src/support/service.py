"""Orquesta validación, proveedor y retry; el mock sigue siendo predeterminado."""

from time import perf_counter

from pydantic import ValidationError

from ..llm.factory import create_provider
from ..llm.prompts import load_prompt
from ..llm.providers.base import Provider, ProviderError
from ..llm.usage import TokenUsage
from ..runtime.config import Settings
from ..runtime.request_metrics import record_request
from .guardrails import check_input, check_output
from .http_retry import HttpRetryState, generate_with_http_retry
from .repair import _validation_feedback as _validation_feedback
from .schemas import SupportResponse, validation_failure_code


def simulate_response(
    query: str, provider: Provider | None = None, *, settings: Settings | None = None
) -> SupportResponse:
    # Invocaciones programáticas no registran métricas salvo pedido explícito.
    settings = settings if settings is not None else Settings()
    started = perf_counter()
    http_retry = HttpRetryState()
    status = "rejected_input"
    failure_code = None
    failure_http_status = None
    usage_by_attempt: list[TokenUsage] = []
    injected = provider is not None
    try:
        check_input(query, settings.max_query_chars)
        status = "configuration_error"
        prompt = load_prompt(settings.prompt)
        base_instructions = prompt.render()
        instructions = base_instructions
        if provider is None:
            provider = create_provider(settings, SupportResponse.model_json_schema)
        for attempt in range(1, settings.max_attempts + 1):
            status = "provider_error"
            result = generate_with_http_retry(
                provider,
                instructions,
                query,
                settings=settings,
                usages=usage_by_attempt,
                state=http_retry,
            )
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
        failure_http_status = error.http_status
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
            record_request(
                settings,
                provider,
                injected=injected,
                status=status,
                failure_code=failure_code,
                failure_http_status=failure_http_status,
                attempts=len(usage_by_attempt),
                http_retry=http_retry,
                started=started,
                usage_by_attempt=usage_by_attempt,
            )
