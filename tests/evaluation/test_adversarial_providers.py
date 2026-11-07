"""Plan y ejecución pareada con adaptadores reales y transportes falsos, sin red."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import URLError

from evals.adversarial.plan import prepare_plan
from evals.adversarial.report import analyze, execution_summary
from evals.adversarial.runner import execute_plan
from evals.run_adversarial_pairs import main, run_pairs
from src.llm.providers.base import ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.llm.providers.ollama_provider import OllamaProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.runtime.config import ROOT, Settings
from src.support.guardrails import check_input

PROMPTS = ("v1_zero_shot", "v2_few_shot", "v3_structured", "v4_reasoning")
VALID = json.dumps(
    {
        "answer": "PRIVATE_FIXTURE_OUTPUT",
        "confidence": 0.5,
        "category": "billing",
        "actions": [],
    }
)


class AdversarialProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "run"
        for target in (
            "src.runtime.environment.load_api_key",
            "src.llm.providers.openai_provider.urlopen",
            "src.llm.providers.gemini_provider.urlopen",
            "src.llm.providers.ollama_provider.build_opener",
        ):
            blocker = patch(target, side_effect=AssertionError("No keys or network"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def plan(self, provider="openai", prompts=("v3_structured",), **overrides):
        return prepare_plan(
            Settings(
                provider=provider,
                model=overrides.pop("model", "fixture"),
                max_attempts=3,
                **overrides,
            ),
            prompts,
            self.output,
            max_calls=128,
        )

    def adapter_patch(self, provider, calls, text=VALID, fail=False, usage=None):
        def transport(request, timeout):
            self.assertTrue((self.output / "plan.json").is_file())
            self.assertEqual(
                timeout, 10 if request.full_url.endswith("/api/show") else 30
            )
            if request.full_url.endswith("/api/show"):
                return {"details": {"format": "gguf"}, "capabilities": ["completion"]}
            calls.append(json.loads(request.data))
            if fail:
                raise URLError("PRIVATE_TRANSPORT_DETAIL")
            if provider == "ollama":
                return {
                    "done": True,
                    "done_reason": "stop",
                    "message": {"role": "assistant", "content": text},
                    "prompt_eval_count": 20,
                    "eval_count": 10,
                }
            return {
                "status": "completed",
                "usage": usage,
                "output" if provider == "openai" else "steps": [
                    {
                        "type": "message" if provider == "openai" else "model_output",
                        "content": [
                            {
                                "type": "output_text"
                                if provider == "openai"
                                else "text",
                                "text": text,
                            }
                        ],
                    }
                ],
            }

        adapter = {
            "openai": OpenAIProvider,
            "gemini": GeminiProvider,
            "ollama": OllamaProvider,
        }[provider]

        def factory(**kwargs):
            if provider != "ollama":
                kwargs["api_key"] = "fake-test-key"
            return adapter(**kwargs, transport=transport)

        return patch(f"src.llm.factory.{adapter.__name__}", side_effect=factory)

    def run_fake(self, provider, prompts=("v3_structured",), **transport_options):
        calls = []
        plan = self.plan(provider, prompts)
        with (
            self.adapter_patch(provider, calls, **transport_options),
            redirect_stderr(StringIO()),
        ):
            report = execute_plan(
                plan,
                execute=True,
                allow_local_inference=True,
                allow_remote_inference=True,
            )
        rows = [
            json.loads(line)
            for line in (self.output / "results.jsonl").read_text().splitlines()
        ]
        return plan, report, rows, calls

    def cli(self, provider, *options):
        argv = [
            "pairs",
            "--provider",
            provider,
            "--model",
            "fixture",
            "--prompt",
            "v3_structured",
            "--max-calls",
            "30",
            "--output",
            str(self.output),
            *options,
        ]
        with (
            patch("sys.argv", argv),
            redirect_stdout(StringIO()) as stdout,
            redirect_stderr(StringIO()),
        ):
            status = main()
        return status, json.loads(stdout.getvalue()) if stdout.getvalue() else None

    def test_every_provider_preview_is_offline_and_has_same_protocol(self):
        plans = []
        for provider in ("mock", "ollama", "openai", "gemini"):
            plan = self.plan(provider, PROMPTS)
            plans.append(plan)
            self.assertEqual(plan.metadata["generation_upper_bound"], 120)
            self.assertEqual(
                plan.metadata["remote_calls_upper_bound"],
                120 if provider in {"openai", "gemini"} else 0,
            )
            self.assertEqual(plan.settings.max_attempts, 1)
            self.assertFalse(plan.metadata["execution_requested"])
            self.assertFalse(self.output.exists())
        for plan in plans[1:]:
            self.assertEqual(plan.jobs, plans[0].jobs)
            self.assertEqual(
                plan.metadata["dataset_sha256"], plans[0].metadata["dataset_sha256"]
            )
            self.assertEqual(
                plan.metadata["prompt_sha256"], plans[0].metadata["prompt_sha256"]
            )

    def test_all_three_real_adapters_receive_same_queries_and_prompts(self):
        observed = []
        for provider in ("openai", "gemini", "ollama"):
            self.output = Path(self.temp.name) / provider
            plan, report, rows, calls = self.run_fake(provider, PROMPTS)
            self.assertEqual(len(rows), 120)
            self.assertEqual(len(calls), 88)
            self.assertEqual(report["execution"]["generation_attempts"], 88)
            self.assertEqual(
                report["execution"]["remote_calls_attempted"],
                0 if provider == "ollama" else 88,
            )
            self.assertTrue(report["execution"]["completed"])
            self.assertTrue(
                all(
                    row["provider"] == provider and row["model"] == "fixture"
                    for row in rows
                )
            )
            self.assertEqual(sum(row["attempts"] == 0 for row in rows), 32)
            self.assertEqual(
                {**analyze(rows), "execution": execution_summary(rows, plan.metadata)},
                report,
            )
            requests = []
            for call in calls:
                if provider == "ollama":
                    self.assertEqual(call["options"]["num_predict"], 256)
                    requests.append(
                        (call["messages"][0]["content"], call["messages"][1]["content"])
                    )
                else:
                    limit = (
                        call["max_output_tokens"]
                        if provider == "openai"
                        else call["generation_config"]["max_output_tokens"]
                    )
                    self.assertEqual(limit, 256)
                    requests.append(
                        (
                            call[
                                "instructions"
                                if provider == "openai"
                                else "system_instruction"
                            ],
                            call["input"],
                        )
                    )
            observed.append(requests)
            expected_queries = []
            for _, _, query, _, _ in plan.jobs:
                try:
                    check_input(query)
                except ValueError:
                    continue
                expected_queries.append(query)
            self.assertEqual([query for _, query in requests], expected_queries * 4)
            for path in self.output.iterdir():
                for private in (
                    "PRIVATE_FIXTURE_OUTPUT",
                    "fake-test-key",
                    "Solicito el comprobante",
                ):
                    self.assertNotIn(private, path.read_text())
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(observed[1], observed[2])

    def test_remote_gates_reject_each_missing_permission_without_files(self):
        for provider in ("openai", "gemini"):
            for options in (
                {},
                {"execute": True},
                {"allow_remote_inference": True},
                {"execute": True, "allow_local_inference": True},
            ):
                with (
                    self.subTest(provider=provider, options=options),
                    self.assertRaises(ValueError),
                ):
                    execute_plan(self.plan(provider), **options)
                self.assertFalse(self.output.exists())
            with self.assertRaises(ValueError):
                run_pairs(
                    self.plan(provider).settings,
                    ("v3_structured",),
                    self.output,
                    max_calls=30,
                    allow_local_inference=True,
                )
            self.assertFalse(self.output.exists())

    def test_local_and_mock_execution_gates(self):
        with self.assertRaises(ValueError):
            execute_plan(self.plan("ollama"), execute=True)
        with self.assertRaises(ValueError):
            execute_plan(self.plan("mock"))
        self.assertFalse(self.output.exists())

    def test_mock_is_marked_simulated_and_never_reads_credentials(self):
        with redirect_stderr(StringIO()):
            report = execute_plan(self.plan("mock"), execute=True)
        self.assertTrue(report["execution"]["simulated"])
        self.assertTrue(report["execution"]["completed"])
        self.assertFalse(report["safety_claim"])
        self.assertEqual(report["execution"]["remote_calls_attempted"], 0)
        self.assertIsNone(report["execution"]["usage_and_cost"]["cost_usd"])

    def test_budget_type_and_bounds_checked_before_output(self):
        for budget in (0, 29, 129, True, 30.0):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                prepare_plan(
                    Settings(), ("v3_structured",), self.output, max_calls=budget
                )
            self.assertFalse(self.output.exists())
        self.assertEqual(self.plan().metadata["planned_service_calls"], 30)

    def test_effective_limits_are_capped_and_recorded(self):
        plan = self.plan(
            openai_max_output_tokens=4096,
            gemini_max_output_tokens=4096,
            ollama_max_output_tokens=64,
            ollama_timeout_seconds=120,
            ollama_num_ctx=4096,
        )
        settings = plan.metadata["settings"]
        self.assertEqual(settings["max_attempts"], 1)
        self.assertEqual(settings["openai_max_output_tokens"], 256)
        self.assertEqual(settings["gemini_max_output_tokens"], 256)
        self.assertEqual(settings["ollama_max_output_tokens"], 64)
        self.assertEqual(settings["ollama_timeout_seconds"], 30)
        self.assertEqual(settings["ollama_num_ctx"], 2048)

    def test_invalid_output_is_not_repaired_or_called_a_defense(self):
        _, report, rows, calls = self.run_fake("gemini", text="not-json")
        self.assertEqual(len(calls), 22)
        self.assertEqual(sum(row["attempts"] for row in rows), 22)
        self.assertTrue(report["execution"]["completed"])
        self.assertEqual(report["by_prompt"]["v3_structured"]["eligible_valid"], 0)
        self.assertEqual(
            report["by_prompt"]["v3_structured"]["uninterpretable_baseline"], 12
        )

    def test_transport_failure_stops_and_keeps_partial_report(self):
        for provider in ("openai", "gemini"):
            self.output = Path(self.temp.name) / provider
            _, report, rows, calls = self.run_fake(provider, PROMPTS, fail=True)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(rows), 1)
            self.assertFalse(report["execution"]["completed"])
            self.assertEqual(report["execution"]["not_run"], 119)
            self.assertFalse(
                report["execution"]["by_prompt"]["v4_reasoning"]["completed"]
            )
            group = report["by_prompt"]["v1_zero_shot"]
            self.assertEqual(group["incomplete_pairs"], 1)
            self.assertEqual(group["eligible_admitted"], 0)
            self.assertIsNone(
                group["pair_outcomes"][0]["targeted_category_flip_observed"]
            )
            for path in self.output.iterdir():
                self.assertNotIn("PRIVATE_TRANSPORT_DETAIL", path.read_text())

    def test_configuration_failure_stops_with_zero_generations(self):
        with (
            patch(
                "src.llm.factory.OpenAIProvider",
                side_effect=ProviderError("PRIVATE_CONFIG_ERROR"),
            ),
            redirect_stderr(StringIO()),
        ):
            report = execute_plan(
                self.plan(), execute=True, allow_remote_inference=True
            )
        self.assertEqual(report["execution"]["generation_attempts"], 0)
        self.assertEqual(report["execution"]["not_run"], 29)
        self.assertEqual(
            report["execution"]["status_counts"], {"configuration_error": 1}
        )

    def test_missing_attack_is_not_eligible_and_mixed_runs_are_rejected(self):
        row = {
            "case_id": "pair",
            "condition": "clean",
            "category": "billing",
            "status": "ok",
            "expected_category": "billing",
            "attacker_target": "other",
            "prompt_version": "v3_structured",
            "attempts": 1,
            "provider": "openai",
            "model": "fixture",
        }
        report = analyze([row])["by_prompt"]["v3_structured"]
        self.assertEqual(report["baseline_correct"], 1)
        self.assertEqual(report["eligible_admitted"], 0)
        self.assertEqual(report["incomplete_pairs"], 1)
        for other in (
            row,
            {**row, "provider": "gemini"},
            {**row, "model": "different"},
        ):
            with self.assertRaises(ValueError):
                analyze([row, other])

    def test_cli_preview_and_remote_gate(self):
        for provider in ("openai", "gemini"):
            for options in (
                (),
                ("--allow-remote-inference",),
                ("--allow-local-inference",),
            ):
                status, preview = self.cli(provider, *options)
                self.assertEqual(status, 0)
                self.assertFalse(preview["execution_requested"])
                self.assertFalse(self.output.exists())
            status, report = self.cli(provider, "--execute")
            self.assertEqual(status, 2)
            self.assertIsNone(report)
            self.assertFalse(self.output.exists())

    def test_cli_remote_execution_and_partial_exit(self):
        for provider in ("openai", "gemini"):
            self.output = Path(self.temp.name) / provider
            calls = []
            with self.adapter_patch(provider, calls):
                status, report = self.cli(
                    provider, "--execute", "--allow-remote-inference"
                )
            self.assertEqual(status, 0)
            self.assertTrue(report["execution"]["completed"])
            self.assertEqual(len(calls), 22)
        self.output = Path(self.temp.name) / "partial"
        with self.adapter_patch("gemini", [], fail=True):
            status, report = self.cli("gemini", "--execute", "--allow-remote-inference")
        self.assertEqual(status, 2)
        self.assertFalse(report["execution"]["completed"])

    def test_legacy_local_cli_executes_and_explicit_preview_wins(self):
        argv = [
            "pairs",
            "--config",
            str(ROOT / "config.ollama.example.toml"),
            "--prompt",
            "v3_structured",
            "--max-calls",
            "30",
            "--output",
            str(self.output),
            "--allow-local-inference",
        ]
        with (
            patch("sys.argv", argv + ["--preview"]),
            redirect_stdout(StringIO()) as stream,
        ):
            self.assertEqual(main(), 0)
        self.assertFalse(json.loads(stream.getvalue())["execution_requested"])
        self.assertFalse(self.output.exists())
        calls = []
        with (
            patch("sys.argv", argv),
            self.adapter_patch("ollama", calls),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(main(), 0)
        self.assertEqual(len(calls), 22)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("previous-run")
        with self.assertRaises(FileExistsError):
            self.plan()
        self.assertEqual(marker.read_text(), "previous-run")

    def test_priced_generations_keep_total_despite_preblocks(self):
        plan = self.plan(
            model="gpt-6-luna",
            pricing_path=str(ROOT / "pricing/standard-text-2026-11-05.json"),
        )
        usage = {
            "input_tokens": 20,
            "output_tokens": 10,
            "total_tokens": 30,
            "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
        }
        with self.adapter_patch("openai", [], usage=usage), redirect_stderr(StringIO()):
            report = execute_plan(plan, execute=True, allow_remote_inference=True)
        financials = report["execution"]["usage_and_cost"]
        self.assertEqual(
            financials["cost_status_counts"], {"estimated": 22, "not_requested": 8}
        )
        self.assertEqual(Decimal(financials["cost_usd"]), Decimal("0.000154"))
        self.assertFalse(financials["billing_verified"])

    def test_explicit_pricing_catalog_is_snapshotted(self):
        path = ROOT / "pricing/standard-text-2026-11-05.json"
        plan = self.plan(pricing_path=str(path))
        self.assertIsNotNone(plan.metadata["pricing"])
        with self.adapter_patch("openai", []), redirect_stderr(StringIO()):
            execute_plan(plan, execute=True, allow_remote_inference=True)
        self.assertEqual((self.output / "pricing.json").read_bytes(), path.read_bytes())


if __name__ == "__main__":
    unittest.main()
