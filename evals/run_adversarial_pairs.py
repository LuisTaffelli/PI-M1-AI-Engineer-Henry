"""Entrada compatible: python -m evals.run_adversarial_pairs; implementación en evals.cli.adversarial."""

from evals.adversarial.pairs import AttackPair as AttackPair
from evals.adversarial.pairs import load_protocol as load_protocol
from evals.adversarial.report import analyze as analyze
from evals.adversarial.runner import run_pairs as run_pairs
from evals.cli.adversarial import main as main

if __name__ == "__main__":
    raise SystemExit(main())
