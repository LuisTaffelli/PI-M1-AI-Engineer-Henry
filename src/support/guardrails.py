"""Heurísticas demostrativas: no equivalen a moderación completa."""

import re
import unicodedata

from .schemas import SupportResponse

MAX_QUERY_CHARS = 500

INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?previous\s+instructions|"
    r"ignor[aá]\s+(?:todas\s+)?(?:las\s+)?instrucciones\s+(?:previas|anteriores)",
    re.IGNORECASE,
)
CREDENTIAL = re.compile(
    r"(?:api[_ -]?key|password|contrase[nñ]a)\s*[:=]\s*\S+", re.IGNORECASE
)


class GuardrailError(ValueError):
    pass


class InputTooLongError(GuardrailError):
    """Rechazo con un mensaje local que nunca incluye la consulta."""

    def __init__(self, max_chars: int) -> None:
        super().__init__(f"La consulta no puede superar los {max_chars} caracteres.")


def _detection_text(value: str) -> str:
    # Detectar equivalentes Unicode sin cambiar lo enviado al modelo ni al usuario.
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Cf")


def check_input(query: str, max_chars: int = MAX_QUERY_CHARS) -> None:
    # len cuenta puntos de código Unicode del original, incluidos espacios e invisibles.
    # Un caller puede imponer un límite menor, pero no ampliar el techo de seguridad.
    limit = min(max_chars, MAX_QUERY_CHARS)
    if len(query) > limit:
        raise InputTooLongError(limit)
    if not query.strip():
        raise GuardrailError("Consulta vacía.")
    if INJECTION.search(_detection_text(query)):
        raise GuardrailError("Patrón de injection bloqueado por la heurística.")


def check_output(response: SupportResponse) -> None:
    content = "\n".join([response.answer, *response.actions])
    if CREDENTIAL.search(_detection_text(content)):
        raise GuardrailError("Posible credencial en la salida.")
