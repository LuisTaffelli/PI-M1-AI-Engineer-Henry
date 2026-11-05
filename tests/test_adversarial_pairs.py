"""Protocolos pareados y denominadores sin modelos reales."""

import json
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evals.run_adversarial_pairs import analyze, load_protocol, run_pairs
from src.runtime.config import ROOT, Settings


def observation(
    case_id, condition, category, status="ok", expected="billing", target="other"
):
    return {
        "case_id": case_id,
        "condition": condition,
        "category": category,
        "status": status,
        "expected_category": expected,
        "attacker_target": target,
        "prompt_version": "v3_structured",
        "attempts": 0 if status == "rejected_input" else 1,
    }


class AdversarialPairTests(unittest.TestCase):
    def setUp(self):
        for name in ("OpenAIProvider", "GeminiProvider"):
            p = patch(
                "src.llm.factory." + name,
                side_effect=AssertionError("No paid provider"),
            )
            p.start()
            self.addCleanup(p.stop)
        p = patch(
            "src.llm.providers.ollama_provider.build_opener",
            side_effect=AssertionError("No real network"),
        )
        p.start()
        self.addCleanup(p.stop)

    def test_wrong_baseline_and_preblocks_are_not_attack_success_or_model_resistance(
        self,
    ):
        rows = [
            observation("flip", "clean", "billing"),
            observation("flip", "attacked", "other"),
            observation("wrong", "clean", "other"),
            observation("wrong", "attacked", "other"),
            observation("blocked", "clean", "billing"),
            observation("blocked", "attacked", None, "rejected_input"),
            observation("error", "clean", "billing"),
            observation("error", "attacked", None, "provider_error"),
            observation("third", "clean", "billing"),
            observation("third", "attacked", "technical"),
            observation("benign", "benign_control", None, "rejected_input"),
            observation("quote", "policy_pending", None, "rejected_input"),
        ]
        group = analyze(rows)["by_prompt"]["v3_structured"]
        self.assertEqual(group["pairs"], 5)
        self.assertEqual(group["uninterpretable_baseline"], 1)
        self.assertEqual(group["input_preblocked"], 1)
        self.assertEqual(group["eligible_admitted"], 3)
        self.assertEqual(group["eligible_valid"], 2)
        self.assertEqual(group["targeted_category_flips_observed"], 1)
        self.assertEqual(group["task_category_retained"], 0)
        self.assertEqual(group["benign_input_blocks"], 1)
        self.assertEqual(group["policy_cases_excluded"], 1)
        pending = {p["case_id"]: p for p in group["pair_outcomes"]}
        self.assertIsNone(pending["wrong"]["targeted_category_flip_observed"])
        self.assertIsNone(pending["blocked"]["targeted_category_flip_observed"])
        self.assertIsNone(pending["error"]["targeted_category_flip_observed"])

    def test_protocol_links_twelve_distinct_attack_refs_with_different_targets(self):
        pairs, attacks, controls = load_protocol(
            ROOT / "evals/adversarial_pairs.jsonl",
            [
                ROOT / "evals/adversarial.jsonl",
                ROOT / "evals/adversarial_unicode.jsonl",
            ],
            ROOT / "evals/guardrail_controls.jsonl",
        )
        self.assertEqual(len(pairs), 12)
        self.assertEqual(set(p.attack_case_id for p in pairs), set(attacks))
        self.assertTrue(all(p.expected_category != p.attacker_target for p in pairs))
        self.assertEqual(len(controls), 6)
        with TemporaryDirectory() as directory:
            bad = Path(directory) / "pairs.jsonl"
            rows = [p.model_dump() for p in pairs]
            rows[0]["attacker_target"] = rows[0]["expected_category"]
            bad.write_text("\n".join(json.dumps(r) for r in rows))
            with self.assertRaises(ValueError):
                load_protocol(
                    bad,
                    [
                        ROOT / "evals/adversarial.jsonl",
                        ROOT / "evals/adversarial_unicode.jsonl",
                    ],
                    ROOT / "evals/guardrail_controls.jsonl",
                )

    def test_permission_provider_prompts_and_budget_fail_before_output(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            settings = Settings(provider="ollama", model="fixture-local")
            for selected, prompts, allowed, budget in (
                (settings, ("v3_structured",), False, 30),
                (
                    Settings(provider="openai", model="fixture"),
                    ("v3_structured",),
                    True,
                    30,
                ),
                (settings, ("v3_structured", "v3_structured"), True, 60),
                (settings, ("unknown",), True, 30),
                (settings, ("v3_structured",), True, 29),
                (settings, ("v3_structured",), True, 129),
            ):
                with (
                    self.subTest(budget=budget, prompts=prompts),
                    self.assertRaises(ValueError),
                ):
                    run_pairs(
                        selected,
                        prompts,
                        output,
                        allow_local_inference=allowed,
                        max_calls=budget,
                    )
                self.assertFalse(output.exists())

    def test_saved_runs_keep_clean_and_attacked_separate_without_raw_text(self):
        content = json.dumps(
            {
                "answer": "SYNTHETIC_RESPONSE_ONLY",
                "confidence": 0.5,
                "category": "billing",
                "actions": [],
            }
        )
        chat_queries = []

        def transport(request, timeout):
            if request.full_url.endswith("/api/show"):
                return {"details": {"format": "gguf"}, "capabilities": ["completion"]}
            chat_queries.append(json.loads(request.data)["messages"][1]["content"])
            return {
                "done": True,
                "done_reason": "stop",
                "message": {"role": "assistant", "content": content},
                "prompt_eval_count": 20,
                "eval_count": 10,
            }

        with TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with (
                patch("src.llm.providers.ollama_provider._post_json", transport),
                redirect_stderr(StringIO()),
            ):
                report = run_pairs(
                    Settings(provider="ollama", model="fixture-local"),
                    ("v3_structured",),
                    output,
                    allow_local_inference=True,
                    max_calls=30,
                )
            plan = json.loads((output / "plan.json").read_text())
            self.assertEqual(plan["planned_service_calls"], 30)
            rows = [
                json.loads(line)
                for line in (output / "results.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(rows), 30)
            self.assertEqual(len({r["request_id"] for r in rows}), 30)
            self.assertEqual(len(chat_queries), 22)
            self.assertEqual(sum(r["attempts"] for r in rows), 22)
            self.assertEqual(
                report["by_prompt"]["v3_structured"]["input_preblocked"], 6
            )
            self.assertEqual(
                report["by_prompt"]["v3_structured"]["policy_input_blocks"], 2
            )
            self.assertEqual(analyze(rows), report)
            for path in output.iterdir():
                raw = path.read_text()
                self.assertNotIn("SYNTHETIC_RESPONSE_ONLY", raw)
                self.assertNotIn("Solicito el comprobante", raw)
            with self.assertRaises(FileExistsError):
                run_pairs(
                    Settings(provider="ollama", model="fixture-local"),
                    ("v3_structured",),
                    output,
                    allow_local_inference=True,
                    max_calls=30,
                )
