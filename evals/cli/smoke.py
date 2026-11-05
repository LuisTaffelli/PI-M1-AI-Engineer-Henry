"""Ejecutar desde la raíz: python -m evals.run_evals. No mide un LLM real."""

import argparse
import json
import sys
from pathlib import Path

from evals.classification.dataset import check_dataset, load_cases
from evals.classification.smoke import evaluate
from src.llm.prompt_catalog import PROMPT_NAMES
from src.runtime.config import ROOT, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluación estructural offline con mock."
    )
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/eval_sample.jsonl")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--prompt", choices=PROMPT_NAMES)
    parser.add_argument(
        "--check-dataset",
        action="store_true",
        help="Controlar corpus de al menos 30 casos, metadatos y separación, sin proveedor.",
    )
    args = parser.parse_args()
    try:
        cases = load_cases(args.dataset)
        if args.check_dataset:
            report = check_dataset(cases)
        else:
            # También proteger la ejecución normal de un corpus con metadatos.
            if args.dataset.resolve() == ROOT / "data/eval_dataset.jsonl" or any(
                case.case_id is not None for case in cases
            ):
                check_dataset(cases)
            report = evaluate(cases, load_settings(args.config, prompt=args.prompt))
    except (ValueError, OSError):
        print("Error: dataset o configuración inválidos.", file=sys.stderr)
        return 2
    if args.check_dataset:
        print(
            "CONTROL OFFLINE: formato/cobertura/separación; etiquetas pendientes de revisión humana.",
            file=sys.stderr,
        )
    else:
        print("SIMULACIÓN: resultados del mock, no de un LLM.", file=sys.stderr)
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if report.get("errors", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
