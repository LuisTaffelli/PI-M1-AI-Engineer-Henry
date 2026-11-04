"""Consumo reportado: números permitidos, sin conservar el objeto HTTP original."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    cached_prompt_tokens: int | None = None

    def __post_init__(self):
        for value in asdict(self).values():
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(
                    "El consumo debe contener enteros no negativos o null."
                )

        if (
            self.cached_prompt_tokens is not None
            and self.prompt_tokens is not None
            and self.cached_prompt_tokens > self.prompt_tokens
        ):
            raise ValueError("El consumo cacheado no puede superar la entrada.")

    @property
    def complete(self) -> bool:
        return (
            all(
                value is not None
                for value in (
                    self.prompt_tokens,
                    self.completion_tokens,
                    self.total_tokens,
                )
            )
            and self.total_tokens == self.prompt_tokens + self.completion_tokens
        )


def _count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _cached(value: object, inputs: int | None) -> int | None:
    count = _count(value)
    return (
        count if count is not None and inputs is not None and count <= inputs else None
    )


def openai_usage(raw: object) -> TokenUsage:
    if not isinstance(raw, dict):
        return TokenUsage()
    inputs = _count(raw.get("input_tokens"))
    details = raw.get("input_tokens_details")
    cached = details.get("cached_tokens") if isinstance(details, dict) else None
    # Cached sigue incluido en entrada, pero se preserva su desglose para precio.
    return TokenUsage(
        inputs,
        _count(raw.get("output_tokens")),
        _count(raw.get("total_tokens")),
        _cached(cached, inputs),
    )


def gemini_usage(raw: object) -> TokenUsage:
    if not isinstance(raw, dict):
        return TokenUsage()
    inputs = _count(raw.get("total_input_tokens"))
    outputs = _count(raw.get("total_output_tokens"))
    thoughts = _count(raw.get("total_thought_tokens"))
    total = _count(raw.get("total_tokens"))
    tools = _count(raw.get("total_tool_use_tokens"))
    # Interactions reporta pensamiento separado del texto. Sólo normalizar salida
    # cuando los contadores permiten reconciliar el total; nunca sumar initial_input.
    completion = None
    if (
        inputs is not None
        and outputs is not None
        and total is not None
        and tools in (None, 0)
    ):
        if total == inputs + outputs and thoughts in (None, 0):
            completion = outputs
        elif thoughts is not None and total == inputs + outputs + thoughts:
            completion = outputs + thoughts
    return TokenUsage(
        inputs, completion, total, _cached(raw.get("total_cached_tokens"), inputs)
    )


def ollama_usage(raw: object) -> TokenUsage:
    if not isinstance(raw, dict):
        return TokenUsage()
    inputs = _count(raw.get("prompt_eval_count"))
    outputs = _count(raw.get("eval_count"))
    # Ollama no devuelve total_tokens: es suma derivada de sus dos contadores.
    total = inputs + outputs if inputs is not None and outputs is not None else None
    return TokenUsage(inputs, outputs, total)


def summarize_usage(attempts: list[TokenUsage]) -> dict:
    observed = [asdict(usage) for usage in attempts]
    complete = bool(attempts) and all(usage.complete for usage in attempts)
    any_counts = any(value is not None for row in observed for value in row.values())
    if complete:
        status = "reported"
    elif any_counts:
        status = "partial"
    elif attempts:
        status = "unavailable"
    else:
        status = "not_requested"
    return {
        **{
            name: sum(row[name] for row in observed) if complete else None
            for name in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        "cached_prompt_tokens": sum(usage.cached_prompt_tokens for usage in attempts)
        if complete
        and all(usage.cached_prompt_tokens is not None for usage in attempts)
        else None,
        "usage_status": status,
        "usage_by_attempt": observed,
    }
