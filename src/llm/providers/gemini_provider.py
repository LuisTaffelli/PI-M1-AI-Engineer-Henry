"""Gemini Interactions HTTP v1beta; transporte sustituible para pruebas offline."""

import json
import os
from collections.abc import Callable
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..usage import gemini_usage
from .base import GenerationResult, ProviderError

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
Transport = Callable[[Request, float], object]


def _post_json(request: Request, timeout: float) -> object:
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


class GeminiProvider:
    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        max_output_tokens: int = 512,
        transport: Transport | None = None,
        response_schema: dict | None = None,
    ):
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("Elegí un modelo antes de usar Gemini.")
        key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not isinstance(key, str) or not key.strip():
            raise ProviderError("Falta GEMINI_API_KEY en el entorno del proceso.")
        self._key = key.strip()
        self.model = model.strip()
        self.max_output_tokens = max_output_tokens
        self._transport = transport if transport is not None else _post_json
        self.response_schema = response_schema

    def generate(self, instructions: str, query: str) -> GenerationResult:
        payload = {
            "model": self.model,
            "system_instruction": instructions,
            "input": query,
            "generation_config": {"max_output_tokens": self.max_output_tokens},
            "store": False,
        }
        if self.response_schema is not None:
            # Interactions recibe JSON Schema aquí, no en generation_config.
            payload["response_format"] = {
                "type": "text",
                "mime_type": "application/json",
                "schema": self.response_schema,
            }
        request = Request(
            ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"x-goog-api-key": self._key, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            data = self._transport(request, 30.0)
        except HTTPError as error:
            error.close()
            raise ProviderError(
                "Gemini rechazó la solicitud HTTP.", code="http_error"
            ) from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ProviderError(
                "Gemini devolvió JSON HTTP inválido.", code="http_json_invalid"
            ) from None
        except (URLError, OSError, HTTPException, ValueError):
            raise ProviderError(
                "No se pudo obtener una respuesta de Gemini.", code="transport_error"
            ) from None
        usage = gemini_usage(data.get("usage") if isinstance(data, dict) else None)
        try:
            return GenerationResult(_extract_text(data), usage)
        except ProviderError as error:
            # Puede haber consumo aun con incomplete/refusal/texto no utilizable.
            error.usage = usage
            raise


def _extract_text(data: object) -> str:
    if not isinstance(data, dict):
        raise ProviderError(
            "Formato de respuesta Gemini no admitido.", code="invalid_envelope"
        )
    if data.get("status") != "completed":
        raise ProviderError(
            "Gemini no completó una respuesta utilizable.",
            code="incomplete_response",
        )
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise ProviderError(
            "Formato de respuesta Gemini no admitido.", code="invalid_envelope"
        )
    texts = []
    for step in steps:
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        content = step.get("content")
        if not isinstance(content, list):
            raise ProviderError(
                "Formato de mensaje Gemini no admitido.", code="invalid_content"
            )
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "text":
                raise ProviderError(
                    "Gemini no entregó sólo texto de respuesta.",
                    code="non_text_output",
                )
            text = part.get("text")
            if not isinstance(text, str):
                raise ProviderError(
                    "Gemini entregó texto inválido.", code="invalid_content"
                )
            texts.append(text)
    if not texts or not "".join(texts).strip():
        raise ProviderError(
            "Gemini no entregó texto de respuesta.", code="empty_output"
        )
    return "".join(texts)
