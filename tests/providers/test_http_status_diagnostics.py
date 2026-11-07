"""HTTP status numérico con transportes falsos, sin leer cuerpos o usar la red."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from evals.adversarial.plan import prepare_plan as paired_plan
from evals.adversarial.runner import execute_plan as execute_pairs
from evals.classification.plan import prepare_plan
from evals.classification.runner import execute_plan
from src.llm.providers.base import GenerationResult, ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.main import main
from src.runtime.config import ROOT, Settings
from src.support.service import simulate_response

MARKER = "PRIVATE_HTTP_FIXTURE_CONTENT"
KEY = "FAKE_HTTP_DIAGNOSTIC_KEY"
VALID = json.dumps(
    {
        "answer": "Revisar cargos.",
        "confidence": 0.7,
        "category": "billing",
        "actions": [],
    }
)


class UnreadableBody(BytesIO):
    def read(self, *args, **kwargs):
        raise AssertionError("El cuerpo HTTP no debe leerse.")


class HttpStatusDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        blocker = patch(
            "src.llm.providers.gemini_provider.urlopen",
            side_effect=AssertionError("Red real prohibida en esta prueba."),
        )
        self.urlopen = blocker.start()
        self.addCleanup(blocker.stop)
        credentials = patch(
            "src.runtime.environment.load_api_key",
            side_effect=AssertionError("No leer credenciales reales."),
        )
        credentials.start()
        self.addCleanup(credentials.stop)

    def provider(self, status):
        body = UnreadableBody(MARKER.encode())
        error = HTTPError(
            "https://fixture.invalid/" + MARKER + "?key=" + KEY,
            status,
            MARKER,
            {"Authorization": KEY, "X-Private": MARKER},
            body,
        )
        transport = Mock(side_effect=error)
        return GeminiProvider("fixture", api_key=KEY, transport=transport), body

    def assert_private(self, raw):
        for private in (MARKER, KEY, "fixture.invalid", "Revisar cargos"):
            self.assertNotIn(private, raw)

    def test_provider_error_accepts_only_http_error_status_in_range(self):
        for status in (400, 401, 403, 404, 408, 409, 422, 429, 500, 503, 599):
            with self.subTest(status=status):
                error = ProviderError("fixed", code="http_error", http_status=status)
                self.assertEqual(error.code, "http_error")
                self.assertEqual(error.http_status, status)
        for status in (None, True, False, 399, 600, "429", 429.0, MARKER, [], {}):
            with self.subTest(status=status):
                error = ProviderError("fixed", code="http_error", http_status=status)
                self.assertIsNone(error.http_status)
        for code in ("provider_error", "transport_error", MARKER):
            with self.subTest(code=code):
                self.assertIsNone(
                    ProviderError("fixed", code=code, http_status=429).http_status
                )

    def test_gemini_retains_status_without_reading_private_error(self):
        for status in (400, 401, 403, 404, 429, 500, 503, 599):
            with self.subTest(status=status):
                provider, body = self.provider(status)
                with self.assertRaises(ProviderError) as caught:
                    provider.generate(MARKER, MARKER)
                self.assertEqual(caught.exception.code, "http_error")
                self.assertEqual(caught.exception.http_status, status)
                self.assert_private(str(caught.exception))
                self.assertTrue(body.closed)
                provider._transport.assert_called_once()
        self.urlopen.assert_not_called()

    def test_gemini_discards_invalid_status_without_copying_it(self):
        for status in (MARKER, "429", 429.0, True, 200, 600, None):
            with self.subTest(status=status):
                provider, body = self.provider(status)
                with self.assertRaises(ProviderError) as caught:
                    provider.generate(MARKER, MARKER)
                self.assertEqual(caught.exception.code, "http_error")
                self.assertIsNone(caught.exception.http_status)
                self.assert_private(str(caught.exception))
                self.assertTrue(body.closed)

    def test_metrics_keep_status_without_retries_or_stale_fields(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            settings = Settings(
                provider="gemini",
                model="fixture",
                max_attempts=3,
                log_metrics=True,
                metrics_path=str(path),
            )
            provider, _ = self.provider(429)
            with self.assertRaises(ProviderError):
                simulate_response(MARKER, provider, settings=settings)
            provider._transport.assert_called_once()
            simulate_response(
                MARKER,
                Mock(generate=Mock(return_value=GenerationResult(VALID))),
                settings=settings,
            )
            raw = path.read_text()
            self.assert_private(raw)
            failed, successful = map(json.loads, raw.splitlines())
            self.assertEqual(failed["failure_code"], "http_error")
            self.assertEqual(failed["failure_http_status"], 429)
            self.assertEqual(failed["attempts"], 1)
            self.assertIsNone(failed["total_tokens"])
            self.assertIsNone(failed["cost_usd"])
            self.assertIsNone(successful["failure_code"])
            self.assertIsNone(successful["failure_http_status"])

    def test_cli_shows_safe_code_and_status_not_exception_message(self):
        for status in (429, 503, MARKER, None):
            with self.subTest(status=status):
                stdout, stderr = StringIO(), StringIO()
                error = ProviderError(MARKER, code="http_error", http_status=status)
                with (
                    patch("src.main.simulate_response", side_effect=error),
                    patch("sys.argv", ["nubbix", MARKER, "--no-metrics"]),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    self.assertEqual(main(), 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("[http_error]", stderr.getvalue())
                if type(status) is int:
                    self.assertIn(f"HTTP {status}", stderr.getvalue())
                else:
                    self.assertNotIn(" HTTP ", stderr.getvalue())
                self.assert_private(stderr.getvalue())

    def test_both_evaluation_runners_preserve_numeric_status_and_stop(self):
        for paired in (False, True):
            with self.subTest(paired=paired), TemporaryDirectory() as directory:
                output = Path(directory) / "run"
                settings = Settings(provider="gemini", model="fixture")
                if paired:
                    plan = paired_plan(
                        settings, ("v3_structured",), output, max_calls=30
                    )
                else:
                    plan = prepare_plan(
                        ROOT / "data/eval_dataset.jsonl",
                        settings,
                        ["nubbix-b01", "nubbix-t01"],
                        ("v3_structured",),
                        output,
                        all_cases=False,
                        max_calls=4,
                    )
                provider, _ = self.provider(503)
                with (
                    patch("src.llm.factory.GeminiProvider", return_value=provider),
                    redirect_stderr(StringIO()),
                ):
                    runner = execute_pairs if paired else execute_plan
                    report = runner(plan, execute=True, allow_remote_inference=True)
                provider._transport.assert_called_once()
                execution = report["execution"] if paired else report
                self.assertFalse(execution["completed"])
                for name in ("metrics.jsonl", "results.jsonl"):
                    raw = (output / name).read_text()
                    self.assert_private(raw)
                    rows = [json.loads(line) for line in raw.splitlines()]
                    self.assertEqual(len(rows), 1)
                    self.assertEqual(rows[0]["failure_code"], "http_error")
                    self.assertEqual(rows[0]["failure_http_status"], 503)
                    self.assertEqual(rows[0]["attempts"], 1)
                for path in output.iterdir():
                    self.assert_private(path.read_text())
        self.urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
