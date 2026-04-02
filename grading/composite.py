"""Composite score calculation helpers."""

from __future__ import annotations

from typing import Any


class CompositeGrader:
    @staticmethod
    def score_executable(*, sandbox_exit_code: int | None, judge_score: int | None) -> float | None:
        if judge_score is None:
            return None
        sandbox_binary = 1.0 if sandbox_exit_code == 0 else 0.0
        judge_score_normalized = judge_score / 2.0
        return (sandbox_binary * 0.6) + (judge_score_normalized * 0.4)

    @staticmethod
    def score_non_executable(*, judge_score: int | None) -> float | None:
        if judge_score is None:
            return None
        return judge_score / 2.0

    @staticmethod
    def judge_only_bundle(
        *,
        baseline_judge_score: int | None,
        treatment_judge_score: int | None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        baseline = CompositeGrader.score_non_executable(judge_score=baseline_judge_score)
        treatment = CompositeGrader.score_non_executable(judge_score=treatment_judge_score)
        delta = None if baseline is None or treatment is None else treatment - baseline
        status = "ok" if baseline is not None and treatment is not None else "pending"
        payload: dict[str, Any] = {
            "status": status,
            "mode": "judge_only",
            "baseline": baseline,
            "treatment": treatment,
            "delta": delta,
        }
        if reason:
            payload["reason"] = reason
        return payload
