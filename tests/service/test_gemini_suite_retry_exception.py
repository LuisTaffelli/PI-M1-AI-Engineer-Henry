"""Excepción Gemini: transportes y esperas falsos, sin claves ni red reales."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError

from evals.adversarial.plan import prepare_plan as paired_plan
from evals.classification.plan import prepare_plan
from evals.run_adversarial_pairs import main as paired_main
from evals.run_provider_evals import main as eval_main
from src.llm.http_retry import parse_retry_after
from src.llm.providers.base import ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.main import main
from src.runtime.config import ROOT, Settings, load_settings
from src.support.http_retry import HttpRetryState
from src.support.service import simulate_response
from tests.service import test_http_retry as fixtures


class GeminiSuiteExceptionTests(unittest.TestCase):
    setUp = fixtures.HttpRetryTests.setUp
    execute = fixtures.HttpRetryTests.execute

    def provider(self, name, replies):
        return GeminiProvider(
            "gemini-3.5-flash-lite",
            api_key=fixtures.KEY,
            transport=Mock(side_effect=replies),
            retry_after_max_delay_seconds=120,
        )

    def settings(self, **changes):
        return Settings(
            **{
                "provider": "gemini",
                "model": "fixture",
                "max_attempts": 1,
                "http_max_attempts": 3,
                "gemini_suite_retry_exception": True,
                "http_retry_max_delay_seconds": 120.0,
                "http_retry_max_total_wait_seconds": 300.0,
                **changes,
            }
        )

    def run_exception(self, replies, **changes):
        settings = self.settings(**changes).model_dump()
        for key in ("provider", "model", "metrics_path", "log_metrics"):
            settings.pop(key)
        return self.execute("gemini", replies, **settings)

    def test_defaults_unchanged_and_exception_scope_validated(self):
        defaults = Settings()
        self.assertFalse(defaults.gemini_suite_retry_exception)
        self.assertEqual(defaults.http_retry_max_delay_seconds, 30)
        self.assertEqual(defaults.http_retry_max_total_wait_seconds, 60)
        for changes in (
            {"provider": "openai"},
            {"provider": "mock"},
            {"provider": "ollama"},
            {"max_attempts": 2},
            {"max_attempts": 3},
            {"http_max_attempts": 4},
            {"http_retry_max_delay_seconds": 120.1},
            {"http_retry_max_total_wait_seconds": 300.1},
            {"gemini_suite_retry_exception": False},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.settings(**changes)

    def test_exception_toml_load_and_main_cli_refuses_it(self):
        config = Path(self.temp.name) / "exception.toml"
        config.write_text(
            'provider="gemini"\nmodel="fixture"\nmax_attempts=1\n'
            "gemini_suite_retry_exception=true\nhttp_max_attempts=3\n"
            "http_retry_max_delay_seconds=120.0\n"
            "http_retry_max_total_wait_seconds=300.0\n"
        )
        self.assertEqual(load_settings(config), self.settings())
        with (
            patch("sys.argv", ["nubbix", "Consulta", "--config", str(config)]),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(main(), 2)

    def test_each_retryable_status_waits_full_120_and_keeps_safe_seconds(self):
        for status in (429, 500, 502, 503, 504):
            provider, metric, error = self.run_exception(
                [fixtures.http_error(status, " 000120 "), fixtures.envelope("gemini")]
            )
            self.assertIsNone(error)
            self.assertEqual(provider._transport.call_count, 2)
            self.sleep.assert_called_with(120)
            event = metric["http_retry_events"][0]
            self.assertEqual(event["retry_after_seconds"], 120)
            self.assertEqual(event["delay_seconds"], 120)
            self.assertTrue(event["retried"])
            self.assertEqual(metric["http_retry_wait_seconds"], 120)

    def test_factory_uses_exception_with_real_adapter_and_fake_transport(self):
        transport = Mock(
            side_effect=[fixtures.http_error(429, "120"), fixtures.envelope("gemini")]
        )
        with (
            patch("src.runtime.environment.load_api_key", return_value=fixtures.KEY),
            patch("src.llm.providers.gemini_provider._post_json", transport),
        ):
            result = simulate_response(
                "Consulta",
                settings=self.settings(log_metrics=True, metrics_path=str(self.path)),
            )
        self.assertEqual(result.category, "billing")
        self.assertEqual(transport.call_count, 2)
        self.sleep.assert_called_once_with(120)
        metric = json.loads(self.path.read_text())
        self.assertEqual(metric["provider"], "gemini")
        self.assertEqual(metric["http_retry_events"][0]["retry_after_seconds"], 120)
        self.assertNotIn(fixtures.KEY, self.path.read_text())

    def test_121_seconds_aborts_and_preserves_value_without_sleep(self):
        provider, metric, error = self.run_exception(
            [fixtures.http_error(429, "000121")]
        )
        self.assertIsInstance(error, ProviderError)
        provider._transport.assert_called_once()
        self.sleep.assert_not_called()
        event = metric["http_retry_events"][0]
        self.assertEqual(event["retry_after_seconds"], 121)
        self.assertEqual(event["stop_reason"], "retry_after_too_long")
        self.assertIsNone(event["delay_seconds"])
        self.assertIsNone(metric["cost_usd"])

    def test_http_dates_round_up_and_preserve_excessive_seconds(self):
        now = datetime(2026, 11, 7, 0, 0, 0, 500000, tzinfo=timezone.utc)
        for value, seconds, state in (
            ("Sat, 07 Nov 2026 00:02:00 GMT", 120, "valid"),
            ("Sat, 07 Nov 2026 00:02:01 GMT", 121, "too_long"),
            ("Saturday, 07-Nov-26 00:02:01 GMT", 121, "too_long"),
            ("Sat Nov  7 00:02:00 2026", 120, "valid"),
        ):
            parsed = parse_retry_after(value, now=now, max_delay_seconds=120)
            self.assertEqual(parsed.state, state)
            self.assertEqual(parsed.requested_seconds, seconds)

    def test_three_attempts_include_first_and_no_fourth_after_240_seconds(self):
        provider, metric, error = self.run_exception(
            [
                fixtures.http_error(429, "120"),
                fixtures.http_error(503, "120"),
                fixtures.http_error(429, "119"),
                fixtures.envelope("gemini"),
            ]
        )
        self.assertIsInstance(error, ProviderError)
        self.assertEqual(provider._transport.call_count, 3)
        self.assertEqual(metric["attempts"], 3)
        self.assertEqual(metric["http_retry_count"], 2)
        self.assertEqual(metric["http_retry_wait_seconds"], 240)
        self.assertEqual(
            metric["http_retry_events"][-1]["stop_reason"], "attempt_limit"
        )
        self.assertEqual(metric["http_retry_events"][-1]["retry_after_seconds"], 119)

    def test_accumulated_budget_boundary_never_clamps_retry_after(self):
        error = ProviderError(
            "fixed",
            code="http_error",
            http_status=429,
            retry_after=parse_retry_after("120", max_delay_seconds=120),
        )
        self.assertEqual(
            HttpRetryState(wait_seconds=180).delay(error, self.settings(), 1), 120
        )
        state = HttpRetryState(wait_seconds=181)
        self.assertIsNone(state.delay(error, self.settings(), 1))
        self.assertEqual(state.events[-1]["stop_reason"], "wait_budget")
        self.assertEqual(state.events[-1]["retry_after_seconds"], 120)
        self.sleep.assert_not_called()

    def test_lower_total_budget_rejects_second_wait_without_early_call(self):
        provider, metric, _ = self.run_exception(
            [
                fixtures.http_error(429, "120"),
                fixtures.http_error(503, "120"),
                fixtures.envelope("gemini"),
            ],
            http_retry_max_total_wait_seconds=200.0,
        )
        self.assertEqual(provider._transport.call_count, 2)
        self.assertEqual(metric["http_retry_wait_seconds"], 120)
        self.assertEqual(metric["http_retry_events"][-1]["stop_reason"], "wait_budget")
        self.sleep.assert_called_once_with(120)

    def test_terminal_and_uncertain_failures_never_retry_under_exception(self):
        for reply, status in (
            (fixtures.http_error(401, "120"), 401),
            (TimeoutError(fixtures.PRIVATE), None),
            ({"status": "incomplete"}, None),
        ):
            provider, metric, error = self.run_exception([reply])
            self.assertIsInstance(error, ProviderError)
            provider._transport.assert_called_once()
            self.assertEqual(metric["failure_http_status"], status)
        self.sleep.assert_not_called()

    def test_full_suite_budgets_and_metadata_offline(self):
        for dataset, diagnostic, bound in (
            ("eval_dataset.jsonl", False, 384),
            ("eval_robustness.jsonl", True, 96),
        ):
            kwargs = dict(all_cases=True, max_calls=bound, diagnostic_suite=diagnostic)
            plan = prepare_plan(
                ROOT / "data" / dataset,
                self.settings(),
                [],
                fixtures.PROMPTS,
                Path(self.temp.name) / "plan",
                **kwargs,
            )
            self.assertEqual(plan.metadata["provider_calls_upper_bound"], bound)
            self.assertEqual(
                plan.metadata["settings"]["http_retry_max_total_wait_seconds"], 300
            )
            with self.assertRaises(ValueError):
                prepare_plan(
                    ROOT / "data" / dataset,
                    self.settings(),
                    [],
                    fixtures.PROMPTS,
                    Path(self.temp.name) / "plan",
                    **{**kwargs, "max_calls": bound - 1},
                )
        plan = paired_plan(
            self.settings(),
            fixtures.PROMPTS,
            Path(self.temp.name) / "pairs",
            max_calls=360,
        )
        self.assertEqual(plan.metadata["provider_calls_upper_bound"], 360)
        with self.assertRaises(ValueError):
            paired_plan(
                self.settings(),
                fixtures.PROMPTS,
                Path(self.temp.name) / "pairs",
                max_calls=359,
            )
        with self.assertRaises(ValueError):
            prepare_plan(
                ROOT / "data/eval_dataset.jsonl",
                self.settings(),
                [],
                fixtures.PROMPTS,
                Path(self.temp.name) / "plan",
                all_cases=True,
                max_calls=384,
                continue_on_error=True,
            )

    def test_cli_flag_sets_limits_and_rejects_non_gemini_without_calls(self):
        for paired, cli in ((False, eval_main), (True, paired_main)):
            for name, expected in (("gemini", 0), ("openai", 2)):
                argv = [
                    "eval",
                    "--provider",
                    name,
                    "--model",
                    "fixture",
                    "--prompt",
                    "v3_structured",
                    "--max-calls",
                    "90" if paired else "3",
                    "--http-max-attempts",
                    "3",
                    "--gemini-suite-retry-exception",
                    "--output",
                    str(Path(self.temp.name) / "plan"),
                ]
                if not paired:
                    argv += ["--case-id", "nubbix-b01"]
                with (
                    patch("sys.argv", argv),
                    redirect_stdout(StringIO()) as stdout,
                    redirect_stderr(StringIO()),
                ):
                    self.assertEqual(cli(), expected)
                if expected == 0:
                    metadata = json.loads(stdout.getvalue())
                    self.assertTrue(
                        metadata["settings"]["gemini_suite_retry_exception"]
                    )
                    self.assertEqual(
                        metadata["settings"]["http_retry_max_delay_seconds"], 120
                    )
                    self.assertEqual(
                        metadata["settings"]["http_retry_max_total_wait_seconds"], 300
                    )

    def test_parser_default_stays_30_and_huge_seconds_are_safe(self):
        parsed = parse_retry_after("31")
        self.assertEqual(parsed.state, "too_long")
        self.assertEqual(parsed.requested_seconds, 31)
        parsed = parse_retry_after("9" * 1000)
        self.assertEqual(len(str(parsed.requested_seconds)), 1000)
        parsed = parse_retry_after("9" * 1001)
        self.assertEqual(parsed.state, "too_long")
        self.assertIsNone(parsed.requested_seconds)
        self.assertEqual(parsed.requested_seconds_digits, 1001)


if __name__ == "__main__":
    unittest.main()
