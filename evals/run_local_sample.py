"""Entrada compatible: python -m evals.run_local_sample; implementación en evals.cli.local."""

from evals.classification.local import run_sample as run_sample
from evals.classification.scoring import summarize as summarize
from evals.cli.local import main as main

if __name__ == "__main__":
    raise SystemExit(main())
