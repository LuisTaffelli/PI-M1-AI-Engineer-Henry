"""Sólo archivos y claves ficticios; nunca se abre el .env del checkout."""

import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evals.run_provider_evals import main as eval_main
from src.llm.providers.ollama_provider import OllamaProvider
from src.main import main as cli_main
from src.runtime.environment import load_api_key


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dotenv = Path(self.tmp.name) / ".env"
        patcher = patch("src.runtime.environment.DOTENV_PATH", self.dotenv)
        patcher.start()
        self.addCleanup(patcher.stop)
        for module in ("openai", "gemini"):
            patcher = patch(
                f"src.llm.providers.{module}_provider.urlopen",
                side_effect=AssertionError("No network"),
            )
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_literals_export_comments_and_selected_key(self):
        self.dotenv.write_text(
            "# comment\nUNRELATED invalid syntax\nexport OPENAI_API_KEY = 'fake-first' # comment\nGEMINI_API_KEY=\"fake-second\"\n"
        )
        environ = {}
        self.assertEqual(load_api_key("OPENAI_API_KEY", environ), "fake-first")
        self.assertEqual(load_api_key("GEMINI_API_KEY", environ), "fake-second")
        self.assertEqual(environ, {})

    def test_default_environment_is_resolved_lazily_without_mutation(self):
        self.dotenv.write_text("OPENAI_API_KEY=fake-file\n")
        environ = {"OPENAI_API_KEY": "fake-environment"}
        with patch("src.runtime.environment.os.environ", environ):
            self.assertEqual(load_api_key("OPENAI_API_KEY"), "fake-environment")
            self.assertEqual(environ, {"OPENAI_API_KEY": "fake-environment"})
            # An explicitly injected empty mapping must not fall back to the process.
            self.assertEqual(load_api_key("OPENAI_API_KEY", {}), "fake-file")
            environ["OPENAI_API_KEY"] = ""
            self.assertEqual(load_api_key("OPENAI_API_KEY"), "")
            environ.clear()
            self.assertEqual(load_api_key("OPENAI_API_KEY"), "fake-file")
            self.assertEqual(environ, {})

    def test_explicit_adapter_keys_bypass_environment(self):
        from src.llm.providers.gemini_provider import GeminiProvider
        from src.llm.providers.openai_provider import OpenAIProvider

        with patch(
            "src.runtime.environment.load_api_key",
            side_effect=AssertionError("No credential read"),
        ):
            for adapter in (OpenAIProvider, GeminiProvider):
                with self.subTest(adapter=adapter.__name__):
                    adapter("fixture", api_key="fake-explicit")

    def test_precedence_even_empty_skips_file(self):
        self.dotenv.mkdir()  # Leerla fallaría; entorno tiene precedencia.
        for value in ("fake-exported", ""):
            self.assertEqual(
                load_api_key("OPENAI_API_KEY", {"OPENAI_API_KEY": value}), value
            )

    def test_absent_file_key_and_empty_value(self):
        self.assertIsNone(load_api_key("OPENAI_API_KEY", {}))
        for line in ("GEMINI_API_KEY=fake-other", "# nothing"):
            self.dotenv.write_text(line)
            self.assertIsNone(load_api_key("OPENAI_API_KEY", {}))
        for line in (
            "OPENAI_API_KEY=",
            "OPENAI_API_KEY= # empty",
            "OPENAI_API_KEY=''",
            'OPENAI_API_KEY=""',
        ):
            self.dotenv.write_text(line)
            self.assertEqual(load_api_key("OPENAI_API_KEY", {}), "")

    def test_malformed_duplicate_and_read_errors_are_sanitized(self):
        for text in (
            "OPENAI_API_KEY='fake-private",
            "OPENAI_API_KEY='fake-private' trailing",
            "OPENAI_API_KEY fake-private",
            "OPENAI_API_KEY=fake-private\nOPENAI_API_KEY=duplicate",
            "OPENAI_API_KEY=fake-private\x00",
            "OPENAI_API_KEY=fake-private\\",
        ):
            self.dotenv.write_text(text)
            with self.assertRaises(ValueError) as error:
                load_api_key("OPENAI_API_KEY", {})
            self.assertNotIn("fake-private", str(error.exception))
        self.dotenv.write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            load_api_key("OPENAI_API_KEY", {})
        with patch.object(
            Path, "read_text", side_effect=PermissionError("private-path")
        ):
            with self.assertRaises(ValueError) as error:
                load_api_key("OPENAI_API_KEY", {})
            self.assertNotIn("private-path", str(error.exception))

    def test_no_substitution_or_script_execution(self):
        marker = Path(self.tmp.name) / "must-not-exist"
        value = f"$(touch {marker})"
        self.dotenv.write_text(f"OPENAI_API_KEY='{value}'\n")
        self.assertEqual(load_api_key("OPENAI_API_KEY", {}), value)
        self.dotenv.write_text("OPENAI_API_KEY=${OTHER_KEY}\n")
        self.assertEqual(
            load_api_key("OPENAI_API_KEY", {"OTHER_KEY": "not-expanded"}),
            "${OTHER_KEY}",
        )
        self.assertFalse(marker.exists())
        with self.assertRaises(ValueError):
            load_api_key("PATH", {})

    def test_preview_and_missing_remote_permission_do_not_read_dotenv(self):
        args = [
            "eval",
            "--provider",
            "openai",
            "--model",
            "fixture",
            "--prompt",
            "v3_structured",
            "--case-id",
            "nubbix-b01",
            "--max-calls",
            "1",
            "--output",
            str(Path(self.tmp.name) / "run"),
        ]
        with (
            patch(
                "src.runtime.environment.load_api_key",
                side_effect=AssertionError("No credential read"),
            ),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            with patch("sys.argv", args):
                self.assertEqual(eval_main(), 0)
            with patch("sys.argv", args + ["--execute"]):
                self.assertEqual(eval_main(), 2)

    def test_cli_and_evaluator_load_fake_dotenv_for_both_adapters(self):
        self.dotenv.write_text(
            "OPENAI_API_KEY=fake-openai\nGEMINI_API_KEY=fake-gemini\n"
        )
        text = json.dumps(
            {
                "answer": "fixture",
                "category": "billing",
                "confidence": 0.5,
                "actions": [],
            }
        )
        for provider in ("openai", "gemini"):
            calls = []

            def transport(request, timeout):
                calls.append(request)
                return {
                    "status": "completed",
                    "output" if provider == "openai" else "steps": [
                        {
                            "type": "message"
                            if provider == "openai"
                            else "model_output",
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

            with (
                patch("src.runtime.environment.os.environ", {}),
                patch(
                    f"src.llm.providers.{provider}_provider._post_json",
                    side_effect=transport,
                ),
                redirect_stdout(StringIO()) as stdout,
                redirect_stderr(StringIO()) as stderr,
            ):
                with patch(
                    "sys.argv",
                    [
                        "cli",
                        "Ticket sintético de cobro duplicado",
                        "--provider",
                        provider,
                        "--model",
                        "fixture",
                        "--no-metrics",
                    ],
                ):
                    self.assertEqual(cli_main(), 0)
                output = Path(self.tmp.name) / provider
                with patch(
                    "sys.argv",
                    [
                        "eval",
                        "--provider",
                        provider,
                        "--model",
                        "fixture",
                        "--prompt",
                        "v3_structured",
                        "--case-id",
                        "nubbix-b01",
                        "--max-calls",
                        "1",
                        "--output",
                        str(output),
                        "--execute",
                        "--allow-remote-inference",
                    ],
                ):
                    self.assertEqual(eval_main(), 0)
                self.assertEqual(len(calls), 2)
                for path in output.iterdir():
                    self.assertNotIn(f"fake-{provider}", path.read_text())
                self.assertNotIn(
                    f"fake-{provider}", stdout.getvalue() + stderr.getvalue()
                )

    def test_mock_and_ollama_never_load_credentials(self):
        with (
            patch(
                "src.runtime.environment.load_api_key",
                side_effect=AssertionError("No credentials"),
            ),
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
            patch(
                "sys.argv",
                ["cli", "Ticket sintético", "--provider", "mock", "--no-metrics"],
            ),
        ):
            self.assertEqual(cli_main(), 0)

            def transport(request, timeout):
                if request.full_url.endswith("/api/show"):
                    return {
                        "details": {"format": "gguf"},
                        "capabilities": ["completion"],
                    }
                return {
                    "done": True,
                    "done_reason": "stop",
                    "message": {"role": "assistant", "content": "fixture"},
                }

            result = OllamaProvider("fixture-local", transport=transport).generate(
                "instructions", "query"
            )
            self.assertEqual(result.text, "fixture")


if __name__ == "__main__":
    unittest.main()
