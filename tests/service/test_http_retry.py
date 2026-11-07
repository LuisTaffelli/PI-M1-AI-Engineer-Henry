"""Retries simulados: red, credenciales y sleeps reales bloqueados."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from datetime import datetime, timezone
from email.message import Message
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from pydantic import ValidationError

from evals.adversarial.plan import prepare_plan as paired_plan
from evals.classification.plan import prepare_plan
from evals.run_adversarial_pairs import main as paired_main
from evals.run_provider_evals import main as eval_main
from src.llm.http_retry import RetryAfter, parse_retry_after
from src.llm.providers.base import ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.main import main
from src.runtime.config import ROOT, Settings
from src.support.service import simulate_response

KEY = "FAKE_HTTP_RETRY_KEY"
PRIVATE = "PRIVATE_ERROR_URL_REASON_HEADER_BODY_QUERY"
VALID = json.dumps(
    {
        "answer": "Revisar cargos.",
        "confidence": 0.7,
        "category": "billing",
        "actions": [],
    }
)
PROMPTS = ("v1_zero_shot", "v2_few_shot", "v3_structured", "v4_reasoning")


class UnreadableBody(BytesIO):
    def read(self, *args, **kwargs):
        raise AssertionError("No se debe leer el cuerpo de un error HTTP.")


def http_error(status=429, retry_after=None):
    headers = Message()
    headers["X-Private"] = PRIVATE
    if retry_after is not None:
        headers["retry-after"] = retry_after
    return HTTPError(
        "https://fixture.invalid/" + PRIVATE,
        status,
        PRIVATE,
        headers,
        UnreadableBody(PRIVATE.encode()),
    )


def envelope(provider, text=VALID):
    if provider == "openai":
        return {
            "status": "completed",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 2,
                "total_tokens": 12,
                "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0},
            },
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": text}]}
            ],
        }
    return {
        "status": "completed",
        "usage": {
            "total_input_tokens": 10,
            "total_output_tokens": 2,
            "total_tokens": 12,
            "total_thought_tokens": 0,
            "total_tool_use_tokens": 0,
            "total_cached_tokens": 0,
        },
        "steps": [
            {"type": "model_output", "content": [{"type": "text", "text": text}]}
        ],
    }


class RetryAfterTests(unittest.TestCase):
    def test_delta_seconds_and_leading_zeroes(self):
        for value, seconds in (("0", 0), (" 5 ", 5), ("30", 30), ("0002", 2)):
            with self.subTest(value=value):
                self.assertEqual(parse_retry_after(value), RetryAfter("valid", seconds))

    def test_long_delays_are_rejected_not_clamped(self):
        for value in ("31", "60", "86400", "9" * 1000, "000031"):
            self.assertEqual(parse_retry_after(value), RetryAfter("too_long"))

    def test_http_dates_future_past_and_rounding(self):
        now = datetime(2026, 11, 6, 12, 0, 0, 500000, tzinfo=timezone.utc)
        for value, expected in (
            ("Fri, 06 Nov 2026 12:00:10 GMT", RetryAfter("valid", 10)),
            ("Fri, 06 Nov 2026 12:00:30 GMT", RetryAfter("valid", 30)),
            ("Fri, 06 Nov 2026 11:59:59 GMT", RetryAfter("valid", 0)),
            ("Fri, 06 Nov 2026 12:00:31 GMT", RetryAfter("too_long")),
            ("Fri, 06 Nov 2026 12:00:10", RetryAfter("invalid")),
        ):
            self.assertEqual(parse_retry_after(value, now=now), expected)

    def test_obsolete_http_dates_use_gmt_including_asctime_without_zone(self):
        now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
        for text, expected in (
            ("Fri Nov  6 12:00:20 2026", RetryAfter("valid", 20)),
            ("Fri Nov  6 12:02:00 2026", RetryAfter("too_long")),
            ("Friday, 06-Nov-26 12:00:20 GMT", RetryAfter("valid", 20)),
            ("Friday, 06-Nov-26 12:02:00 GMT", RetryAfter("too_long")),
        ):
            self.assertEqual(parse_retry_after(text, now=now), expected)

    def test_rfc850_two_digit_year_uses_http_fifty_year_window(self):
        now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            parse_retry_after("Thursday, 06-Nov-70 12:02:00 GMT", now=now),
            RetryAfter("too_long"),
        )
        self.assertEqual(
            parse_retry_after("Saturday, 06-Nov-77 12:02:00 GMT", now=now),
            RetryAfter("valid", 0),
        )
        # También cruza de siglo, sin el corte fijo de email.utils.
        self.assertEqual(
            parse_retry_after(
                "Friday, 06-Nov-26 12:02:00 GMT",
                now=datetime(1990, 11, 6, 12, 0, tzinfo=timezone.utc),
            ),
            RetryAfter("too_long"),
        )

    def test_missing_and_invalid_values_do_not_escape(self):
        self.assertEqual(parse_retry_after(None), RetryAfter())
        for value in (
            "",
            "-1",
            "+5",
            "1.5",
            "nan",
            "inf",
            "1, 2",
            PRIVATE,
            True,
            12,
            [],
            "x" * 1000,
        ):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(parse_retry_after(value), RetryAfter("invalid"))

    def test_retry_after_value_object_is_bounded(self):
        for state, value in (
            (PRIVATE, None),
            ("valid", None),
            ("valid", True),
            ("valid", -1),
            ("valid", 31),
            ("valid", float("nan")),
            ("valid", float("inf")),
            ("invalid", 5),
        ):
            with self.subTest(state=state), self.assertRaises(ValueError):
                RetryAfter(state, value)
        self.assertEqual(
            ProviderError("fixed", retry_after=RetryAfter("valid", 5)).retry_after,
            RetryAfter(),
        )


class HttpRetryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "metrics.jsonl"
        for target in (
            "src.runtime.environment.load_api_key",
            "src.llm.providers.openai_provider.urlopen",
            "src.llm.providers.gemini_provider.urlopen",
            "src.llm.providers.ollama_provider.build_opener",
        ):
            blocker = patch(target, side_effect=AssertionError("No keys or network"))
            blocker.start()
            self.addCleanup(blocker.stop)
        sleeper = patch("src.support.http_retry.sleep")
        self.sleep = sleeper.start()
        self.addCleanup(sleeper.stop)
        jitter = patch("src.support.http_retry.uniform", return_value=0.25)
        jitter.start()
        self.addCleanup(jitter.stop)

    def provider(self, name, replies):
        cls = OpenAIProvider if name == "openai" else GeminiProvider
        return cls(
            "gpt-6-luna" if name == "openai" else "gemini-3.5-flash-lite",
            api_key=KEY,
            transport=Mock(side_effect=replies),
        )

    def execute(self, name, replies, **settings):
        provider = self.provider(name, replies)
        error = None
        try:
            simulate_response(
                PRIVATE,
                provider,
                settings=Settings(
                    provider=name,
                    model=provider.model,
                    max_attempts=settings.pop("max_attempts", 1),
                    http_max_attempts=settings.pop("http_max_attempts", 3),
                    log_metrics=True,
                    metrics_path=str(self.path),
                    **settings,
                ),
            )
        except ValueError as failure:
            error = failure
        raw = self.path.read_text()
        for secret in (KEY, PRIVATE, "fixture.invalid", "Revisar cargos"):
            self.assertNotIn(secret, raw)
        return provider, json.loads(raw.splitlines()[-1]), error

    def test_both_providers_retry_429_and_keep_identical_request(self):
        for name in ("openai", "gemini"):
            failure = http_error(429, "5")
            provider, metric, error = self.execute(name, [failure, envelope(name)])
            self.assertIsNone(error)
            self.assertEqual(metric["status"], "ok")
            self.assertEqual(metric["attempts"], 2)
            self.assertEqual(metric["http_retry_count"], 1)
            self.assertEqual(metric["http_retry_wait_seconds"], 5)
            self.assertIsNone(metric["failure_http_status"])
            self.assertIsNone(metric["failure_code"])
            first, second = provider._transport.call_args_list
            self.assertEqual(first.args[0].data, second.args[0].data)
            self.assertTrue(failure.fp.closed)
            self.sleep.assert_called_with(5)

    def test_all_retryable_http_statuses_recover(self):
        for name in ("openai", "gemini"):
            for status in (429, 500, 502, 503, 504):
                provider, metric, error = self.execute(
                    name, [http_error(status, "0"), envelope(name)]
                )
                self.assertIsNone(error)
                self.assertEqual(provider._transport.call_count, 2)
                self.assertEqual(metric["http_retry_count"], 1)
        self.sleep.assert_not_called()

    def test_non_retryable_statuses_are_terminal(self):
        for status in (400, 401, 403, 404, 408, 409, 422, 501, 505, 599):
            provider, metric, error = self.execute("openai", [http_error(status, "5")])
            self.assertIsInstance(error, ProviderError)
            self.assertEqual(metric["failure_http_status"], status)
            self.assertEqual(
                metric["http_retry_events"][-1]["stop_reason"], "status_not_retryable"
            )
            provider._transport.assert_called_once()
        self.sleep.assert_not_called()

    def test_default_is_disabled_and_direct_adapter_never_retries(self):
        self.assertEqual(Settings().http_max_attempts, 1)
        for name in ("openai", "gemini"):
            provider, metric, _ = self.execute(
                name, [http_error()], http_max_attempts=1
            )
            provider._transport.assert_called_once()
            self.assertEqual(metric["http_retry_count"], 0)
            self.assertEqual(metric["http_retry_events"][0]["stop_reason"], "disabled")
            provider = self.provider(name, [http_error()])
            with self.assertRaises(ProviderError):
                provider.generate("instructions", "query")
            provider._transport.assert_called_once()
        self.sleep.assert_not_called()

    def test_missing_invalid_header_backoff_jitter_and_exhaustion(self):
        provider, metric, error = self.execute(
            "gemini", [http_error(), http_error(503, PRIVATE), http_error()]
        )
        self.assertIsInstance(error, ProviderError)
        self.assertEqual(provider._transport.call_count, 3)
        self.assertEqual(
            [call.args[0] for call in self.sleep.call_args_list], [1.25, 2.25]
        )
        self.assertEqual(metric["http_retry_wait_seconds"], 3.5)
        self.assertEqual(metric["http_retry_count"], 2)
        self.assertEqual(
            metric["http_retry_events"][-1]["stop_reason"], "attempt_limit"
        )

    def test_excessive_or_lower_configured_delay_aborts_without_clamping(self):
        for header, settings, reason in (
            ("31", {}, "retry_after_too_long"),
            ("5", {"http_retry_max_delay_seconds": 4.0}, "delay_limit"),
            (None, {"http_retry_max_delay_seconds": 0.5}, "delay_limit"),
        ):
            provider, metric, _ = self.execute(
                "gemini", [http_error(429, header)], **settings
            )
            provider._transport.assert_called_once()
            self.assertEqual(metric["http_retry_events"][-1]["stop_reason"], reason)
        self.sleep.assert_not_called()

    def test_total_wait_budget_is_shared_across_json_repair_rounds(self):
        _, metric, error = self.execute(
            "openai",
            [
                http_error(429, "30"),
                envelope("openai", "invalid"),
                http_error(503, "30"),
                envelope("openai", "invalid"),
                http_error(429, "1"),
            ],
            max_attempts=3,
        )
        self.assertIsInstance(error, ProviderError)
        self.assertEqual(metric["attempts"], 5)
        self.assertEqual(metric["http_retry_count"], 2)
        self.assertEqual(metric["http_retry_wait_seconds"], 60)
        self.assertEqual(metric["http_retry_events"][-1]["stop_reason"], "wait_budget")
        self.assertEqual(len(self.sleep.call_args_list), 2)

    def test_http_retries_do_not_use_up_json_repair_or_change_its_feedback(self):
        provider, metric, error = self.execute(
            "gemini",
            [
                http_error(429, "0"),
                envelope("gemini", "invalid"),
                http_error(503, "0"),
                envelope("gemini"),
            ],
            max_attempts=2,
            http_max_attempts=2,
        )
        self.assertIsNone(error)
        self.assertEqual(metric["attempts"], 4)
        self.assertEqual(metric["http_retry_count"], 2)
        bodies = [
            json.loads(call.args[0].data) for call in provider._transport.call_args_list
        ]
        self.assertEqual(bodies[0], bodies[1])
        self.assertEqual(bodies[2], bodies[3])
        self.assertNotEqual(
            bodies[1]["system_instruction"], bodies[2]["system_instruction"]
        )
        self.assertTrue(all(body["input"] == PRIVATE for body in bodies))

    def test_uncertain_transport_and_response_failures_never_retry(self):
        for name in ("openai", "gemini"):
            for reply, code in (
                (URLError(PRIVATE), "transport_error"),
                (TimeoutError(PRIVATE), "transport_error"),
                (json.JSONDecodeError("fixed", PRIVATE, 0), "http_json_invalid"),
                ({"status": "incomplete"}, "incomplete_response"),
                ([], "invalid_envelope"),
            ):
                provider, metric, _ = self.execute(name, [reply], max_attempts=3)
                provider._transport.assert_called_once()
                self.assertEqual(metric["failure_code"], code)
                self.assertEqual(metric["http_retry_count"], 0)
        self.sleep.assert_not_called()

    def test_failed_http_attempt_keeps_unknown_usage_and_cost(self):
        _, metric, error = self.execute(
            "openai",
            [http_error(503, "0"), envelope("openai")],
            pricing_path=str(ROOT / "pricing/standard-text-2026-11-05.json"),
        )
        self.assertIsNone(error)
        self.assertEqual(metric["usage_status"], "partial")
        self.assertEqual(len(metric["usage_by_attempt"]), 2)
        self.assertIsNone(metric["total_tokens"])
        self.assertIsNone(metric["cost_usd"])
        self.assertEqual(metric["cost_status"], "partial")
        self.assertIsNone(metric["cost_by_attempt"][0])
        self.assertIsNotNone(metric["cost_by_attempt"][1])

    def test_rejected_input_has_no_retry_or_usage(self):
        provider = self.provider("openai", [])
        with self.assertRaises(ValueError):
            simulate_response(
                "x" * 501,
                provider,
                settings=Settings(
                    provider="openai",
                    model="fixture",
                    http_max_attempts=3,
                    log_metrics=True,
                    metrics_path=str(self.path),
                ),
            )
        metric = json.loads(self.path.read_text())
        self.assertEqual(metric["attempts"], 0)
        self.assertEqual(metric["http_retry_count"], 0)
        self.assertEqual(metric["http_retry_events"], [])
        provider._transport.assert_not_called()
        self.sleep.assert_not_called()

    def test_cli_opt_in_recovers_with_fake_transport(self):
        provider = self.provider("openai", [http_error(429, "0"), envelope("openai")])
        with (
            patch("src.llm.factory.OpenAIProvider", return_value=provider),
            patch(
                "sys.argv",
                [
                    "nubbix",
                    "Consulta",
                    "--provider",
                    "openai",
                    "--model",
                    "fixture",
                    "--http-max-attempts",
                    "2",
                    "--no-metrics",
                ],
            ),
            redirect_stdout(StringIO()) as stdout,
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(main(), 0)
        self.assertEqual(json.loads(stdout.getvalue())["category"], "billing")
        self.assertEqual(provider._transport.call_count, 2)

    def test_settings_reject_values_above_fixed_caps(self):
        for options in (
            {"http_max_attempts": 0},
            {"http_max_attempts": 4},
            {"http_max_attempts": True},
            {"http_max_attempts": 2.0},
            {"http_retry_max_delay_seconds": 30.1},
            {"http_retry_max_delay_seconds": -1.0},
            {"http_retry_max_total_wait_seconds": 60.1},
            {"http_retry_max_total_wait_seconds": float("nan")},
        ):
            with self.subTest(options=options), self.assertRaises(ValidationError):
                Settings(**options)

    def test_classification_budget_multiplies_http_and_repair_attempts(self):
        output = Path(self.temp.name) / "plan"
        settings = Settings(
            provider="openai", model="fixture", max_attempts=3, http_max_attempts=3
        )
        for budget in (3, 8):
            with self.assertRaises(ValueError):
                prepare_plan(
                    ROOT / "data/eval_dataset.jsonl",
                    settings,
                    ["nubbix-b01"],
                    ("v3_structured",),
                    output,
                    all_cases=False,
                    max_calls=budget,
                )
        plan = prepare_plan(
            ROOT / "data/eval_dataset.jsonl",
            settings,
            ["nubbix-b01"],
            ("v3_structured",),
            output,
            all_cases=False,
            max_calls=9,
        )
        self.assertEqual(plan.metadata["provider_calls_upper_bound"], 9)
        self.assertEqual(plan.metadata["settings"]["http_max_attempts"], 3)
        self.assertFalse(output.exists())

    def test_paired_budget_multiplies_http_but_not_json_repairs(self):
        output = Path(self.temp.name) / "plan"
        settings = Settings(
            provider="gemini", model="fixture", max_attempts=3, http_max_attempts=3
        )
        with self.assertRaises(ValueError):
            paired_plan(settings, PROMPTS, output, max_calls=120)
        plan = paired_plan(settings, PROMPTS, output, max_calls=360)
        self.assertEqual(plan.settings.max_attempts, 1)
        self.assertEqual(plan.metadata["planned_service_calls"], 120)
        self.assertEqual(plan.metadata["provider_calls_upper_bound"], 360)
        local = paired_plan(
            Settings(http_max_attempts=3), PROMPTS, output, max_calls=120
        )
        self.assertEqual(local.metadata["provider_calls_upper_bound"], 120)
        self.assertEqual(local.metadata["remote_calls_upper_bound"], 0)
        self.assertFalse(output.exists())

    def test_preview_cli_exposes_retry_configuration_without_calls(self):
        for paired, cli in ((False, eval_main), (True, paired_main)):
            argv = [
                "eval",
                "--provider",
                "gemini",
                "--model",
                "fixture",
                "--prompt",
                "v3_structured",
                "--max-calls",
                "90" if paired else "3",
                "--http-max-attempts",
                "3",
                "--output",
                str(Path(self.temp.name) / "plan"),
            ]
            if not paired:
                argv += ["--case-id", "nubbix-b01"]
            with patch("sys.argv", argv), redirect_stdout(StringIO()) as stdout:
                self.assertEqual(cli(), 0)
            metadata = json.loads(stdout.getvalue())
            self.assertEqual(metadata["http_max_attempts_per_generation"], 3)
            self.assertEqual(
                metadata["provider_calls_upper_bound"], 90 if paired else 3
            )

    def test_last_provider_error_returns_exit_two_despite_complete_coverage(self):
        for fail_configuration in (False, True):
            output = Path(self.temp.name) / ("config" if fail_configuration else "http")
            plan = paired_plan(
                Settings(provider="openai", model="fixture"),
                ("v3_structured",),
                output,
                max_calls=30,
            )
            plan = replace(
                plan,
                jobs=plan.jobs[:1],
                metadata={**plan.metadata, "planned_service_calls": 1},
            )
            provider = self.provider(
                "openai", [] if fail_configuration else [http_error(503)]
            )
            factory = (
                patch(
                    "src.llm.factory.OpenAIProvider", side_effect=ProviderError("fixed")
                )
                if fail_configuration
                else patch("src.llm.factory.OpenAIProvider", return_value=provider)
            )
            with (
                patch("evals.cli.adversarial.prepare_plan", return_value=plan),
                factory,
                patch(
                    "sys.argv",
                    [
                        "pairs",
                        "--provider",
                        "openai",
                        "--model",
                        "fixture",
                        "--prompt",
                        "v3_structured",
                        "--max-calls",
                        "30",
                        "--output",
                        str(output),
                        "--execute",
                        "--allow-remote-inference",
                    ],
                ),
                redirect_stdout(StringIO()) as stdout,
                redirect_stderr(StringIO()),
            ):
                self.assertEqual(paired_main(), 2)
            execution = json.loads(stdout.getvalue())["execution"]
            self.assertTrue(execution["completed"])
            self.assertEqual(execution["failed_provider_cases"], 1)


if __name__ == "__main__":
    unittest.main()
