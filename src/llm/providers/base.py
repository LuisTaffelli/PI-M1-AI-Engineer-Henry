"""Interfaz mínima independiente de SDKs y de la validación de negocio."""

from typing import Protocol


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
        }
    )

    def __init__(self, message: str, *, code: str = "provider_error") -> None:
        super().__init__(message)
        self.code = code if code in self.CODES else "provider_error"


class Provider(Protocol):
    def generate(self, instructions: str, query: str) -> str:
        """Recibir instrucciones y consulta; devolver texto sin validar."""
        ...
