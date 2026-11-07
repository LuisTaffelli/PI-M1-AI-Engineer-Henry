"""Regresiones del verificador sobre copias temporales, sin importar proveedores."""

import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verificar_corridas", HERE / "verificar_corridas.py"
)
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class VerifyOriginalRunsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / "docs/evidencia"
        self.evidence.mkdir(parents=True)
        manifest = json.loads((HERE / VERIFIER.MANIFEST).read_text())
        run = min(manifest["runs"], key=lambda row: row["rows"])
        self.directory = self.root / run["directory"]
        self.manifest = {
            "format_version": 2,
            "check_historical_remote_report": False,
            "runs": [run],
            "files": [
                entry
                for entry in manifest["files"]
                if Path(entry["path"]).parent == Path(run["directory"])
            ],
        }
        shutil.copytree(HERE.parents[1] / run["directory"], self.directory)
        self.save_manifest()

    def save_manifest(self):
        (self.evidence / VERIFIER.MANIFEST).write_text(json.dumps(self.manifest))

    def update_digest(self, path):
        for entry in self.manifest["files"]:
            if entry["path"] == str(path.relative_to(self.root)):
                entry["sha256"] = sha256(path.read_bytes()).hexdigest()
                entry["bytes"] = path.stat().st_size
        self.save_manifest()

    def test_portable_clone_does_not_require_mtime(self):
        os.utime(self.directory / "plan.json", (0, 0))
        self.assertEqual(VERIFIER.verify(self.evidence), (1, 5, 2))
        with self.assertRaisesRegex(ValueError, "mtime"):
            VERIFIER.verify(self.evidence, check_mtime=True)

    def test_missing_file(self):
        (self.directory / "plan.json").unlink()
        with self.assertRaisesRegex(ValueError, "Faltan archivos"):
            VERIFIER.verify(self.evidence)

    def test_extra_file(self):
        (self.directory / "extra.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "no inventariados"):
            VERIFIER.verify(self.evidence)

    def test_same_size_corruption(self):
        path = self.directory / "plan.json"
        path.write_bytes(b" " + path.read_bytes()[1:])
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            VERIFIER.verify(self.evidence)

    def test_metrics_mismatch_even_with_updated_digest(self):
        path = self.directory / "metrics.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["latency_seconds"] += 1
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        self.update_digest(path)
        with self.assertRaisesRegex(ValueError, "Métrica/resultado"):
            VERIFIER.verify(self.evidence)

    def test_duplicate_file(self):
        self.manifest["files"].append(self.manifest["files"][0])
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "duplicados"):
            VERIFIER.verify(self.evidence)

    def test_duplicate_run(self):
        self.manifest["runs"].append(self.manifest["runs"][0])
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Corrida duplicada"):
            VERIFIER.verify(self.evidence)

    def test_run_outside_local_runs(self):
        self.manifest["runs"][0]["directory"] = "docs/evidencia"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "data/local_runs"):
            VERIFIER.verify(self.evidence)

    def test_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "Ruta relativa inválida"):
            VERIFIER.verify(self.evidence, manifest_name="../manifest.json")

    def test_symlink_directory(self):
        target = self.root / "original"
        self.directory.rename(target)
        self.directory.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "simbólico"):
            VERIFIER.verify(self.evidence)

    def test_symlink_file(self):
        path = self.directory / "plan.json"
        target = self.root / "plan.json"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "simbólico"):
            VERIFIER.verify(self.evidence)


if __name__ == "__main__":
    unittest.main()
