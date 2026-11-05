"""Smoke test con mock: verifica el recorrido, no mide calidad de un LLM."""

from evals.classification.dataset import Case
from src.runtime.config import Settings
from src.support.service import simulate_response


def evaluate(cases: list[Case], settings: Settings) -> dict:
    if settings.provider != "mock":
        raise ValueError(
            "Este runner de checkpoint admite sólo mock, sin llamadas API."
        )
    if not cases:
        raise ValueError("Dataset vacío.")
    scores = {
        category: {"count": 0, "correct": 0, "errors": 0}
        for category in ("billing", "technical", "account", "other")
    }
    # Las evals no mezclan sus requests con las métricas de uso de CLI.
    settings = settings.model_copy(update={"log_metrics": False})
    for case in cases:
        group = scores[case.expected_category]
        group["count"] += 1
        try:
            response = simulate_response(case.query, settings=settings)
            group["correct"] += int(response.category == case.expected_category)
        except (ValueError, OSError):
            group["errors"] += 1
    for group in scores.values():
        group["exact_match"] = (
            group["correct"] / group["count"] if group["count"] else None
        )
    errors = sum(group["errors"] for group in scores.values())
    return {
        "simulated": True,
        "quality_claim": False,
        "warning": "Smoke test del runner con mock fijo; no evalúa capacidad de un modelo ni permite elegir un prompt.",
        "prompt_version": settings.prompt,
        "total": len(cases),
        "errors": errors,
        "ambiguous_total": sum(case.ambiguous for case in cases),
        "ambiguous_included_in_score": True,
        "exact_match": sum(group["correct"] for group in scores.values()) / len(cases),
        "by_category": scores,
    }
