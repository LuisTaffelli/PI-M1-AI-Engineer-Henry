"""Pruebas unitarias/de CLI offline; no son la suite académica de evals."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

from src.support.schemas import SupportResponse

ROOT = Path(__file__).resolve().parents[2]


class ContractTests(unittest.TestCase):
    def payload(self):
        return {
            "answer": "Respuesta",
            "confidence": 0.5,
            "category": "billing",
            "actions": ["Revisar factura."],
        }

    def test_valid_boundaries(self):
        for confidence in (0.0, 1.0):
            with self.subTest(confidence=confidence):
                SupportResponse(**{**self.payload(), "confidence": confidence})

    def test_rejects_invalid_contract(self):
        invalid_changes = [
            {"confidence": -0.1},
            {"confidence": 1.1},
            {"confidence": float("nan")},
            {"confidence": "0.5"},
            {"category": "refund"},
            {"actions": "Revisar"},
            {"actions": [{"name": "refund"}]},
            {"actions": [" "]},
            {"answer": " "},
            {"unexpected": True},
        ]
        for changes in invalid_changes:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                SupportResponse(**{**self.payload(), **changes})

    def test_requires_every_field(self):
        for field in self.payload():
            data = self.payload()
            del data[field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SupportResponse(**data)


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "src.main", "--no-metrics", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def test_json_stdout_and_simulation_disclosure(self):
        result = self.run_cli("Quiero consultar por las funciones del plan.")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        SupportResponse.model_validate(data)
        self.assertEqual(set(data), {"answer", "confidence", "category", "actions"})
        self.assertIn("SIMULACIÓN", data["answer"])
        self.assertIn("sin LLM", result.stderr)
        self.assertEqual(data["confidence"], 0.0)

    def test_empty_query_fails_without_json(self):
        result = self.run_cli("   ")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("Error:", result.stderr)

    def test_missing_argument(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
