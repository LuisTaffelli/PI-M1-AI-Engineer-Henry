"""Compatibilidad de cuatro variantes sin inferencia remota ni claves reales."""

import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from evals.run_evals import check_dataset, load_cases
from evals.run_local_sample import run_sample, summarize
from src.llm.prompt_catalog import PROMPT_NAMES
from src.llm.prompts import load_prompt
from src.runtime.config import ROOT, Settings
from src.support.schemas import SupportResponse

INFO = {"details": {"format": "gguf"}, "capabilities": ["completion"]}
TEXT = json.dumps(
    {
        "answer": "Consulta recibida.",
        "confidence": 0.5,
        "category": "other",
        "actions": [],
    }
)
REPLY = {
    "done": True,
    "done_reason": "stop",
    "message": {"role": "assistant", "content": TEXT},
    "prompt_eval_count": 10,
    "eval_count": 10,
}


class PromptVersionTests(unittest.TestCase):
    def setUp(self):
        blocker = patch(
            "src.llm.providers.ollama_provider.build_opener",
            side_effect=AssertionError("No network"),
        )
        blocker.start()
        self.addCleanup(blocker.stop)

    def test_four_versions_keep_contract_and_old_defaults(self):
        self.assertEqual(len(PROMPT_NAMES), 4)
        self.assertEqual(Settings().prompt, "v1_zero_shot")
        for name in PROMPT_NAMES:
            document = load_prompt(name)
            self.assertEqual(document.version, name)
            self.assertEqual(Settings(prompt=name).prompt, name)
        self.assertEqual(load_prompt("v3_structured").examples, [])
        self.assertEqual(load_prompt("v4_reasoning").examples, [])
        self.assertNotEqual(
            load_prompt("v3_structured").render(), load_prompt("v4_reasoning").render()
        )
        self.assertEqual(
            set(SupportResponse.model_fields),
            {"answer", "confidence", "category", "actions"},
        )

    def test_new_prompt_name_must_match_its_file_metadata(self):
        with (
            patch(
                "pathlib.Path.read_text",
                return_value=(ROOT / "prompts/v3_structured.yaml").read_text(),
            ),
            self.assertRaises(ValueError),
        ):
            load_prompt("v4_reasoning")

    def test_cli_accepts_new_versions_and_preserves_exact_json_contract(self):
        for name in ("v3_structured", "v4_reasoning"):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.main",
                    "Consulta sintética",
                    "--prompt",
                    name,
                    "--no-metrics",
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                set(json.loads(result.stdout)),
                {"answer", "confidence", "category", "actions"},
            )
            result = subprocess.run(
                [sys.executable, "-m", "evals.run_evals", "--prompt", name],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["prompt_version"], name)

    def test_new_versions_reach_ollama_without_enabling_a_reasoning_mode(self):
        requests = []

        def transport(request, timeout):
            if request.full_url.endswith("/api/show"):
                return INFO
            requests.append(json.loads(request.data))
            return REPLY

        with (
            TemporaryDirectory() as directory,
            patch("src.llm.providers.ollama_provider._post_json", transport),
            redirect_stderr(StringIO()),
        ):
            out = Path(directory) / "run"
            report = run_sample(
                ROOT / "data/eval_dataset.jsonl",
                Settings(provider="ollama", model="fixture-local"),
                ["nubbix-o01"],
                out,
                allow_local_inference=True,
                prompts=("v3_structured", "v4_reasoning"),
                max_generations=2,
            )
            self.assertEqual(
                set(report["by_prompt"]), {"v3_structured", "v4_reasoning"}
            )
            plan = json.loads((out / "plan.json").read_text())
            self.assertEqual(plan["prompts"], ["v3_structured", "v4_reasoning"])
            self.assertEqual(plan["planned_generations"], 2)
        for payload, name in zip(
            requests, ("v3_structured", "v4_reasoning"), strict=True
        ):
            self.assertEqual(
                payload["messages"][0]["content"], load_prompt(name).render()
            )
            self.assertEqual(payload["format"], SupportResponse.model_json_schema())
            self.assertNotIn("think", payload)
            self.assertNotIn("reasoning", payload)
            self.assertEqual(
                payload["options"],
                {"temperature": 0, "num_predict": 256, "num_ctx": 2048},
            )
        self.assertEqual(requests[0]["messages"][1], requests[1]["messages"][1])

    def test_invalid_or_duplicate_comparison_versions_fail_before_output(self):
        with TemporaryDirectory() as directory:
            out = Path(directory) / "run"
            for prompts in ((), ("unknown",), ("v4_reasoning", "v4_reasoning")):
                with self.subTest(prompts=prompts), self.assertRaises(ValueError):
                    run_sample(
                        ROOT / "data/eval_dataset.jsonl",
                        Settings(provider="ollama", model="fixture-local"),
                        ["nubbix-o01"],
                        out,
                        allow_local_inference=True,
                        prompts=prompts,
                    )
                self.assertFalse(out.exists())

    def test_overlap_check_includes_new_prompt_versions(self):
        cases = load_cases(ROOT / "data/eval_dataset.jsonl")
        original = load_prompt

        def lookup(name):
            if name == "v3_structured":
                return SimpleNamespace(examples=[SimpleNamespace(query=cases[0].query)])
            return original(name)

        with (
            patch("evals.classification.dataset.load_prompt", lookup),
            self.assertRaisesRegex(ValueError, "ejemplos de prompt"),
        ):
            check_dataset(cases)

    def test_previously_saved_v1_v2_reports_can_still_be_replayed(self):
        artifact = json.loads((ROOT / "docs/EVAL_LOCAL_2026-11-04.json").read_text())
        for suite in artifact["suites"].values():
            computed = summarize(suite["results"])
            computed["suite_kind"] = suite["summary"]["suite_kind"]
            self.assertEqual(computed, suite["summary"])
