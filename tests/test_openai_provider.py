"""Contrato HTTP de OpenAI con transportes falsos; nunca usa claves o red reales."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.client import HTTPException
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from pydantic import ValidationError

from evals.run_evals import Case, evaluate
from src.llm.providers.base import ProviderError
from src.llm.providers.openai_provider import ENDPOINT, OpenAIProvider
from src.main import main
from src.runtime.config import Settings
from src.support.service import simulate_response

FAKE_KEY = "TEST_ONLY_NOT_AN_API_KEY"


def answer_text():
    return json.dumps(
        {
            "answer": "Respuesta sintética de prueba: revisar el cobro.",
            "confidence": 0.7,
            "category": "billing",
            "actions": ["Revisar movimientos con un agente humano."],
        }
    )


def envelope(text):
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": text},
                ],
            },
        ],
    }


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        dotenv = patch(
            "src.runtime.environment.DOTENV_PATH", Path(directory.name) / ".env"
        )
        dotenv.start()
        self.addCleanup(dotenv.stop)
        blocker = patch(
            "src.llm.providers.openai_provider.urlopen",
            side_effect=AssertionError("La prueba intentó usar una red no simulada."),
        )
        self.urlopen = blocker.start()
        self.addCleanup(blocker.stop)

    def test_http_request_and_response_shape_without_sdk(self):
        self.urlopen.side_effect = None
        self.urlopen.return_value = BytesIO(
            json.dumps(envelope(answer_text())).encode()
        )
        provider = OpenAIProvider("fixture-model", api_key=FAKE_KEY)
        self.assertEqual(
            (provider.generate("Instrucciones", "Consulta")).text, answer_text()
        )
        request = self.urlopen.call_args.args[0]
        self.assertEqual(request.full_url, ENDPOINT)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), f"Bearer {FAKE_KEY}")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "fixture-model")
        self.assertEqual(payload["instructions"], "Instrucciones")
        self.assertEqual(payload["input"], "Consulta")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["max_output_tokens"], 512)
        self.assertNotIn(FAKE_KEY, json.dumps(payload))
        self.assertEqual(self.urlopen.call_args.kwargs["timeout"], 30.0)

    def test_missing_key_fails_before_transport_without_reading_real_environment(self):
        transport = Mock()
        with patch("src.runtime.environment.os.environ", {}):
            with self.assertRaisesRegex(ProviderError, "Falta OPENAI_API_KEY"):
                OpenAIProvider("fixture-model", transport=transport)
        transport.assert_not_called()
        self.urlopen.assert_not_called()

    def test_explicit_empty_key_does_not_fall_back_to_environment(self):
        with patch("src.runtime.environment.os.environ", {"OPENAI_API_KEY": FAKE_KEY}):
            with self.assertRaises(ProviderError):
                OpenAIProvider("fixture-model", api_key="")

    def test_openai_configuration_requires_model_and_bounds_output(self):
        for change in (
            {},
            {"model": " "},
            {"model": "fixture", "openai_max_output_tokens": 0},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                Settings(provider="openai", **change)
        self.assertEqual(Settings(provider="openai", model="fixture").model, "fixture")

    def test_http_and_network_errors_do_not_expose_bodies_or_keys(self):
        marker = "SYNTHETIC_PRIVATE_BODY"
        for error in (
            HTTPError(ENDPOINT, 401, marker, {}, BytesIO(marker.encode())),
            HTTPError(ENDPOINT, 429, marker, {}, BytesIO(marker.encode())),
            URLError(marker),
            HTTPException(marker),
            TimeoutError(marker),
            ValueError(marker),
        ):
            provider = OpenAIProvider(
                "fixture", api_key=FAKE_KEY, transport=Mock(side_effect=error)
            )
            with (
                self.subTest(error=type(error).__name__),
                self.assertRaises(ProviderError) as captured,
            ):
                provider.generate("Instrucciones", "Consulta")
            self.assertNotIn(marker, str(captured.exception))
            self.assertNotIn(FAKE_KEY, str(captured.exception))
            if isinstance(error, HTTPError):
                self.assertTrue(error.fp.closed)
        self.urlopen.assert_not_called()

    def test_incomplete_refused_empty_and_invalid_envelopes_fail(self):
        invalid = [
            {"status": "incomplete", "output": []},
            {"status": "completed", "output": []},
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "fake"}],
                    }
                ],
            },
            {"status": "completed", "output": "bad"},
            envelope(" "),
            envelope(42),
            [],
        ]
        for payload in invalid:
            provider = OpenAIProvider(
                "fixture", api_key=FAKE_KEY, transport=Mock(return_value=payload)
            )
            with self.subTest(payload=payload), self.assertRaises(ProviderError):
                provider.generate("Instrucciones", "Consulta")

    def test_text_reaches_pydantic_and_repair_feedback_reaches_http_payload(self):
        def reply(request, timeout):
            instructions = json.loads(request.data)["instructions"]
            return envelope(
                answer_text()
                if "Corrección de salida anterior:" in instructions
                else '{"answer":'
            )

        transport = Mock(side_effect=reply)
        provider = OpenAIProvider("fixture", api_key=FAKE_KEY, transport=transport)
        response = simulate_response(
            "Me cobraron dos veces este mes.",
            provider,
            settings=Settings(provider="openai", model="fixture"),
        )
        self.assertEqual(response.category, "billing")
        self.assertEqual(transport.call_count, 2)
        first, second = [
            json.loads(call.args[0].data) for call in transport.call_args_list
        ]
        self.assertEqual(first["input"], second["input"])
        self.assertIn("JSON válido y completo", second["instructions"])

    def test_parsing_exhaustion_and_provider_failure_have_distinct_retry_behavior(self):
        for error, expected_calls, expected_error in (
            (None, 2, ValidationError),
            (URLError("fake"), 1, ProviderError),
        ):
            transport = Mock(return_value=envelope("not JSON"), side_effect=error)
            provider = OpenAIProvider("fixture", api_key=FAKE_KEY, transport=transport)
            with self.subTest(error=error), self.assertRaises(expected_error):
                simulate_response(
                    "Consulta",
                    provider,
                    settings=Settings(provider="openai", model="fixture"),
                )
            self.assertEqual(transport.call_count, expected_calls)

    def test_cli_selection_uses_controlled_fake_transport(self):
        for key, expected_code in ((FAKE_KEY, 0), ("", 2)):
            stdout, stderr = StringIO(), StringIO()
            with (
                patch(
                    "src.runtime.environment.os.environ",
                    {"OPENAI_API_KEY": key},
                ),
                patch(
                    "src.llm.providers.openai_provider._post_json",
                    return_value=envelope(answer_text()),
                ) as transport,
                patch(
                    "sys.argv",
                    [
                        "nubbix",
                        "Consulta",
                        "--provider",
                        "openai",
                        "--model",
                        "fixture",
                        "--no-metrics",
                    ],
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = main()
            self.assertEqual(code, expected_code)
            self.assertNotIn(FAKE_KEY, stderr.getvalue())
            if expected_code:
                self.assertEqual(stdout.getvalue(), "")
                transport.assert_not_called()
            else:
                self.assertEqual(json.loads(stdout.getvalue())["category"], "billing")
                self.assertNotIn("SIMULACIÓN LOCAL", stderr.getvalue())
                transport.assert_called_once()
        self.urlopen.assert_not_called()

    def test_metrics_never_include_key_query_or_raw_response(self):
        marker = "SYNTHETIC_QUERY_MARKER"
        provider = OpenAIProvider(
            "fixture",
            api_key=FAKE_KEY,
            transport=Mock(return_value=envelope(answer_text())),
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            simulate_response(
                marker,
                provider,
                settings=Settings(
                    provider="openai",
                    model="fixture",
                    log_metrics=True,
                    metrics_path=str(path),
                ),
            )
            raw = path.read_text()
            for forbidden in (
                marker,
                FAKE_KEY,
                answer_text(),
                "Respuesta sintética de prueba",
            ):
                self.assertNotIn(forbidden, raw)
            record = json.loads(raw)
            self.assertTrue(record["simulated"])  # inyección de prueba
            self.assertIsNone(record["total_tokens"])
            self.assertIsNone(record["cost_usd"])
            self.assertEqual(record["usage_status"], "unavailable")

    def test_sample_eval_runner_cannot_silently_make_openai_calls(self):
        with self.assertRaisesRegex(ValueError, "sólo mock"):
            evaluate(
                [Case(query="Consulta", expected_category="other")],
                Settings(provider="openai", model="fixture"),
            )
        self.urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
