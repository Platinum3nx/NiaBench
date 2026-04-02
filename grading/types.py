"""Shared grading result types."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class SandboxResult:
    executed: bool
    exit_code: int | None
    stdout: str | None
    stderr: str | None
    error_type: str | None
    status: str = "pending"
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class JudgeResult:
    baseline_score: int | None
    treatment_score: int | None
    baseline_rationale: str | None
    treatment_rationale: str | None
    status: str = "pending"
    error: str | None = None
    parse_error: str | None = None
    provider_error: str | None = None
    judge_prompt: str | None = None
    judge_raw_response: str | None = None
    request_id: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    model_provider: str | None = None
    model: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
