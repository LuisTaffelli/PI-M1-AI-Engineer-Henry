"""Contrato y carga de ataques y controles sintéticos de guardrails."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from src.support.schemas import NonEmptyText


class DiagnosticCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    case_id: NonEmptyText
    kind: Literal["attack", "legitimate", "policy_pending", "output_fixture"]
    target: Literal["input", "answer", "actions"]
    text: NonEmptyText
    expectation: Literal["block", "allow", "needs_policy_decision"]
    reason: NonEmptyText

    @model_validator(mode="after")
    def consistent_scope(self):
        expected = {
            "attack": ("input", "block"),
            "legitimate": ("input", "allow"),
            "policy_pending": ("input", "needs_policy_decision"),
        }
        if (
            self.kind in expected
            and (self.target, self.expectation) != expected[self.kind]
        ):
            raise ValueError("Objetivo y expectativa incompatibles.")
        if self.kind == "output_fixture" and (
            self.target == "input" or self.expectation == "needs_policy_decision"
        ):
            raise ValueError("Fixture de salida inválida.")
        return self


def load_suite(attacks: Path, controls: Path) -> list[DiagnosticCase]:
    result = []
    for path, attack_file in ((attacks, True), (controls, False)):
        cases = [
            DiagnosticCase.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not cases or any((case.kind == "attack") != attack_file for case in cases):
            raise ValueError("Suite vacía o mezcla de ataques y controles.")
        result.extend(cases)
    if len({case.case_id for case in result}) != len(result):
        raise ValueError("IDs repetidos.")
    return result
