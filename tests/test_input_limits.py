"""Límite de consultas en CLI y servicio, siempre offline y sin truncamiento."""

import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from pydantic import ValidationError

from evals.adversarial.cases import DiagnosticCase
from evals.adversarial.guardrails import evaluate
from src.llm.providers.base import Provider
from src.llm.providers.mock_provider import MockProvider
from src.main import main
from src.runtime.config import ROOT, Settings, load_settings
from src.support.guardrails import MAX_QUERY_CHARS, InputTooLongError, check_input
from src.support.service import simulate_response


class InputLimitTests(unittest.TestCase):
    def setUp(self):
        blocker = patch(
            "socket.create_connection", side_effect=AssertionError("No network")
        )
        blocker.start()
        self.addCleanup(blocker.stop)

    def boundary_queries(self):
        # Caracteres compuestos cuentan cada punto de código, no cada glifo visible.
        return (
            "x" * 500,
            "ñ" * 500,
            "🙂" * 500,
            "e\u0301" * 250,
            "Ａ" * 500,
            "x\u200b" * 250,
            " x\t\n" * 125,
            "ﬃ" * 500,
        )

    def test_defaults_and_shipped_config_use_500(self):
        self.assertEqual(MAX_QUERY_CHARS, 500)
        self.assertEqual(Settings().max_query_chars, 500)
        self.assertEqual(load_settings().max_query_chars, 500)
        self.assertEqual(
            load_settings(ROOT / "config.ollama.example.toml").max_query_chars, 500
        )

    def test_config_can_lower_but_not_increase_limit(self):
        for limit in (1, 10, 500):
            with self.subTest(limit=limit):
                self.assertEqual(Settings(max_query_chars=limit).max_query_chars, limit)
        for limit in (0, -1, 501, 4000, 20000, "500", True):
            with self.subTest(limit=limit), self.assertRaises(ValidationError):
                Settings(max_query_chars=limit)

    def test_toml_cannot_increase_limit(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("max_query_chars = 501\n")
            with self.assertRaises(ValidationError):
                load_settings(path)

    def test_500_original_unicode_code_points_reach_provider_unchanged(self):
        for query in self.boundary_queries():
            with self.subTest(first_code_point=ord(query[0])):
                self.assertEqual(len(query), 500)
                provider = Mock(spec=Provider)
                provider.generate.return_value = MockProvider().generate("", "")
                simulate_response(query, provider)
                provider.generate.assert_called_once()
                self.assertEqual(provider.generate.call_args.args[1], query)

    def test_501_original_unicode_code_points_never_reach_provider(self):
        for query in self.boundary_queries():
            provider = Mock(spec=Provider)
            with self.subTest(first_code_point=ord(query[0])):
                with self.assertRaisesRegex(InputTooLongError, "500 caracteres"):
                    simulate_response(query + "x", provider)
                provider.generate.assert_not_called()

    def test_rejection_precedes_prompt_loading_and_all_provider_construction(self):
        for name in ("mock", "openai", "gemini", "ollama"):
            settings = Settings(provider=name, model="fixture-not-used")
            with (
                self.subTest(provider=name),
                patch("src.support.service.load_prompt") as prompt,
                patch("src.support.service.create_provider") as factory,
            ):
                with self.assertRaises(InputTooLongError):
                    simulate_response("x" * 501, settings=settings)
                prompt.assert_not_called()
                factory.assert_not_called()

    def test_direct_precheck_cannot_bypass_hard_limit(self):
        check_input("x" * 500)
        with self.assertRaisesRegex(InputTooLongError, "500 caracteres"):
            check_input("x" * 501, 4000)
        with self.assertRaisesRegex(InputTooLongError, "10 caracteres"):
            check_input("x" * 11, 10)

    def test_unvalidated_settings_copy_cannot_raise_limit(self):
        settings = Settings().model_copy(update={"max_query_chars": 4000})
        provider = Mock(spec=Provider)
        with self.assertRaisesRegex(InputTooLongError, "500 caracteres"):
            simulate_response("x" * 501, provider, settings=settings)
        provider.generate.assert_not_called()

    def test_diagnostics_use_same_limit_and_cannot_increase_it(self):
        cases = [
            DiagnosticCase(
                case_id=f"length-{length}",
                kind="legitimate" if length == 500 else "attack",
                target="input",
                text="x" * length,
                expectation="allow" if length == 500 else "block",
                reason="Fixture sintética del límite de entrada.",
            )
            for length in (500, 501)
        ]
        report = evaluate(cases)
        self.assertEqual(report["max_query_chars"], 500)
        self.assertEqual(report["model_requests"], 0)
        self.assertEqual([row["blocked"] for row in report["results"]], [False, True])
        for limit in (0, 501, 4000, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                evaluate(cases, max_query_chars=limit)

    def test_lower_configured_limit_accepts_boundary_and_rejects_next_character(self):
        settings = Settings(max_query_chars=10)
        provider = MockProvider()
        simulate_response("x" * 10, provider, settings=settings)
        self.assertEqual(provider.calls, 1)
        with self.assertRaisesRegex(InputTooLongError, "10 caracteres"):
            simulate_response("x" * 11, provider, settings=settings)
        self.assertEqual(provider.calls, 1)

    def test_rejected_metrics_contain_zero_attempts_and_no_query(self):
        query = "PRIVATE_SYNTHETIC_INPUT_" + "x" * 501
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            settings = Settings(log_metrics=True, metrics_path=str(path))
            with self.assertRaises(InputTooLongError) as caught:
                simulate_response(query, settings=settings)
            raw = path.read_text()
            metric = json.loads(raw)
            self.assertEqual(metric["status"], "rejected_input")
            self.assertEqual(metric["attempts"], 0)
            self.assertNotIn("PRIVATE_SYNTHETIC_INPUT_", raw)
            self.assertNotIn("PRIVATE_SYNTHETIC_INPUT_", str(caught.exception))
            self.assertNotIn("query", metric)
            self.assertNotIn("answer", metric)

    def test_cli_accepts_500_and_rejects_501_without_success_json_or_query_echo(self):
        for char in ("x", "🙂"):
            for length in (500, 501):
                query = char * length
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.main",
                        query,
                        "--provider",
                        "mock",
                        "--no-metrics",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                with self.subTest(char=char, length=length):
                    if length == 500:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(json.loads(result.stdout)["category"], "other")
                    else:
                        self.assertEqual(result.returncode, 2)
                        self.assertEqual(result.stdout, "")
                        self.assertIn("500 caracteres", result.stderr)
                        self.assertNotIn(query, result.stderr)

    def test_cli_reports_configured_lower_limit(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("max_query_chars = 10\n")
            stdout, stderr = StringIO(), StringIO()
            with (
                patch(
                    "sys.argv",
                    ["nubbix", "x" * 11, "--config", str(path), "--no-metrics"],
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                self.assertEqual(main(), 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("10 caracteres", stderr.getvalue())

    def test_cli_help_displays_limit(self):
        stdout = StringIO()
        with (
            patch("sys.argv", ["nubbix", "--help"]),
            redirect_stdout(stdout),
            self.assertRaises(SystemExit) as caught,
        ):
            main()
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("500 caracteres", " ".join(stdout.getvalue().split()))


if __name__ == "__main__":
    unittest.main()
