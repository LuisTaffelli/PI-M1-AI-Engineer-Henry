"""Ataques pareados multiproveedor; preview sin claves ni red por defecto."""

import argparse
import json
import sys
from pathlib import Path

from evals.adversarial.plan import prepare_plan
from evals.adversarial.runner import execute_plan
from src.llm.prompt_catalog import PROMPT_NAMES
from src.runtime.config import ROOT, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--provider", choices=("mock", "ollama", "openai", "gemini"))
    parser.add_argument("--model")
    parser.add_argument(
        "--prompt", action="append", choices=PROMPT_NAMES, required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-calls", type=int, required=True)
    parser.add_argument(
        "--max-output-tokens", type=int, choices=range(16, 257), metavar="16..256"
    )
    pricing = parser.add_mutually_exclusive_group()
    pricing.add_argument("--pricing", type=Path)
    pricing.add_argument("--no-pricing", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute", action="store_true")
    mode.add_argument(
        "--preview",
        action="store_true",
        help="No ejecutar, incluso con el flag local histórico.",
    )
    parser.add_argument("--allow-local-inference", action="store_true")
    parser.add_argument("--allow-remote-inference", action="store_true")
    args = parser.parse_args()
    try:
        if args.provider in {"ollama", "openai", "gemini"} and not args.model:
            raise ValueError(
                "Un override de proveedor requiere elegir modelo explícito."
            )
        settings = load_settings(
            args.config,
            provider=args.provider,
            model=args.model,
            **{
                f"{p}_max_output_tokens": args.max_output_tokens
                for p in ("openai", "gemini", "ollama")
            },
        )
        settings = settings.model_copy(
            update={
                "pricing_path": None
                if args.no_pricing
                else str(args.pricing)
                if args.pricing
                else settings.pricing_path
            }
        )
        plan = prepare_plan(
            settings, tuple(args.prompt), args.output, max_calls=args.max_calls
        )
        # Compatibilidad: el comando antiguo de Ollama ya pedía inferencia explícita.
        execute = not args.preview and (
            args.execute
            or (settings.provider == "ollama" and args.allow_local_inference)
        )
        if not execute:
            print(json.dumps(plan.metadata, ensure_ascii=False, indent=2))
            return 0
        report = execute_plan(
            plan,
            execute=True,
            allow_local_inference=args.allow_local_inference,
            allow_remote_inference=args.allow_remote_inference,
        )
    except (ValueError, OSError):
        print(
            "Error de configuración, permiso o registro; conservar la corrida y no repetir automáticamente.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["execution"]["completed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
