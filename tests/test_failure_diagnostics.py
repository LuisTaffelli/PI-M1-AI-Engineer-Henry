"""Diagnósticos de etapas con fixtures; no recuperan la respuesta real perdida."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from src.llm.providers.base import GenerationResult, ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.main import main
from src.runtime.config import Settings
from src.support.service import simulate_response

MARKER = "PRIVATE_FIXTURE_CONTENT"
KEY = "FAKE_DIAGNOSTIC_KEY"
PAYLOAD = {
    "answer": "Revisar cargos.",
    "confidence": 0.7,
    "category": "billing",
    "actions": [],
}


def envelope(text):
    return {
        "status": "completed",
        "steps": [
            {"type": "model_output", "content": [{"type": "text", "text": text}]}
        ],
    }


class FailureDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        for module in ("gemini_provider", "openai_provider"):
            blocker = patch(
                f"src.llm.providers.{module}.urlopen",
                side_effect=AssertionError("Network forbidden"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)

    def provider(self, reply):
        return GeminiProvider(
            "fixture", api_key=KEY, transport=Mock(return_value=reply)
        )

    def test_documented_model_output_extracts_fragmented_text_ignoring_other_steps(
        self,
    ):
        text = json.dumps(PAYLOAD)
        reply = envelope(text)
        reply["steps"].insert(0, {"type": "thought", "summary": MARKER})
        reply["steps"].insert(1, {"type": "user_input", "content": MARKER})
        reply["steps"][-1]["content"] = [
            {"type": "text", "text": text[:20]},
            {"type": "text", "text": text[20:], "annotations": []},
        ]
        self.assertEqual((self.provider(reply).generate(MARKER, MARKER)).text, text)

    def test_extraction_codes_are_fixed_and_never_copy_external_values(self):
        for reply, code in (
            ([], "invalid_envelope"),
            ({"status": "completed", "steps": MARKER}, "invalid_envelope"),
            ({"status": MARKER}, "incomplete_response"),
            ({"status": "completed", "steps": []}, "empty_output"),
            (envelope(" "), "empty_output"),
            (envelope(17), "invalid_content"),
            (
                {
                    "status": "completed",
                    "steps": [{"type": "model_output", "content": MARKER}],
                },
                "invalid_content",
            ),
            (
                {
                    "status": "completed",
                    "steps": [
                        {
                            "type": "model_output",
                            "content": [{"type": MARKER, "text": MARKER}],
                        }
                    ],
                },
                "non_text_output",
            ),
        ):
            with self.subTest(code=code), self.assertRaises(ProviderError) as caught:
                self.provider(reply).generate(MARKER, MARKER)
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn(MARKER, str(caught.exception))

    def test_unknown_diagnostic_code_is_normalized(self):
        self.assertEqual(ProviderError("fixed", code=MARKER).code, "provider_error")

    def metric_for(self, provider, *, attempts=1):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metric.jsonl"
            try:
                simulate_response(
                    MARKER,
                    provider,
                    settings=Settings(
                        provider="gemini",
                        model="fixture",
                        max_attempts=attempts,
                        log_metrics=True,
                        metrics_path=str(path),
                    ),
                )
            except ValueError:
                pass
            raw = path.read_text()
            self.assertNotIn(MARKER, raw)
            self.assertNotIn(KEY, raw)
            self.assertNotIn("Revisar cargos", raw)
            return json.loads(raw)

    def test_service_distinguishes_extraction_json_contract_and_guardrail(self):
        for reply, stage, code in (
            ({"status": "completed", "steps": []}, "provider_error", "empty_output"),
            (
                envelope("```json\n" + json.dumps(PAYLOAD) + "\n```"),
                "invalid_response",
                "json_invalid",
            ),
            (envelope(MARKER), "invalid_response", "json_invalid"),
            (
                envelope(json.dumps({**PAYLOAD, "category": MARKER})),
                "invalid_response",
                "contract_invalid",
            ),
            (
                envelope(json.dumps({**PAYLOAD, MARKER: MARKER})),
                "invalid_response",
                "contract_invalid",
            ),
            (
                envelope(json.dumps({**PAYLOAD, "answer": "password=" + MARKER})),
                "rejected_output",
                None,
            ),
        ):
            with self.subTest(stage=stage, code=code):
                provider = self.provider(reply)
                record = self.metric_for(provider)
                self.assertEqual(record["failure_stage"], stage)
                self.assertEqual(record["failure_code"], code)
                self.assertEqual(record["attempts"], 1)
                provider._transport.assert_called_once()

    def test_transport_json_and_network_errors_are_separate(self):
        for error, code in (
            (json.JSONDecodeError("fixture", MARKER, 0), "http_json_invalid"),
            (ValueError(MARKER), "transport_error"),
            (TimeoutError(MARKER), "transport_error"),
        ):
            provider = GeminiProvider(
                "fixture", api_key=KEY, transport=Mock(side_effect=error)
            )
            record = self.metric_for(provider)
            self.assertEqual(record["failure_stage"], "provider_error")
            self.assertEqual(record["failure_code"], code)
            provider._transport.assert_called_once()

    def test_success_and_recovery_do_not_keep_stale_failure_codes(self):
        for replies, attempts in (
            ([envelope(json.dumps(PAYLOAD))], 1),
            ([envelope(MARKER), envelope(json.dumps(PAYLOAD))], 2),
        ):
            provider = GeminiProvider(
                "fixture", api_key=KEY, transport=Mock(side_effect=replies)
            )
            record = self.metric_for(provider, attempts=attempts)
            self.assertEqual(record["status"], "ok")
            self.assertIsNone(record["failure_code"])
            self.assertIsNone(record["failure_stage"])
            self.assertEqual(provider._transport.call_count, attempts)

    def test_cli_reports_fixed_codes_without_success_json_or_private_errors(self):
        for side_effect, result, code in (
            (ProviderError(MARKER, code="empty_output"), None, "empty_output"),
            (None, MARKER, "json_invalid"),
            (None, json.dumps({**PAYLOAD, "confidence": 9}), "contract_invalid"),
        ):
            stdout, stderr = StringIO(), StringIO()
            with (
                patch(
                    "src.support.service.MockProvider.generate",
                    side_effect=side_effect,
                    return_value=GenerationResult(result or ""),
                ),
                patch(
                    "sys.argv", ["nubbix", MARKER, "--provider", "mock", "--no-metrics"]
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = main()
            self.assertEqual(exit_code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("[" + code + "]", stderr.getvalue())
            self.assertNotIn(MARKER, stderr.getvalue())

    def test_cli_configuration_failure_is_not_reported_as_model_output(self):
        stdout, stderr = StringIO(), StringIO()
        with (
            patch(
                "sys.argv",
                [
                    "nubbix",
                    MARKER,
                    "--provider",
                    "gemini",
                    "--model",
                    " ",
                    "--no-metrics",
                ],
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            exit_code = main()
        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("[configuration_invalid]", stderr.getvalue())
        self.assertNotIn(MARKER, stderr.getvalue())
