"""Entrada compatible: python -m evals.run_guardrail_diagnostics; implementación en evals.cli.guardrails."""

from evals.adversarial.cases import DiagnosticCase as DiagnosticCase
from evals.adversarial.cases import load_suite as load_suite
from evals.adversarial.guardrails import evaluate as evaluate
from evals.cli.guardrails import main as main

if __name__ == "__main__":
    raise SystemExit(main())
