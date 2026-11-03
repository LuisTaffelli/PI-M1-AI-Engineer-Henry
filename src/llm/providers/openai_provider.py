"""Adaptador HTTP de Responses; pruebas offline mediante transporte inyectable."""

import json
import os
from collections.abc import Callable
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import ProviderError

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
        # Se consulta sólo al crear este adaptador; no se abre .env.
        key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        if not isinstance(key, str) or not key.strip():
            raise ProviderError("Falta OPENAI_API_KEY en el entorno del proceso.")
        self._key = key.strip()
        self.model = model.strip()
        self.max_output_tokens = max_output_tokens
        self._transport = transport if transport is not None else _post_json

    def generate(self, instructions: str, query: str) -> str:
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
            error.close()
            raise ProviderError("OpenAI rechazó la solicitud HTTP.") from None
        except (URLError, OSError, HTTPException, ValueError):
            raise ProviderError("No se pudo obtener una respuesta de OpenAI.") from None
        if not isinstance(data, dict) or data.get("status") != "completed":
            raise ProviderError("OpenAI no completó una respuesta utilizable.")
        output = data.get("output")
        if not isinstance(output, list):
            raise ProviderError("Formato de respuesta OpenAI no admitido.")
        texts = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                raise ProviderError("Formato de mensaje OpenAI no admitido.")
            for part in content:
                if not isinstance(part, dict) or part.get("type") != "output_text":
                    raise ProviderError("OpenAI no entregó sólo texto de respuesta.")
                text = part.get("text")
                if not isinstance(text, str):
                    raise ProviderError("OpenAI entregó texto inválido.")
                texts.append(text)
        if not texts or not "".join(texts).strip():
            raise ProviderError("OpenAI no entregó texto de respuesta.")
        # No validar aquí el contrato Nubbix: eso corresponde al servicio/retry.
        return "".join(texts)
