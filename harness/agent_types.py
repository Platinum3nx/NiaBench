"""Core Layer 2 task and run datatypes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


AGENT_RUN_SCHEMA_VERSION = "nia.layer2.run.v1"
AGGREGATE_SCHEMA_VERSION = "nia.layer2.aggregate.v1"
ALLOWED_AGENT_CONDITIONS = ("no_retrieval_agent", "nia_agent")
ALLOWED_ARTIFACT_KINDS = ("code_file", "config_file", "text_file", "json_file")
ALLOWED_DIFFICULTIES = ("easy", "medium", "hard")
ALLOWED_CATEGORIES = (
    "api-migration",
    "import-path",
    "config-schema",
    "type-signature",
    "best-practice",
)
ALLOWED_TURN_STOP_REASONS = ("completed", "tool_calls", "max_tokens_truncated", "unexpected")
ALLOWED_TERMINAL_STATUSES = (
    "ok",
    "max_steps_exhausted",
    "timeout",
    "provider_error",
    "max_tokens_truncated",
    "unexpected_stop_reason",
    "workspace_tool_error",
    "retrieval_error",
    "no_artifacts",
    "judge_error",
    "runner_exception",
    "dry_run",
)

AgentCondition = Literal["no_retrieval_agent", "nia_agent"]
AgentStopReason = Literal["completed", "tool_calls", "max_tokens_truncated", "unexpected"]
AgentTerminalStatus = Literal[
    "ok",
    "max_steps_exhausted",
    "timeout",
    "provider_error",
    "max_tokens_truncated",
    "unexpected_stop_reason",
    "workspace_tool_error",
    "retrieval_error",
    "no_artifacts",
    "judge_error",
    "runner_exception",
    "dry_run",
]


@dataclass(frozen=True)
class WorkspaceSeed:
    seed_dir: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceSeed":
        return cls(seed_dir=_require_str(payload, "seed_dir"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactSpec:
    path: str
    kind: str
    required: bool = True
    max_bytes: int | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ArtifactSpec":
        return cls(
            path=_require_str(payload, "path"),
            kind=_require_str(payload, "kind"),
            required=bool(payload.get("required", True)),
            max_bytes=_coerce_optional_int(payload.get("max_bytes")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TestCommand:
    argv: list[str]
    cwd: str = "."
    timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TestCommand":
        argv = payload.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            raise ValueError("test_command.argv must be a non-empty array of strings")
        cwd = payload.get("cwd", ".")
        if not isinstance(cwd, str) or not cwd:
            raise ValueError("test_command.cwd must be a non-empty string")
        timeout = payload.get("timeout_seconds", 30)
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("test_command.timeout_seconds must be a positive integer")
        return cls(argv=list(argv), cwd=cwd, timeout_seconds=timeout)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentTask:
    id: str
    source_task_id: str
    library: str
    version_introduced: str
    category: str
    difficulty: str
    agent_goal: str
    workspace_seed: WorkspaceSeed
    expected_artifacts: list[ArtifactSpec]
    allowed_output_paths: list[str]
    retrieval_hints: list[str]
    test_command: TestCommand | None = None
    success_notes: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentTask":
        expected_artifacts_payload = payload.get("expected_artifacts")
        if not isinstance(expected_artifacts_payload, list):
            raise ValueError("expected_artifacts must be an array")
        expected_artifacts = [
            ArtifactSpec.from_dict(item)
            for item in expected_artifacts_payload
            if isinstance(item, dict)
        ]
        if len(expected_artifacts) != len(expected_artifacts_payload):
            raise ValueError("expected_artifacts must contain only objects")

        allowed_output_paths = payload.get("allowed_output_paths")
        if not isinstance(allowed_output_paths, list) or not all(
            isinstance(item, str) for item in allowed_output_paths
        ):
            raise ValueError("allowed_output_paths must be an array of strings")

        retrieval_hints = payload.get("retrieval_hints", [])
        if not isinstance(retrieval_hints, list) or not all(isinstance(item, str) for item in retrieval_hints):
            raise ValueError("retrieval_hints must be an array of strings")

        test_command_payload = payload.get("test_command")
        test_command = None
        if test_command_payload is not None:
            if not isinstance(test_command_payload, dict):
                raise ValueError("test_command must be an object when provided")
            test_command = TestCommand.from_dict(test_command_payload)

        success_notes = payload.get("success_notes")
        if success_notes is not None and not isinstance(success_notes, str):
            raise ValueError("success_notes must be a string or null")

        workspace_seed_payload = payload.get("workspace_seed")
        if not isinstance(workspace_seed_payload, dict):
            raise ValueError("workspace_seed must be an object")

        return cls(
            id=_require_str(payload, "id"),
            source_task_id=_require_str(payload, "source_task_id"),
            library=_require_str(payload, "library"),
            version_introduced=_require_str(payload, "version_introduced"),
            category=_require_str(payload, "category"),
            difficulty=_require_str(payload, "difficulty"),
            agent_goal=_require_str(payload, "agent_goal"),
            workspace_seed=WorkspaceSeed.from_dict(workspace_seed_payload),
            expected_artifacts=expected_artifacts,
            allowed_output_paths=list(allowed_output_paths),
            retrieval_hints=list(retrieval_hints),
            test_command=test_command,
            success_notes=success_notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, object]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentTurnResult:
    text: str
    tool_calls: list[ToolCallRequest]
    stop_reason: AgentStopReason
    request_id: str | None
    tokens_in: int | None
    tokens_out: int | None
    raw_response: dict[str, object]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentStepRecord:
    step_index: int
    assistant_text: str
    stop_reason: AgentStopReason
    request_id: str | None
    tokens_in: int | None
    tokens_out: int | None
    tool_call_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolCallRecord:
    step_index: int
    call_id: str
    name: str
    arguments: dict[str, object]
    result: dict[str, Any] | None
    status: str
    error: str | None
    started_at: str
    finished_at: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentRunBudgets:
    max_steps: int
    timeout_seconds: int
    max_tokens_per_turn: int
    max_total_tokens: int
    temperature: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentRunTimings:
    started_at: str
    finished_at: str
    wall_clock_ms: int
    provider_time_ms: int | None = None
    judge_time_ms: int | None = None
    retrieval_time_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentPromptRecord:
    system_prompt: str
    initial_user_prompt: str
    available_tools: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArtifactCapture:
    expected_artifacts: list[dict[str, Any]]
    found_artifacts: list[str]
    missing_artifacts: list[str]
    extracted_text: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskCommandResult:
    exists: bool
    ran: bool
    argv: list[str] | None
    cwd: str | None
    timeout_seconds: int | None
    exit_code: int | None
    stdout: str | None
    stderr: str | None
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentScoreBundle:
    quality_score_pct: float | None
    crash_aware_score_pct: float | None
    pass_bool: bool | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FailureDetail:
    kind: str
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentRunArtifact:
    schema_version: str
    run_id: str
    task_id: str
    source_task_id: str
    condition: AgentCondition
    repetition_index: int
    model_provider: str
    model: str
    judge_provider: str
    judge_model: str
    timestamp: str
    status: AgentTerminalStatus
    budgets: AgentRunBudgets
    timings_ms: AgentRunTimings
    prompt: AgentPromptRecord
    steps: list[AgentStepRecord]
    tool_calls: list[ToolCallRecord]
    final_response_text: str | None
    final_response_parse_error: str | None
    artifacts: ArtifactCapture
    task_command: TaskCommandResult
    judge_result: dict[str, Any] | None
    scores: AgentScoreBundle
    failure: FailureDetail | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConditionAggregateRow:
    condition: AgentCondition
    total_runs: int
    unique_tasks: int
    completed_runs: int
    task_macro_completed_only_avg_quality_pct: float | None
    task_macro_crash_aware_avg_quality_pct: float | None
    run_level_completion_rate: float
    run_level_crash_rate: float
    run_level_timeout_rate: float
    run_level_no_artifact_rate: float
    run_level_judge_error_rate: float
    avg_tool_calls_per_run: float
    avg_nia_calls_per_run: float
    nia_usage_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskAggregateRow:
    task_id: str
    library: str
    difficulty: str
    by_condition: dict[str, dict[str, Any]]
    delta_completed_only_pct: float | None
    delta_crash_aware_pct: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _coerce_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raise ValueError("max_bytes must be an integer or null")
