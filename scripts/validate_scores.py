#!/usr/bin/env python3
"""Validate aggregated scores.json contract used by dashboard."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = {"generated_at", "summary", "libraries", "tasks"}
REQUIRED_SUMMARY = {
    "overall_without_nia",
    "overall_with_nia",
    "improvement_delta_pct",
    "tasks_evaluated",
    "evaluations_count",
    "unique_tasks",
    "nonperfect_baseline_without_nia",
    "nonperfect_baseline_with_nia",
    "nonperfect_baseline_delta_pct",
    "nonperfect_baseline_count",
    "perfect_baseline_without_nia",
    "perfect_baseline_with_nia",
    "perfect_baseline_delta_pct",
    "perfect_baseline_count",
    "libraries_covered",
    "models_tested",
}
REQUIRED_LIBRARY = {
    "id",
    "label",
    "tasks",
    "without_nia",
    "with_nia",
    "delta_pct",
}


def load_payload(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("scores file must be a JSON object")
    return payload


def validate_scores(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing_top = REQUIRED_TOP_LEVEL - payload.keys()
    if missing_top:
        errors.append(f"missing top-level fields: {', '.join(sorted(missing_top))}")
        return errors

    generated_at = payload["generated_at"]
    if generated_at is not None and not isinstance(generated_at, str):
        errors.append("generated_at must be string or null")

    summary = payload["summary"]
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
    else:
        missing_summary = REQUIRED_SUMMARY - summary.keys()
        if missing_summary:
            errors.append(f"summary missing fields: {', '.join(sorted(missing_summary))}")
        else:
            _validate_number_or_null(summary, "overall_without_nia", errors)
            _validate_number_or_null(summary, "overall_with_nia", errors)
            _validate_number_or_null(summary, "improvement_delta_pct", errors)
            _validate_number_or_null(summary, "nonperfect_baseline_without_nia", errors)
            _validate_number_or_null(summary, "nonperfect_baseline_with_nia", errors)
            _validate_number_or_null(summary, "nonperfect_baseline_delta_pct", errors)
            _validate_number_or_null(summary, "perfect_baseline_without_nia", errors)
            _validate_number_or_null(summary, "perfect_baseline_with_nia", errors)
            _validate_number_or_null(summary, "perfect_baseline_delta_pct", errors)

            if not isinstance(summary.get("tasks_evaluated"), int):
                errors.append("summary.tasks_evaluated must be an integer")
            if not isinstance(summary.get("evaluations_count"), int):
                errors.append("summary.evaluations_count must be an integer")
            if not isinstance(summary.get("unique_tasks"), int):
                errors.append("summary.unique_tasks must be an integer")
            if not isinstance(summary.get("nonperfect_baseline_count"), int):
                errors.append("summary.nonperfect_baseline_count must be an integer")
            if not isinstance(summary.get("perfect_baseline_count"), int):
                errors.append("summary.perfect_baseline_count must be an integer")
            if not isinstance(summary.get("libraries_covered"), int):
                errors.append("summary.libraries_covered must be an integer")

            if isinstance(summary.get("tasks_evaluated"), int) and isinstance(
                summary.get("evaluations_count"), int
            ):
                if summary["tasks_evaluated"] != summary["evaluations_count"]:
                    errors.append(
                        "summary.tasks_evaluated must equal summary.evaluations_count"
                    )

            if isinstance(summary.get("nonperfect_baseline_count"), int) and isinstance(
                summary.get("perfect_baseline_count"), int
            ) and isinstance(summary.get("evaluations_count"), int):
                if (
                    summary["nonperfect_baseline_count"] + summary["perfect_baseline_count"]
                    != summary["evaluations_count"]
                ):
                    errors.append(
                        "summary.nonperfect_baseline_count + summary.perfect_baseline_count "
                        "must equal summary.evaluations_count"
                    )

            models_tested = summary.get("models_tested")
            if not isinstance(models_tested, list) or not all(
                isinstance(item, str) for item in models_tested
            ):
                errors.append("summary.models_tested must be an array of strings")

    libraries = payload["libraries"]
    if not isinstance(libraries, list):
        errors.append("libraries must be an array")
    else:
        for index, item in enumerate(libraries):
            prefix = f"libraries[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            missing = REQUIRED_LIBRARY - item.keys()
            if missing:
                errors.append(f"{prefix} missing fields: {', '.join(sorted(missing))}")
                continue

            if not isinstance(item["id"], str) or not item["id"].strip():
                errors.append(f"{prefix}.id must be a non-empty string")
            if not isinstance(item["label"], str) or not item["label"].strip():
                errors.append(f"{prefix}.label must be a non-empty string")
            if not isinstance(item["tasks"], int):
                errors.append(f"{prefix}.tasks must be an integer")
            _validate_number_or_null(item, "without_nia", errors, prefix=prefix)
            _validate_number_or_null(item, "with_nia", errors, prefix=prefix)
            _validate_number_or_null(item, "delta_pct", errors, prefix=prefix)

    tasks = payload["tasks"]
    if not isinstance(tasks, list):
        errors.append("tasks must be an array")

    return errors


def _validate_number_or_null(
    obj: dict[str, Any],
    key: str,
    errors: list[str],
    *,
    prefix: str = "summary",
) -> None:
    value = obj.get(key)
    if value is not None and not isinstance(value, (int, float)):
        errors.append(f"{prefix}.{key} must be a number or null")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python3 scripts/validate_scores.py <results/scores.json>", file=sys.stderr)
        return 1

    path = Path(argv[1])
    try:
        payload = load_payload(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    errors = validate_scores(payload)
    if errors:
        print(f"{path}: validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"{path}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
