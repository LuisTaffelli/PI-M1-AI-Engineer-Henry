"""Plan pareado offline, con el mismo protocolo y límites para cada proveedor."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from evals.adversarial.pairs import build_jobs, load_protocol
from evals.common.artifacts import prompt_hashes, sha256, source_hashes
from src.llm.prompt_catalog import PROMPT_NAMES
from src.llm.prompts import load_prompt
from src.runtime.config import ROOT, Settings
from src.runtime.pricing import load_catalog

REMOTE_PROVIDERS = frozenset({"openai", "gemini"})
MAX_CALLS = 384


@dataclass(frozen=True)
class PairedPlan:
    settings: Settings
    prompts: tuple[str, ...]
    jobs: tuple[tuple, ...]
    output: Path
    metadata: dict
    pricing_data: bytes | None = None


def prepare_plan(
    settings: Settings,
    prompts: tuple[str, ...],
    output: Path,
    *,
    max_calls: int,
    pairs_path: Path = ROOT / "evals/adversarial_pairs.jsonl",
    attack_paths: list[Path] | None = None,
    controls_path: Path = ROOT / "evals/guardrail_controls.jsonl",
) -> PairedPlan:
    if (
        not prompts
        or len(set(prompts)) != len(prompts)
        or any(p not in PROMPT_NAMES for p in prompts)
    ):
        raise ValueError("Prompts inválidos o repetidos.")
    for prompt in prompts:
        load_prompt(prompt)
    attack_paths = (
        attack_paths
        if attack_paths is not None
        else [
            ROOT / "evals/adversarial.jsonl",
            ROOT / "evals/adversarial_unicode.jsonl",
        ]
    )
    pairs, attacks, controls = load_protocol(pairs_path, attack_paths, controls_path)
    jobs = tuple(build_jobs(pairs, attacks, controls))
    planned = len(prompts) * len(jobs)
    http_attempts = (
        settings.http_max_attempts if settings.provider in REMOTE_PROVIDERS else 1
    )
    upper_bound = planned * http_attempts
    if (
        type(max_calls) is not int
        or not 1 <= max_calls <= MAX_CALLS
        or upper_bound > max_calls
    ):
        raise ValueError(
            "Presupuesto insuficiente o superior a 384 invocaciones de proveedor."
        )
    output = output.resolve()
    if output.exists():
        raise FileExistsError("Elegí un directorio de salida nuevo.")
    # Un solo intento y el mismo techo de salida: nunca reparar sólo un proveedor.
    effective = Settings.model_validate(
        {
            **settings.model_dump(),
            "max_attempts": 1,
            "log_metrics": True,
            "metrics_path": str(output / "metrics.jsonl"),
            **{
                f"{p}_max_output_tokens": min(
                    getattr(settings, f"{p}_max_output_tokens"), 256
                )
                for p in ("openai", "gemini", "ollama")
            },
            "ollama_num_ctx": min(settings.ollama_num_ctx, 2048),
            "ollama_timeout_seconds": min(settings.ollama_timeout_seconds, 30),
        }
    )
    pricing_data = None
    pricing_metadata = None
    if settings.pricing_path is not None and settings.provider in REMOTE_PROVIDERS:
        catalog, pricing_data = load_catalog(ROOT / settings.pricing_path)
        pricing_metadata = {
            "catalog_version": catalog.catalog_version,
            "sha256": hashlib.sha256(pricing_data).hexdigest(),
            "basis": "paid_standard_text_estimate_not_invoice",
        }
    files = [pairs_path, controls_path, *attack_paths]
    metadata = {
        "format_version": 3,
        "provider": effective.provider,
        "model": effective.model,
        "simulated": effective.provider == "mock",
        "planned_service_calls": planned,
        "generation_upper_bound": upper_bound,
        "provider_calls_upper_bound": upper_bound,
        "http_max_attempts_per_generation": http_attempts,
        "remote_calls_upper_bound": upper_bound
        if effective.provider in REMOTE_PROVIDERS
        else 0,
        "max_calls": max_calls,
        "calls_unit": "Provider.generate upper bound including HTTP retries, without JSON repair; not all HTTP requests or a monetary cap",
        "monetary_cap_enforced": False,
        "execution_requested": False,
        "pricing": pricing_metadata,
        "prompts": list(prompts),
        "dataset_sha256": {p.name: sha256(p) for p in files},
        "prompt_sha256": prompt_hashes(prompts),
        "source_sha256": source_hashes(),
        "settings": {
            k: v
            for k, v in effective.model_dump().items()
            if k.startswith(("openai_", "gemini_", "ollama_", "http_"))
            or k
            in {"provider", "model", "max_attempts", "max_query_chars", "mock_scenario"}
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
        "stop_policy": "configuration_error or terminal provider_error; bounded HTTP retries only if opted in, no automatic resume",
    }
    return PairedPlan(effective, prompts, jobs, output, metadata, pricing_data)
