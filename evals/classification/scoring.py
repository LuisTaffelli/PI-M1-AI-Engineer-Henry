"""Criterios compartidos de clasificación; sin llamadas a proveedores."""

from collections import Counter
from statistics import median

from src.llm.prompt_catalog import PROMPT_NAMES


def summarize(rows: list[dict]) -> dict:
    reports = {}
    for prompt in PROMPT_NAMES:
        group = [row for row in rows if row["prompt_version"] == prompt]
        if not group:
            continue
        scores = {}
        for category in ("billing", "technical", "account", "other"):
            cases = [r for r in group if r["expected_category"] == category]
            scores[category] = {
                "count": len(cases),
                "correct": sum(r["correct"] for r in cases),
                "errors": sum(r["status"] != "ok" for r in cases),
                "exact_match": sum(r["correct"] for r in cases) / len(cases)
                if cases
                else None,
            }
        reports[prompt] = {
            "total": len(group),
            "correct": sum(r["correct"] for r in group),
            "exact_match": sum(r["correct"] for r in group) / len(group),
            "validated_outputs": sum(r["status"] == "ok" for r in group),
            "schema_valid_outputs": sum(
                r["application_contract_valid"] is True for r in group
            ),
            "status_counts": dict(Counter(r["status"] for r in group)),
            "latency_median_seconds": median(r["latency_seconds"] for r in group),
            "latency_min_seconds": min(r["latency_seconds"] for r in group),
            "latency_max_seconds": max(r["latency_seconds"] for r in group),
            "by_category": scores,
            "confusion_matrix": {
                expected: dict(
                    Counter(
                        r["predicted_category"] or "error"
                        for r in group
                        if r["expected_category"] == expected
                    )
                )
                for expected in scores
            },
            "by_ambiguity": {
                name: {
                    "count": len(selected),
                    "correct": sum(r["correct"] for r in selected),
                    "exact_match": sum(r["correct"] for r in selected) / len(selected)
                    if selected
                    else None,
                }
                for name, selected in (
                    ("marked_ambiguous", [r for r in group if r["ambiguous"]]),
                    ("not_marked_ambiguous", [r for r in group if not r["ambiguous"]]),
                )
            },
        }
    return {
        "simulated": False,
        "quality_claim": False,
        "label_review_status": "not_verified_by_this_run",
        "warning": "Comparación exploratoria con referencias propuestas; sin validación humana nueva, ranking general ni elección definitiva de prompt.",
        "by_prompt": reports,
    }


def classification_result(metric, model, case, response) -> dict:
    """Contrato compartido de filas: sin ticket ni respuesta cruda."""
    status = metric["status"]
    return {
        **metric,
        "model": model,
        "case_id": case.case_id,
        "expected_category": case.expected_category,
        "ambiguous": case.ambiguous,
        "predicted_category": response.category if response else None,
        "correct": response is not None and response.category == case.expected_category,
        "application_contract_valid": True
        if status in {"ok", "rejected_output"}
        else False
        if status == "invalid_response"
        else None,
        "application_output_guardrail_passed": True
        if status == "ok"
        else False
        if status == "rejected_output"
        else None,
    }
