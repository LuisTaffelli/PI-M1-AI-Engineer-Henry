"""Resumen de una evaluación, incluida parcialidad y costos observados."""

from evals.classification.plan import REMOTE_PROVIDERS
from evals.classification.scoring import summarize
from evals.common.costs import summarize_financials


def evaluation_report(rows, plan):
    settings, metadata = plan.settings, plan.metadata
    remote = settings.provider in REMOTE_PROVIDERS
    report = summarize(rows)
    for prompt in plan.prompts:
        group = report["by_prompt"].setdefault(
            prompt, {"total": 0, "exact_match": None}
        )
        group["planned"] = len(plan.cases)
        group["not_run"] = len(plan.cases) - group["total"]
        group["exact_match_on_processed"] = group["exact_match"]
        if group["not_run"]:
            group["exact_match"] = None
            for category in group.get("by_category", {}).values():
                category["exact_match_on_processed"] = category["exact_match"]
                category["exact_match"] = None
            for subset in group.get("by_ambiguity", {}).values():
                subset["exact_match_on_processed"] = subset["exact_match"]
                subset["exact_match"] = None
    report["usage_and_cost"] = summarize_financials(rows)
    for prompt in plan.prompts:
        report["by_prompt"][prompt]["usage_and_cost"] = summarize_financials(
            [row for row in rows if row["prompt_version"] == prompt]
        )
    attempts = sum(row["attempts"] for row in rows)
    report.update(
        simulated=settings.provider == "mock",
        provider=settings.provider,
        model=settings.model,
        suite_kind=metadata["suite_kind"],
        planned=metadata["planned_cases"],
        processed=len(rows),
        not_run=metadata["planned_cases"] - len(rows),
        completed=len(rows) == metadata["planned_cases"],
        generation_attempts=attempts,
        remote_calls_attempted=attempts if remote else 0,
        provider_calls_upper_bound=metadata["provider_calls_upper_bound"],
        monetary_cap_enforced=False,
        failed_cases=sum(row["status"] != "ok" for row in rows),
    )
    return report
