"""Diagnóstico de guardrails puro: expectativas técnicas, sin llamadas al modelo."""

from collections import Counter

from evals.adversarial.cases import DiagnosticCase
from src.support.guardrails import (
    MAX_QUERY_CHARS,
    GuardrailError,
    check_input,
    check_output,
)
from src.support.schemas import SupportResponse


def evaluate(
    cases: list[DiagnosticCase], *, max_query_chars: int = MAX_QUERY_CHARS
) -> dict:
    if (
        not cases
        or type(max_query_chars) is not int
        or not 1 <= max_query_chars <= MAX_QUERY_CHARS
    ):
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
