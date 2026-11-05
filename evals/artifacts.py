"""Archivos de evaluación: hashes, JSON y verificación del registro por request."""

import hashlib
import json
from pathlib import Path

from src.runtime.config import ROOT


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): sha256(path)
        for folder in ("src", "evals")
        for path in sorted((ROOT / folder).rglob("*.py"))
    }


def prompt_hashes(prompts) -> dict[str, str]:
    return {name: sha256(ROOT / "prompts" / f"{name}.yaml") for name in prompts}


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def next_metric(path: Path, completed: int, message: str) -> dict:
    lines = path.read_text().splitlines()
    if len(lines) != completed + 1:
        raise ValueError(message)
    return json.loads(lines[-1])
