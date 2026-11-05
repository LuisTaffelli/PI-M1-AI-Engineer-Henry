"""Corpus etiquetado: contrato, carga y validación offline compartidos."""

import unicodedata
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.llm.prompt_catalog import PROMPT_NAMES
from src.llm.prompts import load_prompt
from src.support.schemas import NonEmptyText


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    case_id: NonEmptyText | None = None
    label_reason: NonEmptyText | None = None
    ambiguous: bool = False
    query: NonEmptyText
    expected_category: Literal["billing", "technical", "account", "other"]


def load_cases(path: Path) -> list[Case]:
    cases = [
        Case.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases:
        raise ValueError("Dataset vacío.")
    return cases


def normalized_query(text: str) -> str:
    """Detectar repeticiones por caja, espacios, tildes y puntuación; no semántica."""
    folded = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        char for char in folded if not unicodedata.combining(char)
    )
    return " ".join(
        "".join(char if char.isalnum() else " " for char in without_accents).split()
    )


def check_dataset(cases: list[Case], *, minimum_cases: int = 30) -> dict:
    """Control del corpus de trabajo; el sample legacy no pasa como dataset de 30."""
    if len(cases) < minimum_cases:
        raise ValueError(f"El corpus requiere al menos {minimum_cases} casos.")
    ids = [case.case_id for case in cases]
    if any(not case.case_id or not case.label_reason for case in cases):
        raise ValueError("Falta ID o justificación de etiqueta.")
    if any("ambiguous" not in case.model_fields_set for case in cases):
        raise ValueError("Falta marca explícita de ambigüedad.")
    if len(set(ids)) != len(ids):
        raise ValueError("IDs repetidos.")
    queries = [normalized_query(case.query) for case in cases]
    if any(not query for query in queries) or len(set(queries)) != len(queries):
        raise ValueError("Consultas vacías o repetidas tras normalización.")
    counts = Counter(case.expected_category for case in cases)
    if set(counts) != {"billing", "technical", "account", "other"}:
        raise ValueError("Falta cobertura de categorías.")
    # Se revisan ambas variantes para que cambiar prompt no habilite contaminación.
    examples = {
        normalized_query(example.query)
        for name in PROMPT_NAMES
        for example in load_prompt(name).examples
    }
    if set(queries) & examples:
        raise ValueError("Hay consultas usadas como ejemplos de prompt.")
    return {
        "dataset_valid": True,
        "content_provenance_checked": False,
        "total": len(cases),
        "by_category": dict(sorted(counts.items())),
        "balanced": len(set(counts.values())) == 1,
        "ambiguous_case_ids": [case.case_id for case in cases if case.ambiguous],
        "label_review_status": "not_verified_by_this_check",
        "few_shot_overlap_check": "normalized_exact_only_not_semantic",
    }
