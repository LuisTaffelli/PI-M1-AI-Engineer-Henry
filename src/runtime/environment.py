"""Claves locales diferidas: entorno primero, luego .env fijo; sin ejecutar código."""

import os
import re
from collections.abc import Mapping

from .paths import ROOT

DOTENV_PATH = ROOT / ".env"
KEY_NAMES = frozenset({"OPENAI_API_KEY", "GEMINI_API_KEY"})
ERROR = "Configuración .env inválida; revisá la asignación de la clave seleccionada."


def _literal(value: str) -> str:
    value = value.strip()
    if value.startswith("#"):
        return ""
    if value.startswith(("'", '"')):
        quote = value[0]
        end = value.find(quote, 1)
        if end < 0 or (
            value[end + 1 :].strip() and not value[end + 1 :].lstrip().startswith("#")
        ):
            raise ValueError(ERROR)
        value = value[1:end]
    else:
        value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        if any(char.isspace() for char in value) or value.endswith("\\"):
            raise ValueError(ERROR)
    if "\x00" in value:
        raise ValueError(ERROR)
    return value


def load_api_key(name: str, environ: Mapping[str, str] | None = None) -> str | None:
    """No modifica os.environ; incluso un valor exportado vacío tiene prioridad."""
    if name not in KEY_NAMES:
        raise ValueError("Variable de credencial no admitida.")
    environ = os.environ if environ is None else environ
    if name in environ:
        return environ[name]
    try:
        text = DOTENV_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError):
        raise ValueError(
            "No se pudo leer .env; revisá ubicación, permisos y UTF-8."
        ) from None
    selected = None
    found = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)(.*)", line)
        if not match or match[1] != name:
            continue
        rest = match[2].lstrip()
        if found or not rest.startswith("="):
            raise ValueError(ERROR)
        selected = _literal(rest[1:])
        found = True
    return selected
