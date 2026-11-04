"""Proveedor simulado: devuelve siempre el mismo texto JSON, sin red."""

import json

from .base import GenerationResult


class MockProvider:
    def __init__(self, scenario: str = "fixed"):
        if scenario not in ("fixed", "malformed", "invalid_contract", "recover_once"):
            raise ValueError("Escenario de mock desconocido.")
        self.scenario = scenario
        self.calls = 0

    def generate(self, instructions: str, query: str) -> GenerationResult:
        self.calls += 1
        if self.scenario == "malformed" or (
            self.scenario == "recover_once" and self.calls == 1
        ):
            return GenerationResult('{"answer":')
        if self.scenario == "invalid_contract":
            return GenerationResult(
                '{"answer":"SIMULACIÓN", "confidence": 2, "category":"refund", "actions":[]}'
            )
        # No interpreta instrucciones ni consulta. Son valores de prueba fijos.
        return GenerationResult(
            json.dumps(
                {
                    "answer": "SIMULACIÓN: recibimos tu consulta; un agente humano debe revisarla.",
                    "confidence": 0.0,
                    "category": "other",
                    "actions": [
                        "Revisar manualmente la consulta y asignar la categoría correcta."
                    ],
                },
                ensure_ascii=False,
            )
        )
