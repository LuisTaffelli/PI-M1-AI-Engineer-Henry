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


def estimate_components(
    usage: TokenUsage, rate: Rate, *, allow_fixture: bool = False
) -> dict[str, str] | None:
    if rate.verification != "verified_public" and not (
        rate.verification == "fixture" and allow_fixture
    ):
        return None
    if not usage.complete or usage.cached_prompt_tokens is None:
        return None
    if (
        rate.max_input_tokens is not None
        and usage.prompt_tokens > rate.max_input_tokens
    ):
        return None
    if (
        usage.reasoning_tokens is not None
        and usage.reasoning_tokens > usage.completion_tokens
    ):
        return None
    if usage.tool_use_prompt_tokens not in (None, 0):
        return None
    writes = usage.cache_write_tokens
    if rate.requires_cache_write_usage and writes is None:
        return None
    writes = writes or 0
    if usage.cached_prompt_tokens + writes > usage.prompt_tokens:
        return None
    short = long = 0
    if writes:
        short, long = usage.cache_write_30m_tokens, usage.cache_write_12h_tokens
        if short is None or long is None or short + long != writes:
            return None
        if (
            rate.cache_write_30m_usd_per_million is None
            or rate.cache_write_12h_usd_per_million is None
        ):
            return None
    elif any(
        value not in (None, 0)
        for value in (usage.cache_write_30m_tokens, usage.cache_write_12h_tokens)
    ):
        return None
    with localcontext() as context:
        context.prec = _precision([usage])
        amounts = {
            "uncached_input_usd": (
                usage.prompt_tokens - usage.cached_prompt_tokens - writes
            )
            * Decimal(rate.input_usd_per_million),
            "cached_input_usd": usage.cached_prompt_tokens
            * Decimal(rate.cached_input_usd_per_million),
            "cache_write_30m_usd": short
            * Decimal(rate.cache_write_30m_usd_per_million or "0"),
            "cache_write_12h_usd": long
            * Decimal(rate.cache_write_12h_usd_per_million or "0"),
            "output_including_reasoning_usd": usage.completion_tokens
            * Decimal(rate.output_usd_per_million),
        }
        return {
            name: format(value / Decimal(1_000_000), "f")
            for name, value in amounts.items()
        }


def estimate_attempt(
    usage: TokenUsage, rate: Rate, *, allow_fixture: bool = False
) -> Decimal | None:
    components = estimate_components(usage, rate, allow_fixture=allow_fixture)
    if components is None:
        return None
    with localcontext() as context:
        context.prec = _precision([usage])
        return sum(map(Decimal, components.values()), Decimal(0))


def _unpriced_reason(usage: TokenUsage, rate: Rate) -> str:
    if not usage.complete:
        return "incomplete_or_inconsistent_usage"
    if usage.cached_prompt_tokens is None:
        return "cached_input_unavailable"
    if (
        rate.max_input_tokens is not None
        and usage.prompt_tokens > rate.max_input_tokens
    ):
        return "rate_input_range_exceeded"
    if rate.requires_cache_write_usage and usage.cache_write_tokens is None:
        return "cache_write_usage_unavailable"
    return "unsupported_or_inconsistent_breakdown"


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
        "cost_unavailable_reason_by_attempt": [None for _ in usages],
        "cost_components_by_attempt": [None for _ in usages],
        "pricing_version": None,
        "rate_version": None,
        "pricing_sha256": None,
        "cost_basis": "standard_text_tokens_only",
        "billing_verified": False,
        "rate_source_url": None,
        "rate_checked_on": None,
    }
    if not usages:
        return result
    if pricing_path is None:
        return {**result, "cost_status": "pricing_unconfigured"}
    try:
        catalog, data = load_catalog(pricing_path)
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
    result.update(
        rate_version=rate.rate_version,
        rate_source_url=rate.source_url
        if rate.verification == "verified_public"
        else None,
        rate_checked_on=rate.checked_on
        if rate.verification == "verified_public"
        else None,
    )
    if rate.verification != "verified_public" and not (
        rate.verification == "fixture" and allow_fixture
    ):
        return {**result, "cost_status": "rate_unverified"}
    costs = [
        estimate_attempt(usage, rate, allow_fixture=allow_fixture) for usage in usages
    ]
    result["cost_unavailable_reason_by_attempt"] = [
        _unpriced_reason(usage, rate) if cost is None else None
        for usage, cost in zip(usages, costs)
    ]
    result["cost_components_by_attempt"] = [
        estimate_components(usage, rate, allow_fixture=allow_fixture)
        for usage in usages
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
