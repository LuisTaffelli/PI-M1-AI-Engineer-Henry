"""Configuración TOML local; no lee entorno ni archivos de credenciales."""

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..llm.http_retry import (
    GEMINI_SUITE_MAX_DELAY_SECONDS,
    GEMINI_SUITE_MAX_WAIT_SECONDS,
    MAX_HTTP_ATTEMPTS,
    MAX_HTTP_RETRY_DELAY_SECONDS,
    MAX_HTTP_RETRY_WAIT_SECONDS,
)
from ..llm.prompt_catalog import PromptName
from ..llm.providers.ollama_provider import normalize_base_url
from ..support.guardrails import MAX_QUERY_CHARS
from .paths import ROOT as ROOT


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider: Literal["mock", "openai", "gemini", "ollama"] = "mock"
    model: str | None = Field(default=None, min_length=1, max_length=128)
    openai_max_output_tokens: int = Field(default=512, ge=16, le=4096)
    gemini_max_output_tokens: int = Field(default=512, ge=16, le=4096)
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_max_output_tokens: int = Field(default=256, ge=16, le=4096)
    ollama_num_ctx: int = Field(default=2048, ge=512, le=16384)
    ollama_timeout_seconds: int = Field(default=120, ge=1, le=300)
    prompt: PromptName = "v1_zero_shot"
    mock_scenario: Literal["fixed", "malformed", "invalid_contract", "recover_once"] = (
        "fixed"
    )
    max_attempts: int = Field(default=2, ge=1, le=3)
    # Opt-in: preserva el coste/cantidad de llamadas de comandos existentes.
    http_max_attempts: int = Field(default=1, ge=1, le=MAX_HTTP_ATTEMPTS)
    gemini_suite_retry_exception: bool = False
    http_retry_max_delay_seconds: float = Field(
        default=MAX_HTTP_RETRY_DELAY_SECONDS, ge=0, le=GEMINI_SUITE_MAX_DELAY_SECONDS
    )
    http_retry_max_total_wait_seconds: float = Field(
        default=MAX_HTTP_RETRY_WAIT_SECONDS, ge=0, le=GEMINI_SUITE_MAX_WAIT_SECONDS
    )
    max_query_chars: int = Field(default=MAX_QUERY_CHARS, ge=1, le=MAX_QUERY_CHARS)
    log_metrics: bool = False
    metrics_path: str = Field(default="data/metrics.jsonl", min_length=1)
    pricing_path: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def scoped_retry_limits(self):
        if self.gemini_suite_retry_exception:
            if self.provider != "gemini" or self.max_attempts != 1:
                raise ValueError(
                    "La excepción requiere Gemini y una sola generación por consulta."
                )
        elif (
            self.http_retry_max_delay_seconds > MAX_HTTP_RETRY_DELAY_SECONDS
            or self.http_retry_max_total_wait_seconds > MAX_HTTP_RETRY_WAIT_SECONDS
        ):
            raise ValueError("Ampliar esperas requiere la excepción de suite Gemini.")
        return self

    @field_validator("ollama_base_url")
    @classmethod
    def local_ollama_only(cls, value):
        return normalize_base_url(value)

    @model_validator(mode="after")
    def require_model_for_selected_provider(self):
        if self.provider != "mock" and (self.model is None or not self.model.strip()):
            raise ValueError(
                "Un proveedor distinto de mock requiere un modelo elegido explícitamente."
            )
        return self


def load_settings(path: Path = ROOT / "config.toml", **overrides) -> Settings:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    data.update({key: value for key, value in overrides.items() if value is not None})
    return Settings.model_validate(data)
