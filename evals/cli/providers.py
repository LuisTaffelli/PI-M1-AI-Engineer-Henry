"""Evaluación de corpus multiproveedor; por defecto sólo previsualiza sin red."""

import argparse
import json
import sys
from pathlib import Path

from evals.classification.plan import REMOTE_PROVIDERS, prepare_plan
from evals.classification.runner import execute_plan
from src.llm.prompt_catalog import PROMPT_NAMES
from src.runtime.config import ROOT, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/eval_dataset.jsonl"
    )
    parser.add_argument(
        "--provider", required=True, choices=("mock", "ollama", "openai", "gemini")
    )
    parser.add_argument("--model")
    parser.add_argument(
        "--prompt", action="append", required=True, choices=PROMPT_NAMES
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case-id", action="append")
    selection.add_argument("--all-cases", action="store_true")
    parser.add_argument("--max-calls", type=int, required=True)
    pricing = parser.add_mutually_exclusive_group()
    pricing.add_argument("--pricing", type=Path)
    pricing.add_argument("--no-pricing", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=1)
    parser.add_argument("--max-output-tokens", type=int, default=256)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic-suite", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-remote-inference", action="store_true")
    args = parser.parse_args()
    try:
        if args.provider != "mock" and not args.model:
            raise ValueError("Elegí un modelo explícito.")
        settings = load_settings(
            args.config,
            provider=args.provider,
            model=args.model,
            max_attempts=args.max_attempts,
            **{
                f"{p}_max_output_tokens": args.max_output_tokens
                for p in ("openai", "gemini", "ollama")
            },
        )
        settings = settings.model_copy(
            update={
                "pricing_path": str(
                    args.pricing
                    or settings.pricing_path
                    or ROOT / "pricing/standard-text-2026-11-05.json"
                )
                if not args.no_pricing and args.provider in REMOTE_PROVIDERS
                else None
            }
        )
        plan = prepare_plan(
            args.dataset,
            settings,
            args.case_id or [],
            tuple(args.prompt),
            args.output,
            all_cases=args.all_cases,
            max_calls=args.max_calls,
            diagnostic_suite=args.diagnostic_suite,
            continue_on_error=args.continue_on_error,
        )
        if not args.execute:
            print(json.dumps(plan.metadata, indent=2, ensure_ascii=False))
            return 0
        if args.provider in REMOTE_PROVIDERS and not args.allow_remote_inference:
            raise ValueError(
                "Falta --allow-remote-inference; no se ejecutó ninguna llamada."
            )
        report = execute_plan(
            plan, execute=True, allow_remote_inference=args.allow_remote_inference
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2 if report["failed_cases"] or not report["completed"] else 0
    except (ValueError, OSError):
        print(
            "Configuración, permiso o registro inválido. Revisá el plan y usá una salida nueva; no repetir automáticamente.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
