"""Diagnóstico de heurísticas offline; no certifica seguridad de un modelo."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evals.run_guardrail_diagnostics import DiagnosticCase, evaluate, load_suite, main
from src.runtime.config import ROOT, Settings

ATTACKS = ROOT / "evals/adversarial.jsonl"
CONTROLS = ROOT / "evals/guardrail_controls.jsonl"


class GuardrailDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        for name in ("OpenAIProvider", "GeminiProvider", "OllamaProvider"):
            blocker = patch(
                "src.llm.factory." + name,
                side_effect=AssertionError("No provider construction"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)
        blocker = patch(
            "socket.create_connection", side_effect=AssertionError("No network")
        )
        blocker.start()
        self.addCleanup(blocker.stop)

    def test_datasets_have_ten_attacks_and_separate_controls_without_raw_report_text(
        self,
    ):
        cases = load_suite(ATTACKS, CONTROLS)
        report = evaluate(cases)
        self.assertEqual(report["by_kind"]["attack"]["total"], 10)
        self.assertEqual(report["by_kind"]["legitimate"]["total"], 4)
        self.assertEqual(report["by_kind"]["output_fixture"]["total"], 3)
        self.assertEqual(report["model_requests"], 0)
        self.assertFalse(report["safety_claim"])
        self.assertFalse(report["bonus_completion_claim"])
        raw = json.dumps(report)
        for case in cases:
            self.assertNotIn(case.text, raw)
        self.assertNotIn("DEMO_PLACEHOLDER_ONLY", raw)

    def test_policy_cases_remain_unscored_even_if_they_are_blocked(self):
        cases = [
            case
            for case in load_suite(ATTACKS, CONTROLS)
            if case.kind == "policy_pending"
        ]
        report = evaluate(cases)
        self.assertTrue(
            all(row["expectation_matched"] is None for row in report["results"])
        )
        self.assertEqual(report["by_kind"]["policy_pending"]["expectations_scored"], 0)

    def test_nonmatching_expectation_is_reported_not_hidden_or_treated_as_crash(self):
        case = DiagnosticCase(
            case_id="test-attack",
            kind="attack",
            target="input",
            text="UNRECOGNIZED_SYNTHETIC_INSTRUCTION",
            expectation="block",
            reason="Fixture para comprobar resumen de discrepancias.",
        )
        report = evaluate([case])
        row = report["results"][0]
        self.assertFalse(row["blocked"])
        self.assertFalse(row["expectation_matched"])
        self.assertEqual(report["by_kind"]["attack"]["not_blocked"], 1)
        self.assertEqual(report["by_kind"]["attack"]["expectations_matched"], 0)

    def test_output_fixtures_exercise_answer_and_actions(self):
        cases = [
            case
            for case in load_suite(ATTACKS, CONTROLS)
            if case.kind == "output_fixture"
        ]
        rows = {row["case_id"]: row for row in evaluate(cases)["results"]}
        self.assertTrue(rows["output-01"]["blocked"])
        self.assertTrue(rows["output-02"]["blocked"])
        self.assertFalse(rows["output-03"]["blocked"])
        self.assertTrue(all(row["expectation_matched"] for row in rows.values()))

    def test_invalid_duplicates_or_mixed_suites_are_rejected(self):
        valid = json.loads(ATTACKS.read_text().splitlines()[0])
        with TemporaryDirectory() as directory:
            path = Path(directory) / "suite.jsonl"
            for rows in (
                [valid, valid],
                [{**valid, "target": "answer"}],
                [{**valid, "unexpected": "PRIVATE_FIXTURE"}],
                [json.loads(CONTROLS.read_text().splitlines()[0])],
            ):
                path.write_text("\n".join(json.dumps(row) for row in rows))
                with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                    load_suite(path, CONTROLS)

    def test_cli_writes_new_report_without_using_configured_remote_provider(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            args = ["diag", "--output", str(path)]
            settings = Settings(provider="openai", model="fixture-not-used")
            with (
                patch("sys.argv", args),
                patch(
                    "evals.cli.guardrails.load_settings",
                    return_value=settings,
                ),
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(main(), 0)
                original = path.read_bytes()
                self.assertEqual(main(), 2)
            self.assertEqual(original, path.read_bytes())
            report = json.loads(original)
            self.assertEqual(len(report["dataset_sha256"]["attacks"]), 64)
            self.assertEqual(report["model_requests"], 0)
            for source in (
                "src/support/guardrails.py",
                "evals/cli/guardrails.py",
                "evals/adversarial/cases.py",
                "evals/adversarial/guardrails.py",
                "src/runtime/paths.py",
            ):
                self.assertIn(source, report["source_sha256"])
            self.assertNotIn("evals/diagnostic_cases.py", report["source_sha256"])

    def test_invalid_file_does_not_leak_its_contents_or_create_output(self):
        with TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.jsonl"
            bad.write_text("PRIVATE_BAD_JSON")
            output = Path(directory) / "report.json"
            stdout, stderr = StringIO(), StringIO()
            with (
                patch(
                    "sys.argv", ["diag", "--attacks", str(bad), "--output", str(output)]
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                self.assertEqual(main(), 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertNotIn("PRIVATE_BAD_JSON", stderr.getvalue())
            self.assertFalse(output.exists())

    def test_new_prompts_preserve_precheck_order_and_output_rejection(self):
        from unittest.mock import Mock

        from src.llm.providers.base import GenerationResult
        from src.support.guardrails import GuardrailError
        from src.support.service import simulate_response

        for prompt in ("v3_structured", "v4_reasoning"):
            for case in load_suite(ATTACKS, CONTROLS):
                if case.kind != "attack":
                    continue
                provider = Mock()
                safe = json.dumps(
                    {
                        "answer": "Respuesta sintética.",
                        "confidence": 0.5,
                        "category": "other",
                        "actions": [],
                    }
                )
                provider.generate.return_value = GenerationResult(safe)
                try:
                    simulate_response(
                        case.text, provider, settings=Settings(prompt=prompt)
                    )
                except GuardrailError:
                    provider.generate.assert_not_called()
                else:
                    # Admisión del filtro no demuestra resistencia del modelo.
                    self.assertEqual(provider.generate.call_args.args[1], case.text)
            provider = Mock()
            unsafe = json.dumps(
                {
                    "answer": "password=DEMO_PLACEHOLDER_ONLY",
                    "confidence": 0.5,
                    "category": "other",
                    "actions": [],
                }
            )
            provider.generate.return_value = GenerationResult(unsafe)
            with self.assertRaises(GuardrailError):
                simulate_response(
                    "Consulta sintética",
                    provider,
                    settings=Settings(prompt=prompt, max_attempts=3),
                )
            provider.generate.assert_called_once()
