"""Totales trazables sólo sobre casos procesados; subtotal conocido no es factura."""

from collections import Counter
from decimal import Decimal, localcontext

TOKEN_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cached_prompt_tokens",
    "reasoning_tokens",
    "tool_use_prompt_tokens",
    "cache_write_tokens",
    "cache_write_30m_tokens",
    "cache_write_12h_tokens",
)


def summarize_financials(rows: list[dict]) -> dict:
    attempts = [usage for row in rows for usage in row.get("usage_by_attempt", [])]
    tokens = {}
    for name in TOKEN_FIELDS:
        known = [usage[name] for usage in attempts if usage.get(name) is not None]
        tokens[name] = {
            "total": sum(known) if attempts and len(known) == len(attempts) else None,
            "reported_subtotal": sum(known) if known else None,
            "attempts_with_reported_value": len(known),
        }
    known_costs = [
        Decimal(cost)
        for row in rows
        for cost in row.get("cost_by_attempt", [])
        if cost is not None
        and row.get("cost_status") in {"estimated", "partial"}
        and not row.get("simulated", False)
    ]
    with localcontext() as context:
        context.prec = max(50, sum(len(str(cost)) for cost in known_costs) + 10)
        subtotal = format(sum(known_costs, Decimal(0)), "f") if known_costs else None
    all_estimated = (
        bool(rows)
        and len(known_costs) == len(attempts)
        and all(
            row.get("cost_status") == "estimated" and not row.get("simulated", False)
            for row in rows
        )
    )
    return {
        "scope": "processed_cases_only",
        "processed_cases": len(rows),
        "generation_attempts": len(attempts),
        "tokens": tokens,
        "cost_usd": subtotal if all_estimated else None,
        "known_estimated_subtotal_usd": subtotal,
        "attempts_with_estimated_cost": len(known_costs),
        "cost_status_counts": dict(
            Counter(row.get("cost_status", "unknown") for row in rows)
        ),
        "cost_unavailable_reason_counts": dict(
            Counter(
                reason
                for row in rows
                for reason in row.get("cost_unavailable_reason_by_attempt", [])
                if reason
            )
        ),
        "billing_verified": False,
        "pricing_sha256": sorted(
            {row["pricing_sha256"] for row in rows if row.get("pricing_sha256")}
        ),
    }
