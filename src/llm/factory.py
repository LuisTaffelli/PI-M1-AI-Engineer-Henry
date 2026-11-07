"""Construcción diferida del proveedor seleccionado; no carga claves al importar."""

from collections.abc import Callable

from ..runtime.config import Settings
from .providers.base import Provider
from .providers.gemini_provider import GeminiProvider
from .providers.mock_provider import MockProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider


def create_provider(
    settings: Settings, response_schema: Callable[[], dict]
) -> Provider:
    if settings.provider == "mock":
        return MockProvider(settings.mock_scenario)
    elif settings.provider == "openai":
        return OpenAIProvider(
            model=settings.model or "",
            max_output_tokens=settings.openai_max_output_tokens,
        )
    elif settings.provider == "gemini":
        return GeminiProvider(
            model=settings.model or "",
            max_output_tokens=settings.gemini_max_output_tokens,
            retry_after_max_delay_seconds=settings.http_retry_max_delay_seconds,
            response_schema=response_schema(),
        )
    else:
        return OllamaProvider(
            model=settings.model or "",
            base_url=settings.ollama_base_url,
            max_output_tokens=settings.ollama_max_output_tokens,
            num_ctx=settings.ollama_num_ctx,
            timeout_seconds=settings.ollama_timeout_seconds,
            response_schema=response_schema(),
        )
