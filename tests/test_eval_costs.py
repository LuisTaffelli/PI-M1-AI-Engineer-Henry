"""Precios públicos fechados y fixtures sintéticos; sin credenciales ni red."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evals.classification.plan import prepare_plan
from evals.classification.runner import execute_plan
from evals.common.costs import summarize_financials
from evals.reprice_run import reprice
from evals.run_provider_evals import main
from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.usage import TokenUsage, gemini_usage, openai_usage
from src.runtime.config import ROOT, Settings
from src.runtime.pricing import cost_metrics, estimate_attempt, load_catalog

CATALOG = ROOT / "pricing/standard-text-2026-11-05.json"


class EvalCostTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog, _ = load_catalog(CATALOG)
        self.luna, self.gemini = self.catalog.rates
        for name in ("openai", "gemini"):
            blocker = patch(
                f"src.llm.providers.{name}_provider.urlopen",
                side_effect=AssertionError("No network"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)

    def usage(self, **changes):
        data = dict(
            prompt_tokens=12000,
            completion_tokens=100,
            total_tokens=12100,
            cached_prompt_tokens=4000,
            cache_write_tokens=7000,
            cache_write_30m_tokens=3000,
            cache_write_12h_tokens=4000,
            reasoning_tokens=80,
        )
        return TokenUsage(**{**data, **changes})

    def test_public_catalog_and_luna_mixed_cache_lifetimes(self):
        self.assertEqual(self.luna.checked_on, "2026-11-05")
        self.assertEqual(self.gemini.model, "gemini-3.5-flash-lite")
        cost = estimate_attempt(self.usage(), self.luna)
        self.assertEqual(cost, Decimal("0.001565"))
        report = cost_metrics(
            [self.usage()], provider="openai", model="gpt-6-luna", pricing_path=CATALOG
        )
        components = report["cost_components_by_attempt"][0]
        self.assertEqual(sum(map(Decimal, components.values())), cost)
        self.assertEqual(
            Decimal(components["output_including_reasoning_usd"]), Decimal("0.00005")
        )
        self.assertFalse(report["billing_verified"])
        self.assertEqual(report["rate_checked_on"], "2026-11-05")

    def test_missing_inconsistent_cache_or_out_of_scope_is_unknown(self):
        for changes in (
            {"cache_write_tokens": None},
            {"cache_write_30m_tokens": None},
            {"cache_write_12h_tokens": 1},
            {"cached_prompt_tokens": 6000},
            {"reasoning_tokens": 101},
            {"tool_use_prompt_tokens": 1},
            {"prompt_tokens": 272001, "total_tokens": 272101},
        ):
            with self.subTest(changes=changes):
                self.assertIsNone(estimate_attempt(self.usage(**changes), self.luna))
        self.assertEqual(
            estimate_attempt(TokenUsage(0, 0, 0, 0, cache_write_tokens=0), self.luna),
            Decimal(0),
        )

    def test_provider_normalization_retains_components_without_double_count(self):
        usage = openai_usage(
            {
                "input_tokens": 12000,
                "output_tokens": 100,
                "total_tokens": 12100,
                "input_tokens_details": {
                    "cached_tokens": 4000,
                    "cache_write_tokens": 7000,
                    "cache_write_tokens_details": {
                        "ttl_30m_tokens": 3000,
                        "ttl_12h_tokens": 4000,
                    },
                },
                "output_tokens_details": {"reasoning_tokens": 80},
            }
        )
        self.assertEqual(usage, self.usage())
        gemini = gemini_usage(
            {
                "total_input_tokens": 100,
                "total_output_tokens": 10,
                "total_thought_tokens": 20,
                "total_tokens": 130,
                "total_cached_tokens": 40,
                "total_tool_use_tokens": 0,
            }
        )
        self.assertEqual(gemini.completion_tokens, 30)
        self.assertEqual(gemini.reasoning_tokens, 20)
        self.assertEqual(estimate_attempt(gemini, self.gemini), Decimal("0.0000942"))

    def test_financial_totals_distinguish_known_subtotal_and_unknown_total(self):
        usages = [self.usage(), TokenUsage()]
        cost = cost_metrics(
            usages, provider="openai", model="gpt-6-luna", pricing_path=CATALOG
        )
        row = {
            **cost,
            "usage_by_attempt": [usage.__dict__ for usage in usages],
            "simulated": False,
        }
        report = summarize_financials([row])
        self.assertIsNone(report["cost_usd"])
        self.assertEqual(
            Decimal(report["known_estimated_subtotal_usd"]), Decimal("0.001565")
        )
        self.assertIsNone(report["tokens"]["prompt_tokens"]["total"])
        self.assertEqual(report["tokens"]["prompt_tokens"]["reported_subtotal"], 12000)
        self.assertIsNone(summarize_financials([])["cost_usd"])
        row["simulated"] = True
        self.assertIsNone(summarize_financials([row])["known_estimated_subtotal_usd"])

    def test_plan_snapshot_retry_failure_and_summary_costs(self):
        copied = self.root / "catalog.json"
        copied.write_bytes(CATALOG.read_bytes())
        output = self.root / "run"
        settings = Settings(
            provider="openai",
            model="gpt-6-luna",
            max_attempts=2,
            pricing_path=str(copied),
        )
        plan = prepare_plan(
            ROOT / "data/eval_dataset.jsonl",
            settings,
            ["nubbix-b01"],
            ("v3_structured",),
            output,
            all_cases=False,
            max_calls=2,
        )
        copied.write_text("invalid-after-plan")
        answers = iter(
            [
                "invalid-json",
                json.dumps(
                    {
                        "answer": "synthetic",
                        "category": "billing",
                        "confidence": 0.5,
                        "actions": [],
                    }
                ),
            ]
        )

        def transport(request, timeout):
            return {
                "status": "completed",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "total_tokens": 120,
                    "input_tokens_details": {
                        "cached_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                },
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": next(answers)}],
                    }
                ],
            }

        def factory(**options):
            return OpenAIProvider(**options, api_key="fake-key", transport=transport)

        with patch("src.llm.factory.OpenAIProvider", side_effect=factory):
            report = execute_plan(plan, execute=True, allow_remote_inference=True)
        self.assertEqual(report["usage_and_cost"]["generation_attempts"], 2)
        self.assertEqual(
            Decimal(report["usage_and_cost"]["cost_usd"]), Decimal("0.00004")
        )
        self.assertEqual((output / "pricing.json").read_bytes(), CATALOG.read_bytes())
        rows = [
            json.loads(line)
            for line in (output / "results.jsonl").read_text().splitlines()
        ]
        self.assertEqual(rows[0]["pricing_sha256"], plan.metadata["pricing"]["sha256"])
        self.assertEqual(
            report["by_prompt"]["v3_structured"]["usage_and_cost"],
            report["usage_and_cost"],
        )

    def test_cli_default_custom_and_disabled_pricing_without_key_reads(self):
        argv = [
            "eval",
            "--provider",
            "openai",
            "--model",
            "gpt-6-luna",
            "--prompt",
            "v3_structured",
            "--case-id",
            "nubbix-b01",
            "--max-calls",
            "1",
            "--output",
            str(self.root / "preview"),
        ]
        for options, configured in (
            ([], True),
            (["--no-pricing"], False),
            (["--pricing", str(CATALOG)], True),
        ):
            with (
                patch("sys.argv", argv + options),
                patch(
                    "src.runtime.environment.load_api_key",
                    side_effect=AssertionError("No keys"),
                ),
                redirect_stdout(StringIO()) as stream,
            ):
                self.assertEqual(main(), 0)
            metadata = json.loads(stream.getvalue())
            self.assertEqual(metadata["pricing"] is not None, configured)
            self.assertFalse((self.root / "preview").exists())
        with (
            patch("sys.argv", argv + ["--pricing", str(self.root / "missing.json")]),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(main(), 2)
        self.assertFalse((self.root / "preview").exists())

    def test_offline_reprice_preserves_originals_and_old_unknown_writes(self):
        run = self.root / "original"
        run.mkdir()
        (run / "plan.json").write_text(
            json.dumps({"provider": "openai", "model": "gpt-6-luna"})
        )
        raw = {
            "provider": "openai",
            "simulated": False,
            "prompt_version": "v3_structured",
            "attempts": 1,
            "usage_by_attempt": [
                {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                    "cached_prompt_tokens": 0,
                }
            ],
            "private_fixture_field": "do-not-copy",
        }
        source = run / "metrics.jsonl"
        source.write_text(json.dumps(raw) + "\n")
        before = source.read_bytes()
        result = reprice(run, CATALOG, self.root / "repriced")
        self.assertIsNone(result["usage_and_cost"]["cost_usd"])
        self.assertEqual(source.read_bytes(), before)
        self.assertNotIn(
            "do-not-copy", (self.root / "repriced/costs.jsonl").read_text()
        )
        with self.assertRaises(FileExistsError):
            reprice(run, CATALOG, self.root / "repriced")


if __name__ == "__main__":
    unittest.main()
