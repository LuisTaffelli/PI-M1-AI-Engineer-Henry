"""Ejecutar desde la raíz: python -m evals.run_evals. No mide un LLM real."""

import argparse
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from src.llm.prompts import load_prompt
from src.runtime.config import ROOT, Settings, load_settings
from src.support.schemas import NonEmptyText
from src.support.service import simulate_response


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
        for name in ("v1_zero_shot", "v2_few_shot")
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


def evaluate(cases: list[Case], settings: Settings) -> dict:
    if settings.provider != "mock":
        raise ValueError(
            "Este runner de checkpoint admite sólo mock, sin llamadas API."
        )
    if not cases:
        raise ValueError("Dataset vacío.")
    scores = {
        category: {"count": 0, "correct": 0, "errors": 0}
        for category in ("billing", "technical", "account", "other")
    }
    # Las evals no mezclan sus requests con las métricas de uso de CLI.
    settings = settings.model_copy(update={"log_metrics": False})
    for case in cases:
        group = scores[case.expected_category]
        group["count"] += 1
        try:
            response = simulate_response(case.query, settings=settings)
            group["correct"] += int(response.category == case.expected_category)
        except (ValueError, OSError):
            group["errors"] += 1
    for group in scores.values():
        group["exact_match"] = (
            group["correct"] / group["count"] if group["count"] else None
        )
    errors = sum(group["errors"] for group in scores.values())
    return {
        "simulated": True,
        "quality_claim": False,
        "warning": "Smoke test del runner con mock fijo; no evalúa capacidad de un modelo ni permite elegir un prompt.",
        "prompt_version": settings.prompt,
        "total": len(cases),
        "errors": errors,
        "ambiguous_total": sum(case.ambiguous for case in cases),
        "ambiguous_included_in_score": True,
        "exact_match": sum(group["correct"] for group in scores.values()) / len(cases),
        "by_category": scores,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluación estructural offline con mock."
    )
    parser.add_argument("--dataset", type=Path, default=ROOT / "data/eval_sample.jsonl")
    parser.add_argument("--config", type=Path, default=ROOT / "config.toml")
    parser.add_argument("--prompt", choices=["v1_zero_shot", "v2_few_shot"])
    parser.add_argument(
        "--check-dataset",
        action="store_true",
        help="Controlar corpus de al menos 30 casos, metadatos y separación, sin proveedor.",
    )
    args = parser.parse_args()
    try:
        cases = load_cases(args.dataset)
        if args.check_dataset:
            report = check_dataset(cases)
        else:
            # También proteger la ejecución normal de un corpus con metadatos.
            if args.dataset.resolve() == ROOT / "data/eval_dataset.jsonl" or any(
                case.case_id is not None for case in cases
            ):
                check_dataset(cases)
            report = evaluate(cases, load_settings(args.config, prompt=args.prompt))
    except (ValueError, OSError):
        print("Error: dataset o configuración inválidos.", file=sys.stderr)
        return 2
    if args.check_dataset:
        print(
            "CONTROL OFFLINE: formato/cobertura/separación; etiquetas pendientes de revisión humana.",
            file=sys.stderr,
        )
    else:
        print("SIMULACIÓN: resultados del mock, no de un LLM.", file=sys.stderr)
    print(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if report.get("errors", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
