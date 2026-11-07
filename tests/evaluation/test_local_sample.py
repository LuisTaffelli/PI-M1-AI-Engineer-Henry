"""Corridas reproducibles con transporte falso, sin inferencia local ni remota."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evals.run_local_sample import main, run_sample
from src.runtime.config import ROOT, Settings

DATASET = ROOT / "data/eval_dataset.jsonl"
INFO = {"details": {"format": "gguf"}, "capabilities": ["completion"]}


def reply(text):
    return {
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": text},
        "prompt_eval_count": 20,
        "eval_count": 10,
    }


def valid(category="billing", answer="Respuesta de fixture"):
    return json.dumps(
        {"answer": answer, "confidence": 0.5, "category": category, "actions": []}
    )


class LocalSampleTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "run"
        self.settings = Settings(provider="ollama", model="fixture-local")
        for name in ("openai_provider", "gemini_provider"):
            blocker = patch(
                f"src.llm.providers.{name}.urlopen",
                side_effect=AssertionError("No remote network"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)
        blocker = patch(
            "src.llm.providers.ollama_provider.build_opener",
            side_effect=AssertionError("No local network in tests"),
        )
        blocker.start()
        self.addCleanup(blocker.stop)

    def run_fixture(self, responses):
        calls = iter(responses)

        def transport(request, timeout):
            # El plan y las etiquetas deben estar conservados antes de generar.
            plan = json.loads((self.output / "plan.json").read_text())
            self.assertEqual(plan["cases"][0]["expected_category"], "billing")
            if request.full_url.endswith("/api/show"):
                return INFO
            payload = json.loads(request.data)
            self.assertNotIn("expected_category", payload)
            return reply(next(calls))

        with (
            patch("src.llm.providers.ollama_provider._post_json", transport),
            redirect_stderr(StringIO()),
        ):
            return run_sample(
                DATASET,
                self.settings,
                ["nubbix-b01"],
                self.output,
                allow_local_inference=True,
            )

    def test_requires_explicit_permission_local_provider_valid_ids_and_budget(self):
        for settings, ids, allowed in (
            (self.settings, ["nubbix-b01"], False),
            (Settings(provider="openai", model="fixture"), ["nubbix-b01"], True),
            (Settings(provider="gemini", model="fixture"), ["nubbix-b01"], True),
            (self.settings, [], True),
            (self.settings, ["nubbix-b01"] * 2, True),
            (self.settings, [f"nubbix-b0{i}" for i in range(1, 6)], True),
            (self.settings, ["missing"], True),
        ):
            with (
                self.subTest(ids=ids, provider=settings.provider),
                self.assertRaises(ValueError),
            ):
                run_sample(
                    DATASET, settings, ids, self.output, allow_local_inference=allowed
                )
            self.assertFalse(self.output.exists())

    def test_plan_results_summary_and_metrics_survive_without_raw_text(self):
        report = self.run_fixture([valid(), valid("account")])
        self.assertFalse(report["quality_claim"])
        groups = report["by_prompt"]
        self.assertEqual(groups["v1_zero_shot"]["exact_match"], 1)
        self.assertEqual(groups["v2_few_shot"]["exact_match"], 0)
        self.assertEqual(groups["v2_few_shot"]["validated_outputs"], 1)
        rows = [
            json.loads(s)
            for s in (self.output / "results.jsonl").read_text().splitlines()
        ]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["attempts"] == 1 and r["cost_usd"] is None for r in rows))
        self.assertTrue(all(r["application_output_guardrail_passed"] for r in rows))
        plan = json.loads((self.output / "plan.json").read_text())
        self.assertEqual(plan["planned_generations"], 2)
        self.assertEqual(plan["settings"]["ollama_timeout_seconds"], 30)
        self.assertEqual(len(plan["dataset_sha256"]), 64)
        for path in self.output.iterdir():
            raw = path.read_text()
            self.assertNotIn("Respuesta de fixture", raw)
            self.assertNotIn("Necesito el comprobante", raw)
        self.assertEqual(json.loads((self.output / "summary.json").read_text()), report)

    def test_format_and_guardrail_failures_are_scored_without_retry(self):
        report = self.run_fixture(
            ["not JSON", valid(answer="password: PRIVATE_FIXTURE")]
        )
        rows = [
            json.loads(s)
            for s in (self.output / "results.jsonl").read_text().splitlines()
        ]
        self.assertFalse(rows[0]["application_contract_valid"])
        self.assertIsNone(rows[0]["application_output_guardrail_passed"])
        self.assertTrue(rows[1]["application_contract_valid"])
        self.assertFalse(rows[1]["application_output_guardrail_passed"])
        self.assertTrue(all(r["attempts"] == 1 and not r["correct"] for r in rows))
        self.assertEqual(report["by_prompt"]["v2_few_shot"]["schema_valid_outputs"], 1)
        self.assertEqual(report["by_prompt"]["v2_few_shot"]["validated_outputs"], 0)
        self.assertNotIn("PRIVATE_FIXTURE", (self.output / "results.jsonl").read_text())

    def test_network_failures_are_unknown_format_not_fake_success(self):
        with (
            patch(
                "src.llm.providers.ollama_provider._post_json",
                side_effect=TimeoutError("PRIVATE_FAILURE"),
            ),
            redirect_stderr(StringIO()),
        ):
            report = run_sample(
                DATASET,
                self.settings,
                ["nubbix-b01"],
                self.output,
                allow_local_inference=True,
            )
        rows = [
            json.loads(s)
            for s in (self.output / "results.jsonl").read_text().splitlines()
        ]
        self.assertTrue(all(r["status"] == "provider_error" for r in rows))
        self.assertTrue(all(r["application_contract_valid"] is None for r in rows))
        self.assertEqual(report["by_prompt"]["v1_zero_shot"]["exact_match"], 0)
        self.assertNotIn("PRIVATE_FAILURE", (self.output / "results.jsonl").read_text())

    def test_existing_run_cannot_be_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "plan.json"
        sentinel.write_text("existing")
        with self.assertRaises(FileExistsError):
            run_sample(
                DATASET,
                self.settings,
                ["nubbix-b01"],
                self.output,
                allow_local_inference=True,
            )
        self.assertEqual(sentinel.read_text(), "existing")

    def test_cli_without_opt_in_rejects_before_network_and_output(self):
        config = Path(self.directory.name) / "config.toml"
        config.write_text('provider="ollama"\nmodel="fixture-local"\n')
        with (
            patch(
                "sys.argv",
                [
                    "local",
                    "--config",
                    str(config),
                    "--case-id",
                    "nubbix-b01",
                    "--output",
                    str(self.output),
                ],
            ),
            redirect_stderr(StringIO()),
            redirect_stdout(StringIO()),
        ):
            self.assertEqual(main(), 2)
        self.assertFalse(self.output.exists())

    def test_full_corpus_requires_budget_and_reports_failures_in_denominator(self):
        with self.assertRaises(ValueError):
            run_sample(
                DATASET,
                self.settings,
                [],
                self.output,
                allow_local_inference=True,
                all_cases=True,
            )
        self.assertFalse(self.output.exists())
        from evals.run_evals import load_cases

        queries = {case.query for case in load_cases(DATASET)}
        calls = 0

        def transport(request, timeout):
            nonlocal calls
            plan = json.loads((self.output / "plan.json").read_text())
            self.assertEqual(plan["planned_generations"], 64)
            self.assertEqual(len(plan["cases"]), 32)
            if request.full_url.endswith("/api/show"):
                return INFO
            payload = json.loads(request.data)
            self.assertIn(payload["messages"][1]["content"], queries)
            calls += 1
            return reply("not JSON" if calls == 33 else valid("other"))

        with (
            patch("src.llm.providers.ollama_provider._post_json", transport),
            redirect_stderr(StringIO()),
        ):
            report = run_sample(
                DATASET,
                self.settings,
                [],
                self.output,
                allow_local_inference=True,
                all_cases=True,
                max_generations=64,
            )
        self.assertEqual(calls, 64)
        self.assertEqual(report["by_prompt"]["v1_zero_shot"]["exact_match"], 0.25)
        group = report["by_prompt"]["v2_few_shot"]
        self.assertEqual(group["total"], 32)
        self.assertEqual(group["exact_match"], 0.25)
        self.assertEqual(group["validated_outputs"], 31)
        self.assertEqual(group["confusion_matrix"]["billing"]["error"], 1)
        self.assertEqual(group["by_ambiguity"]["marked_ambiguous"]["count"], 8)
        self.assertEqual(group["by_category"]["billing"]["errors"], 1)

    def test_diagnostic_suite_is_explicit_and_keeps_its_smaller_scope(self):
        diagnostic = ROOT / "data/eval_robustness.jsonl"
        with self.assertRaises(ValueError):
            run_sample(
                diagnostic,
                self.settings,
                [],
                self.output,
                allow_local_inference=True,
                all_cases=True,
                max_generations=16,
            )
        self.assertFalse(self.output.exists())

        def transport(request, timeout):
            return (
                INFO
                if request.full_url.endswith("/api/show")
                else reply(valid("other"))
            )

        with (
            patch("src.llm.providers.ollama_provider._post_json", transport),
            redirect_stderr(StringIO()),
        ):
            report = run_sample(
                diagnostic,
                self.settings,
                [],
                self.output,
                allow_local_inference=True,
                all_cases=True,
                max_generations=16,
                diagnostic_suite=True,
            )
        self.assertEqual(report["suite_kind"], "supplementary_diagnostic")
        self.assertEqual(report["by_prompt"]["v1_zero_shot"]["total"], 8)
        self.assertEqual(report["by_prompt"]["v1_zero_shot"]["exact_match"], 0.25)
        self.assertFalse(report["quality_claim"])
        plan = json.loads((self.output / "plan.json").read_text())
        self.assertEqual(plan["planned_generations"], 16)

    def test_selection_and_hard_budget_reject_before_output_or_transport(self):
        for change in (
            {"all_cases": True},
            {"max_generations": 65},
            {"max_generations": True},
            {"max_generations": 1},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                run_sample(
                    DATASET,
                    self.settings,
                    ["nubbix-b01"],
                    self.output,
                    allow_local_inference=True,
                    **change,
                )
            self.assertFalse(self.output.exists())
