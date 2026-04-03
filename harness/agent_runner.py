"""Layer 2 bounded agent loop and run artifact generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from harness.agent_conditions import AgentConditionConfig
from harness.agent_llm_clients import AgentLLMClientError, BaseAgentLLMClient
from harness.agent_prompts import build_agent_prompts
from harness.agent_tools import (
    NIA_TOOL_NAME,
    AgentToolError,
    AgentTools,
    build_tool_inventory,
    build_tool_schemas,
)
from harness.agent_types import (
    AGENT_RUN_SCHEMA_VERSION,
    AgentRunBudgets,
    AgentRunTimings,
    AgentScoreBundle,
    AgentStepRecord,
    AgentTask,
    AgentTerminalStatus,
    AgentTurnResult,
    ArtifactCapture,
    FailureDetail,
    TaskCommandResult,
    ToolCallRecord,
)
from harness.agent_workspace import AgentWorkspace, WorkspaceError, materialize_workspace, snapshot_final_workspace


JudgeCallable = Callable[
    [AgentTask, str | None, ArtifactCapture, TaskCommandResult, AgentTerminalStatus],
    tuple[dict[str, Any] | None, AgentScoreBundle, AgentTerminalStatus, FailureDetail | None],
]


def run_agent_task(
    *,
    task: AgentTask,
    condition: AgentConditionConfig,
    provider: str,
    model: str,
    judge_provider: str,
    judge_model: str,
    run_id: str,
    repetition_index: int,
    output_root: Path,
    agent_client: BaseAgentLLMClient | None,
    nia_search_callable: Any | None,
    judge_callable: JudgeCallable | None,
    dry_run: bool,
    skip_judge: bool,
    temperature: float,
    max_steps: int,
    timeout_seconds: int,
    max_tokens_per_turn: int,
    max_total_tokens: int,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    run_dir = output_root
    run_dir.mkdir(parents=True, exist_ok=True)

    workspace = materialize_workspace(task=task, run_root=run_dir)
    tool_inventory = build_tool_inventory(
        include_nia=condition.include_nia_tool,
        task_has_test_command=task.test_command is not None,
    )
    tool_schemas = build_tool_schemas(
        include_nia=condition.include_nia_tool,
        task_has_test_command=task.test_command is not None,
    )
    system_prompt, initial_user_prompt = build_agent_prompts(task=task, tool_inventory=tool_inventory)
    (run_dir / "prompt_system.txt").write_text(system_prompt, encoding="utf-8")
    (run_dir / "prompt_initial_user.txt").write_text(initial_user_prompt, encoding="utf-8")

    tools = AgentTools(
        workspace=workspace,
        task=task,
        include_nia=condition.include_nia_tool,
        nia_search_callable=nia_search_callable,
    )

    terminal_status: AgentTerminalStatus = "dry_run" if dry_run else "ok"
    failure_detail: FailureDetail | None = None
    final_response_text: str | None = None
    final_response_parse_error: str | None = None
    steps: list[AgentStepRecord] = []
    tool_call_records: list[ToolCallRecord] = []
    total_tokens_out = 0

    messages: list[dict[str, object]] = [{"role": "user", "content": initial_user_prompt}]
    loop_started = datetime.now(timezone.utc)
    step_count = 0

    if dry_run:
        artifact_capture = collect_artifacts(task=task, workspace=workspace)
        task_command_result = derive_task_command_result(task=task, tools=tools)
        if not artifact_capture.found_artifacts:
            terminal_status = "dry_run"
        score_bundle = AgentScoreBundle(quality_score_pct=None, crash_aware_score_pct=None, pass_bool=None)
        judge_result = None
    else:
        if agent_client is None:
            raise ValueError("agent_client is required for live runs")

        while True:
            elapsed_seconds = (datetime.now(timezone.utc) - loop_started).total_seconds()
            if elapsed_seconds >= timeout_seconds:
                terminal_status = "timeout"
                failure_detail = FailureDetail(kind="timeout", detail="Run wall-clock budget exhausted")
                break
            if step_count >= max_steps:
                terminal_status = "max_steps_exhausted"
                failure_detail = FailureDetail(kind="max_steps_exhausted", detail="Step budget exhausted")
                break
            if total_tokens_out >= max_total_tokens:
                terminal_status = "max_tokens_truncated"
                failure_detail = FailureDetail(
                    kind="max_tokens_truncated",
                    detail="Total token budget exhausted",
                )
                break

            turn: AgentTurnResult
            try:
                turn = run_turn_with_retry(
                    agent_client=agent_client,
                    model=model,
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tool_schemas,
                    temperature=temperature,
                    max_tokens=max_tokens_per_turn,
                )
            except AgentLLMClientError as exc:
                terminal_status = "provider_error"
                failure_detail = FailureDetail(kind="provider_error", detail=str(exc))
                break

            step_count += 1
            total_tokens_out += turn.tokens_out or 0
            steps.append(
                AgentStepRecord(
                    step_index=step_count,
                    assistant_text=turn.text,
                    stop_reason=turn.stop_reason,
                    request_id=turn.request_id,
                    tokens_in=turn.tokens_in,
                    tokens_out=turn.tokens_out,
                    tool_call_ids=[tool_call.id for tool_call in turn.tool_calls],
                )
            )

            if turn.tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "content": turn.text,
                        "tool_calls": [tool_call.to_dict() for tool_call in turn.tool_calls],
                    }
                )
                tool_error = execute_turn_tool_calls(
                    tools=tools,
                    turn=turn,
                    step_index=step_count,
                    messages=messages,
                    tool_call_records=tool_call_records,
                )
                if tool_error is not None:
                    terminal_status, failure_detail = tool_error
                    break
                continue

            final_response_text = turn.text
            if turn.stop_reason == "completed":
                terminal_status = "ok"
            elif turn.stop_reason == "max_tokens_truncated":
                terminal_status = "max_tokens_truncated"
                failure_detail = FailureDetail(
                    kind="max_tokens_truncated",
                    detail="Provider stopped due to max tokens",
                )
            else:
                terminal_status = "unexpected_stop_reason"
                failure_detail = FailureDetail(
                    kind="unexpected_stop_reason",
                    detail=f"stop_reason={turn.stop_reason}",
                )
            break

        artifact_capture = collect_artifacts(task=task, workspace=workspace)
        task_command_result = derive_task_command_result(task=task, tools=tools)
        if terminal_status == "ok" and not artifact_capture.found_artifacts:
            terminal_status = "no_artifacts"
            failure_detail = FailureDetail(kind="no_artifacts", detail="No expected artifacts were found")

        _final_json, parse_error = parse_final_response_json(final_response_text)
        final_response_parse_error = parse_error

        if skip_judge or judge_callable is None:
            judge_result = (
                {
                    "status": "skipped",
                    "error": "Judge explicitly skipped via --skip-judge",
                    "model_provider": judge_provider,
                    "model": judge_model,
                }
                if skip_judge
                else None
            )
            crash_aware = 0.0 if terminal_status != "ok" else None
            score_bundle = AgentScoreBundle(
                quality_score_pct=None,
                crash_aware_score_pct=crash_aware,
                pass_bool=None,
            )
        else:
            judge_result, score_bundle, terminal_status, failure_detail = judge_callable(
                task,
                final_response_text,
                artifact_capture,
                task_command_result,
                terminal_status,
            )

    snapshot_final_workspace(workspace)

    finished_at = datetime.now(timezone.utc)
    timings = AgentRunTimings(
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        wall_clock_ms=int((finished_at - started_at).total_seconds() * 1000),
    )
    budgets = AgentRunBudgets(
        max_steps=max_steps,
        timeout_seconds=timeout_seconds,
        max_tokens_per_turn=max_tokens_per_turn,
        max_total_tokens=max_total_tokens,
        temperature=temperature,
    )

    payload = {
        "schema_version": AGENT_RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "task_id": task.id,
        "source_task_id": task.source_task_id,
        "condition": condition.id,
        "repetition_index": repetition_index,
        "model_provider": provider,
        "model": model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": terminal_status,
        "budgets": budgets.to_dict(),
        "timings_ms": timings.to_dict(),
        "prompt": {
            "system_prompt": system_prompt,
            "initial_user_prompt": initial_user_prompt,
            "available_tools": tool_inventory,
        },
        "steps": [step.to_dict() for step in steps],
        "tool_calls": [record.to_dict() for record in tool_call_records],
        "final_response_text": final_response_text,
        "final_response_parse_error": final_response_parse_error,
        "artifacts": artifact_capture.to_dict(),
        "task_command": task_command_result.to_dict(),
        "judge_result": judge_result,
        "scores": score_bundle.to_dict(),
        "failure": failure_detail.to_dict() if failure_detail is not None else None,
    }
    (run_dir / "run.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def run_turn_with_retry(
    *,
    agent_client: BaseAgentLLMClient,
    model: str,
    system_prompt: str,
    messages: list[dict[str, object]],
    tools: list[dict[str, object]],
    temperature: float,
    max_tokens: int,
) -> AgentTurnResult:
    errors: list[str] = []
    for _attempt in range(2):
        try:
            return agent_client.run_turn(
                model=model,
                system_prompt=system_prompt,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AgentLLMClientError as exc:
            errors.append(str(exc))
    raise AgentLLMClientError(errors[-1])


def execute_turn_tool_calls(
    *,
    tools: AgentTools,
    turn: AgentTurnResult,
    step_index: int,
    messages: list[dict[str, object]],
    tool_call_records: list[ToolCallRecord],
) -> tuple[AgentTerminalStatus, FailureDetail] | None:
    for tool_call in turn.tool_calls:
        started = datetime.now(timezone.utc)
        try:
            result = tools.execute(name=tool_call.name, arguments=tool_call.arguments)
            error = None
            status = "ok"
        except AgentToolError as exc:
            result = None
            error = str(exc)
            status = "error"
        finished = datetime.now(timezone.utc)

        tool_call_records.append(
            ToolCallRecord(
                step_index=step_index,
                call_id=tool_call.id,
                name=tool_call.name,
                arguments=tool_call.arguments,
                result=result,
                status=status,
                error=error,
                started_at=started.isoformat(),
                finished_at=finished.isoformat(),
                duration_ms=int((finished - started).total_seconds() * 1000),
            )
        )

        if error is not None:
            if tool_call.name == NIA_TOOL_NAME:
                return "retrieval_error", FailureDetail(kind="retrieval_error", detail=error)
            return "workspace_tool_error", FailureDetail(kind="workspace_tool_error", detail=error)

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
    return None


def collect_artifacts(*, task: AgentTask, workspace: AgentWorkspace) -> ArtifactCapture:
    found: list[str] = []
    missing: list[str] = []
    extracted_text: dict[str, str] = {}

    for spec in task.expected_artifacts:
        try:
            candidate = workspace.resolve_read_path(spec.path)
        except WorkspaceError:
            candidate = None
        if candidate is None or not candidate.exists() or not candidate.is_file():
            if spec.required:
                missing.append(spec.path)
            continue

        found.append(spec.path)
        raw = candidate.read_bytes()
        if spec.max_bytes is not None:
            raw = raw[: spec.max_bytes]
        extracted_text[spec.path] = raw.decode("utf-8", errors="replace")

    return ArtifactCapture(
        expected_artifacts=[artifact.to_dict() for artifact in task.expected_artifacts],
        found_artifacts=found,
        missing_artifacts=missing,
        extracted_text=extracted_text,
    )


def derive_task_command_result(*, task: AgentTask, tools: AgentTools) -> TaskCommandResult:
    if task.test_command is None:
        return TaskCommandResult(
            exists=False,
            ran=False,
            argv=None,
            cwd=None,
            timeout_seconds=None,
            exit_code=None,
            stdout=None,
            stderr=None,
            error=None,
        )

    last_run = None
    for log in tools.tool_logs:
        if log.get("tool_name") == "run_task_command":
            last_run = log

    if last_run is None:
        return TaskCommandResult(
            exists=True,
            ran=False,
            argv=task.test_command.argv,
            cwd=task.test_command.cwd,
            timeout_seconds=task.test_command.timeout_seconds,
            exit_code=None,
            stdout=None,
            stderr=None,
            error=None,
        )

    result = last_run.get("result") if isinstance(last_run.get("result"), dict) else {}
    return TaskCommandResult(
        exists=True,
        ran=True,
        argv=result.get("argv") if isinstance(result.get("argv"), list) else task.test_command.argv,
        cwd=result.get("cwd") if isinstance(result.get("cwd"), str) else task.test_command.cwd,
        timeout_seconds=(
            result.get("timeout_seconds")
            if isinstance(result.get("timeout_seconds"), int)
            else task.test_command.timeout_seconds
        ),
        exit_code=result.get("exit_code") if isinstance(result.get("exit_code"), int) else None,
        stdout=result.get("stdout") if isinstance(result.get("stdout"), str) else None,
        stderr=result.get("stderr") if isinstance(result.get("stderr"), str) else None,
        error=last_run.get("error") if isinstance(last_run.get("error"), str) else None,
    )


def parse_final_response_json(text: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if text is None:
        return None, None
    stripped = text.strip()
    if not stripped:
        return None, None

    candidate = _strip_code_fence(stripped)
    try:
        decoded = json.loads(candidate)
    except json.JSONDecodeError:
        blob = _extract_balanced_json_object(candidate)
        if blob is None:
            return None, "Could not find a JSON object in final response"
        try:
            decoded = json.loads(blob)
        except json.JSONDecodeError as exc:
            return None, f"Invalid final JSON: {exc}"

    if not isinstance(decoded, dict):
        return None, "Final JSON must be an object"
    return decoded, None


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return text


def _extract_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None
