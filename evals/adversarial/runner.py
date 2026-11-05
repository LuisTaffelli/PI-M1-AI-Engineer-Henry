"""Ejecución pareada multiproveedor mediante el servicio y guardrails comunes."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from evals.adversarial.plan import REMOTE_PROVIDERS, PairedPlan, prepare_plan
from evals.adversarial.report import analyze, execution_summary
from evals.common.artifacts import next_metric, write_json
from src.runtime.config import ROOT, Settings
from src.runtime.metrics import append_metric
from src.support.service import simulate_response


def execute_plan(
    plan: PairedPlan,
    *,
    execute: bool = False,
    allow_local_inference: bool = False,
    allow_remote_inference: bool = False,
) -> dict:
    remote = plan.settings.provider in REMOTE_PROVIDERS
    if (
        not execute
        or (remote and not allow_remote_inference)
        or (plan.settings.provider == "ollama" and not allow_local_inference)
    ):
        raise ValueError(
            "Falta permiso explícito para ejecutar el proveedor seleccionado."
        )
    plan.output.mkdir(parents=True, exist_ok=False)
    write_json(
        plan.output / "plan.json",
        {
            **plan.metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "execution_requested": True,
            "remote_execution_confirmed": remote,
        },
    )
    pricing_path = None
    if plan.pricing_data is not None:
        pricing_path = plan.output / "pricing.json"
        pricing_path.write_bytes(plan.pricing_data)
    settings = plan.settings.model_copy(
        update={"pricing_path": str(pricing_path) if pricing_path else None}
    )
    rows = []
    stop = False
    for prompt in plan.prompts:
        current = settings.model_copy(update={"prompt": prompt})
        for case_id, condition, query, expected, target in plan.jobs:
            response = None
            try:
                response = simulate_response(query, settings=current)
            except (ValueError, OSError):
                pass  # No persistir mensajes/cuerpos de error ni repetir llamadas.
            metric = next_metric(
                Path(current.metrics_path),
                len(rows),
                "Métricas incompletas; conservar corrida parcial.",
            )
            row = {
                **metric,
                "model": current.model,
                "case_id": case_id,
                "condition": condition,
                "expected_category": expected,
                "attacker_target": target,
                "category": response.category if response else None,
            }
            append_metric(plan.output / "results.jsonl", row)
            rows.append(row)
            print(f"{prompt} {case_id} {condition}: {row['status']}", file=sys.stderr)
            if row["status"] in {"configuration_error", "provider_error"}:
                stop = True
                break
        if stop:
            break
    # analyze conserva el formato histórico para replay; ejecución se informa aparte.
    report = {**analyze(rows), "execution": execution_summary(rows, plan.metadata)}
    write_json(plan.output / "summary.json", report)
    return report


def run_pairs(
    settings: Settings,
    prompts: tuple[str, ...],
    output: Path,
    *,
    allow_local_inference: bool = False,
    max_calls: int,
    pairs_path: Path = ROOT / "evals/adversarial_pairs.jsonl",
    attack_paths: list[Path] | None = None,
    controls_path: Path = ROOT / "evals/guardrail_controls.jsonl",
    execute: bool = False,
    allow_remote_inference: bool = False,
):
    """Fachada histórica: el permiso Ollama sigue implicando ejecución local."""
    plan = prepare_plan(
        settings,
        prompts,
        output,
        max_calls=max_calls,
        pairs_path=pairs_path,
        attack_paths=attack_paths,
        controls_path=controls_path,
    )
    return execute_plan(
        plan,
        execute=execute or (settings.provider == "ollama" and allow_local_inference),
        allow_local_inference=allow_local_inference,
        allow_remote_inference=allow_remote_inference,
    )
