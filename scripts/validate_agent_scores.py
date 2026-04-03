#!/usr/bin/env python3
"""Validate Layer 2 aggregate score contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


TOP_LEVEL_FIELDS = {"generated_at", "schema_version", "summary", "conditions", "libraries", "tasks"}
SUMMARY_FIELDS = {
    "delta_completed_only_pct",
    "delta_crash_aware_pct",
    "run_level_completion_rate",
    "run_level_crash_rate",
    "run_level_timeout_rate",
    "run_level_no_artifact_rate",
    "run_level_judge_error_rate",
    "nia_usage_rate",
    "avg_nia_calls_per_nia_run",
    "task_delta_ties",
    "task_delta_nia_positive",
    "task_delta_no_retrieval_positive",
    "pairwise_comparisons",
    "pairwise_nia_wins",
    "pairwise_ties",
    "pairwise_no_retrieval_wins",
    "pairwise_tie_rate",
    "unique_tasks",
    "total_runs",
    "model_provider",
    "model",
    "judge_provider",
    "judge_model",
}
CONDITION_FIELDS = {
    "condition",
    "total_runs",
    "unique_tasks",
    "completed_runs",
    "task_macro_completed_only_avg_quality_pct",
    "task_macro_crash_aware_avg_quality_pct",
    "run_level_completion_rate",
    "run_level_crash_rate",
    "run_level_timeout_rate",
    "run_level_no_artifact_rate",
    "run_level_judge_error_rate",
    "run_level_retrieval_error_rate",
    "run_level_workspace_tool_error_rate",
    "run_level_nia_tool_error_rate",
    "avg_tool_calls_per_run",
    "avg_tool_error_calls_per_run",
    "avg_nia_calls_per_run",
    "avg_nia_tool_error_calls_per_run",
    "nia_usage_rate",
    "avg_nia_calls_per_nia_run",
}
TASK_FIELDS = {
    "task_id",
    "library",
    "difficulty",
    "by_condition",
    "delta_completed_only_pct",
    "delta_crash_aware_pct",
    "pairwise_comparisons",
    "pairwise_nia_wins",
    "pairwise_ties",
    "pairwise_no_retrieval_wins",
}
LIBRARY_FIELDS = {
    "library",
    "tasks",
    "by_condition",
    "delta_completed_only_pct",
    "delta_crash_aware_pct",
    "pairwise_comparisons",
    "pairwise_nia_wins",
    "pairwise_ties",
    "pairwise_no_retrieval_wins",
}

CONDITIONS = {"no_retrieval_agent", "nia_agent"}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python3 scripts/validate_agent_scores.py <results/agent_scores.json>", file=sys.stderr)
        return 1

    path = Path(argv[1])
    try:
        payload = load_payload(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    errors = validate_payload(payload)
    if errors:
        print(f"{path}: validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"{path}: OK")
    return 0


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Aggregate payload must be an object")
    return payload


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing_top = TOP_LEVEL_FIELDS - payload.keys()
    if missing_top:
        errors.append(f"Missing top-level fields: {', '.join(sorted(missing_top))}")
        return errors

    schema_version = payload.get("schema_version")
    if schema_version != "nia.layer2.aggregate.v1":
        errors.append("schema_version must be nia.layer2.aggregate.v1")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
    else:
        missing_summary = SUMMARY_FIELDS - summary.keys()
        if missing_summary:
            errors.append(f"summary missing fields: {', '.join(sorted(missing_summary))}")
        else:
            validate_number_or_null(summary, "delta_completed_only_pct", errors, "summary")
            validate_number_or_null(summary, "delta_crash_aware_pct", errors, "summary")
            validate_number_or_null(summary, "nia_usage_rate", errors, "summary")
            validate_number_or_null(summary, "avg_nia_calls_per_nia_run", errors, "summary")
            validate_number_or_null(summary, "pairwise_tie_rate", errors, "summary")
            validate_percent_map(summary, "run_level_completion_rate", errors)
            validate_percent_map(summary, "run_level_crash_rate", errors)
            validate_percent_map(summary, "run_level_timeout_rate", errors)
            validate_percent_map(summary, "run_level_no_artifact_rate", errors)
            validate_percent_map(summary, "run_level_judge_error_rate", errors)
            for field in (
                "task_delta_ties",
                "task_delta_nia_positive",
                "task_delta_no_retrieval_positive",
                "pairwise_comparisons",
                "pairwise_nia_wins",
                "pairwise_ties",
                "pairwise_no_retrieval_wins",
                "unique_tasks",
                "total_runs",
            ):
                if not isinstance(summary.get(field), int):
                    errors.append(f"summary.{field} must be an integer")

    conditions = payload.get("conditions")
    if not isinstance(conditions, list):
        errors.append("conditions must be an array")
    else:
        seen_conditions: set[str] = set()
        for index, item in enumerate(conditions):
            prefix = f"conditions[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            missing = CONDITION_FIELDS - item.keys()
            if missing:
                errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
                continue
            condition = item.get("condition")
            if condition not in CONDITIONS:
                errors.append(f"{prefix}.condition must be one of {', '.join(sorted(CONDITIONS))}")
            else:
                seen_conditions.add(condition)
            for field in ("total_runs", "unique_tasks", "completed_runs"):
                if not isinstance(item.get(field), int):
                    errors.append(f"{prefix}.{field} must be an integer")
            for field in (
                "task_macro_completed_only_avg_quality_pct",
                "task_macro_crash_aware_avg_quality_pct",
                "run_level_completion_rate",
                "run_level_crash_rate",
                "run_level_timeout_rate",
                "run_level_no_artifact_rate",
                "run_level_judge_error_rate",
                "run_level_retrieval_error_rate",
                "run_level_workspace_tool_error_rate",
                "run_level_nia_tool_error_rate",
                "avg_tool_calls_per_run",
                "avg_tool_error_calls_per_run",
                "avg_nia_calls_per_run",
                "avg_nia_tool_error_calls_per_run",
                "nia_usage_rate",
                "avg_nia_calls_per_nia_run",
            ):
                validate_number_or_null(item, field, errors, prefix)
        if seen_conditions and seen_conditions != CONDITIONS:
            errors.append("conditions must include exactly no_retrieval_agent and nia_agent rows")

    libraries = payload.get("libraries")
    if not isinstance(libraries, list):
        errors.append("libraries must be an array")
    else:
        for index, item in enumerate(libraries):
            prefix = f"libraries[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            missing = LIBRARY_FIELDS - item.keys()
            if missing:
                errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
                continue
            if not isinstance(item.get("library"), str) or not str(item.get("library")).strip():
                errors.append(f"{prefix}.library must be a non-empty string")
            if not isinstance(item.get("tasks"), int):
                errors.append(f"{prefix}.tasks must be an integer")
            validate_number_or_null(item, "delta_completed_only_pct", errors, prefix)
            validate_number_or_null(item, "delta_crash_aware_pct", errors, prefix)
            for field in (
                "pairwise_comparisons",
                "pairwise_nia_wins",
                "pairwise_ties",
                "pairwise_no_retrieval_wins",
            ):
                if not isinstance(item.get(field), int):
                    errors.append(f"{prefix}.{field} must be an integer")
            validate_by_condition_map(item.get("by_condition"), errors, f"{prefix}.by_condition")

    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        errors.append("tasks must be an array")
    else:
        seen_task_ids: set[str] = set()
        for index, item in enumerate(tasks):
            prefix = f"tasks[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            missing = TASK_FIELDS - item.keys()
            if missing:
                errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
                continue
            task_id = item.get("task_id")
            if not isinstance(task_id, str) or not task_id.strip():
                errors.append(f"{prefix}.task_id must be a non-empty string")
            elif task_id in seen_task_ids:
                errors.append(f"{prefix}.task_id duplicate '{task_id}'")
            else:
                seen_task_ids.add(task_id)
            if not isinstance(item.get("library"), str):
                errors.append(f"{prefix}.library must be a string")
            if not isinstance(item.get("difficulty"), str):
                errors.append(f"{prefix}.difficulty must be a string")
            validate_number_or_null(item, "delta_completed_only_pct", errors, prefix)
            validate_number_or_null(item, "delta_crash_aware_pct", errors, prefix)
            for field in (
                "pairwise_comparisons",
                "pairwise_nia_wins",
                "pairwise_ties",
                "pairwise_no_retrieval_wins",
            ):
                if not isinstance(item.get(field), int):
                    errors.append(f"{prefix}.{field} must be an integer")
            validate_by_condition_map(item.get("by_condition"), errors, f"{prefix}.by_condition")

    return errors


def validate_number_or_null(obj: dict[str, Any], key: str, errors: list[str], prefix: str) -> None:
    value = obj.get(key)
    if value is not None and not isinstance(value, (int, float)):
        errors.append(f"{prefix}.{key} must be a number or null")


def validate_percent_map(summary: dict[str, Any], key: str, errors: list[str]) -> None:
    payload = summary.get(key)
    if not isinstance(payload, dict):
        errors.append(f"summary.{key} must be an object keyed by condition")
        return
    for condition in CONDITIONS:
        value = payload.get(condition)
        if value is not None and not isinstance(value, (int, float)):
            errors.append(f"summary.{key}.{condition} must be a number or null")


def validate_by_condition_map(value: Any, errors: list[str], prefix: str) -> None:
    if not isinstance(value, dict):
        errors.append(f"{prefix} must be an object")
        return
    for condition in CONDITIONS:
        entry = value.get(condition)
        if not isinstance(entry, dict):
            errors.append(f"{prefix}.{condition} must be an object")
            continue
        if "repetitions" in entry and not isinstance(entry.get("repetitions"), int):
            errors.append(f"{prefix}.{condition}.repetitions must be an integer")
        for key in (
            "completed_only_avg_quality_pct",
            "crash_aware_avg_quality_pct",
            "completion_rate",
            "completed_only_min_pct",
            "completed_only_max_pct",
            "completed_only_stddev_pct",
            "tasks",
        ):
            if key in entry and entry[key] is not None and not isinstance(entry[key], (int, float)):
                errors.append(f"{prefix}.{condition}.{key} must be a number or null")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
