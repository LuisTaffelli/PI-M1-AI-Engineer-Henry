"""Consumo de fixtures, nunca medición remota ni estimación de costo."""

import json
import unittest
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.error import URLError

from pydantic import ValidationError

from src.llm.providers.base import GenerationResult, ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.llm.providers.mock_provider import MockProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.usage import TokenUsage, gemini_usage, openai_usage, summarize_usage
from src.runtime.config import Settings
from src.support.guardrails import GuardrailError
from src.support.service import simulate_response

KEY = "FAKE_USAGE_KEY"
MARKER = "PRIVATE_USAGE_FIXTURE"
VALID = json.dumps(
    {"answer": MARKER, "confidence": 0.5, "category": "billing", "actions": []}
)


def envelope(name, text=VALID, counts=(10, 2, 12)):
    if name == "openai":
        data = {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": text}]}
            ],
        }
        if counts is not None:
            data["usage"] = dict(
                zip(("input_tokens", "output_tokens", "total_tokens"), counts)
            )
    else:
        data = {
            "status": "completed",
            "steps": [
                {"type": "model_output", "content": [{"type": "text", "text": text}]}
            ],
        }
        if counts is not None:
            data["usage"] = dict(
                zip(
                    ("total_input_tokens", "total_output_tokens", "total_tokens"),
                    counts,
                )
            )
            data["usage"].update(total_thought_tokens=0, total_tool_use_tokens=0)
    return data


class TokenUsageTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        dotenv = patch(
            "src.runtime.credentials.DOTENV_PATH", Path(directory.name) / ".env"
        )
        dotenv.start()
        self.addCleanup(dotenv.stop)
        for module in ("gemini_provider", "openai_provider"):
            blocker = patch(
                f"src.llm.providers.{module}.urlopen",
                side_effect=AssertionError("Real network forbidden"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)

    def provider(self, name, replies):
        cls = OpenAIProvider if name == "openai" else GeminiProvider
        transport = Mock(side_effect=replies)
        return cls("fixture", api_key=KEY, transport=transport), transport

    def execute(self, name, replies, *, attempts=2, error=None):
        provider, transport = self.provider(name, replies)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            settings = Settings(
                provider=name,
                model="fixture",
                max_attempts=attempts,
                log_metrics=True,
                metrics_path=str(path),
            )
            if error:
                with self.assertRaises(error):
                    simulate_response(MARKER, provider, settings=settings)
            else:
                result = simulate_response(MARKER, provider, settings=settings)
                self.assertEqual(
                    set(result.model_dump()),
                    {"answer", "confidence", "category", "actions"},
                )
            raw = path.read_text()
            for forbidden in (MARKER, KEY, VALID, "raw_secret_field"):
                self.assertNotIn(forbidden, raw)
            record = json.loads(raw)
            self.assertIsNone(record["cost_usd"])
            self.assertTrue(record["simulated"])
            return record, transport

    def test_openai_counts_do_not_double_count_cached_or_reasoning_breakdowns(self):
        raw = {
            "input_tokens": 100,
            "output_tokens": 20,
            "total_tokens": 120,
            "input_tokens_details": {"cached_tokens": 40},
            "output_tokens_details": {"reasoning_tokens": 8},
            "raw_secret_field": MARKER,
        }
        provider, _ = self.provider("openai", [{**envelope("openai"), "usage": raw}])
        result = provider.generate(MARKER, MARKER)
        self.assertIsInstance(result, GenerationResult)
        self.assertEqual(result.usage, TokenUsage(100, 20, 120, 40, reasoning_tokens=8))
        self.assertNotIn(MARKER, repr(result))
        self.assertNotIn("raw_secret_field", repr(result))

    def test_gemini_counts_include_separate_thoughts_but_not_initial_or_cache_again(
        self,
    ):
        # Forma y números del ejemplo Usage de la documentación oficial.
        raw = {
            "total_input_tokens": 7,
            "initial_input_tokens": 999,
            "total_output_tokens": 23,
            "total_thought_tokens": 49,
            "total_tokens": 79,
            "total_cached_tokens": 5,
            "total_tool_use_tokens": 0,
            "raw_secret_field": MARKER,
        }
        provider, _ = self.provider("gemini", [{**envelope("gemini"), "usage": raw}])
        result = provider.generate(MARKER, MARKER)
        self.assertEqual(
            result.usage,
            TokenUsage(7, 72, 79, 5, reasoning_tokens=49, tool_use_prompt_tokens=0),
        )
        self.assertNotIn(MARKER, repr(result))

    def test_zero_is_reported_usage_while_missing_usage_is_not_zero(self):
        for name in ("openai", "gemini"):
            record, _ = self.execute(name, [envelope(name, counts=(0, 0, 0))])
            self.assertEqual(record["usage_status"], "reported")
            self.assertEqual(record["total_tokens"], 0)
            record, _ = self.execute(name, [envelope(name, counts=None)])
            self.assertEqual(record["usage_status"], "unavailable")
            self.assertIsNone(record["total_tokens"])

    def test_bad_usage_never_coerces_booleans_strings_floats_or_negative_counts(self):
        for bad in (True, -1, 1.5, "12", {"raw_secret_field": MARKER}):
            with self.subTest(bad=bad):
                usage = openai_usage(
                    {"input_tokens": bad, "output_tokens": 2, "total_tokens": 12}
                )
                self.assertIsNone(usage.prompt_tokens)
                self.assertFalse(usage.complete)
                report = summarize_usage([usage])
                self.assertEqual(report["usage_status"], "partial")
                self.assertIsNone(report["total_tokens"])
                self.assertNotIn(MARKER, json.dumps(report))
                with self.assertRaises(ValueError):
                    TokenUsage(bad, 2, 12)
        for raw in (None, [], MARKER, {}):
            self.assertEqual(openai_usage(raw), TokenUsage())
            self.assertEqual(gemini_usage(raw), TokenUsage())

    def test_inconsistent_totals_and_unknown_gemini_breakdown_remain_partial(self):
        for usage in (
            openai_usage({"input_tokens": 10, "output_tokens": 2, "total_tokens": 99}),
            gemini_usage(
                {"total_input_tokens": 10, "total_output_tokens": 2, "total_tokens": 99}
            ),
            gemini_usage(
                {
                    "total_input_tokens": 10,
                    "total_output_tokens": 2,
                    "total_thought_tokens": 3,
                    "total_tokens": 12,
                }
            ),
            gemini_usage(
                {
                    "total_input_tokens": 10,
                    "total_output_tokens": 2,
                    "total_thought_tokens": 0,
                    "total_tool_use_tokens": 1,
                    "total_tokens": 13,
                }
            ),
        ):
            summary = summarize_usage([usage])
            self.assertEqual(summary["usage_status"], "partial")
            self.assertIsNone(summary["total_tokens"])
            self.assertEqual(summary["usage_by_attempt"], [asdict(usage)])

    def test_retry_sums_invalid_json_and_success_for_both_providers(self):
        for name in ("openai", "gemini"):
            record, transport = self.execute(
                name,
                [envelope(name, "{", (10, 2, 12)), envelope(name, VALID, (20, 4, 24))],
            )
            self.assertEqual(transport.call_count, 2)
            self.assertEqual(record["status"], "ok")
            self.assertEqual(
                (
                    record["prompt_tokens"],
                    record["completion_tokens"],
                    record["total_tokens"],
                ),
                (30, 6, 36),
            )
            self.assertEqual(record["usage_status"], "reported")
            self.assertEqual(
                record["usage_by_attempt"],
                [
                    asdict(
                        TokenUsage(
                            10, 2, 12, reasoning_tokens=0, tool_use_prompt_tokens=0
                        )
                    )
                    if name == "gemini"
                    else asdict(TokenUsage(10, 2, 12)),
                    asdict(
                        TokenUsage(
                            20, 4, 24, reasoning_tokens=0, tool_use_prompt_tokens=0
                        )
                    )
                    if name == "gemini"
                    else asdict(TokenUsage(20, 4, 24)),
                ],
            )

    def test_exhaustion_keeps_usage_from_every_invalid_json_or_contract_response(self):
        for name in ("openai", "gemini"):
            for text in ("{", json.dumps({"answer": "invalid"})):
                record, transport = self.execute(
                    name,
                    [
                        envelope(name, text, (10, 2, 12)),
                        envelope(name, text, (20, 4, 24)),
                    ],
                    error=ValidationError,
                )
                self.assertEqual(transport.call_count, 2)
                self.assertEqual(record["status"], "invalid_response")
                self.assertEqual(record["total_tokens"], 36)

    def test_missing_usage_on_one_attempt_cannot_look_like_a_complete_total(self):
        for name in ("openai", "gemini"):
            record, _ = self.execute(
                name, [envelope(name, "{", None), envelope(name, VALID, (20, 4, 24))]
            )
            self.assertEqual(record["usage_status"], "partial")
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                self.assertIsNone(record[field])
            self.assertEqual(
                record["usage_by_attempt"][1],
                asdict(
                    TokenUsage(20, 4, 24, reasoning_tokens=0, tool_use_prompt_tokens=0)
                )
                if name == "gemini"
                else asdict(TokenUsage(20, 4, 24)),
            )

    def test_incomplete_provider_response_preserves_usage_on_error_without_retry(self):
        for name in ("openai", "gemini"):
            reply = envelope(name)
            reply["status"] = "incomplete"
            record, transport = self.execute(
                name, [reply], attempts=3, error=ProviderError
            )
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(record["status"], "provider_error")
            self.assertEqual(record["usage_status"], "reported")
            self.assertEqual(record["total_tokens"], 12)

    def test_transport_failure_after_parsing_retry_is_unknown_not_free(self):
        for name in ("openai", "gemini"):
            record, transport = self.execute(
                name, [envelope(name, "{"), URLError(MARKER)], error=ProviderError
            )
            self.assertEqual(transport.call_count, 2)
            self.assertEqual(record["usage_status"], "partial")
            self.assertIsNone(record["total_tokens"])
            self.assertEqual(record["usage_by_attempt"][0]["total_tokens"], 12)
            self.assertIsNone(record["usage_by_attempt"][1]["total_tokens"])

    def test_output_guardrail_rejection_still_records_reported_usage(self):
        text = json.dumps(
            {
                "answer": "password=" + MARKER,
                "confidence": 0.5,
                "category": "billing",
                "actions": [],
            }
        )
        for name in ("openai", "gemini"):
            record, transport = self.execute(
                name, [envelope(name, text)], error=GuardrailError
            )
            self.assertEqual(transport.call_count, 1)
            self.assertEqual(record["status"], "rejected_output")
            self.assertEqual(record["total_tokens"], 12)

    def test_append_and_missing_usage_do_not_reuse_a_previous_requests_counts(self):
        for name in ("openai", "gemini"):
            provider, transport = self.provider(
                name, [envelope(name), envelope(name, counts=None)]
            )
            with TemporaryDirectory() as directory:
                path = Path(directory) / "metrics.jsonl"
                settings = Settings(
                    provider=name,
                    model="fixture",
                    log_metrics=True,
                    metrics_path=str(path),
                )
                simulate_response(MARKER, provider, settings=settings)
                first = path.read_bytes()
                simulate_response(MARKER, provider, settings=settings)
                self.assertTrue(path.read_bytes().startswith(first))
                records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(records[0]["total_tokens"], 12)
            self.assertIsNone(records[1]["total_tokens"])
            self.assertEqual(records[1]["usage_status"], "unavailable")
            self.assertEqual(transport.call_count, 2)

    def test_mock_has_no_usage_and_missing_key_has_no_attempts(self):
        result = MockProvider().generate(MARKER, MARKER)
        self.assertEqual(result.usage, TokenUsage())
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            with (
                patch("src.llm.providers.gemini_provider.os.environ", {}),
                self.assertRaises(ProviderError),
            ):
                simulate_response(
                    MARKER,
                    settings=Settings(
                        provider="gemini",
                        model="fixture",
                        log_metrics=True,
                        metrics_path=str(path),
                    ),
                )
            record = json.loads(path.read_text())
        self.assertEqual(record["attempts"], 0)
        self.assertEqual(record["usage_status"], "not_requested")
        self.assertEqual(record["usage_by_attempt"], [])
        self.assertEqual(summarize_usage([])["usage_status"], "not_requested")
