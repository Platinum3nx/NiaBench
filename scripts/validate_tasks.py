#!/usr/bin/env python3
"""Validate NiaBench task files without external dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "id",
    "library",
    "version_introduced",
    "task_description",
    "deprecated_pattern",
    "correct_pattern",
    "reference_solution",
    "difficulty",
    "category",
    "executable",
    "why_models_fail_this",
}

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_CATEGORIES = {
    "api-migration",
    "import-path",
    "config-schema",
    "type-signature",
    "best-practice",
}
TASK_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
VERSION_HINT_PATTERN = re.compile(r"\d")


def load_tasks(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON array at the top level")
    return data


def validate_task(task: dict[str, Any], index: int, seen_ids: set[str]) -> list[str]:
    errors: list[str] = []
    prefix = f"task[{index}]"

    if not isinstance(task, dict):
        return [f"{prefix}: expected an object"]

    missing = REQUIRED_FIELDS - task.keys()
    extra = set(task.keys()) - REQUIRED_FIELDS
    if missing:
        errors.append(f"{prefix}: missing fields: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{prefix}: unexpected fields: {', '.join(sorted(extra))}")
    if missing:
        return errors

    task_id = task["id"]
    if not isinstance(task_id, str) or not TASK_ID_PATTERN.fullmatch(task_id):
        errors.append(f"{prefix}.id: must match {TASK_ID_PATTERN.pattern}")
    elif task_id in seen_ids:
        errors.append(f"{prefix}.id: duplicate id '{task_id}'")
    else:
        seen_ids.add(task_id)

    string_fields = {
        "library": 2,
        "version_introduced": 1,
        "task_description": 20,
        "deprecated_pattern": 3,
        "correct_pattern": 3,
        "why_models_fail_this": 20,
    }
    for field_name, min_length in string_fields.items():
        value = task[field_name]
        if not isinstance(value, str) or len(value.strip()) < min_length:
            errors.append(f"{prefix}.{field_name}: must be a string of length >= {min_length}")

    if isinstance(task["version_introduced"], str) and not VERSION_HINT_PATTERN.search(
        task["version_introduced"]
    ):
        errors.append(f"{prefix}.version_introduced: should contain a recognizable version hint")

    reference_solution = task["reference_solution"]
    if reference_solution is not None and not isinstance(reference_solution, str):
        errors.append(f"{prefix}.reference_solution: must be a string or null")

    executable = task["executable"]
    if not isinstance(executable, bool):
        errors.append(f"{prefix}.executable: must be a boolean")
    elif executable and (not isinstance(reference_solution, str) or not reference_solution.strip()):
        errors.append(f"{prefix}.reference_solution: executable tasks require a non-empty solution")

    difficulty = task["difficulty"]
    if difficulty not in ALLOWED_DIFFICULTIES:
        errors.append(
            f"{prefix}.difficulty: must be one of {', '.join(sorted(ALLOWED_DIFFICULTIES))}"
        )

    category = task["category"]
    if category not in ALLOWED_CATEGORIES:
        errors.append(
            f"{prefix}.category: must be one of {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    deprecated_pattern = task["deprecated_pattern"]
    correct_pattern = task["correct_pattern"]
    if (
        isinstance(deprecated_pattern, str)
        and isinstance(correct_pattern, str)
        and deprecated_pattern.strip() == correct_pattern.strip()
    ):
        errors.append(f"{prefix}: deprecated_pattern and correct_pattern must be different")

    return errors


def validate_file(path: Path) -> int:
    try:
        tasks = load_tasks(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, task in enumerate(tasks):
        errors.extend(validate_task(task, index, seen_ids))

    if errors:
        print(f"{path}: validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"{path}: OK ({len(tasks)} task(s))")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/validate_tasks.py <tasks.json> [more files...]", file=sys.stderr)
        return 1

    exit_code = 0
    for raw_path in argv[1:]:
        result = validate_file(Path(raw_path))
        if result != 0:
            exit_code = result
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
