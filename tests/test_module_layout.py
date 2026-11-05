"""Regresiones de recursos/imports después de mover los módulos internos."""

import json
import subprocess
import sys
import tomllib
import unittest
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

from src.runtime.config import ROOT


class ModuleLayoutTests(unittest.TestCase):
    def invoke_from_other_directory(self, module, *args):
        # Hacer disponible el árbol fuente explícitamente, sin usar el paquete
        # antiguo instalado ni copiar el entorno/credenciales de la máquina.
        with TemporaryDirectory() as directory:
            return subprocess.run(
                [sys.executable, "-m", module, *args],
                cwd=directory,
                env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
            )

    def test_cli_loads_config_and_prompts_outside_project_directory(self):
        self.assertEqual(ROOT, Path(__file__).resolve().parents[1])
        for scenario, expected in (("fixed", 0), ("recover_once", 0), ("malformed", 2)):
            result = self.invoke_from_other_directory(
                "src.main",
                "Me cobraron dos veces este mes.",
                "--prompt",
                "v2_few_shot",
                "--mock-scenario",
                scenario,
                "--no-metrics",
            )
            with self.subTest(scenario=scenario):
                self.assertEqual(result.returncode, expected, result.stderr)
                if expected:
                    self.assertEqual(result.stdout, "")
                else:
                    self.assertEqual(json.loads(result.stdout)["category"], "other")
                    self.assertIn("SIMULACIÓN", result.stderr)

    def test_eval_loads_dataset_outside_project_directory(self):
        for version in ("v1_zero_shot", "v2_few_shot"):
            result = self.invoke_from_other_directory(
                "evals.run_evals", "--prompt", version
            )
            with self.subTest(version=version):
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["total"], 4)
                self.assertEqual(report["exact_match"], 0.25)
                self.assertFalse(report["quality_claim"])

    def test_legacy_imports_resolve_to_the_same_implementations(self):
        aliases = {
            "evals.run_evals": {
                "evals.datasets": (
                    "Case",
                    "load_cases",
                    "normalized_query",
                    "check_dataset",
                )
            },
            "evals.run_local_sample": {
                "evals.local_evaluation": ("run_sample",),
                "evals.classification_report": ("summarize",),
            },
            "evals.run_guardrail_diagnostics": {
                "evals.diagnostic_cases": ("DiagnosticCase", "load_suite"),
                "evals.guardrail_report": ("evaluate",),
            },
            "evals.run_adversarial_pairs": {
                "evals.paired_cases": ("AttackPair", "load_protocol"),
                "evals.paired_report": ("analyze",),
                "evals.paired_evaluation": ("run_pairs",),
            },
            "src.runtime.pricing": {
                "src.runtime.pricing_catalog": (
                    "Rate",
                    "PricingCatalog",
                    "load_catalog",
                ),
                "src.runtime.pricing_calculation": (
                    "estimate_attempt",
                    "estimate_components",
                ),
            },
            "src.support.service": {"src.support.repair": ("_validation_feedback",)},
        }
        for facade, owners in aliases.items():
            for owner, names in owners.items():
                for name in names:
                    with self.subTest(facade=facade, symbol=name):
                        self.assertIs(
                            getattr(import_module(facade), name),
                            getattr(import_module(owner), name),
                        )

    def test_all_commands_can_show_help_outside_checkout_without_credentials(self):
        for module in (
            "src.main",
            "evals.run_evals",
            "evals.run_local_sample",
            "evals.run_guardrail_diagnostics",
            "evals.run_adversarial_pairs",
            "evals.run_provider_evals",
            "evals.reprice_run",
        ):
            with self.subTest(module=module):
                result = self.invoke_from_other_directory(module, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout)

    def test_saved_adversarial_observations_keep_the_same_analysis(self):
        from evals.paired_report import analyze

        artifact = json.loads(
            (ROOT / "docs/ADVERSARIAL_PAIRS_2026-11-04.json").read_text()
        )
        self.assertEqual(analyze(artifact["results"]), artifact["summary"])

    def test_packaging_includes_each_source_package(self):
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
        declared = set(metadata["tool"]["setuptools"]["packages"])
        actual = {
            str(path.parent.relative_to(ROOT)).replace("/", ".")
            for directory in (ROOT / "src", ROOT / "evals")
            for path in directory.rglob("__init__.py")
        }
        self.assertEqual(declared, actual)


if __name__ == "__main__":
    unittest.main()
