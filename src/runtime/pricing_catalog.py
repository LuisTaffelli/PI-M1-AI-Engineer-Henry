"""Schema, procedencia y lectura de catálogos JSON; sin cálculo ni red."""

from datetime import date
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ..support.schemas import NonEmptyText

Version = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
]
# Strings decimales acotados: sin float binario, exponentes, NaN o infinito.
Price = Annotated[
    str, StringConstraints(pattern=r"^(0|[1-9][0-9]{0,8})(\.[0-9]{1,12})?$")
]


class Rate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    provider: Literal["openai", "gemini"]
    model: NonEmptyText
    mode: Literal["standard_text"]
    currency: Literal["USD"]
    rate_version: Version
    verification: Literal["unverified", "verified_public", "fixture"]
    source_url: str | None = None
    checked_on: str | None = None
    input_usd_per_million: Price
    cached_input_usd_per_million: Price
    output_usd_per_million: Price

    max_input_tokens: int | None = Field(default=None, ge=1)
    requires_cache_write_usage: bool = False
    cache_write_30m_usd_per_million: Price | None = None
    cache_write_12h_usd_per_million: Price | None = None

    @model_validator(mode="after")
    def verification_evidence(self):
        if self.verification == "verified_public":
            date.fromisoformat(self.checked_on or "")
            url = urlsplit(self.source_url or "")
            hosts = {
                "openai": {"openai.com", "developers.openai.com"},
                "gemini": {"ai.google.dev", "aistudio.google.com"},
            }
            if (
                url.scheme != "https"
                or url.hostname not in hosts[self.provider]
                or not url.path
                or url.query
                or url.fragment
                or url.username
                or url.password
            ):
                raise ValueError("Falta fuente pública oficial de la tarifa.")
        return self


class PricingCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    format_version: int = Field(ge=1, le=1)
    catalog_version: Version
    rates: list[Rate]

    @model_validator(mode="after")
    def unique_rates(self):
        keys = [(rate.provider, rate.model, rate.mode) for rate in self.rates]
        if len(keys) != len(set(keys)):
            raise ValueError("Hay tarifas duplicadas para proveedor/modelo/modalidad.")
        return self


def load_catalog(path: Path) -> tuple[PricingCatalog, bytes]:
    if path.suffix != ".json" or path.is_symlink():
        raise ValueError("El catálogo debe ser un archivo JSON regular.")
    data = path.read_bytes()
    return PricingCatalog.model_validate_json(data), data
