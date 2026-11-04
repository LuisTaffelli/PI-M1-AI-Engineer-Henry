"""Diagnóstico offline del prechequeo y guardrail de salida; no llama modelos."""

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from src.runtime.config import ROOT, load_settings
from src.support.guardrails import GuardrailError, check_input, check_output
from src.support.schemas import NonEmptyText, SupportResponse


class DiagnosticCase(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    case_id: NonEmptyText
    kind: Literal["attack", "legitimate", "policy_pending", "output_fixture"]
    target: Literal["input", "answer", "actions"]
    text: NonEmptyText
    expectation: Literal["block", "allow", "needs_policy_decision"]
    reason: NonEmptyText

    @model_validator(mode="after")
    def consistent_scope(self):
        expected = {
            "attack": ("input", "block"),
            "legitimate": ("input", "allow"),
            "policy_pending": ("input", "needs_policy_decision"),
        }
        if (
            self.kind in expected
            and (self.target, self.expectation) != expected[self.kind]
        ):
            raise ValueError("Objetivo y expectativa incompatibles.")
        if self.kind == "output_fixture" and (
            self.target == "input" or self.expectation == "needs_policy_decision"
        ):
            raise ValueError("Fixture de salida inválida.")
        return self


def load_suite(attacks: Path, controls: Path) -> list[DiagnosticCase]:
    result = []
    for path, attack_file in ((attacks, True), (controls, False)):
        cases = [
            DiagnosticCase.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not cases or any((case.kind == "attack") != attack_file for case in cases):
            raise ValueError("Suite vacía o mezcla de ataques y controles.")
        result.extend(cases)
    if len({case.case_id for case in result}) != len(result):
        raise ValueError("IDs repetidos.")
    return result


def evaluate(cases: list[DiagnosticCase], *, max_query_chars: int = 4000) -> dict:
    if not cases or type(max_query_chars) is not int or max_query_chars < 1:
        raise ValueError("Suite o límite inválido.")
    rows = []
    for case in cases:
        blocked = False
        try:
            if case.target == "input":
                check_input(case.text, max_query_chars)
            else:
                response = SupportResponse(
                    answer=case.text
                    if case.target == "answer"
                    else "Respuesta sintética.",
                    confidence=0.5,
                    category="other",
                    actions=[case.text] if case.target == "actions" else [],
                )
                check_output(response)
        except GuardrailError:
            blocked = True
        rows.append(
            {
                "case_id": case.case_id,
                "kind": case.kind,
                "target": case.target,
                "expectation": case.expectation,
                "blocked": blocked,
                "expectation_matched": None
                if case.expectation == "needs_policy_decision"
                else blocked == (case.expectation == "block"),
            }
        )
    groups = {}
    for kind in ("attack", "legitimate", "policy_pending", "output_fixture"):
        selected = [row for row in rows if row["kind"] == kind]
        groups[kind] = {
            "total": len(selected),
            "blocked": sum(row["blocked"] for row in selected),
            "not_blocked": sum(not row["blocked"] for row in selected),
            "expectations_scored": sum(
                row["expectation_matched"] is not None for row in selected
            ),
            "expectations_matched": sum(
                row["expectation_matched"] is True for row in selected
            ),
        }
    return {
        "format_version": 1,
        "model_requests": 0,
        "safety_claim": False,
        "bonus_completion_claim": False,
        "scope": "application input precheck and synthetic output fixtures; not model robustness",
        "expectation_status": "technical_diagnostic_proposal; quoted-text policy unresolved",
        "max_query_chars": max_query_chars,
        "total": len(rows),
        "targets": dict(Counter(row["target"] for row in rows)),
        "by_kind": groups,
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attacks", type=Path, default=ROOT / "evals/adversarial.jsonl"
    )
    parser.add_argument(
        "--controls", type=Path, default=ROOT / "evals/guardrail_controls.jsonl"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        settings = load_settings()
        report = evaluate(
            load_suite(args.attacks, args.controls),
            max_query_chars=settings.max_query_chars,
        )
        report["timestamp"] = datetime.now(timezone.utc).isoformat()
        report["dataset_sha256"] = {
            "attacks": hashlib.sha256(args.attacks.read_bytes()).hexdigest(),
            "controls": hashlib.sha256(args.controls.read_bytes()).hexdigest(),
        }
        report["source_sha256"] = {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in (
                "evals/run_guardrail_diagnostics.py",
                "src/support/guardrails.py",
                "src/support/schemas.py",
                "config.toml",
            )
        }
        raw = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(raw)
    except (ValueError, OSError):
        print(
            "Error: suite/configuración inválida o salida ya existente; no se sobrescribió.",
            file=sys.stderr,
        )
        return 2
    print(raw, end="")
    # 0 indica que se produjo el diagnóstico, no que se superaron las expectativas.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
