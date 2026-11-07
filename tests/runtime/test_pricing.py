"""Tarifas ficticias para fixture-model; ningún precio comercial verificado/activo."""

import hashlib
import json
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from pydantic import ValidationError

from src.llm.providers.base import ProviderError
from src.llm.providers.gemini_provider import GeminiProvider
from src.llm.providers.openai_provider import OpenAIProvider
from src.llm.usage import TokenUsage, gemini_usage, openai_usage, summarize_usage
from src.runtime.config import ROOT, Settings
from src.runtime.pricing import PricingCatalog, Rate, cost_metrics, estimate_attempt
from src.support.service import simulate_response

MARKER = "PRIVATE_PRICING_FIXTURE"
KEY = "FAKE_PRICING_KEY"
TEXT = json.dumps(
    {"answer": MARKER, "confidence": 0.6, "category": "billing", "actions": []}
)


def rate_data(provider="openai", **change):
    # Estos números son inventados, no tarifas de OpenAI ni Gemini.
    return {
        "provider": provider,
        "model": "fixture-model",
        "mode": "standard_text",
        "currency": "USD",
        "rate_version": "fixture-only-v1",
        "verification": "fixture",
        "source_url": "https://example.invalid/fixture?token=" + MARKER,
        "input_usd_per_million": "2.00",
        "cached_input_usd_per_million": "0.50",
        "output_usd_per_million": "4.00",
        **change,
    }


def catalog_data(provider="openai", **rate_change):
    return {
        "format_version": 1,
        "catalog_version": "fixture-catalog-v1",
        "rates": [rate_data(provider, **rate_change)],
    }


def reply(provider, text=TEXT, usage=TokenUsage(100, 20, 120, 40)):
    if provider == "openai":
        return {
            "status": "completed",
            "usage": {
                "input_tokens": usage.prompt_tokens,
                "output_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "input_tokens_details": {"cached_tokens": usage.cached_prompt_tokens},
            },
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": text}]}
            ],
        }
    return {
        "status": "completed",
        "usage": {
            "total_input_tokens": usage.prompt_tokens,
            "total_output_tokens": usage.completion_tokens,
            "total_thought_tokens": 0,
            "total_tokens": usage.total_tokens,
            "total_cached_tokens": usage.cached_prompt_tokens,
            "total_tool_use_tokens": 0,
        },
        "steps": [
            {"type": "model_output", "content": [{"type": "text", "text": text}]}
        ],
    }


