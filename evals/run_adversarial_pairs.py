"""Prueba pareada optativa de redirección de categoría, sólo con Ollama local."""

import argparse
import json
import sys
from pathlib import Path

from evals.paired_cases import AttackPair as AttackPair
from evals.paired_cases import load_protocol as load_protocol
from evals.paired_evaluation import run_pairs as run_pairs
from evals.paired_report import analyze as analyze
from src.llm.prompt_catalog import PROMPT_NAMES
from src.runtime.config import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--prompt", action="append", choices=PROMPT_NAMES, required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-calls", type=int, required=True)
    parser.add_argument("--allow-local-inference", action="store_true")
    args = parser.parse_args()
    try:
        report = run_pairs(
            load_settings(args.config),
            tuple(args.prompt),
            args.output,
            allow_local_inference=args.allow_local_inference,
            max_calls=args.max_calls,
        )
    except (ValueError, OSError):
        print(
            "Error de configuración/registro; no sobrescribir la corrida.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
