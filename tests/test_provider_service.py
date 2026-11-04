"""Frontera proveedor → texto → validación; todo se ejecuta offline."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import Mock, patch

from pydantic import ValidationError

from src.llm.providers.base import GenerationResult, Provider
from src.main import main
from src.support.service import simulate_response


class ProviderServiceTests(unittest.TestCase):
    def valid_payload(self):
        return {
            "answer": "SIMULACIÓN: revisar posible cobro duplicado.",
            "confidence": 0.5,
            "category": "billing",
            "actions": ["Revisar los movimientos."],
        }

    def provider_returning(self, text):
        provider = Mock(spec=Provider)
        provider.generate.return_value = GenerationResult(text)
        return provider

    def test_valid_json_is_parsed_and_query_reaches_provider(self):
        # Fixture de prueba: billing y 0.5 tampoco son predicciones reales.
        provider = self.provider_returning(json.dumps(self.valid_payload()))
        query = "Me cobraron dos veces este mes."
        response = simulate_response(query, provider)
        self.assertEqual(response.model_dump(), self.valid_payload())
        provider.generate.assert_called_once()
        instructions, received_query = provider.generate.call_args.args
        self.assertTrue(instructions.strip())
        self.assertEqual(received_query, query)

    def test_malformed_json_is_rejected(self):
        provider = self.provider_returning('{"answer":')
        with self.assertRaises(ValidationError):
            simulate_response("Consulta", provider)

    def test_json_outside_contract_is_rejected(self):
        for change in (
            {"category": "refund"},
            {"confidence": 1.5},
            {"actions": "Reembolsar"},
            {"confidence": "0.5"},
        ):
            provider = self.provider_returning(
                json.dumps({**self.valid_payload(), **change})
            )
            with self.subTest(change=change), self.assertRaises(ValidationError):
                simulate_response("Consulta", provider)

    def test_empty_query_does_not_call_provider(self):
        provider = self.provider_returning("{}")
        with self.assertRaises(ValueError):
            simulate_response("   ", provider)
        provider.generate.assert_not_called()

    def test_cli_provider_failure_has_nonzero_exit_and_no_success_output(self):
        invalid_outputs = [
            '{"answer":',
            json.dumps({**self.valid_payload(), "category": "refund"}),
        ]
        for text in invalid_outputs:
            stdout, stderr = StringIO(), StringIO()
            with (
                self.subTest(text=text),
                patch(
                    "src.support.service.MockProvider.generate",
                    return_value=GenerationResult(text or ""),
                ),
                patch(
                    "sys.argv",
                    ["nubbix", "--no-metrics", "Me cobraron dos veces este mes."],
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = main()
            self.assertEqual(code, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Error:", stderr.getvalue())
            self.assertNotIn("SIMULACIÓN LOCAL", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
