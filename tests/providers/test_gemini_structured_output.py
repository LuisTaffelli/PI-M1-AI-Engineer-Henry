"""Salida estructurada Gemini: contrato HTTP y validación siguen siendo offline."""

import json
import unittest
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from pydantic import ValidationError

from src.llm.providers.base import ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.runtime.config import Settings
from src.support.schemas import SupportResponse
from src.support.service import simulate_response

KEY = "STRUCTURED_OUTPUT_FAKE_KEY"
MARKER = "SYNTHETIC_PRIVATE_OUTPUT"
VALID = {
    "answer": "Revisar cargos con un agente.",
    "confidence": 0.8,
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


class GeminiStructuredOutputTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        dotenv = patch(
            "src.runtime.environment.DOTENV_PATH", Path(directory.name) / ".env"
        )
        dotenv.start()
        self.addCleanup(dotenv.stop)
        blocker = patch(
            "src.llm.providers.gemini_provider.urlopen",
            side_effect=AssertionError("Real network forbidden"),
        )
        blocker.start()
        self.addCleanup(blocker.stop)

    def test_service_requests_interactions_json_format_with_contract_from_pydantic(
        self,
    ):
        with (
            patch("src.runtime.environment.os.environ", {"GEMINI_API_KEY": KEY}),
            patch(
                "src.llm.providers.gemini_provider._post_json",
                return_value=envelope(json.dumps(VALID)),
            ) as transport,
        ):
            result = simulate_response(
                "Consulta ficticia",
                settings=Settings(provider="gemini", model="fixture", max_attempts=1),
            )
        self.assertEqual(result.model_dump(), VALID)
        transport.assert_called_once()
        request = transport.call_args.args[0]
        payload = json.loads(request.data)
        fmt = payload["response_format"]
        self.assertEqual(fmt["type"], "text")
        self.assertEqual(fmt["mime_type"], "application/json")
        self.assertEqual(fmt["schema"], SupportResponse.model_json_schema())
        schema = fmt["schema"]
        self.assertEqual(
            set(schema["required"]), {"answer", "confidence", "category", "actions"}
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["category"]["enum"],
            ["billing", "technical", "account", "other"],
        )
        self.assertEqual(schema["properties"]["confidence"]["minimum"], 0)
        self.assertEqual(schema["properties"]["confidence"]["maximum"], 1)
        self.assertNotIn("response_mime_type", payload["generation_config"])
        self.assertNotIn("response_format", payload["generation_config"])
        self.assertNotIn(KEY, json.dumps(payload))
        self.assertFalse(payload["store"])

    def test_direct_adapter_accepts_injected_schema_without_mutating_it(self):
        schema = SupportResponse.model_json_schema()
        snapshot = deepcopy(schema)
        transport = Mock(return_value=envelope(json.dumps(VALID)))
        provider = GeminiProvider(
            "fixture", api_key=KEY, response_schema=schema, transport=transport
        )
        self.assertEqual(
            (provider.generate("Instrucciones", "Consulta")).text, json.dumps(VALID)
        )
        self.assertEqual(schema, snapshot)
        self.assertEqual(
            json.loads(transport.call_args.args[0].data)["response_format"]["schema"],
            snapshot,
        )

    def test_requesting_a_schema_never_skips_local_pydantic_checks(self):
        for invalid in (
            {**VALID, "answer": " "},
            {**VALID, "actions": [" "]},
            {**VALID, "confidence": 2},
            {**VALID, "confidence": "0.8"},
            {**VALID, "category": "refund"},
            {**VALID, MARKER: MARKER},
        ):
            with (
                self.subTest(invalid=invalid),
                patch(
                    "src.runtime.environment.os.environ",
                    {"GEMINI_API_KEY": KEY},
                ),
                patch(
                    "src.llm.providers.gemini_provider._post_json",
                    return_value=envelope(json.dumps(invalid)),
                ) as transport,
                self.assertRaises(ValidationError),
            ):
                simulate_response(
                    "Consulta ficticia",
                    settings=Settings(
                        provider="gemini", model="fixture", max_attempts=1
                    ),
                )
            transport.assert_called_once()
            self.assertIn(
                "response_format", json.loads(transport.call_args.args[0].data)
            )

    def test_retry_preserves_schema_and_sends_safe_feedback(self):
        with (
            patch("src.runtime.environment.os.environ", {"GEMINI_API_KEY": KEY}),
            patch(
                "src.llm.providers.gemini_provider._post_json",
                side_effect=[
                    envelope("```json\n" + json.dumps(VALID) + "\n```"),
                    envelope(json.dumps(VALID)),
                ],
            ) as transport,
        ):
            result = simulate_response(
                "Consulta ficticia",
                settings=Settings(provider="gemini", model="fixture", max_attempts=2),
            )
        self.assertEqual(result.category, "billing")
        self.assertEqual(transport.call_count, 2)
        first, second = [json.loads(c.args[0].data) for c in transport.call_args_list]
        self.assertEqual(first["response_format"], second["response_format"])
        self.assertIn("JSON válido y completo", second["system_instruction"])

    def test_schema_does_not_make_markdown_valid_or_leak_failed_output(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            with (
                patch(
                    "src.runtime.environment.os.environ",
                    {"GEMINI_API_KEY": KEY},
                ),
                patch(
                    "src.llm.providers.gemini_provider._post_json",
                    return_value=envelope("```json\n" + MARKER + "\n```"),
                ) as transport,
                self.assertRaises(ValidationError),
            ):
                simulate_response(
                    "Consulta ficticia",
                    settings=Settings(
                        provider="gemini",
                        model="fixture",
                        max_attempts=1,
                        log_metrics=True,
                        metrics_path=str(path),
                    ),
                )
            raw = path.read_text()
            self.assertNotIn(MARKER, raw)
            self.assertNotIn(KEY, raw)
            self.assertNotIn("Consulta ficticia", raw)
            record = json.loads(raw)
            self.assertEqual(record["failure_code"], "json_invalid")
            self.assertEqual(record["failure_stage"], "invalid_response")
            transport.assert_called_once()

    def test_incomplete_response_still_fails_without_retry_or_raw_output(self):
        reply = envelope(MARKER)
        reply["status"] = "incomplete"
        with (
            patch("src.runtime.environment.os.environ", {"GEMINI_API_KEY": KEY}),
            patch(
                "src.llm.providers.gemini_provider._post_json", return_value=reply
            ) as transport,
            self.assertRaises(ProviderError) as caught,
        ):
            simulate_response(
                "Consulta ficticia",
                settings=Settings(provider="gemini", model="fixture", max_attempts=2),
            )
        self.assertEqual(caught.exception.code, "incomplete_response")
        self.assertNotIn(MARKER, str(caught.exception))
        transport.assert_called_once()

    def test_schema_rejected_by_api_has_no_silent_fallback_or_http_retry(self):
        error = HTTPError(
            "https://fixture.invalid", 400, MARKER, {}, BytesIO(MARKER.encode())
        )
        with (
            patch("src.runtime.environment.os.environ", {"GEMINI_API_KEY": KEY}),
            patch(
                "src.llm.providers.gemini_provider._post_json", side_effect=error
            ) as transport,
            self.assertRaises(ProviderError) as caught,
        ):
            simulate_response(
                "Consulta ficticia",
                settings=Settings(provider="gemini", model="fixture", max_attempts=3),
            )
        self.assertEqual(caught.exception.code, "http_error")
        self.assertNotIn(MARKER, str(caught.exception))
        self.assertTrue(error.fp.closed)
        transport.assert_called_once()
        self.assertIn("response_format", json.loads(transport.call_args.args[0].data))
