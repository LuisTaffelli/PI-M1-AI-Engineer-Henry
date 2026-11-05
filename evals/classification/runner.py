"""Ejecución explícita del plan con el servicio y métricas de producción."""

from evals.classification.plan import REMOTE_PROVIDERS, EvaluationPlan
from evals.classification.report import evaluation_report
from evals.classification.scoring import classification_result
from evals.common.artifacts import next_metric, write_json
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
    write_json(plan.output / "plan.json", metadata)
    pricing_path = None
    if plan.pricing_data is not None:
        pricing_path = plan.output / "pricing.json"
        pricing_path.write_bytes(plan.pricing_data)
    settings = plan.settings.model_copy(
        update={
            "log_metrics": True,
            "metrics_path": str(plan.output / "metrics.jsonl"),
            "pricing_path": str(pricing_path) if pricing_path else None,
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
            metric = next_metric(
                plan.output / "metrics.jsonl",
                len(rows),
                "Métricas incompletas; conservar corrida, no repetir automáticamente.",
            )
            status = metric["status"]
            row = classification_result(metric, settings.model, case, response)
            rows.append(row)
            append_metric(plan.output / "results.jsonl", row)
            stop = status == "configuration_error" or (
                status != "ok" and not metadata["continue_on_error"]
            )
            if stop:
                break
        if stop:
            break
    report = evaluation_report(rows, plan)
    write_json(plan.output / "summary.json", report)
    return report
