"""Interfaz mínima independiente de SDKs y de la validación de negocio."""

from dataclasses import dataclass, field
from typing import Protocol

from ..http_retry import RetryAfter
from ..usage import TokenUsage


class ProviderError(ValueError):
    """Error controlado; code sólo admite etiquetas locales, nunca texto externo."""

    CODES = frozenset(
        {
            "provider_error",
            "http_error",
            "transport_error",
            "http_json_invalid",
            "incomplete_response",
            "invalid_envelope",
            "invalid_content",
            "non_text_output",
            "empty_output",
            "local_model_required",
        }
    )

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        usage: TokenUsage | None = None,
        http_status: int | None = None,
        retry_after: RetryAfter | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code if code in self.CODES else "provider_error"
        # Sólo el número HTTP de error: nunca reason, URL, headers o cuerpo.
        self.http_status = (
            http_status
            if self.code == "http_error"
            and type(http_status) is int
            and 400 <= http_status <= 599
            else None
        )
        self.retry_after = (
            retry_after
            if self.http_status is not None and isinstance(retry_after, RetryAfter)
            else RetryAfter()
        )
        self.usage = usage if isinstance(usage, TokenUsage) else TokenUsage()


@dataclass(frozen=True)
class GenerationResult:
    text: str = field(repr=False)
    usage: TokenUsage = field(default_factory=TokenUsage)

    def __post_init__(self):
        if not isinstance(self.text, str) or not isinstance(self.usage, TokenUsage):
            raise ValueError("Resultado interno de proveedor inválido.")


class Provider(Protocol):
    def generate(self, instructions: str, query: str) -> GenerationResult:
        """Devolver texto sin validar y consumo opcional, nunca el objeto HTTP crudo."""
        ...
