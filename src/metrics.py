"""Registro append-only por request, sin consultas ni respuestas crudas."""

import json
from pathlib import Path


def append_metric(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
