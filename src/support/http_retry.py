"""Reintentos HTTP explícitos, separados de la reparación de JSON/contrato."""

from dataclasses import dataclass, field
from random import uniform
from time import sleep

from ..llm.http_retry import HTTP_RETRY_STATUSES
from ..llm.providers.base import GenerationResult, Provider, ProviderError
from ..llm.usage import TokenUsage
from ..runtime.config import Settings


@dataclass
class HttpRetryState:
    retry_count: int = 0
    wait_seconds: float = 0.0
    events: list[dict] = field(default_factory=list)

    def delay(self, error: ProviderError, settings: Settings, attempt: int):
        if error.http_status is None:
            return None
        event = {
            "http_status": error.http_status,
            "retry_after_state": error.retry_after.state,
            "retry_after_seconds": error.retry_after.requested_seconds,
            "retry_after_seconds_digits": error.retry_after.requested_seconds_digits,
            "delay_seconds": None,
            "retried": False,
            "stop_reason": None,
        }
        self.events.append(event)
        if settings.provider not in {"openai", "gemini"}:
            reason = "provider_not_supported"
        elif error.http_status not in HTTP_RETRY_STATUSES:
            reason = "status_not_retryable"
        elif settings.http_max_attempts == 1:
            reason = "disabled"
        elif attempt >= settings.http_max_attempts:
            reason = "attempt_limit"
        elif error.retry_after.state == "too_long":
            reason = "retry_after_too_long"
        else:
            delay = (
                error.retry_after.seconds
                if error.retry_after.state == "valid"
                else 2 ** (attempt - 1) + uniform(0.0, 0.25)
            )
            event["delay_seconds"] = delay
            # No recortar un Retry-After largo: fallar antes de reintentar temprano.
            if delay > settings.http_retry_max_delay_seconds:
                reason = "delay_limit"
            elif delay > settings.http_retry_max_total_wait_seconds - self.wait_seconds:
                reason = "wait_budget"
            else:
                return delay
        event["stop_reason"] = reason
        return None


def generate_with_http_retry(
    provider: Provider,
    instructions: str,
    query: str,
    *,
    settings: Settings,
    usages: list[TokenUsage],
    state: HttpRetryState,
) -> GenerationResult:
    limit = (
        settings.http_max_attempts if settings.provider in {"openai", "gemini"} else 1
    )
    for http_attempt in range(1, limit + 1):
        # Un registro por invocación, incluidos fallos sin usage. No asumir coste 0.
        usages.append(TokenUsage())
        try:
            result = provider.generate(instructions, query)
            if not isinstance(result, GenerationResult):
                raise ProviderError("El proveedor incumple el contrato interno.")
            usages[-1] = result.usage
            return result
        except ProviderError as error:
            usages[-1] = error.usage
            delay = state.delay(error, settings, http_attempt)
            if delay is None:
                raise
            if delay:
                sleep(delay)
            state.wait_seconds += delay
            state.retry_count += 1
            state.events[-1]["retried"] = True
    raise RuntimeError("No se ejecutó ningún intento HTTP.")
