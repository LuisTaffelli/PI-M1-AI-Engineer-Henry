"""Entrada compatible: python -m evals.reprice_run; implementación en evals.cli.reprice."""

from evals.classification.reprice import reprice as reprice
from evals.cli.reprice import main as main

if __name__ == "__main__":
    raise SystemExit(main())
