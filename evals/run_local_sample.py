"""Comparación optativa Ollama, con selección y presupuesto explícitos; sin APIs remotas."""

import argparse
import json
import sys
from pathlib import Path

from evals.classification_report import summarize as summarize
from evals.local_evaluation import run_sample as run_sample
from src.llm.prompt_catalog import DEFAULT_COMPARISON, PROMPT_NAMES
from src.runtime.config import ROOT, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/eval_dataset.jsonl"
    )
    parser.add_argument("--config", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case-id", action="append")
    selection.add_argument("--all-cases", action="store_true")
    parser.add_argument("--max-generations", type=int, default=8)
    parser.add_argument("--prompt", action="append", choices=PROMPT_NAMES)
    parser.add_argument("--diagnostic-suite", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-local-inference", action="store_true")
    args = parser.parse_args()
    try:
        report = run_sample(
            args.dataset,
            load_settings(args.config),
            args.case_id or [],
            args.output,
            allow_local_inference=args.allow_local_inference,
            all_cases=args.all_cases,
            max_generations=args.max_generations,
            diagnostic_suite=args.diagnostic_suite,
            prompts=tuple(args.prompt) if args.prompt else DEFAULT_COMPARISON,
        )
    except (ValueError, OSError):
        print(
            "Error de configuración/registro; no sobrescribir la corrida.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return (
        2
        if any(
            group["validated_outputs"] != group["total"]
            for group in report["by_prompt"].values()
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
