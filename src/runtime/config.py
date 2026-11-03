"""Configuración TOML local; no lee entorno ni archivos de credenciales."""

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider: Literal["mock", "openai", "gemini"] = "mock"
    model: str | None = Field(default=None, min_length=1, max_length=128)
    openai_max_output_tokens: int = Field(default=512, ge=16, le=4096)
    gemini_max_output_tokens: int = Field(default=512, ge=16, le=4096)
    prompt: Literal["v1_zero_shot", "v2_few_shot"] = "v1_zero_shot"
    mock_scenario: Literal["fixed", "malformed", "invalid_contract", "recover_once"] = (
        "fixed"
    )
    max_attempts: int = Field(default=2, ge=1, le=3)
    max_query_chars: int = Field(default=4000, ge=1, le=20000)
    log_metrics: bool = False
    metrics_path: str = Field(default="data/metrics.jsonl", min_length=1)

    @model_validator(mode="after")
    def require_model_for_remote_provider(self):
        if self.provider != "mock" and (self.model is None or not self.model.strip()):
            raise ValueError(
                "Un proveedor remoto requiere un modelo elegido explícitamente."
            )
        return self


def load_settings(path: Path = ROOT / "config.toml", **overrides) -> Settings:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    data.update({key: value for key, value in overrides.items() if value is not None})
    return Settings.model_validate(data)
