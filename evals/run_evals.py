"""Entrada compatible: python -m evals.run_evals; implementación en evals.cli.smoke."""

from evals.classification.dataset import Case as Case
from evals.classification.dataset import check_dataset as check_dataset
from evals.classification.dataset import load_cases as load_cases
from evals.classification.dataset import normalized_query as normalized_query
from evals.classification.smoke import evaluate as evaluate
from evals.cli.smoke import main as main

if __name__ == "__main__":
    raise SystemExit(main())
