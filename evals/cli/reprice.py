"""Reestimar una corrida registrada, offline y sin modificar sus archivos originales."""

import argparse
import json
import sys
from pathlib import Path

from evals.classification.reprice import reprice
from src.runtime.paths import ROOT


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
