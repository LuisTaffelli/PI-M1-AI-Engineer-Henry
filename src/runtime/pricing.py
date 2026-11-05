"""API compatible de costos: coordina catálogo, cálculo y métricas por intento."""

import hashlib
from decimal import Decimal, localcontext
from pathlib import Path

from ..llm.usage import TokenUsage
from .pricing_calculation import _precision, _unpriced_reason
from .pricing_calculation import estimate_attempt as estimate_attempt
from .pricing_calculation import estimate_components as estimate_components
from .pricing_catalog import Price as Price
from .pricing_catalog import PricingCatalog as PricingCatalog
from .pricing_catalog import Rate as Rate
from .pricing_catalog import Version as Version
from .pricing_catalog import load_catalog as load_catalog


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
