"""Aritmética Decimal por intento, alcance de tarifas y razones de costo desconocido."""

from decimal import Decimal, localcontext

from ..llm.usage import TokenUsage
from .pricing_catalog import Rate


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
