"""Heurísticas demostrativas: no equivalen a moderación completa."""

import re

from .schemas import SupportResponse

INJECTION = re.compile(
    r"ignore\s+(?:all\s+)?previous\s+instructions|"
    r"ignor[aá]\s+(?:todas\s+)?(?:las\s+)?instrucciones\s+(?:previas|anteriores)",
    re.IGNORECASE,
)
CREDENTIAL = re.compile(r"(?:api[_ -]?key|password|contrase[nñ]a)\s*[:=]\s*\S+", re.IGNORECASE)


class GuardrailError(ValueError):
    pass


def check_input(query: str, max_chars: int) -> None:
    if not query.strip():
        raise GuardrailError("Consulta vacía.")
    if len(query) > max_chars:
        raise GuardrailError("Consulta demasiado larga.")
    if INJECTION.search(query):
        raise GuardrailError("Patrón de injection bloqueado por la heurística.")


def check_output(response: SupportResponse) -> None:
    content = "\n".join([response.answer, *response.actions])
    if CREDENTIAL.search(content):
        raise GuardrailError("Posible credencial en la salida.")