class PricingTests(unittest.TestCase):
    def setUp(self):
        for name in ("openai_provider", "gemini_provider"):
            blocker = patch(
                "src.llm.providers." + name + ".urlopen",
                side_effect=AssertionError("Network forbidden"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)

    def report(
        self,
        usages,
        *,
        catalog=None,
        provider="openai",
        model="fixture-model",
        allow_fixture=True,
    ):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pricing.json"
            path.write_text(json.dumps(catalog or catalog_data(provider)))
            return cost_metrics(
                usages,
                provider=provider,
                model=model,
                pricing_path=path,
                allow_fixture=allow_fixture,
            )

    def service_records(
        self, name, replies, *, error=None, verification="fixture", pricing_text=None
    ):
        cls = OpenAIProvider if name == "openai" else GeminiProvider
        transport = Mock(side_effect=replies)
        provider = cls("fixture-model", api_key=KEY, transport=transport)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            pricing = Path(directory) / "pricing.json"
            pricing.write_text(
                pricing_text
                if pricing_text is not None
                else json.dumps(catalog_data(name, verification=verification))
            )
            settings = Settings(
                provider=name,
                model="fixture-model",
                max_attempts=2,
                log_metrics=True,
                metrics_path=str(path),
                pricing_path=str(pricing),
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
            for forbidden in (
                MARKER,
                KEY,
                TEXT,
                "example.invalid",
                "input_usd_per_million",
            ):
                self.assertNotIn(forbidden, raw)
            record = json.loads(raw)
            if record["cost_status"] == "pricing_unavailable":
                self.assertIsNone(record["pricing_sha256"])
            else:
                self.assertEqual(
                    record["pricing_sha256"],
                    hashlib.sha256(pricing.read_bytes()).hexdigest(),
                )
            self.assertTrue(record["simulated"])
            return record, transport

    def test_decimal_formula_splits_cached_input_without_double_charging(self):
        rate = Rate(**rate_data())
        self.assertEqual(
            estimate_attempt(TokenUsage(100, 20, 120, 40), rate, allow_fixture=True),
            Decimal("0.000220"),
        )
        self.assertEqual(
            estimate_attempt(TokenUsage(100, 20, 120, 0), rate, allow_fixture=True),
            Decimal("0.000280"),
        )
        self.assertEqual(
            estimate_attempt(TokenUsage(100, 20, 120, 100), rate, allow_fixture=True),
            Decimal("0.000130"),
        )

    def test_fixture_and_unverified_prices_cannot_activate_production_estimates(self):
        usages = [TokenUsage(100, 20, 120, 40)]
        report = self.report(usages, allow_fixture=False)
        self.assertIsNone(report["cost_usd"])
        self.assertEqual(report["cost_status"], "rate_unverified")
        for allow in (True, False):
            report = self.report(
                usages,
                catalog=catalog_data(verification="unverified"),
                allow_fixture=allow,
            )
            self.assertIsNone(report["cost_usd"])
            self.assertEqual(report["cost_status"], "rate_unverified")
        self.assertIsNone(estimate_attempt(usages[0], Rate(**rate_data())))

        # La selección normal del servicio tampoco puede activar el catálogo fixture.
        with TemporaryDirectory() as directory:
            pricing = Path(directory) / "pricing.json"
            path = Path(directory) / "metrics.jsonl"
            pricing.write_text(json.dumps(catalog_data()))
            with (
                patch(
                    "src.runtime.environment.os.environ",
                    {"OPENAI_API_KEY": KEY},
                ),
                patch(
                    "src.llm.providers.openai_provider._post_json",
                    return_value=reply("openai"),
                ) as transport,
            ):
                simulate_response(
                    MARKER,
                    settings=Settings(
                        provider="openai",
                        model="fixture-model",
                        log_metrics=True,
                        metrics_path=str(path),
                        pricing_path=str(pricing),
                    ),
                )
            record = json.loads(path.read_text())
            self.assertIsNone(record["cost_usd"])
            self.assertEqual(record["cost_status"], "rate_unverified")
            transport.assert_called_once()

    def test_versioned_fixture_aggregate_is_exact_and_json_uses_decimal_strings(self):
        report = self.report(
            [TokenUsage(100, 20, 120, 40), TokenUsage(200, 30, 230, 50)]
        )
        self.assertEqual(Decimal(report["cost_usd"]), Decimal("0.000665"))
        self.assertEqual(report["cost_status"], "fixture_estimate")
        self.assertEqual(report["pricing_version"], "fixture-catalog-v1")
        self.assertEqual(report["rate_version"], "fixture-only-v1")
        self.assertEqual(
            sum(map(Decimal, report["cost_by_attempt"])), Decimal(report["cost_usd"])
        )
        self.assertIsInstance(json.loads(json.dumps(report))["cost_usd"], str)

    def test_decimal_precision_does_not_depend_on_ambient_float_or_decimal_context(
        self,
    ):
        usage = TokenUsage(12345678901234567890, 1, 12345678901234567891, 0)
        rate = Rate(
            **rate_data(
                input_usd_per_million="0.123456789012",
                output_usd_per_million="0.000000000001",
            )
        )
        with localcontext() as context:
            context.prec = 80
            expected = (
                Decimal(usage.prompt_tokens) * Decimal("0.123456789012")
                + Decimal("0.000000000001")
            ) / Decimal(1_000_000)
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(
                estimate_attempt(usage, rate, allow_fixture=True), expected
            )

    def test_missing_or_inconsistent_usage_is_unknown_not_zero_or_a_subtotal(self):
        for unknown in (
            TokenUsage(),
            TokenUsage(100, 20, 120),
            TokenUsage(100, 20, 999, 0),
        ):
            report = self.report([unknown])
            self.assertIsNone(report["cost_usd"])
            self.assertEqual(report["cost_status"], "usage_unavailable")
            report = self.report([unknown, TokenUsage(100, 20, 120, 40)])
            self.assertIsNone(report["cost_usd"])
            self.assertEqual(report["cost_status"], "partial")
            self.assertEqual(report["cost_by_attempt"][0], None)
            self.assertEqual(Decimal(report["cost_by_attempt"][1]), Decimal("0.000220"))
        report = self.report([TokenUsage(0, 0, 0, 0)])
        self.assertEqual(Decimal(report["cost_usd"]), Decimal(0))
        self.assertEqual(report["cost_status"], "fixture_estimate")

    def test_invalid_cache_counts_are_unknown_and_do_not_break_valid_token_totals(self):
        for value in (None, True, -1, "40", 1.5, 101):
            for usage in (
                openai_usage(
                    {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "total_tokens": 120,
                        "input_tokens_details": {"cached_tokens": value},
                    }
                ),
                gemini_usage(
                    {
                        "total_input_tokens": 100,
                        "total_output_tokens": 20,
                        "total_tokens": 120,
                        "total_cached_tokens": value,
                        "total_thought_tokens": 0,
                    }
                ),
            ):
                self.assertTrue(usage.complete)
                self.assertIsNone(usage.cached_prompt_tokens)
                self.assertIsNone(self.report([usage])["cost_usd"])
        with self.assertRaises(ValueError):
            TokenUsage(10, 2, 12, 11)
        summary = summarize_usage(
            [TokenUsage(100, 20, 120, 40), TokenUsage(200, 30, 230, 50)]
        )
        self.assertEqual(summary["cached_prompt_tokens"], 90)
        self.assertEqual(summary["prompt_tokens"], 300)
        self.assertEqual(
            summarize_usage([TokenUsage(100, 20, 120, 40), TokenUsage(200, 30, 230)])[
                "cached_prompt_tokens"
            ],
            None,
        )

    def test_catalog_rejects_duplicate_keys_currency_and_unsafe_price_values(self):
        duplicate = catalog_data()
        duplicate["rates"].append(rate_data())
        with self.assertRaises(ValidationError):
            PricingCatalog.model_validate(duplicate)
        for value in (2.0, 2, True, "-1", "1e2", "NaN", "Infinity", "0.1234567890123"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                Rate(**rate_data(input_usd_per_million=value))
        for change in ({"currency": "EUR"}, {"mode": "batch"}, {"extra": MARKER}):
            with self.assertRaises(ValidationError):
                Rate(**rate_data(**change))

    def test_verified_record_requires_source_and_date_but_is_not_an_online_verifier(
        self,
    ):
        # Sólo validar metadatos ficticios del modelo fixture-model; no verificar precios comerciales.
        for change in (
            {},
            {"checked_on": "not-a-date"},
            {
                "checked_on": "2026-11-04",
                "source_url": "https://example.invalid/pricing",
            },
        ):
            with self.assertRaises(ValidationError):
                Rate(**rate_data(verification="verified_public", **change))
        for provider, url in (
            ("openai", "https://developers.openai.com/api/docs/pricing"),
            ("gemini", "https://aistudio.google.com/docs/pricing"),
        ):
            rate = Rate(
                **rate_data(
                    provider,
                    verification="verified_public",
                    checked_on="2026-11-04",
                    source_url=url,
                )
            )
            self.assertEqual(
                estimate_attempt(TokenUsage(100, 20, 120, 40), rate),
                Decimal("0.000220"),
            )

    def test_missing_catalog_or_rate_keeps_null_without_model_alias_fallback(self):
        usages = [TokenUsage(100, 20, 120, 40)]
        self.assertEqual(
            cost_metrics(
                usages, provider="openai", model="fixture-model", pricing_path=None
            )["cost_status"],
            "pricing_unconfigured",
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            report = cost_metrics(
                usages, provider="openai", model="fixture-model", pricing_path=path
            )
            self.assertEqual(report["cost_status"], "pricing_unavailable")
            path.write_text('{"format_version":')
            report = cost_metrics(
                usages, provider="openai", model="fixture-model", pricing_path=path
            )
            self.assertEqual(report["cost_status"], "pricing_unavailable")
            self.assertIsNone(report["cost_usd"])
        for provider, model in (
            ("gemini", "fixture-model"),
            ("openai", "fixture-model-latest"),
        ):
            report = self.report(
                usages, provider=provider, model=model, catalog=catalog_data("openai")
            )
            self.assertEqual(report["cost_status"], "rate_missing")
            self.assertIsNone(report["cost_usd"])

    def test_default_example_is_empty_and_env_paths_are_not_read_as_pricing(self):
        catalog = PricingCatalog.model_validate_json(
            (ROOT / "pricing.example.json").read_bytes()
        )
        self.assertEqual(catalog.rates, [])
        self.assertIsNone(Settings().pricing_path)
        with patch(
            "pathlib.Path.read_bytes", side_effect=AssertionError("Must not read env")
        ):
            report = cost_metrics(
                [TokenUsage(1, 1, 2, 0)],
                provider="openai",
                model="fixture-model",
                pricing_path=Path("not-a-real.env"),
                allow_fixture=True,
            )
        self.assertEqual(report["cost_status"], "pricing_unavailable")
        self.assertEqual(
            cost_metrics(
                [], provider="openai", model="fixture-model", pricing_path=None
            )["cost_status"],
            "not_requested",
        )

    def test_provider_fixtures_and_retry_cost_include_first_invalid_json(self):
        for name in ("openai", "gemini"):
            record, transport = self.service_records(
                name,
                [reply(name, "{"), reply(name, usage=TokenUsage(200, 30, 230, 50))],
            )
            self.assertEqual(record["status"], "ok")
            self.assertEqual(record["cost_status"], "fixture_estimate")
            self.assertEqual(Decimal(record["cost_usd"]), Decimal("0.000665"))
            self.assertEqual(record["cached_prompt_tokens"], 90)
            self.assertEqual(record["total_tokens"], 350)
            self.assertEqual(transport.call_count, 2)

    def test_exhaustion_and_incomplete_responses_still_have_estimated_fixture_cost(
        self,
    ):
        for name in ("openai", "gemini"):
            record, transport = self.service_records(
                name, [reply(name, "{"), reply(name, "{")], error=ValidationError
            )
            self.assertEqual(Decimal(record["cost_usd"]), Decimal("0.000440"))
            self.assertEqual(transport.call_count, 2)
            incomplete = reply(name)
            incomplete["status"] = "incomplete"
            record, transport = self.service_records(
                name, [incomplete], error=ProviderError
            )
            self.assertEqual(Decimal(record["cost_usd"]), Decimal("0.000220"))
            self.assertEqual(transport.call_count, 1)

    def test_unverified_rate_and_missing_cache_do_not_claim_zero_cost(self):
        record, _ = self.service_records(
            "openai", [reply("openai")], verification="unverified"
        )
        self.assertEqual(record["cost_status"], "rate_unverified")
        self.assertIsNone(record["cost_usd"])
        record, _ = self.service_records(
            "gemini", [reply("gemini", usage=TokenUsage(100, 20, 120))]
        )
        self.assertEqual(record["usage_status"], "reported")
        self.assertEqual(record["cost_status"], "usage_unavailable")
        self.assertIsNone(record["cost_usd"])

    def test_invalid_catalog_cannot_mask_support_success_or_original_validation_error(
        self,
    ):
        for name in ("openai", "gemini"):
            record, _ = self.service_records(name, [reply(name)], pricing_text=MARKER)
            self.assertEqual(record["status"], "ok")
            self.assertIsNone(record["cost_usd"])
            self.assertEqual(record["cost_status"], "pricing_unavailable")
            record, transport = self.service_records(
                name,
                [reply(name, "{"), reply(name, "{")],
                error=ValidationError,
                pricing_text=MARKER,
            )
            self.assertEqual(record["failure_code"], "json_invalid")
            self.assertEqual(record["cost_status"], "pricing_unavailable")
            self.assertEqual(transport.call_count, 2)
