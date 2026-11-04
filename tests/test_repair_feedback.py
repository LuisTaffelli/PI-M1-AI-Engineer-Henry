"""Corrección guiada con dobles de prueba, sin inferencia ni proveedores remotos."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

from pydantic import ValidationError

from src.llm.providers.base import GenerationResult, Provider
from src.llm.providers.mock_provider import MockProvider
from src.runtime.config import Settings
from src.support.service import simulate_response


class RepairFeedbackTests(unittest.TestCase):
    def valid_text(self):
        return MockProvider().generate("", "").text

    def test_parse_error_is_corrected_only_after_receiving_feedback(self):
        provider = Mock(spec=Provider)
        provider.generate.side_effect = lambda instructions, query: GenerationResult(
            self.valid_text()
            if "La salida debe ser JSON válido y completo" in instructions
            else '{"answer":'
        )
        response = simulate_response("Me cobraron dos veces este mes.", provider)
        self.assertEqual(response.category, "other")
        self.assertEqual(provider.generate.call_count, 2)
        first, second = [call.args for call in provider.generate.call_args_list]
        self.assertNotIn("Corrección de salida anterior:", first[0])
        self.assertIn("Corrección de salida anterior:", second[0])
        self.assertEqual(first[1], second[1])

    def test_schema_feedback_changes_with_latest_failure_without_accumulating(self):
        payload = json.loads(self.valid_text())
        provider = Mock(spec=Provider)
        provider.generate.side_effect = [
            GenerationResult(json.dumps({**payload, "category": "refund"})),
            GenerationResult(json.dumps({**payload, "confidence": 2.0})),
            GenerationResult(self.valid_text()),
        ]
        simulate_response("Consulta", provider, settings=Settings(max_attempts=3))
        instructions = [call.args[0] for call in provider.generate.call_args_list]
        self.assertIn("category: elegí billing", instructions[1])
        self.assertIn("confidence: usá un número finito", instructions[2])
        self.assertNotIn("category: elegí billing", instructions[2])
        self.assertEqual(instructions[2].count("Corrección de salida anterior:"), 1)

    def test_unknown_keys_and_invalid_values_are_not_echoed_in_feedback_or_metrics(
        self,
    ):
        marker = "SYNTHETIC_PRIVATE_TEST_MARKER"
        payload = json.loads(self.valid_text())
        payload.update({marker: marker, "answer": [marker], "confidence": marker})
        provider = Mock(spec=Provider)
        provider.generate.return_value = GenerationResult(json.dumps(payload))
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            with self.assertRaises(ValidationError):
                simulate_response(
                    "Consulta sintética",
                    provider,
                    settings=Settings(log_metrics=True, metrics_path=str(path)),
                )
            self.assertNotIn(marker, path.read_text())
            self.assertNotIn("Corrección de salida anterior:", path.read_text())
            record = json.loads(path.read_text())
            self.assertEqual(record["status"], "invalid_response")
            self.assertEqual(record["attempts"], 2)
        second = provider.generate.call_args_list[1].args[0]
        self.assertNotIn(marker, second)
        self.assertIn("answer: usá texto no vacío", second)
        self.assertIn("Eliminá campos adicionales", second)

    def test_exhaustion_keeps_exact_attempt_limit(self):
        for limit in (1, 2, 3):
            provider = Mock(spec=Provider)
            provider.generate.return_value = GenerationResult("not JSON")
            with self.subTest(limit=limit), self.assertRaises(ValidationError):
                simulate_response(
                    "Consulta", provider, settings=Settings(max_attempts=limit)
                )
            self.assertEqual(provider.generate.call_count, limit)

    def test_feedback_is_bounded_even_for_large_unknown_field_names(self):
        payload = {"unknown" + "x" * 2000 + str(i): "private" for i in range(20)}
        provider = Mock(spec=Provider)
        provider.generate.side_effect = [
            GenerationResult(json.dumps(payload)),
            GenerationResult(self.valid_text()),
        ]
        simulate_response("Consulta", provider)
        first, second = [call.args[0] for call in provider.generate.call_args_list]
        feedback = second[len(first) :]
        self.assertLessEqual(len(feedback), 600)
        self.assertLessEqual(feedback.count("\n- "), 3)
        self.assertIn("Falta el campo", feedback)
        self.assertNotIn("unknown", feedback)


if __name__ == "__main__":
    unittest.main()
