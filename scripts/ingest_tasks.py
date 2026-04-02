#!/usr/bin/env python3
"""Ingest, normalize, and summarize raw benchmark task batches."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
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

DIFFICULTY_ALIASES = {
    "easy": "easy",
    "beginner": "easy",
    "low": "easy",
    "medium": "medium",
    "intermediate": "medium",
    "moderate": "medium",
    "hard": "hard",
    "advanced": "hard",
    "high": "hard",
}

CATEGORY_ALIASES = {
    "api-migration": "api-migration",
    "api_migration": "api-migration",
    "migration": "api-migration",
    "import-path": "import-path",
    "import_path": "import-path",
    "imports": "import-path",
    "config-schema": "config-schema",
    "config_schema": "config-schema",
    "config": "config-schema",
    "type-signature": "type-signature",
    "type_signature": "type-signature",
    "types": "type-signature",
    "best-practice": "best-practice",
    "best_practice": "best-practice",
    "bestpractice": "best-practice",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", default="dataset/tasks_raw.json", help="Path to raw generated tasks")
    parser.add_argument(
        "--normalized-output",
        default="dataset/tasks_raw.normalized.json",
        help="Path to write normalized valid tasks",
    )
    parser.add_argument(
        "--report",
        default="results/reports/intake.json",
        help="Path to write intake report",
    )
    parser.add_argument("--libraries", default="dataset/libraries.json", help="Library metadata path")
    parser.add_argument("--near-dup-threshold", type=float, default=0.92)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_path = Path(args.raw)
    libraries_path = Path(args.libraries)

    raw_tasks = load_json_array(raw_path)
    libraries = load_json_array(libraries_path)
    library_aliases, expected_library_ids = build_library_aliases(libraries)

    normalized: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []

    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()

    for index, raw in enumerate(raw_tasks):
        if not isinstance(raw, dict):
            invalid.append(
                {
                    "index": index,
                    "id": None,
                    "errors": ["task must be an object"],
                }
            )
            continue

        candidate = normalize_task(raw=raw, index=index, library_aliases=library_aliases)
        task_id = candidate.get("id")

        if isinstance(task_id, str):
            if task_id in seen_ids:
                duplicate_ids.add(task_id)
            else:
                seen_ids.add(task_id)

        errors = validate_task(candidate)
        if errors:
            invalid.append({"index": index, "id": task_id, "errors": errors})
            continue

        normalized.append(candidate)

    normalized = dedupe_by_id(normalized)
    exact_duplicates = detect_exact_duplicates(normalized)
    near_duplicates = detect_near_duplicates(normalized, threshold=args.near_dup_threshold)

    coverage = summarize_coverage(normalized)
    pilot_readiness = summarize_pilot_readiness(
        normalized_tasks=normalized,
        expected_library_ids=expected_library_ids,
    )

    normalized_path = Path(args.normalized_output)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    with normalized_path.open("w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=2)

    report_payload = {
        "raw_file": str(raw_path),
        "normalized_output": str(normalized_path),
        "raw_count": len(raw_tasks),
        "valid_count": len(normalized),
        "invalid_count": len(invalid),
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_ids": sorted(duplicate_ids),
        "exact_duplicate_pairs": exact_duplicates,
        "near_duplicate_pairs": near_duplicates,
        "coverage": coverage,
        "pilot_readiness": pilot_readiness,
        "invalid_examples": invalid[:200],
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report_payload, handle, indent=2)

    print(
        f"Ingested {len(raw_tasks)} raw tasks -> {len(normalized)} valid normalized tasks. "
        f"Report: {report_path}"
    )
    return 0


def load_json_array(path: Path) -> list[Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a top-level JSON array")
    return payload


def build_library_aliases(libraries: list[Any]) -> tuple[dict[str, str], set[str]]:
    aliases: dict[str, str] = {}
    expected_ids: set[str] = set()

    for item in libraries:
        if not isinstance(item, dict):
            continue
        library_id = item.get("id")
        label = item.get("label")
        if not isinstance(library_id, str):
            continue

        expected_ids.add(library_id)
        aliases[_canonical_library_token(library_id)] = library_id
        aliases[_canonical_library_token(library_id.replace("-", " "))] = library_id

        if isinstance(label, str):
            aliases[_canonical_library_token(label)] = library_id
            aliases[_canonical_library_token(label.replace("/", " "))] = library_id

    return aliases, expected_ids


def normalize_task(
    *,
    raw: dict[str, Any],
    index: int,
    library_aliases: dict[str, str],
) -> dict[str, Any]:
    task_id = raw.get("id")
    if not isinstance(task_id, str) or not task_id.strip():
        task_id = f"generated-task-{index+1:04d}"

    task_id = slugify(task_id)

    raw_library = raw.get("library")
    library = normalize_library(raw_library, library_aliases)

    difficulty = normalize_difficulty(raw.get("difficulty"))
    category = normalize_category(raw.get("category"))
    executable = normalize_executable(raw.get("executable"))

    reference_solution = raw.get("reference_solution")
    if reference_solution is not None and not isinstance(reference_solution, str):
        reference_solution = str(reference_solution)

    normalized = {
        "id": task_id,
        "library": library,
        "version_introduced": _as_text(raw.get("version_introduced")),
        "task_description": _as_text(raw.get("task_description")),
        "deprecated_pattern": _as_text(raw.get("deprecated_pattern")),
        "correct_pattern": _as_text(raw.get("correct_pattern")),
        "reference_solution": reference_solution,
        "difficulty": difficulty,
        "category": category,
        "executable": executable,
        "why_models_fail_this": _as_text(raw.get("why_models_fail_this")),
    }
    return normalized


def normalize_library(value: Any, aliases: dict[str, str]) -> str:
    if not isinstance(value, str):
        return ""
    token = _canonical_library_token(value)
    return aliases.get(token, slugify(value))


def normalize_difficulty(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    token = value.strip().lower()
    return DIFFICULTY_ALIASES.get(token, token)


def normalize_category(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    token = value.strip().lower().replace(" ", "-")
    return CATEGORY_ALIASES.get(token, token)


def normalize_executable(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return False


def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = REQUIRED_FIELDS - task.keys()
    if missing:
        errors.append(f"missing fields: {', '.join(sorted(missing))}")
        return errors

    task_id = task["id"]
    if not isinstance(task_id, str) or not re.fullmatch(r"^[a-z0-9-]+$", task_id):
        errors.append("id must match ^[a-z0-9-]+$")

    for key, min_len in {
        "library": 2,
        "version_introduced": 1,
        "task_description": 20,
        "deprecated_pattern": 3,
        "correct_pattern": 3,
        "why_models_fail_this": 20,
    }.items():
        value = task.get(key)
        if not isinstance(value, str) or len(value.strip()) < min_len:
            errors.append(f"{key} must be string length >= {min_len}")

    reference_solution = task.get("reference_solution")
    if reference_solution is not None and not isinstance(reference_solution, str):
        errors.append("reference_solution must be string or null")

    executable = task.get("executable")
    if not isinstance(executable, bool):
        errors.append("executable must be boolean")
    elif executable and (not isinstance(reference_solution, str) or not reference_solution.strip()):
        errors.append("executable tasks require non-empty reference_solution")

    difficulty = task.get("difficulty")
    if difficulty not in ALLOWED_DIFFICULTIES:
        errors.append("difficulty must be one of easy, medium, hard")

    category = task.get("category")
    if category not in ALLOWED_CATEGORIES:
        errors.append(
            "category must be one of api-migration, import-path, config-schema, type-signature, best-practice"
        )

    if task.get("deprecated_pattern") == task.get("correct_pattern"):
        errors.append("deprecated_pattern and correct_pattern must be different")

    return errors


def dedupe_by_id(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()

    for task in tasks:
        task_id = task.get("id")
        if not isinstance(task_id, str):
            continue
        if task_id in seen:
            continue
        seen.add(task_id)
        deduped.append(task)
    return deduped


def detect_exact_duplicates(tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_key: dict[str, list[str]] = defaultdict(list)

    for task in tasks:
        library = str(task.get("library", ""))
        description = canonical_text(str(task.get("task_description", "")))
        key = f"{library}::{description}"
        by_key[key].append(str(task.get("id", "")))

    duplicates: list[dict[str, str]] = []
    for task_ids in by_key.values():
        if len(task_ids) <= 1:
            continue
        first = task_ids[0]
        for duplicate in task_ids[1:]:
            duplicates.append({"base": first, "duplicate": duplicate, "kind": "exact"})
    return duplicates


def detect_near_duplicates(tasks: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    by_library: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        library = str(task.get("library", ""))
        by_library[library].append(task)

    near: list[dict[str, Any]] = []
    for library, items in by_library.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a = canonical_text(str(items[i].get("task_description", "")))
                b = canonical_text(str(items[j].get("task_description", "")))
                if not a or not b:
                    continue
                ratio = SequenceMatcher(None, a, b).ratio()
                if ratio >= threshold:
                    near.append(
                        {
                            "library": library,
                            "a": str(items[i].get("id", "")),
                            "b": str(items[j].get("id", "")),
                            "similarity": round(ratio, 4),
                        }
                    )
    return near


def summarize_coverage(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    by_library = Counter(str(task.get("library", "")) for task in tasks)
    by_difficulty = Counter(str(task.get("difficulty", "")) for task in tasks)
    by_category = Counter(str(task.get("category", "")) for task in tasks)
    by_executable = Counter(bool(task.get("executable")) for task in tasks)

    return {
        "libraries": dict(sorted(by_library.items())),
        "difficulty": dict(sorted(by_difficulty.items())),
        "category": dict(sorted(by_category.items())),
        "executable": {"true": by_executable.get(True, 0), "false": by_executable.get(False, 0)},
    }


def summarize_pilot_readiness(
    *,
    normalized_tasks: list[dict[str, Any]],
    expected_library_ids: set[str],
) -> dict[str, Any]:
    by_library = Counter(str(task.get("library", "")) for task in normalized_tasks)
    by_difficulty = Counter(str(task.get("difficulty", "")) for task in normalized_tasks)

    covered_libraries = {library for library in by_library if library}
    missing_libraries = sorted(expected_library_ids - covered_libraries)
    libraries_with_two_plus = sorted([library for library, count in by_library.items() if count >= 2])

    all_libraries_represented = expected_library_ids.issubset(covered_libraries)
    has_min_tasks = len(normalized_tasks) >= 30
    has_10_double = len(libraries_with_two_plus) >= 10

    total_difficulty = (
        by_difficulty.get("easy", 0) + by_difficulty.get("medium", 0) + by_difficulty.get("hard", 0)
    )
    balanced_difficulty_possible = total_difficulty >= 30 and all(
        by_difficulty.get(level, 0) >= 10 for level in ("easy", "medium", "hard")
    )

    return {
        "valid_task_count": len(normalized_tasks),
        "has_min_30_tasks": has_min_tasks,
        "libraries_covered_count": len(covered_libraries),
        "all_20_libraries_represented": all_libraries_represented,
        "missing_libraries": missing_libraries,
        "libraries_with_two_plus_count": len(libraries_with_two_plus),
        "libraries_with_two_plus": libraries_with_two_plus,
        "has_10_libraries_with_two_plus": has_10_double,
        "difficulty_counts": {
            "easy": by_difficulty.get("easy", 0),
            "medium": by_difficulty.get("medium", 0),
            "hard": by_difficulty.get("hard", 0),
        },
        "difficulty_balance_possible_for_30": balanced_difficulty_possible,
        "can_form_fixed_pilot": has_min_tasks and all_libraries_represented and has_10_double,
    }


def _canonical_library_token(value: str) -> str:
    token = value.strip().lower()
    token = re.sub(r"[^a-z0-9]+", "-", token)
    token = re.sub(r"-+", "-", token).strip("-")
    return token


def canonical_text(value: str) -> str:
    return " ".join(value.lower().split())


def slugify(value: str) -> str:
    token = value.strip().lower()
    token = re.sub(r"[^a-z0-9]+", "-", token)
    token = re.sub(r"-+", "-", token).strip("-")
    return token or "generated-task"


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


if __name__ == "__main__":
    raise SystemExit(main())
