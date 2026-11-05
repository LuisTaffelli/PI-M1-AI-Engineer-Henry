"""Preparación offline de evaluaciones: valida selección y cota de llamadas."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from evals.artifacts import (
    prompt_hashes,
    sha256,
    source_hashes,
)
from evals.datasets import Case, check_dataset, load_cases
from src.llm.prompt_catalog import PROMPT_NAMES
from src.llm.prompts import load_prompt
from src.runtime.config import ROOT, Settings
from src.runtime.pricing import load_catalog

REMOTE_PROVIDERS = frozenset({"openai", "gemini"})
MAX_PROVIDER_CALLS = 384


@dataclass(frozen=True)
class EvaluationPlan:
    settings: Settings
    cases: tuple[Case, ...]
    prompts: tuple[str, ...]
    output: Path
    metadata: dict
    pricing_data: bytes | None = None


def prepare_plan(
    dataset: Path,
    settings: Settings,
    case_ids: list[str],
    prompts: tuple[str, ...],
    output: Path,
    *,
    all_cases: bool,
    max_calls: int,
    diagnostic_suite: bool = False,
    continue_on_error: bool = False,
) -> EvaluationPlan:
    if (
        not prompts
        or len(set(prompts)) != len(prompts)
        or any(p not in PROMPT_NAMES for p in prompts)
    ):
        raise ValueError("Seleccioná prompts conocidos, sin repetirlos.")
    if (all_cases and case_ids) or (
        not all_cases
        and (not 1 <= len(case_ids) <= 4 or len(set(case_ids)) != len(case_ids))
    ):
        raise ValueError("Elegí corpus completo o uno a cuatro IDs únicos.")
    cases = load_cases(dataset)
    check_dataset(cases, minimum_cases=4 if diagnostic_suite else 30)
    if not all_cases:
        indexed = {case.case_id: case for case in cases}
        if any(case_id not in indexed for case_id in case_ids):
            raise ValueError("ID ausente en el dataset.")
        cases = [indexed[case_id] for case_id in case_ids]
    for prompt in prompts:
        load_prompt(prompt)
    planned_cases = len(cases) * len(prompts)
    upper_bound = planned_cases * settings.max_attempts
    if (
        type(max_calls) is not int
        or not 1 <= max_calls <= MAX_PROVIDER_CALLS
        or upper_bound > max_calls
    ):
        raise ValueError("Presupuesto de llamadas insuficiente o fuera de 1..384.")
    output = output.resolve()
    if output.exists():
        raise ValueError("Elegí un directorio de salida nuevo.")
    pricing_data = None
    pricing_metadata = None
    if settings.pricing_path is not None:
        catalog, pricing_data = load_catalog(ROOT / settings.pricing_path)
        pricing_metadata = {
            "catalog_version": catalog.catalog_version,
            "sha256": hashlib.sha256(pricing_data).hexdigest(),
            "basis": "paid_standard_text_estimate_not_invoice",
        }
    metadata = {
        "format_version": 1,
        "provider": settings.provider,
        "model": settings.model,
        "pricing": pricing_metadata,
        "prompts": list(prompts),
        "planned_cases": planned_cases,
        "max_attempts_per_case": settings.max_attempts,
        "provider_calls_upper_bound": upper_bound,
        "remote_calls_upper_bound": upper_bound
        if settings.provider in REMOTE_PROVIDERS
        else 0,
        "max_calls": max_calls,
        "calls_unit": "Provider.generate invocations including JSON/contract repair; not a monetary cap",
        "monetary_cap_enforced": False,
        "execution_requested": False,
        "continue_on_error": continue_on_error,
        "suite_kind": "supplementary_diagnostic" if diagnostic_suite else "base_corpus",
        "reference_status": "not_verified_by_this_run",
        "dataset_sha256": sha256(dataset),
        "prompt_sha256": prompt_hashes(prompts),
        "source_sha256": source_hashes(),
        "settings": {
            k: v
            for k, v in settings.model_dump().items()
            if k.startswith(("openai_", "gemini_", "ollama_"))
            or k in {"max_attempts", "max_query_chars"}
        },
        "cases": [
            {
                "case_id": c.case_id,
                "expected_category": c.expected_category,
                "ambiguous": c.ambiguous,
            }
            for c in cases
        ],
    }
    return EvaluationPlan(
        settings, tuple(cases), prompts, output, metadata, pricing_data
    )
