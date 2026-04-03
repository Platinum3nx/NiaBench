"""Layer 2 grading result datatypes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


ALLOWED_QUALITY_FAILURES = (
    "outdated_api",
    "wrong_import_path",
    "wrong_parameter_or_signature",
    "invented_method_or_object",
    "mixed_version_answer",
    "artifact_missing_required_change",
)

ALLOWED_OPERATIONAL_FAILURES = (
    "timeout",
    "provider_error",
    "max_tokens_truncated",
    "unexpected_stop_reason",
    "retrieval_error",
    "workspace_tool_error",
    "runner_exception",
    "no_artifacts",
    "judge_error",
)

JudgeConfidence = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class ArtifactFinding:
    path: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentJudgeResult:
    score: int | None
    rationale: str | None
    quality_failures: list[str]
    artifact_findings: list[ArtifactFinding]
    confidence: JudgeConfidence | None
    status: str
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

    @property
    def pass_bool(self) -> bool | None:
        if self.score is None:
            return None
        return self.score == 2

    @property
    def quality_score_pct(self) -> float | None:
        if self.score is None:
            return None
        return round((self.score / 2.0) * 100.0, 6)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AggregateSummary:
    delta_completed_only_pct: float | None
    delta_crash_aware_pct: float | None
    unique_tasks: int
    total_runs: int
    pinned_agent_model_provider: str | None
    pinned_agent_model: str | None
    pinned_judge_model_provider: str | None
    pinned_judge_model: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
