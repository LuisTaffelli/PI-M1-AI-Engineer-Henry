"""Integridad y separación del corpus propuesto; no evalúa etiquetas con un LLM."""

import json
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pydantic import ValidationError

from evals.run_evals import (
    Case,
    check_dataset,
    evaluate,
    load_cases,
    main,
    normalized_query,
)
from src.llm.prompts import load_prompt
from src.runtime.config import ROOT, Settings
from src.support.schemas import SupportResponse

DATASET = ROOT / "data/eval_dataset.jsonl"


class EvalDatasetTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases(DATASET)
        for name in ("openai_provider", "gemini_provider"):
            blocker = patch(
                f"src.llm.providers.{name}.urlopen",
                side_effect=AssertionError("Network forbidden"),
            )
            blocker.start()
            self.addCleanup(blocker.stop)

    def test_dataset_jsonl_has_32_explicit_labeled_unique_rows(self):
        lines = DATASET.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 32)
        for line in lines:
            row = json.loads(line)
            self.assertEqual(
                set(row),
                {"case_id", "query", "expected_category", "label_reason", "ambiguous"},
            )
            self.assertIs(type(row["ambiguous"]), bool)
            self.assertTrue(row["label_reason"].strip())
            self.assertLessEqual(len(row["query"]), Settings().max_query_chars)
        report = check_dataset(self.cases)
        self.assertEqual(
            report["by_category"],
            {"billing": 8, "technical": 8, "account": 8, "other": 8},
        )
        self.assertTrue(report["balanced"])
        self.assertEqual(len(set(c.case_id for c in self.cases)), 32)
        self.assertEqual(report["label_review_status"], "not_verified_by_this_check")

    def test_ambiguities_have_reasons_and_are_evenly_distributed(self):
        ambiguous = [c for c in self.cases if c.ambiguous]
        self.assertEqual(len(ambiguous), 8)
        self.assertEqual(
            Counter(c.expected_category for c in ambiguous),
            {"billing": 2, "technical": 2, "account": 2, "other": 2},
        )
        self.assertTrue(all(c.label_reason.startswith("Ambigüedad") for c in ambiguous))

    def test_queries_are_disjoint_from_all_prompt_examples(self):
        queries = {normalized_query(c.query) for c in self.cases}
        examples = {
            normalized_query(e.query)
            for name in ("v1_zero_shot", "v2_few_shot")
            for e in load_prompt(name).examples
        }
        self.assertFalse(queries & examples)

    def test_rejects_too_few_cases_missing_categories_or_missing_metadata(self):
        for cases in (
            self.cases[:29],
            [c for c in self.cases if c.expected_category != "other"],
            [Case(**{**c.model_dump(), "case_id": None}) for c in self.cases],
            [Case(**{**c.model_dump(), "label_reason": None}) for c in self.cases],
            [
                Case(**{k: v for k, v in c.model_dump().items() if k != "ambiguous"})
                for c in self.cases
            ],
        ):
            with self.subTest(count=len(cases)), self.assertRaises(ValueError):
                check_dataset(cases)
        missing_category = [
            Case(**{**c.model_dump(), "expected_category": "billing"})
            if c.expected_category == "other"
            else c
            for c in self.cases
        ]
        with self.assertRaisesRegex(ValueError, "categorías"):
            check_dataset(missing_category)

    def test_rejects_duplicate_ids_and_normalized_duplicate_queries(self):
        for change in (
            {"case_id": self.cases[0].case_id},
            {"query": self.cases[0].query.upper() + " !!!"},
            {"query": "???"},
        ):
            cases = list(self.cases)
            cases[-1] = Case(**{**cases[-1].model_dump(), **change})
            with self.subTest(change=change), self.assertRaises(ValueError):
                check_dataset(cases)
        self.assertEqual(normalized_query("  ¿CÓBRO?  "), normalized_query("cobro!"))

    def test_rejects_normalized_few_shot_overlap_even_if_other_prompt_selected(self):
        cases = list(self.cases)
        query = load_prompt("v2_few_shot").examples[0].query
        cases[0] = Case(**{**cases[0].model_dump(), "query": query.upper() + " !!!"})
        with self.assertRaisesRegex(ValueError, "ejemplos"):
            check_dataset(cases)

    def test_loader_rejects_malformed_unknown_labels_wrong_types_and_extras(self):
        row = self.cases[0].model_dump()
        for text in (
            "not JSON",
            "[]",
            json.dumps({**row, "expected_category": "refund"}),
            json.dumps({**row, "query": 17}),
            json.dumps({**row, "ambiguous": "false"}),
            json.dumps({**row, "extra": "not_allowed"}),
            json.dumps({**row, "query": " "}),
        ):
            with TemporaryDirectory() as directory:
                path = Path(directory) / "dataset.jsonl"
                path.write_text(text)
                with self.subTest(text=text), self.assertRaises(ValidationError):
                    load_cases(path)

    def test_dataset_check_never_constructs_provider_or_calls_service(self):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        stdout, stderr = StringIO(), StringIO()
        with (
            patch("sys.argv", ["eval", "--dataset", str(DATASET), "--check-dataset"]),
            patch("evals.classification.smoke.simulate_response") as service,
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            result = main()
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["total"], 32)
        service.assert_not_called()

    def test_only_query_reaches_inference_and_mock_score_is_not_quality(self):
        response = SupportResponse(
            answer="Fixture", confidence=0.5, category="other", actions=[]
        )
        with patch(
            "evals.classification.smoke.simulate_response", return_value=response
        ) as service:
            report = evaluate(self.cases, Settings())
        self.assertEqual(report["total"], 32)
        self.assertEqual(report["ambiguous_total"], 8)
        self.assertTrue(report["ambiguous_included_in_score"])
        self.assertEqual(report["exact_match"], 0.25)
        self.assertFalse(report["quality_claim"])
        self.assertEqual(
            [call.args for call in service.call_args_list],
            [(c.query,) for c in self.cases],
        )
        with self.assertRaises(ValueError):
            evaluate(self.cases, Settings(provider="gemini", model="fixture"))

    def test_cli_full_dataset_check_and_mock_work_outside_root(self):
        for flags in (["--check-dataset"], ["--prompt", "v2_few_shot"]):
            with TemporaryDirectory() as directory:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "evals.run_evals",
                        "--dataset",
                        str(DATASET),
                        *flags,
                    ],
                    cwd=directory,
                    env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
                    capture_output=True,
                    text=True,
                )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["total"], 32)
            if not flags[0] == "--check-dataset":
                self.assertEqual(report["exact_match"], 0.25)
                self.assertFalse(report["quality_claim"])

    def test_corrupted_full_corpus_is_rejected_before_any_inference(self):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        cases = list(self.cases)
        cases[-1] = Case(**{**cases[-1].model_dump(), "query": cases[0].query})
        with (
            patch("sys.argv", ["eval", "--dataset", str(DATASET)]),
            patch("evals.cli.smoke.load_cases", return_value=cases),
            patch("evals.classification.smoke.simulate_response") as service,
            redirect_stdout(StringIO()),
            redirect_stderr(StringIO()),
        ):
            self.assertEqual(main(), 2)
        service.assert_not_called()
