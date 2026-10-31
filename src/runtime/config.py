"""Configuración TOML local; no lee entorno ni archivos de credenciales."""

from pathlib import Path
import tomllib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider: Literal["mock"] = "mock"
    prompt: Literal["v1_zero_shot", "v2_few_shot"] = "v1_zero_shot"
    mock_scenario: Literal["fixed", "malformed", "invalid_contract", "recover_once"] = "fixed"
    max_attempts: int = Field(default=2, ge=1, le=3)
    max_query_chars: int = Field(default=4000, ge=1, le=20000)
    log_metrics: bool = False
    metrics_path: str = Field(default="data/metrics.jsonl", min_length=1)


def load_settings(path: Path = ROOT / "config.toml", **overrides) -> Settings:
    with path.open("rb") as stream:
        data = tomllib.load(stream)
    data.update({key: value for key, value in overrides.items() if value is not None})
    return Settings.model_validate(data)
