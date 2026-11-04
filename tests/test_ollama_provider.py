"""Ollama con transporte falso: sin modelos reales, cloud, claves o descargas."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request

from pydantic import ValidationError

from evals.run_evals import Case, evaluate
from src.llm.providers.base import ProviderError
from src.llm.providers.ollama_provider import (
    OllamaProvider,
    _NoRedirect,
    _post_json,
    normalize_base_url,
)
from src.llm.usage import TokenUsage, ollama_usage
from src.main import main
from src.runtime.config import Settings
from src.support.schemas import SupportResponse
from src.support.service import simulate_response

INFO = {"details": {"format": "gguf"}, "capabilities": ["completion"]}
MARKER = "PRIVATE_LOCAL_FIXTURE"
TEXT = json.dumps(
    {"answer": MARKER, "confidence": 0.7, "category": "billing", "actions": []}
)


def reply(text=TEXT, **change):
    return {
        "done": True,
        "done_reason": "stop",
        "message": {"role": "assistant", "content": text},
        "prompt_eval_count": 30,
        "eval_count": 10,
        **change,
    }


class OllamaProviderTests(unittest.TestCase):
    def setUp(self):
        blocker = patch(
            "src.llm.providers.ollama_provider.build_opener",
            side_effect=AssertionError("Real network forbidden"),
        )
        self.builder = blocker.start()
        self.addCleanup(blocker.stop)

    def test_local_request_schema_options_and_normalized_usage(self):
        transport = Mock(side_effect=[INFO, reply()])
        provider = OllamaProvider(
            "fixture-local",
            transport=transport,
            response_schema=SupportResponse.model_json_schema(),
        )
        result = provider.generate("Instrucciones", MARKER)
        self.assertEqual(result.text, TEXT)
        self.assertEqual(result.usage, TokenUsage(30, 10, 40))
        show, chat = [call.args[0] for call in transport.call_args_list]
        self.assertEqual(show.full_url, "http://127.0.0.1:11434/api/show")
        self.assertEqual(chat.full_url, "http://127.0.0.1:11434/api/chat")
        payload = json.loads(chat.data)
        self.assertEqual(payload["format"], SupportResponse.model_json_schema())
        self.assertFalse(payload["stream"])
        self.assertEqual(
            payload["messages"],
            [
                {"role": "system", "content": "Instrucciones"},
                {"role": "user", "content": MARKER},
            ],
        )
        self.assertEqual(
            payload["options"], {"temperature": 0, "num_predict": 256, "num_ctx": 2048}
        )
        self.assertNotIn("tools", payload)
        self.assertFalse(
            any(
                key.lower() in {"authorization", "x-goog-api-key"}
                for key, _ in chat.header_items()
            )
        )
        self.assertEqual([c.args[1] for c in transport.call_args_list], [10, 120])

    def test_loopback_urls_only_and_no_cloud_tags_before_any_transport(self):
        self.assertEqual(
            normalize_base_url("http://localhost:11434/"), "http://127.0.0.1:11434"
        )
        self.assertEqual(normalize_base_url("http://[::1]:11434"), "http://[::1]:11434")
        for url in (
            "https://ollama.com",
            "http://192.168.0.2:11434",
            "http://127.0.0.1:11434@external.invalid:80",
            "http://127.0.0.1:11434/api",
            "http://127.0.0.1:11434?key=fake",
            "http://127.0.0.1",
            "http://user:pass@127.0.0.1:11434",
            "http://127.0.0.1:65536",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                OllamaProvider("fixture-local", base_url=url)
        transport = Mock()
        with self.assertRaises(ProviderError):
            OllamaProvider("fixture:cloud", transport=transport)
        transport.assert_not_called()

    def test_remote_unknown_or_non_generative_model_never_reaches_chat(self):
        for info in (
            None,
            {},
            {**INFO, "remote_host": "https://ollama.com"},
            {**INFO, "remote_model": "fixture-remote"},
            {"details": {"format": ""}, "capabilities": ["completion"]},
            {**INFO, "capabilities": None},
            {**INFO, "capabilities": ["embedding"]},
        ):
            transport = Mock(return_value=info)
            with self.subTest(info=info), self.assertRaises(ProviderError) as caught:
                OllamaProvider("fixture-local", transport=transport).generate(
                    MARKER, MARKER
                )
            self.assertEqual(caught.exception.code, "local_model_required")
            transport.assert_called_once()
            self.assertEqual(
                transport.call_args.args[0].full_url, "http://127.0.0.1:11434/api/show"
            )

    def test_resource_limits_rejected_in_settings_and_direct_construction(self):
        for change in (
            {"max_output_tokens": -1},
            {"num_ctx": 0},
            {"timeout_seconds": float("inf")},
            {"timeout_seconds": True},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                OllamaProvider("fixture-local", **change)
        for change in (
            {"ollama_max_output_tokens": -1},
            {"ollama_num_ctx": 0},
            {"ollama_timeout_seconds": 0},
            {"ollama_base_url": "https://ollama.com"},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                Settings(provider="ollama", model="fixture-local", **change)
        with self.assertRaises(ValidationError):
            Settings(provider="ollama")

    def test_http_network_errors_are_sanitized_closed_and_not_retried(self):
        for error in (
            HTTPError(
                "http://127.0.0.1:11434/api/show",
                404,
                MARKER,
                {},
                BytesIO(MARKER.encode()),
            ),
            URLError(MARKER),
            TimeoutError(MARKER),
        ):
            transport = Mock(side_effect=error)
            with self.assertRaises(ProviderError) as caught:
                simulate_response(
                    MARKER,
                    OllamaProvider("fixture-local", transport=transport),
                    settings=Settings(
                        provider="ollama", model="fixture-local", max_attempts=3
                    ),
                )
            self.assertNotIn(MARKER, str(caught.exception))
            transport.assert_called_once()
            if isinstance(error, HTTPError):
                self.assertTrue(error.fp.closed)

    def test_incomplete_empty_or_tool_response_preserves_usage_and_fails(self):
        for payload in (
            reply(done=False),
            reply(done_reason="length"),
            reply(" "),
            reply(message={"role": "user", "content": MARKER}),
            reply(
                message={
                    "role": "assistant",
                    "content": MARKER,
                    "tool_calls": [{"name": MARKER}],
                }
            ),
        ):
            transport = Mock(side_effect=[INFO, payload])
            with (
                self.subTest(payload=payload),
                self.assertRaises(ProviderError) as caught,
            ):
                OllamaProvider("fixture-local", transport=transport).generate(
                    MARKER, MARKER
                )
            self.assertEqual(caught.exception.usage, TokenUsage(30, 10, 40))
            self.assertNotIn(MARKER, str(caught.exception))
            self.assertEqual(transport.call_count, 2)

    def test_schema_validation_retry_and_exhaustion_stay_in_service(self):
        for final, error in ((reply(), None), (reply("not JSON"), ValidationError)):
            transport = Mock(side_effect=[INFO, reply("{"), INFO, final])
            provider = OllamaProvider(
                "fixture-local",
                transport=transport,
                response_schema=SupportResponse.model_json_schema(),
            )
            if error:
                with self.assertRaises(error):
                    simulate_response(
                        MARKER,
                        provider,
                        settings=Settings(
                            provider="ollama", model="fixture-local", max_attempts=2
                        ),
                    )
            else:
                response = simulate_response(
                    MARKER,
                    provider,
                    settings=Settings(
                        provider="ollama", model="fixture-local", max_attempts=2
                    ),
                )
                self.assertEqual(response.category, "billing")
            self.assertEqual(transport.call_count, 4)
            chats = [
                json.loads(c.args[0].data)
                for c in transport.call_args_list
                if c.args[0].full_url.endswith("/api/chat")
            ]
            self.assertIn(
                "Corrección de salida anterior:", chats[1]["messages"][0]["content"]
            )
            self.assertEqual(chats[0]["messages"][1], chats[1]["messages"][1])

    def test_cli_selection_and_metric_privacy_without_remote_provider_creation(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.jsonl"
            config = Path(directory) / "config.toml"
            config.write_text(
                'provider="ollama"\nmodel="fixture-local"\nlog_metrics=true\nmetrics_path='
                + json.dumps(str(path))
                + "\n"
            )
            stdout, stderr = StringIO(), StringIO()
            with (
                patch(
                    "src.llm.providers.ollama_provider._post_json",
                    side_effect=[INFO, reply()],
                ),
                patch(
                    "src.support.service.OpenAIProvider",
                    side_effect=AssertionError("No OpenAI"),
                ),
                patch(
                    "src.support.service.GeminiProvider",
                    side_effect=AssertionError("No Gemini"),
                ),
                patch("sys.argv", ["nubbix", MARKER, "--config", str(config)]),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                code = main()
            self.assertEqual(code, 0)
            self.assertEqual(
                set(json.loads(stdout.getvalue())),
                {"answer", "confidence", "category", "actions"},
            )
            self.assertIn("Ollama local", stderr.getvalue())
            raw = path.read_text()
            self.assertNotIn(MARKER, raw)
            record = json.loads(raw)
            self.assertEqual(record["provider"], "ollama")
            self.assertFalse(record["simulated"])
            self.assertEqual(record["total_tokens"], 40)
            self.assertIsNone(record["cached_prompt_tokens"])
            self.assertIsNone(record["cost_usd"])

    def test_default_transport_disables_proxy_redirects_and_bounds_response(self):
        self.builder.side_effect = None
        opener = Mock()
        self.builder.return_value = opener
        opener.open.return_value = BytesIO(json.dumps(reply()).encode())
        request = Request("http://127.0.0.1:11434/api/chat", data=b"{}", method="POST")
        self.assertEqual(_post_json(request, 12)["eval_count"], 10)
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 12)
        handlers = self.builder.call_args.args
        self.assertTrue(
            any(isinstance(h, ProxyHandler) and h.proxies == {} for h in handlers)
        )
        redirect = next(h for h in handlers if isinstance(h, _NoRedirect))
        self.assertIsNone(
            redirect.redirect_request(
                None, None, 302, "", {}, "https://example.invalid"
            )
        )
        opener.open.return_value = BytesIO(b"x" * 2_000_001)
        with self.assertRaises(ValueError):
            _post_json(request, 12)
        self.builder.reset_mock()
        for url in ("https://ollama.com/api/chat", "http://127.0.0.1:11434/api/pull"):
            with self.assertRaises(ValueError):
                _post_json(Request(url), 12)
        self.builder.assert_not_called()

    def test_local_usage_missing_invalid_or_zero_counts_are_not_fake_prices(self):
        self.assertEqual(
            ollama_usage({"prompt_eval_count": 0, "eval_count": 0}), TokenUsage(0, 0, 0)
        )
        self.assertEqual(
            ollama_usage({"prompt_eval_count": True, "eval_count": 5}),
            TokenUsage(None, 5, None),
        )
        self.assertEqual(ollama_usage(None), TokenUsage())
        self.assertEqual(
            ollama_usage({"prompt_eval_count": 10, "eval_count": -1}),
            TokenUsage(10, None, None),
        )

    def test_eval_runner_does_not_enable_local_inference_just_by_changing_config(self):
        with self.assertRaisesRegex(ValueError, "sólo mock"):
            evaluate(
                [Case(query="Consulta", expected_category="other")],
                Settings(provider="ollama", model="fixture-local"),
            )
