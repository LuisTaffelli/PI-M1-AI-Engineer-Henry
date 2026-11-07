"""Verifica corridas originales versionadas sin importar aplicación, claves ni red."""

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from statistics import median
from uuid import UUID

MANIFEST = "MANIFIESTO_CORRIDAS_2026-11-06.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def confined(root, relative):
    relative = Path(relative)
    require(
        not relative.is_absolute() and ".." not in relative.parts and relative.parts,
        f"Ruta relativa inválida: {relative}",
    )
    path = root
    for part in relative.parts:
        path = path / part
        require(not path.is_symlink(), f"No se admite enlace simbólico: {relative}")
    resolved = path.resolve()
    require(
        resolved.is_relative_to(root.resolve()), f"Ruta fuera del archivo: {relative}"
    )
    return resolved


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def verify(evidence, check_mtime=False, manifest_name=MANIFEST):
    manifest = read_json(confined(evidence, manifest_name))
    require(manifest["format_version"] == 2, "Formato de manifiesto no admitido")
    root = evidence.parents[1]
    entries = manifest["files"]
    directories = {run["directory"] for run in manifest["runs"]}
    require(len(directories) == len(manifest["runs"]), "Corrida duplicada")
    require(
        all(Path(name).parent == Path("data/local_runs") for name in directories),
        "Las corridas deben estar directamente en data/local_runs",
    )
    expected = {entry["path"] for entry in entries}
    require(len(expected) == len(entries), "Archivos duplicados en el manifiesto")
    actual = {
        str(path.relative_to(root))
        for directory in directories
        for path in confined(root, directory).rglob("*")
        if path.is_file() or path.is_symlink()
    }
    require(actual == expected, "Faltan archivos o hay archivos no inventariados")
    for entry in entries:
        path = confined(root, entry["path"])
        raw = path.read_bytes()
        require(len(raw) == entry["bytes"], f"Tamaño distinto: {entry['path']}")
        require(
            sha256(raw).hexdigest() == entry["sha256"],
            f"SHA-256 distinto: {entry['path']}",
        )
        if path.suffix == ".jsonl":
            read_rows(path)
        else:
            read_json(path)
        if check_mtime:
            require(
                path.stat().st_mtime_ns == entry["source_mtime_ns"],
                f"mtime original distinto: {entry['path']}",
            )

    seen = set()
    total_rows = 0
    for run in manifest["runs"]:
        directory = confined(root, run["directory"])
        metrics = read_rows(directory / "metrics.jsonl")
        rows = read_rows(directory / "results.jsonl")
        summary = read_json(directory / "summary.json")
        require(
            len(metrics) == len(rows) == run["rows"],
            f"Cantidad de filas: {run['name']}",
        )
        for metric, row in zip(metrics, rows, strict=True):
            require(
                all(key in row and row[key] == value for key, value in metric.items()),
                f"Métrica/resultado distintos: {run['name']}",
            )
            request_id = row["request_id"]
            require(
                UUID(request_id).version == 4, f"ID local inesperado: {run['name']}"
            )
            require(request_id not in seen, f"Request repetido: {run['name']}")
            seen.add(request_id)
        for prompt, stats in summary["by_prompt"].items():
            group = [row for row in rows if row["prompt_version"] == prompt]
            if not group:
                require(stats.get("total", 0) == 0, f"Resumen sin filas: {run['name']}")
                continue
            require(
                dict(Counter(row["status"] for row in group)) == stats["status_counts"],
                f"Estados distintos: {run['name']}/{prompt}",
            )
            if "correct" in stats:
                calculated = {
                    "total": len(group),
                    "correct": sum(row["correct"] for row in group),
                    "validated_outputs": sum(row["status"] == "ok" for row in group),
                    "latency_median_seconds": median(
                        row["latency_seconds"] for row in group
                    ),
                }
                require(
                    all(stats[key] == value for key, value in calculated.items()),
                    f"Score, validez o latencia distintos: {run['name']}/{prompt}",
                )
        total_rows += len(rows)

    if manifest.get("check_historical_remote_report", True):
        report = read_json(evidence / "EVALS_REMOTOS_2026-11-06.json")
        for run in report["runs"] + report["supplemental_runs"]:
            directory = confined(root, run["run_dir"])
            for filename, digest in run["source_sha256"].items():
                path = confined(directory, filename)
                require(
                    sha256(path.read_bytes()).hexdigest() == digest,
                    "Hash remoto histórico distinto",
                )

        provenance = read_json(
            evidence / "PROCEDENCIA_METRICAS_REMOTAS_2026-11-06.json"
        )
        sample_path = evidence / Path(provenance["extract"]).name
        require(
            sha256(sample_path.read_bytes()).hexdigest()
            == provenance["extract_sha256"],
            "Extracto distinto",
        )
        sample_rows = read_rows(sample_path)
        for item in provenance["rows"]:
            path = confined(root, item["source"])
            row = read_rows(path)[item["source_line"] - 1]
            retained = {field: row[field] for field in item["retained_fields"]}
            require(
                retained == sample_rows[item["extract_line"] - 1],
                "Muestra sin correspondencia literal",
            )
    return len(manifest["runs"]), len(entries), total_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-mtime",
        "--compare-originals",
        action="store_true",
        help="Coteja el mtime observado; no usar en un clon, Git no lo conserva.",
    )
    parser.add_argument(
        "--manifest",
        default=MANIFEST,
        help="Manifiesto relativo a docs/evidencia; el archivo histórico es el predeterminado.",
    )
    args = parser.parse_args()
    try:
        runs, files, rows = verify(
            Path(__file__).resolve().parent, args.check_mtime, args.manifest
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print(
        f"OK: {runs} corridas, {files} archivos y {rows} filas; hashes, métricas y resúmenes coherentes."
    )
    print(
        "Sin llamadas a proveedores. Integridad no equivale a autenticidad independiente ni calidad general."
    )


if __name__ == "__main__":
    main()
