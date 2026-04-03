#!/usr/bin/env python3
"""Validate Layer 2 agent task wrappers and seed workspace references."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
TASK_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
RELATIVE_PATH_PATTERN = re.compile(r"^(?!/)(?!.*\.\.)(?!.*\*)(?!.*//)[A-Za-z0-9._@/-]+$")

REQUIRED_FIELDS = {
    "id",
    "source_task_id",
    "library",
    "version_introduced",
    "category",
    "difficulty",
    "agent_goal",
    "workspace_seed",
    "expected_artifacts",
    "allowed_output_paths",
    "retrieval_hints",
}
OPTIONAL_FIELDS = {"test_command", "success_notes"}

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_CATEGORIES = {
    "api-migration",
    "import-path",
    "config-schema",
    "type-signature",
    "best-practice",
}
ALLOWED_ARTIFACT_KINDS = {"code_file", "config_file", "text_file", "json_file"}

HINT_LEAKAGE_MARKERS = {
    "correct_pattern",
    "reference_solution",
    "deprecated_pattern",
    "why_models_fail_this",
    "rubric",
}


def load_task_source_ids() -> set[str]:
    source_path = REPO_ROOT / "dataset/tasks.json"
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    if not isinstance(payload, list):
        return set()
    source_ids: set[str] = set()
    for item in payload:
        if isinstance(item, dict):
            task_id = item.get("id")
            if isinstance(task_id, str):
                source_ids.add(task_id)
    return source_ids


def load_tasks(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path}: expected top-level JSON array")
    return payload


def validate_file(path: Path, source_task_ids: set[str]) -> int:
    try:
        tasks = load_tasks(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 1

    seen_ids: set[str] = set()
    errors: list[str] = []
    for index, task in enumerate(tasks):
        errors.extend(validate_task(task, index, path, seen_ids, source_task_ids))

    if errors:
        print(f"{path}: validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"{path}: OK ({len(tasks)} task(s))")
    return 0


def validate_task(
    task: Any,
    index: int,
    path: Path,
    seen_ids: set[str],
    source_task_ids: set[str],
) -> list[str]:
    prefix = f"{path}: task[{index}]"
    if not isinstance(task, dict):
        return [f"{prefix} must be an object"]

    errors: list[str] = []
    keys = set(task.keys())
    missing = REQUIRED_FIELDS - keys
    extra = keys - REQUIRED_FIELDS - OPTIONAL_FIELDS
    if missing:
        errors.append(f"{prefix} missing required fields: {', '.join(sorted(missing))}")
        return errors
    if extra:
        errors.append(f"{prefix} contains unsupported fields: {', '.join(sorted(extra))}")

    task_id = task.get("id")
    source_task_id = task.get("source_task_id")
    library = task.get("library")
    version_introduced = task.get("version_introduced")
    category = task.get("category")
    difficulty = task.get("difficulty")
    agent_goal = task.get("agent_goal")

    if not _is_task_id(task_id):
        errors.append(f"{prefix}.id must match {TASK_ID_PATTERN.pattern}")
    elif task_id in seen_ids:
        errors.append(f"{prefix}.id duplicate id '{task_id}'")
    else:
        seen_ids.add(task_id)

    if not _is_task_id(source_task_id):
        errors.append(f"{prefix}.source_task_id must match {TASK_ID_PATTERN.pattern}")
    elif source_task_ids and source_task_id not in source_task_ids:
        errors.append(f"{prefix}.source_task_id '{source_task_id}' not found in dataset/tasks.json")

    if not isinstance(library, str) or len(library.strip()) < 2:
        errors.append(f"{prefix}.library must be a non-empty string")
    if not isinstance(version_introduced, str) or not version_introduced.strip():
        errors.append(f"{prefix}.version_introduced must be a non-empty string")
    if category not in ALLOWED_CATEGORIES:
        errors.append(f"{prefix}.category must be one of {', '.join(sorted(ALLOWED_CATEGORIES))}")
    if difficulty not in ALLOWED_DIFFICULTIES:
        errors.append(
            f"{prefix}.difficulty must be one of {', '.join(sorted(ALLOWED_DIFFICULTIES))}"
        )
    if not isinstance(agent_goal, str) or len(agent_goal.strip()) < 20:
        errors.append(f"{prefix}.agent_goal must be a string with length >= 20")

    workspace_seed = task.get("workspace_seed")
    errors.extend(validate_workspace_seed(workspace_seed, prefix))

    allowed_output_paths_raw = task.get("allowed_output_paths")
    allowed_output_paths: set[str] = set()
    if not isinstance(allowed_output_paths_raw, list) or not allowed_output_paths_raw:
        errors.append(f"{prefix}.allowed_output_paths must be a non-empty array")
    else:
        for item_index, item in enumerate(allowed_output_paths_raw):
            if not isinstance(item, str) or not _is_relative_output_path(item):
                errors.append(
                    f"{prefix}.allowed_output_paths[{item_index}] must be an exact relative path"
                )
            elif item in allowed_output_paths:
                errors.append(f"{prefix}.allowed_output_paths duplicate path '{item}'")
            else:
                allowed_output_paths.add(item)

    expected_artifacts = task.get("expected_artifacts")
    if not isinstance(expected_artifacts, list) or not expected_artifacts:
        errors.append(f"{prefix}.expected_artifacts must be a non-empty array")
    else:
        for artifact_index, artifact in enumerate(expected_artifacts):
            errors.extend(
                validate_artifact_spec(
                    artifact=artifact,
                    prefix=f"{prefix}.expected_artifacts[{artifact_index}]",
                    allowed_output_paths=allowed_output_paths,
                )
            )

    retrieval_hints = task.get("retrieval_hints")
    if not isinstance(retrieval_hints, list):
        errors.append(f"{prefix}.retrieval_hints must be an array")
    else:
        for hint_index, hint in enumerate(retrieval_hints):
            if not isinstance(hint, str) or not hint.strip():
                errors.append(f"{prefix}.retrieval_hints[{hint_index}] must be a non-empty string")
                continue
            lowered = hint.lower()
            for marker in HINT_LEAKAGE_MARKERS:
                if marker in lowered:
                    errors.append(
                        f"{prefix}.retrieval_hints[{hint_index}] appears answer-bearing via '{marker}'"
                    )
                    break

    test_command = task.get("test_command")
    if test_command is not None:
        errors.extend(validate_test_command(test_command, prefix))

    success_notes = task.get("success_notes")
    if success_notes is not None and not isinstance(success_notes, str):
        errors.append(f"{prefix}.success_notes must be a string or null")

    return errors


def validate_workspace_seed(workspace_seed: Any, prefix: str) -> list[str]:
    if not isinstance(workspace_seed, dict):
        return [f"{prefix}.workspace_seed must be an object"]

    errors: list[str] = []
    if set(workspace_seed.keys()) != {"seed_dir"}:
        errors.append(f"{prefix}.workspace_seed supports only 'seed_dir'")

    seed_dir = workspace_seed.get("seed_dir")
    if not isinstance(seed_dir, str) or not seed_dir.strip():
        errors.append(f"{prefix}.workspace_seed.seed_dir must be a non-empty string")
        return errors
    if not RELATIVE_PATH_PATTERN.fullmatch(seed_dir):
        errors.append(f"{prefix}.workspace_seed.seed_dir must be a safe relative path")
        return errors

    seed_path = REPO_ROOT / seed_dir
    if not seed_path.exists():
        errors.append(f"{prefix}.workspace_seed.seed_dir does not exist: {seed_dir}")
    elif not seed_path.is_dir():
        errors.append(f"{prefix}.workspace_seed.seed_dir must be a directory: {seed_dir}")
    else:
        has_files = any(child.is_file() for child in seed_path.rglob("*"))
        if not has_files:
            errors.append(f"{prefix}.workspace_seed.seed_dir is empty: {seed_dir}")
    return errors


def validate_artifact_spec(
    *,
    artifact: Any,
    prefix: str,
    allowed_output_paths: set[str],
) -> list[str]:
    if not isinstance(artifact, dict):
        return [f"{prefix} must be an object"]

    errors: list[str] = []
    keys = set(artifact.keys())
    required = {"path", "kind"}
    optional = {"required", "max_bytes"}
    missing = required - keys
    extra = keys - required - optional
    if missing:
        errors.append(f"{prefix} missing required fields: {', '.join(sorted(missing))}")
        return errors
    if extra:
        errors.append(f"{prefix} contains unsupported fields: {', '.join(sorted(extra))}")

    artifact_path = artifact.get("path")
    if not isinstance(artifact_path, str) or not _is_relative_output_path(artifact_path):
        errors.append(f"{prefix}.path must be an exact relative path")
    elif allowed_output_paths and artifact_path not in allowed_output_paths:
        errors.append(f"{prefix}.path must be listed in allowed_output_paths: {artifact_path}")

    kind = artifact.get("kind")
    if kind not in ALLOWED_ARTIFACT_KINDS:
        errors.append(f"{prefix}.kind must be one of {', '.join(sorted(ALLOWED_ARTIFACT_KINDS))}")

    required_value = artifact.get("required", True)
    if not isinstance(required_value, bool):
        errors.append(f"{prefix}.required must be a boolean when provided")

    max_bytes = artifact.get("max_bytes")
    if max_bytes is not None and (not isinstance(max_bytes, int) or max_bytes <= 0):
        errors.append(f"{prefix}.max_bytes must be a positive integer or null")

    return errors


def validate_test_command(test_command: Any, prefix: str) -> list[str]:
    if not isinstance(test_command, dict):
        return [f"{prefix}.test_command must be an object"]

    errors: list[str] = []
    keys = set(test_command.keys())
    required = {"argv"}
    optional = {"cwd", "timeout_seconds"}
    missing = required - keys
    extra = keys - required - optional
    if missing:
        errors.append(f"{prefix}.test_command missing required fields: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{prefix}.test_command contains unsupported fields: {', '.join(sorted(extra))}")

    argv = test_command.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
        errors.append(f"{prefix}.test_command.argv must be a non-empty array of strings")

    cwd = test_command.get("cwd", ".")
    if not isinstance(cwd, str) or not cwd:
        errors.append(f"{prefix}.test_command.cwd must be a non-empty string")
    elif cwd != "." and not RELATIVE_PATH_PATTERN.fullmatch(cwd):
        errors.append(f"{prefix}.test_command.cwd must be '.' or a safe relative path")

    timeout_seconds = test_command.get("timeout_seconds", 30)
    if not isinstance(timeout_seconds, int) or timeout_seconds <= 0:
        errors.append(f"{prefix}.test_command.timeout_seconds must be a positive integer")

    return errors


def _is_task_id(value: Any) -> bool:
    return isinstance(value, str) and bool(TASK_ID_PATTERN.fullmatch(value))


def _is_relative_output_path(value: str) -> bool:
    return bool(RELATIVE_PATH_PATTERN.fullmatch(value))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: python3 scripts/validate_agent_tasks.py <tasks-layer2.json> [more files...]",
            file=sys.stderr,
        )
        return 1

    source_task_ids = load_task_source_ids()
    exit_code = 0
    for raw_path in argv[1:]:
        result = validate_file(Path(raw_path), source_task_ids)
        if result != 0:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
