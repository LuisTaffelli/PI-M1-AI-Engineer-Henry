"""Ejecutar desde la raíz: python -m evals.run_evals. No mide un LLM real."""

import argparse
import json
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.runtime.config import ROOT, Settings, load_settings
from src.support.schemas import NonEmptyText
from src.support.service import simulate_response


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: NonEmptyText
    expected_category: Literal["billing", "technical", "account", "other"]


def load_cases(path: Path) -> list[Case]:
    cases = [Case.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not cases:
        raise ValueError("Dataset vacío.")
    return cases


def evaluate(cases: list[Case], settings: Settings) -> dict:
    if not cases:
        raise ValueError("Dataset vacío.")
    scores = {category: {"count": 0, "correct": 0, "errors": 0} for category in ("billing", "technical", "account", "other")}
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
        group["exact_match"] = group["correct"] / group["count"] if group["count"] else None
    errors = sum(group["errors"] for group in scores.values())
    return {
        "simulated": True,
        "quality_claim": False,
        "warning": "Smoke test del runner con mock fijo; no evalúa capacidad de un modelo ni permite elegir un prompt.",
        "prompt_version": settings.prompt,
        "total": len(cases),
        "errors": errors,
        "exact_match": sum(group["correct"] for group in scores.values()) / len(cases),
        "by_category": scores,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluación estructural offline con mock.")
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/eval_sample.jsonl")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--prompt", choices=["v1_zero_shot", "v2_few_shot"])
    args = parser.parse_args()
    try:
        cases = load_cases(args.dataset)
        report = evaluate(cases, load_settings(args.config, prompt=args.prompt))
    except (ValueError, OSError):
        print("Error: dataset o configuración inválidos.", file=sys.stderr)
        return 2
    print("SIMULACIÓN: resultados del mock, no de un LLM.", file=sys.stderr)
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
