"""Ejecución pareada local: permiso, plan, orden y registro de resultados."""

import sys
from datetime import datetime, timezone
from pathlib import Path

from evals.adversarial.pairs import build_jobs, load_protocol
from evals.adversarial.report import analyze
from evals.common.artifacts import (
    next_metric,
    prompt_hashes,
    sha256,
    source_hashes,
    write_json,
)
from src.llm.prompt_catalog import PROMPT_NAMES
from src.runtime.config import ROOT, Settings
from src.runtime.metrics import append_metric
from src.support.service import simulate_response


def run_pairs(
    settings: Settings,
    prompts: tuple[str, ...],
    output: Path,
    *,
    allow_local_inference: bool,
    max_calls: int,
    pairs_path: Path = ROOT / "evals/adversarial_pairs.jsonl",
    attack_paths: list[Path] | None = None,
    controls_path: Path = ROOT / "evals/guardrail_controls.jsonl",
):
    if not allow_local_inference or settings.provider != "ollama":
        raise ValueError("Sólo Ollama local con permiso explícito.")
    if (
        not prompts
        or len(set(prompts)) != len(prompts)
        or any(p not in PROMPT_NAMES for p in prompts)
    ):
        raise ValueError("Prompts inválidos o repetidos.")
    attack_paths = (
        attack_paths
        if attack_paths is not None
        else [
            ROOT / "evals/adversarial.jsonl",
            ROOT / "evals/adversarial_unicode.jsonl",
        ]
    )
    pairs, attacks, controls = load_protocol(pairs_path, attack_paths, controls_path)
    planned = len(prompts) * (2 * len(pairs) + len(controls))
    if type(max_calls) is not int or not 1 <= max_calls <= 128 or planned > max_calls:
        raise ValueError(
            "Presupuesto insuficiente o superior a 128 llamadas de servicio."
        )
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    settings = settings.model_copy(
        update={
            "max_attempts": 1,
            "log_metrics": True,
            "metrics_path": str(output / "metrics.jsonl"),
            "pricing_path": None,
            "ollama_max_output_tokens": min(settings.ollama_max_output_tokens, 256),
            "ollama_num_ctx": min(settings.ollama_num_ctx, 2048),
            "ollama_timeout_seconds": min(settings.ollama_timeout_seconds, 30),
        }
    )
    files = [pairs_path, controls_path, *attack_paths]
    plan = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "planned_service_calls": planned,
        "generation_upper_bound": planned,
        "max_calls": max_calls,
        "prompts": list(prompts),
        "dataset_sha256": {p.name: sha256(p) for p in files},
        "prompt_sha256": prompt_hashes(prompts),
        "source_sha256": source_hashes(),
        "settings": {
            k: v
            for k, v in settings.model_dump().items()
            if k.startswith("ollama_")
            or k in {"provider", "model", "max_attempts", "max_query_chars"}
        },
        "pairs": [
            {
                "case_id": p.case_id,
                "attack_case_id": p.attack_case_id,
                "expected_category": p.expected_category,
                "attacker_target": p.attacker_target,
            }
            for p in pairs
        ],
        "order": "prompt then pair(clean, attacked), then controls; no randomization or warmup",
        "reference_status": "technical_proposals; not human validated",
    }
    write_json(output / "plan.json", plan)
    rows = []
    for prompt in prompts:
        current = settings.model_copy(update={"prompt": prompt})
        jobs = build_jobs(pairs, attacks, controls)
        for case_id, condition, query, expected, target in jobs:
            response = None
            try:
                response = simulate_response(query, settings=current)
            except (ValueError, OSError):
                pass
            metric = next_metric(
                Path(current.metrics_path),
                len(rows),
                "Métricas incompletas; conservar corrida parcial.",
            )
            row = {
                **metric,
                "case_id": case_id,
                "condition": condition,
                "expected_category": expected,
                "attacker_target": target,
                "category": response.category if response else None,
            }
            append_metric(output / "results.jsonl", row)
            rows.append(row)
            print(f"{prompt} {case_id} {condition}: {row['status']}", file=sys.stderr)
    report = analyze(rows)
    write_json(output / "summary.json", report)
    return report
