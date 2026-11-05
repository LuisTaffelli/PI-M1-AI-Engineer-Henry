"""Protocolo de consultas limpias, ataques pareados y controles de entrada."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from evals.diagnostic_cases import DiagnosticCase
from src.support.schemas import NonEmptyText

Category = Literal["billing", "technical", "account", "other"]


class AttackPair(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    case_id: NonEmptyText
    attack_case_id: NonEmptyText
    task_query: NonEmptyText
    expected_category: Category
    attacker_target: Category

    @model_validator(mode="after")
    def different_target(self):
        if self.expected_category == self.attacker_target:
            raise ValueError(
                "El objetivo atacante debe diferir de la referencia limpia."
            )
        return self


def load_protocol(pairs_path: Path, attack_paths: list[Path], controls_path: Path):
    attacks = {}
    for path in attack_paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            case = DiagnosticCase.model_validate_json(line)
            if case.kind != "attack" or case.case_id in attacks:
                raise ValueError("Ataque inválido o ID repetido.")
            attacks[case.case_id] = case
    pairs = [
        AttackPair.model_validate_json(line)
        for line in pairs_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(pairs) < 10 or len({p.case_id for p in pairs}) != len(pairs):
        raise ValueError("Se requieren diez pares o más, con IDs únicos.")
    references = [p.attack_case_id for p in pairs]
    if len(set(references)) != len(references) or set(references) != set(attacks):
        raise ValueError("Cada ataque debe tener exactamente una consulta limpia.")
    controls = [
        DiagnosticCase.model_validate_json(line)
        for line in controls_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    controls = [c for c in controls if c.target == "input"]
    if not controls or any(
        c.kind not in {"legitimate", "policy_pending"} for c in controls
    ):
        raise ValueError("Se requieren controles de entrada sin ataques.")
    if len({c.case_id for c in controls}) != len(controls):
        raise ValueError("Controles repetidos.")
    return pairs, attacks, controls


def build_jobs(pairs, attacks, controls):
    jobs = []
    for pair in pairs:
        jobs.extend(
            [
                (
                    pair.case_id,
                    "clean",
                    pair.task_query,
                    pair.expected_category,
                    pair.attacker_target,
                ),
                (
                    pair.case_id,
                    "attacked",
                    pair.task_query + "\n\n" + attacks[pair.attack_case_id].text,
                    pair.expected_category,
                    pair.attacker_target,
                ),
            ]
        )
    jobs.extend(
        (
            c.case_id,
            "benign_control" if c.kind == "legitimate" else "policy_pending",
            c.text,
            None,
            None,
        )
        for c in controls
    )
    return jobs
