"""Ejecución explícita del plan con el servicio y métricas de producción."""

import json

from evals.classification_report import summarize
from evals.evaluation_plan import REMOTE_PROVIDERS, EvaluationPlan
from src.runtime.metrics import append_metric
from src.support.service import simulate_response


def execute_plan(
    plan: EvaluationPlan, *, execute: bool = False, allow_remote_inference: bool = False
) -> dict:
    remote = plan.settings.provider in REMOTE_PROVIDERS
    if not execute or (remote and not allow_remote_inference):
        raise ValueError(
            "Se requiere --execute y, para remotos, --allow-remote-inference."
        )
    plan.output.mkdir(parents=True, exist_ok=False)
    metadata = {
        **plan.metadata,
        "execution_requested": True,
        "remote_execution_confirmed": remote,
    }
    (plan.output / "plan.json").write_text(json.dumps(metadata, indent=2) + "\n")
    settings = plan.settings.model_copy(
        update={
            "log_metrics": True,
            "metrics_path": str(plan.output / "metrics.jsonl"),
            "pricing_path": None,
        }
    )
    rows = []
    stop = False
    for prompt in plan.prompts:
        for case in plan.cases:
            response = None
            try:
                response = simulate_response(
                    case.query, settings=settings.model_copy(update={"prompt": prompt})
                )
            except (ValueError, OSError):
                pass  # Sólo códigos sanitizados del servicio, nunca excepciones crudas.
            metrics = (plan.output / "metrics.jsonl").read_text().splitlines()
            if len(metrics) != len(rows) + 1:
                raise ValueError(
                    "Métricas incompletas; conservar corrida, no repetir automáticamente."
                )
            metric = json.loads(metrics[-1])
            status = metric["status"]
            row = {
                **metric,
                "model": settings.model,
                "case_id": case.case_id,
                "expected_category": case.expected_category,
                "ambiguous": case.ambiguous,
                "predicted_category": response.category if response else None,
                "correct": response is not None
                and response.category == case.expected_category,
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
            rows.append(row)
            append_metric(plan.output / "results.jsonl", row)
            stop = status == "configuration_error" or (
                status != "ok" and not metadata["continue_on_error"]
            )
            if stop:
                break
        if stop:
            break
    report = summarize(rows)
    for prompt in plan.prompts:
        group = report["by_prompt"].setdefault(
            prompt, {"total": 0, "exact_match": None}
        )
        group["planned"] = len(plan.cases)
        group["not_run"] = len(plan.cases) - group["total"]
        group["exact_match_on_processed"] = group["exact_match"]
        if group["not_run"]:
            group["exact_match"] = None
            for category in group.get("by_category", {}).values():
                category["exact_match_on_processed"] = category["exact_match"]
                category["exact_match"] = None
            for subset in group.get("by_ambiguity", {}).values():
                subset["exact_match_on_processed"] = subset["exact_match"]
                subset["exact_match"] = None
    attempts = sum(row["attempts"] for row in rows)
    report.update(
        simulated=settings.provider == "mock",
        provider=settings.provider,
        model=settings.model,
        suite_kind=metadata["suite_kind"],
        planned=metadata["planned_cases"],
        processed=len(rows),
        not_run=metadata["planned_cases"] - len(rows),
        completed=len(rows) == metadata["planned_cases"],
        generation_attempts=attempts,
        remote_calls_attempted=attempts if remote else 0,
        provider_calls_upper_bound=metadata["provider_calls_upper_bound"],
        monetary_cap_enforced=False,
        failed_cases=sum(row["status"] != "ok" for row in rows),
    )
    (plan.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
