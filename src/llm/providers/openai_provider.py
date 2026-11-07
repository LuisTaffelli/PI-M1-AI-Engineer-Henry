"""Adaptador HTTP de Responses; pruebas offline mediante transporte inyectable."""

import json
from collections.abc import Callable
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ...runtime import environment
from ..http_retry import parse_retry_after
from ..usage import openai_usage
from .base import GenerationResult, ProviderError

ENDPOINT = "https://api.openai.com/v1/responses"
Transport = Callable[[Request, float], object]


def _post_json(request: Request, timeout: float) -> object:
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


class OpenAIProvider:
    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        max_output_tokens: int = 512,
        transport: Transport | None = None,
    ):
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("Elegí un modelo antes de usar OpenAI.")
        # Carga diferida: entorno primero y .env local sólo si falta la variable.
        key = (
            api_key
            if api_key is not None
            else environment.load_api_key("OPENAI_API_KEY")
        )
        if not isinstance(key, str) or not key.strip():
            raise ProviderError("Falta OPENAI_API_KEY en el entorno o .env local.")
        self._key = key.strip()
        self.model = model.strip()
        self.max_output_tokens = max_output_tokens
        self._transport = transport if transport is not None else _post_json

    def generate(self, instructions: str, query: str) -> GenerationResult:
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": query,
            "max_output_tokens": self.max_output_tokens,
            "store": False,
        }
        request = Request(
            ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            data = self._transport(request, 30.0)
        except HTTPError as error:
            # Sólo status validado y Retry-After normalizado; nunca leer cuerpo,
            # reason, URL u otros headers. Cerrar también los errores reintentados.
            status = error.code
            retry_after = parse_retry_after(
                error.headers.get("Retry-After") if error.headers is not None else None
            )
            error.close()
            raise ProviderError(
                "OpenAI rechazó la solicitud HTTP.",
                code="http_error",
                http_status=status,
                retry_after=retry_after,
            ) from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ProviderError(
                "OpenAI devolvió JSON HTTP inválido.", code="http_json_invalid"
            ) from None
        except (URLError, OSError, HTTPException, ValueError):
            raise ProviderError(
                "No se pudo obtener una respuesta de OpenAI.", code="transport_error"
            ) from None
        usage = openai_usage(data.get("usage") if isinstance(data, dict) else None)
        try:
            return GenerationResult(_extract_text(data), usage)
        except ProviderError as error:
            # Puede haber consumo aun con incomplete/refusal/texto no utilizable.
            error.usage = usage
            raise


def _extract_text(data: object) -> str:
    if not isinstance(data, dict):
        raise ProviderError(
            "Formato de respuesta OpenAI no admitido.", code="invalid_envelope"
        )
    if data.get("status") != "completed":
        raise ProviderError(
            "OpenAI no completó una respuesta utilizable.", code="incomplete_response"
        )
    output = data.get("output")
    if not isinstance(output, list):
        raise ProviderError(
            "Formato de respuesta OpenAI no admitido.", code="invalid_envelope"
        )
    texts = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            raise ProviderError(
                "Formato de mensaje OpenAI no admitido.", code="invalid_content"
            )
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text":
                raise ProviderError(
                    "OpenAI no entregó sólo texto de respuesta.", code="non_text_output"
                )
            text = part.get("text")
            if not isinstance(text, str):
                raise ProviderError(
                    "OpenAI entregó texto inválido.", code="invalid_content"
                )
            texts.append(text)
    if not texts or not "".join(texts).strip():
        raise ProviderError(
            "OpenAI no entregó texto de respuesta.", code="empty_output"
        )
    # No validar aquí el contrato Nubbix: eso corresponde al servicio/retry.
    return "".join(texts)
