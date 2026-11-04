"""Comparación optativa Ollama, con selección y presupuesto explícitos; sin APIs remotas."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from evals.classification_report import summarize as summarize
from evals.run_evals import check_dataset, load_cases
from src.llm.prompt_catalog import DEFAULT_COMPARISON, PROMPT_NAMES
from src.llm.prompts import load_prompt
from src.runtime.config import ROOT, Settings, load_settings
from src.runtime.metrics import append_metric
from src.support.service import simulate_response


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_sample(
    dataset: Path,
    settings: Settings,
    case_ids: list[str],
    output: Path,
    *,
    allow_local_inference: bool = False,
    all_cases: bool = False,
    max_generations: int = 8,
    diagnostic_suite: bool = False,
    prompts: tuple[str, ...] = DEFAULT_COMPARISON,
) -> dict:
    if not allow_local_inference or settings.provider != "ollama":
        raise ValueError("Se requiere permiso explícito y provider=ollama.")
    if (
        not prompts
        or len(set(prompts)) != len(prompts)
        or any(name not in PROMPT_NAMES for name in prompts)
    ):
        raise ValueError("Elegí versiones conocidas, sin repetirlas.")
    if all_cases and case_ids:
        raise ValueError("Elegí IDs o corpus completo, no ambos.")
    if not all_cases and (
        not 1 <= len(case_ids) <= 4 or len(set(case_ids)) != len(case_ids)
    ):
        raise ValueError("Elegí entre uno y cuatro IDs únicos antes de ejecutar.")
    cases = load_cases(dataset)
    check_dataset(cases, minimum_cases=4 if diagnostic_suite else 30)
    if all_cases:
        case_ids = [case.case_id for case in cases]
    if (
        type(max_generations) is not int
        or not 2 <= max_generations <= 64
        or len(case_ids) * len(prompts) > max_generations
    ):
        raise ValueError(
            "La corrida excede el presupuesto explícito (máximo 64 generaciones)."
        )
    indexed = {case.case_id: case for case in cases}
    if any(case_id not in indexed for case_id in case_ids):
        raise ValueError("ID ausente en el dataset.")
    for prompt in prompts:
        load_prompt(prompt)
    output = output.resolve()
    # Falla si ya existe: una segunda ejecución nunca borra una corrida anterior.
    output.mkdir(parents=True, exist_ok=False)
    settings = settings.model_copy(
        update={
            "max_attempts": 1,
            "ollama_max_output_tokens": min(settings.ollama_max_output_tokens, 256),
            "ollama_num_ctx": min(settings.ollama_num_ctx, 2048),
            "ollama_timeout_seconds": min(settings.ollama_timeout_seconds, 30),
            "log_metrics": True,
            "metrics_path": str(output / "metrics.jsonl"),
            "pricing_path": None,
        }
    )
    plan = {
        "format_version": 2,
        "suite_kind": "supplementary_diagnostic" if diagnostic_suite else "base_corpus",
        "max_generations": max_generations,
        "all_cases": all_cases,
        "prompts": list(prompts),
        "dataset_sha256": _sha(dataset),
        "prompt_sha256": {
            name: _sha(ROOT / "prompts" / f"{name}.yaml") for name in prompts
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): _sha(path)
            for folder in ("src", "evals")
            for path in sorted((ROOT / folder).rglob("*.py"))
        },
        "settings": {
            key: value
            for key, value in settings.model_dump().items()
            if key.startswith("ollama_") or key in {"provider", "model", "max_attempts"}
        },
        "label_review_status": "not_verified_by_this_run",
        "order": "prompt_then_case_id_order; no warmup or randomization",
        "planned_generations": len(case_ids) * len(prompts),
        "cases": [
            {
                "case_id": case_id,
                "expected_category": indexed[case_id].expected_category,
                "ambiguous": indexed[case_id].ambiguous,
            }
            for case_id in case_ids
        ],
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    rows = []
    for prompt in prompts:
        current = settings.model_copy(update={"prompt": prompt})
        for case_id in case_ids:
            case = indexed[case_id]
            response = None
            try:
                response = simulate_response(case.query, settings=current)
            except (ValueError, OSError):
                # La etapa/código fijo de metrics evita conservar excepciones crudas.
                pass
            metrics = Path(current.metrics_path).read_text().splitlines()
            if len(metrics) != len(rows) + 1:
                raise ValueError("Registro de métricas incompleto; corrida conservada.")
            metric = json.loads(metrics[-1])
            status = metric["status"]
            row = {
                **metric,
                "model": current.model,
                "case_id": case_id,
                "expected_category": case.expected_category,
                "ambiguous": case.ambiguous,
                "predicted_category": response.category if response else None,
                "correct": response is not None
                and response.category == case.expected_category,
                "application_contract_valid": True
                if status in {"ok", "rejected_output"}
                else False
                if status == "invalid_response"
                else None,
                "application_output_guardrail_passed": True
                if status == "ok"
                else False
                if status == "rejected_output"
                else None,
            }
            append_metric(output / "results.jsonl", row)
            rows.append(row)
            print(f"{prompt} {case_id}: {row['status']}", file=sys.stderr)
    report = summarize(rows)
    report["suite_kind"] = plan["suite_kind"]
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", type=Path, default=ROOT / "data/eval_dataset.jsonl"
    )
    parser.add_argument("--config", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--case-id", action="append")
    selection.add_argument("--all-cases", action="store_true")
    parser.add_argument("--max-generations", type=int, default=8)
    parser.add_argument("--prompt", action="append", choices=PROMPT_NAMES)
    parser.add_argument("--diagnostic-suite", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-local-inference", action="store_true")
    args = parser.parse_args()
    try:
        report = run_sample(
            args.dataset,
            load_settings(args.config),
            args.case_id or [],
            args.output,
            allow_local_inference=args.allow_local_inference,
            all_cases=args.all_cases,
            max_generations=args.max_generations,
            diagnostic_suite=args.diagnostic_suite,
            prompts=tuple(args.prompt) if args.prompt else DEFAULT_COMPARISON,
        )
    except (ValueError, OSError):
        print(
            "Error de configuración/registro; no sobrescribir la corrida.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return (
        2
        if any(
            group["validated_outputs"] != group["total"]
            for group in report["by_prompt"].values()
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
