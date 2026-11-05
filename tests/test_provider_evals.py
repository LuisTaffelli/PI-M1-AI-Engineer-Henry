"""Evaluaciones con adaptadores reales y transportes falsos; sin claves ni red."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evals.classification.plan import prepare_plan
from evals.classification.runner import execute_plan
from evals.run_provider_evals import main
from src.llm.providers.base import ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.llm.providers.ollama_provider import OllamaProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.runtime.config import ROOT, Settings

DATASET = ROOT / "data/eval_dataset.jsonl"
VALID = json.dumps(
    {
        "answer": "private-fixture-answer",
        "confidence": 0.5,
        "category": "billing",
        "actions": [],
    }
)


class ProviderEvalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "run"
        for module, function in (
            ("openai", "urlopen"),
            ("gemini", "urlopen"),
            ("ollama", "build_opener"),
        ):
            blocker = patch(
                f"src.llm.providers.{module}_provider.{function}",
                side_effect=AssertionError("No network"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)

    def plan(self, provider="openai", attempts=1, prompts=("v3_structured",), **kwargs):
        return prepare_plan(
            DATASET,
            Settings(provider=provider, model="fixture", max_attempts=attempts),
            ["nubbix-b01"],
            prompts,
            self.output,
            all_cases=False,
            max_calls=384,
            **kwargs,
        )

    def run_remote(self, provider, responses, attempts=1, **kwargs):
        calls = []
        replies = iter(responses)

        def transport(request, timeout):
            self.assertTrue((self.output / "plan.json").exists())
            calls.append(json.loads(request.data))
            text = next(replies)
            content = [
                {
                    "type": "output_text" if provider == "openai" else "text",
                    "text": text,
                }
            ]
            return {
                "status": "completed",
                "output" if provider == "openai" else "steps": [
                    {
                        "type": "message" if provider == "openai" else "model_output",
                        "content": content,
                    }
                ],
            }

        adapter = OpenAIProvider if provider == "openai" else GeminiProvider

        def factory(**options):
            return adapter(**options, api_key="fake-test-key", transport=transport)

        with patch(f"src.llm.factory.{adapter.__name__}", side_effect=factory):
            report = execute_plan(
                self.plan(provider, attempts, **kwargs),
                execute=True,
                allow_remote_inference=True,
            )
        return report, calls

    def test_both_remote_adapters_and_private_artifacts(self):
        for provider in ("openai", "gemini"):
            with self.subTest(provider=provider):
                self.output = Path(self.tmp.name) / provider
                report, calls = self.run_remote(provider, [VALID])
                self.assertEqual(report["remote_calls_attempted"], 1)
                self.assertEqual(report["by_prompt"]["v3_structured"]["exact_match"], 1)
                self.assertEqual(len(calls), 1)
                for path in self.output.iterdir():
                    self.assertNotIn("private-fixture-answer", path.read_text())
                    self.assertNotIn("fake-test-key", path.read_text())
                    self.assertNotIn("Me cobraron", path.read_text())

    def test_repair_attempts_counted(self):
        report, calls = self.run_remote("openai", ["malformed", VALID], attempts=2)
        self.assertEqual(report["generation_attempts"], 2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(report["provider_calls_upper_bound"], 2)

    def test_exhaustion_and_partial_scores(self):
        report, calls = self.run_remote(
            "gemini",
            ["invalid"] * 3,
            attempts=3,
            prompts=("v3_structured", "v4_reasoning"),
        )
        self.assertEqual(len(calls), 3)
        self.assertFalse(report["completed"])
        self.assertEqual(report["not_run"], 1)
        self.assertIsNone(report["by_prompt"]["v4_reasoning"]["exact_match"])
        self.assertEqual(report["failed_cases"], 1)

    def test_explicit_continue(self):
        report, calls = self.run_remote(
            "openai",
            ["invalid", VALID],
            prompts=("v3_structured", "v4_reasoning"),
            continue_on_error=True,
        )
        self.assertTrue(report["completed"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(report["failed_cases"], 1)

    def test_execution_gate_no_files_or_key_lookup(self):
        with patch(
            "src.llm.factory.OpenAIProvider",
            side_effect=AssertionError("No key lookup"),
        ):
            for options in ({}, {"execute": True}, {"allow_remote_inference": True}):
                with self.assertRaises(ValueError):
                    execute_plan(self.plan(), **options)
                self.assertFalse(self.output.exists())

    def test_retry_budget_rejected_before_execution(self):
        with self.assertRaises(ValueError):
            prepare_plan(
                DATASET,
                Settings(max_attempts=3),
                ["nubbix-b01"],
                ("v1_zero_shot",),
                self.output,
                all_cases=False,
                max_calls=2,
            )
        self.assertFalse(self.output.exists())

    def test_no_overwrite(self):
        self.output.mkdir()
        with self.assertRaises(ValueError):
            self.plan()

    def test_cli_preview_ignores_config_provider_and_attempts(self):
        argv = [
            "eval",
            "--provider",
            "gemini",
            "--model",
            "fixture",
            "--case-id",
            "nubbix-b01",
            "--prompt",
            "v4_reasoning",
            "--max-calls",
            "1",
            "--output",
            str(self.output),
        ]
        with (
            patch("sys.argv", argv),
            patch(
                "src.llm.factory.GeminiProvider",
                side_effect=AssertionError("No key lookup"),
            ),
            redirect_stdout(StringIO()) as stream,
        ):
            self.assertEqual(main(), 0)
        plan = json.loads(stream.getvalue())
        self.assertEqual(plan["remote_calls_upper_bound"], 1)
        self.assertFalse(self.output.exists())
        with patch("sys.argv", argv + ["--execute"]), redirect_stderr(StringIO()):
            self.assertEqual(main(), 2)
        self.assertFalse(self.output.exists())

    def test_provider_failure_not_retried(self):
        with patch("src.llm.factory.OpenAIProvider") as factory:
            factory.return_value.generate.side_effect = ProviderError(
                "private-error-body"
            )
            report = execute_plan(
                self.plan(attempts=3), execute=True, allow_remote_inference=True
            )
        self.assertEqual(report["generation_attempts"], 1)
        self.assertEqual(report["failed_cases"], 1)
        self.assertNotIn(
            "private-error-body", (self.output / "results.jsonl").read_text()
        )

    def test_configuration_failure_stops_even_with_continue(self):
        with patch(
            "src.llm.factory.GeminiProvider",
            side_effect=ProviderError("Missing fictitious key"),
        ):
            report = execute_plan(
                self.plan(
                    "gemini",
                    prompts=("v3_structured", "v4_reasoning"),
                    continue_on_error=True,
                ),
                execute=True,
                allow_remote_inference=True,
            )
        self.assertEqual(report["generation_attempts"], 0)
        self.assertEqual(report["not_run"], 1)

    def test_ollama_uses_same_service_without_remote_permission(self):
        requests = []

        def transport(request, timeout):
            requests.append(request.full_url)
            if request.full_url.endswith("/api/show"):
                return {"details": {"format": "gguf"}, "capabilities": ["completion"]}
            return {
                "done": True,
                "done_reason": "stop",
                "message": {"role": "assistant", "content": VALID},
            }

        def factory(**options):
            return OllamaProvider(**options, transport=transport)

        with patch("src.llm.factory.OllamaProvider", side_effect=factory):
            report = execute_plan(self.plan("ollama"), execute=True)
        self.assertEqual(len(requests), 2)
        self.assertEqual(report["generation_attempts"], 1)
        self.assertEqual(report["remote_calls_attempted"], 0)

    def test_full_corpus_mock_no_remote_calls(self):
        plan = prepare_plan(
            DATASET,
            Settings(max_attempts=1),
            [],
            ("v3_structured", "v4_reasoning"),
            self.output,
            all_cases=True,
            max_calls=64,
        )
        report = execute_plan(plan, execute=True)
        self.assertTrue(report["completed"])
        self.assertTrue(report["simulated"])
        self.assertEqual(report["remote_calls_attempted"], 0)
        self.assertEqual(report["by_prompt"]["v3_structured"]["exact_match"], 0.25)


if __name__ == "__main__":
    unittest.main()
