"""Diagnóstico offline del prechequeo y guardrail de salida; no llama modelos."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from evals.adversarial.cases import load_suite
from evals.adversarial.guardrails import evaluate
from src.runtime.config import ROOT, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attacks", type=Path, default=ROOT / "evals/adversarial.jsonl"
    )
    parser.add_argument(
        "--controls", type=Path, default=ROOT / "evals/guardrail_controls.jsonl"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        settings = load_settings()
        report = evaluate(
            load_suite(args.attacks, args.controls),
            max_query_chars=settings.max_query_chars,
        )
        report["timestamp"] = datetime.now(timezone.utc).isoformat()
        report["dataset_sha256"] = {
            "attacks": hashlib.sha256(args.attacks.read_bytes()).hexdigest(),
            "controls": hashlib.sha256(args.controls.read_bytes()).hexdigest(),
        }
        report["source_sha256"] = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "evals/run_guardrail_diagnostics.py",
                "evals/cli/guardrails.py",
                "evals/adversarial/cases.py",
                "evals/adversarial/guardrails.py",
                "src/support/guardrails.py",
                "src/support/schemas.py",
                "src/runtime/config.py",
                "src/runtime/paths.py",
                "config.toml",
            )
        }
        raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(raw)
    except (ValueError, OSError):
        print(
            "Error: suite/configuración inválida o salida ya existente; no se sobrescribió.",
            file=sys.stderr,
        )
        return 2
    print(raw, end="")
    # 0 indica que se produjo el diagnóstico, no que se superaron las expectativas.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
