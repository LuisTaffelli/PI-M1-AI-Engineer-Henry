"""Ollama local: preflight GGUF y chat estructurado, sin claves, proxy o descarga."""

import json
from collections.abc import Callable
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from ..usage import ollama_usage
from .base import GenerationResult, ProviderError

Transport = Callable[[Request, float], object]


def normalize_base_url(value: str) -> str:
    try:
        url = urlsplit(value)
        if (
            url.scheme != "http"
            or url.hostname not in {"localhost", "127.0.0.1", "::1"}
            or url.username
            or url.password
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or url.port is None
            or not 1 <= url.port <= 65535
        ):
            raise ValueError("invalid")
        host = "[::1]" if url.hostname == "::1" else "127.0.0.1"
        return f"http://{host}:{url.port}"
    except (ValueError, TypeError):
        raise ValueError(
            "Ollama requiere una URL HTTP loopback con puerto explícito."
        ) from None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _post_json(request: Request, timeout: float) -> object:
    # ProxyHandler vacío evita enviar tickets locales a un proxy del entorno.
    url = urlsplit(request.full_url)
    normalize_base_url(f"{url.scheme}://{url.netloc}")
    if url.path not in ("/api/show", "/api/chat") or url.query or url.fragment:
        raise ValueError("Ruta local Ollama no admitida.")
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    with opener.open(request, timeout=timeout) as response:
        data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("Respuesta local demasiado grande.")
        return json.loads(data)


class OllamaProvider:
    def __init__(
        self,
        model: str,
        *,
        base_url: str = "http://127.0.0.1:11434",
        response_schema: dict | None = None,
        max_output_tokens: int = 256,
        num_ctx: int = 2048,
        timeout_seconds: float = 120,
        transport: Transport | None = None,
    ):
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("Elegí un modelo local ya importado en Ollama.")
        if "cloud" in model.lower():
            raise ProviderError(
                "Este adaptador sólo admite modelos locales.",
                code="local_model_required",
            )
        if (
            type(max_output_tokens) is not int
            or not 16 <= max_output_tokens <= 4096
            or type(num_ctx) is not int
            or not 512 <= num_ctx <= 16384
            or type(timeout_seconds) not in (int, float)
            or not 1 <= timeout_seconds <= 300
        ):
            raise ValueError("Límites de generación Ollama inválidos.")
        self.model = model.strip()
        self.base_url = normalize_base_url(base_url)
        self.response_schema = response_schema
        self.max_output_tokens = max_output_tokens
        self.num_ctx = num_ctx
        self.timeout_seconds = timeout_seconds
        self._transport = transport if transport is not None else _post_json

    def _request(self, path: str, payload: dict, timeout: float) -> object:
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            return self._transport(request, timeout)
        except HTTPError as error:
            error.close()
            raise ProviderError(
                "Ollama rechazó la solicitud; verificá el modelo local.",
                code="http_error",
            ) from None
        except (URLError, OSError, HTTPException, ValueError):
            raise ProviderError(
                "No se pudo obtener una respuesta de Ollama local.",
                code="transport_error",
            ) from None

    def generate(self, instructions: str, query: str) -> GenerationResult:
        # show no genera texto ni importa modelos. No se cachea el permiso entre intentos.
        info = self._request(
            "/api/show", {"model": self.model}, min(self.timeout_seconds, 10)
        )
        details = info.get("details") if isinstance(info, dict) else None
        capabilities = info.get("capabilities") if isinstance(info, dict) else None
        if (
            not isinstance(info, dict)
            or info.get("remote_host")
            or info.get("remote_model")
            or not isinstance(details, dict)
            or details.get("format") != "gguf"
            or not isinstance(capabilities, list)
            or "completion" not in capabilities
        ):
            raise ProviderError(
                "Ollama debe exponer un GGUF local con capacidad de generación.",
                code="local_model_required",
            )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": query},
            ],
            "stream": False,
            "format": self.response_schema
            if self.response_schema is not None
            else "json",
            "options": {
                "temperature": 0,
                "num_predict": self.max_output_tokens,
                "num_ctx": self.num_ctx,
            },
        }
        data = self._request("/api/chat", payload, self.timeout_seconds)
        usage = ollama_usage(data)
        try:
            text = _extract_text(data)
        except ProviderError as error:
            error.usage = usage
            raise
        return GenerationResult(text, usage)


def _extract_text(data: object) -> str:
    if (
        not isinstance(data, dict)
        or data.get("done") is not True
        or data.get("done_reason") not in (None, "stop")
    ):
        raise ProviderError(
            "Ollama no completó una respuesta utilizable.", code="incomplete_response"
        )
    message = data.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        raise ProviderError(
            "Formato de mensaje Ollama no admitido.", code="invalid_envelope"
        )
    if message.get("tool_calls") or message.get("images"):
        raise ProviderError(
            "Ollama no entregó sólo texto de respuesta.", code="non_text_output"
        )
    text = message.get("content")
    if not isinstance(text, str) or not text.strip():
        raise ProviderError(
            "Ollama entregó texto vacío o inválido.", code="empty_output"
        )
    return text
