"""Estimación Decimal de tokens de texto estándar; sin red ni precios incorporados."""

import hashlib
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ..llm.usage import TokenUsage
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


def _precision(usages: list[TokenUsage]) -> int:
    digits = max(
        (
            len(str(value or 0))
            for usage in usages
            for value in (usage.prompt_tokens, usage.completion_tokens)
        ),
        default=1,
    )
    return max(50, digits + len(str(len(usages))) + 32)


def estimate_attempt(
    usage: TokenUsage, rate: Rate, *, allow_fixture: bool = False
) -> Decimal | None:
    if rate.verification != "verified_public" and not (
        rate.verification == "fixture" and allow_fixture
    ):
        return None
    if not usage.complete or usage.cached_prompt_tokens is None:
        return None
    with localcontext() as context:
        context.prec = _precision([usage])
        return (
            (usage.prompt_tokens - usage.cached_prompt_tokens)
            * Decimal(rate.input_usd_per_million)
            + usage.cached_prompt_tokens * Decimal(rate.cached_input_usd_per_million)
            + usage.completion_tokens * Decimal(rate.output_usd_per_million)
        ) / Decimal(1_000_000)


def cost_metrics(
    usages: list[TokenUsage],
    *,
    provider: str,
    model: str | None,
    pricing_path: Path | None,
    allow_fixture: bool = False,
) -> dict:
    result = {
        "cost_usd": None,
        "cost_status": "not_requested",
        "cost_by_attempt": [None for _ in usages],
        "pricing_version": None,
        "rate_version": None,
        "pricing_sha256": None,
        "cost_basis": "standard_text_tokens_only",
    }
    if not usages:
        return result
    if pricing_path is None:
        return {**result, "cost_status": "pricing_unconfigured"}
    try:
        # Nunca interpretar .env ni ejecutar archivos: sólo catálogo JSON explícito.
        if pricing_path.suffix != ".json" or pricing_path.is_symlink():
            raise ValueError("El catálogo debe ser un archivo JSON.")
        data = pricing_path.read_bytes()
        catalog = PricingCatalog.model_validate_json(data)
    except (OSError, UnicodeError, ValueError):
        return {**result, "cost_status": "pricing_unavailable"}
    result.update(
        pricing_version=catalog.catalog_version,
        pricing_sha256=hashlib.sha256(data).hexdigest(),
    )
    rate = next(
        (
            rate
            for rate in catalog.rates
            if rate.provider == provider
            and rate.model == model
            and rate.mode == "standard_text"
        ),
        None,
    )
    if rate is None:
        return {**result, "cost_status": "rate_missing"}
    result["rate_version"] = rate.rate_version
    if rate.verification != "verified_public" and not (
        rate.verification == "fixture" and allow_fixture
    ):
        return {**result, "cost_status": "rate_unverified"}
    costs = [
        estimate_attempt(usage, rate, allow_fixture=allow_fixture) for usage in usages
    ]
    result["cost_by_attempt"] = [
        format(cost, "f") if cost is not None else None for cost in costs
    ]
    if any(cost is None for cost in costs):
        return {
            **result,
            "cost_status": "partial"
            if any(cost is not None for cost in costs)
            else "usage_unavailable",
        }
    with localcontext() as context:
        context.prec = _precision(usages)
        total = sum(costs, Decimal(0))
    return {
        **result,
        "cost_usd": format(total, "f"),
        "cost_status": "fixture_estimate"
        if rate.verification == "fixture"
        else "estimated",
    }
