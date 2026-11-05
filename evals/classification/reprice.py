"""Reestimar una corrida registrada, offline y sin modificar sus archivos originales."""

import hashlib
import json
from datetime import date
from pathlib import Path

from evals.classification.plan import REMOTE_PROVIDERS
from evals.common.costs import summarize_financials
from src.llm.prompt_catalog import PROMPT_NAMES
from src.llm.usage import TokenUsage
from src.runtime.metrics import append_metric
from src.runtime.pricing import cost_metrics, load_catalog


def reprice(run: Path, pricing: Path, output: Path) -> dict:
    plan_data = (run / "plan.json").read_bytes()
    metrics_data = (run / "metrics.jsonl").read_bytes()
    plan = json.loads(plan_data)
    if not isinstance(plan, dict):
        raise ValueError("Plan inválido.")
    provider, model = plan.get("provider"), plan.get("model")
    if (
        provider not in REMOTE_PROVIDERS
        or not isinstance(model, str)
        or not model.strip()
    ):
        raise ValueError("La corrida requiere proveedor/modelo remoto registrados.")
    _, pricing_data = load_catalog(pricing)
    rows = []
    for number, line in enumerate(metrics_data.splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError("Métrica inválida.")
        if (
            raw.get("provider") != provider
            or raw.get("simulated") is not False
            or raw.get("prompt_version") not in PROMPT_NAMES
        ):
            raise ValueError("Sólo registros remotos reales compatibles, sin fixtures.")
        if raw.get("model", model) != model or type(raw.get("attempts")) is not int:
            raise ValueError("Modelo o intentos inconsistentes.")
        usages = [TokenUsage(**usage) for usage in raw["usage_by_attempt"]]
        if len(usages) != raw["attempts"] or not 0 <= len(usages) <= 3:
            raise ValueError("Registro de intentos incompleto.")
        rows.append(
            {
                "source_line": number,
                "provider": provider,
                "model": model,
                "prompt_version": raw["prompt_version"],
                "simulated": False,
                "usage_by_attempt": [usage.__dict__ for usage in usages],
            }
        )
    if not rows or output.resolve() == run.resolve():
        raise ValueError("Se requiere una corrida no vacía y una salida nueva.")
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "pricing.json"
    snapshot.write_bytes(pricing_data)
    for row in rows:
        usages = [TokenUsage(**usage) for usage in row["usage_by_attempt"]]
        row.update(
            cost_metrics(usages, provider=provider, model=model, pricing_path=snapshot)
        )
        append_metric(output / "costs.jsonl", row)
    report = {
        "retrospective_estimate": True,
        "repriced_on": date.today().isoformat(),
        "provider": provider,
        "model": model,
        "source_plan_sha256": hashlib.sha256(plan_data).hexdigest(),
        "source_metrics_sha256": hashlib.sha256(metrics_data).hexdigest(),
        "usage_and_cost": summarize_financials(rows),
        "by_prompt": {
            prompt: summarize_financials(
                [r for r in rows if r["prompt_version"] == prompt]
            )
            for prompt in PROMPT_NAMES
            if any(r["prompt_version"] == prompt for r in rows)
        },
    }
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
