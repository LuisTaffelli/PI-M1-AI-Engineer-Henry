"""Reestimar una corrida registrada, offline y sin modificar sus archivos originales."""

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from evals.evaluation_plan import REMOTE_PROVIDERS
from evals.usage_cost_report import summarize_financials
from src.llm.prompt_catalog import PROMPT_NAMES
from src.llm.usage import TokenUsage
from src.runtime.config import ROOT
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--pricing", type=Path, default=ROOT / "pricing/standard-text-2026-11-05.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = reprice(args.run_dir, args.pricing, args.output)
    except (ValueError, OSError, TypeError, KeyError):
        print(
            "Corrida o catálogo incompatible; usar salida nueva y conservar originales.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
