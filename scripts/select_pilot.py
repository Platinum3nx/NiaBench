#!/usr/bin/env python3
"""Select a fixed 30-task pilot set from normalized candidates."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="dataset/tasks_raw.normalized.json",
        help="Normalized candidate tasks",
    )
    parser.add_argument(
        "--output",
        default="dataset/tasks_candidate_pilot.json",
        help="Selected pilot task output",
    )
    parser.add_argument(
        "--report",
        default="results/reports/pilot_selection.json",
        help="Selection report output",
    )
    parser.add_argument("--libraries", default="dataset/libraries.json", help="Library metadata path")
    parser.add_argument("--target-size", type=int, default=30)
    parser.add_argument("--required-libraries", type=int, default=20)
    parser.add_argument("--double-library-count", type=int, default=10)
    parser.add_argument("--strict-difficulty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates = load_json_array(Path(args.input))
    libraries = load_json_array(Path(args.libraries))

    expected_library_ids = [
        item["id"] for item in libraries if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]

    if len(expected_library_ids) < args.required_libraries:
        raise SystemExit(
            f"Library metadata only contains {len(expected_library_ids)} libraries; "
            f"expected at least {args.required_libraries}."
        )

    expected_library_ids = sorted(expected_library_ids)[: args.required_libraries]

    by_library: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in candidates:
        if not isinstance(task, dict):
            continue
        library = task.get("library")
        if isinstance(library, str):
            by_library[library].append(task)

    errors: list[str] = []
    missing_libraries = [library for library in expected_library_ids if library not in by_library]
    if missing_libraries:
        errors.append(
            "missing required libraries: " + ", ".join(missing_libraries)
        )

    for library in expected_library_ids:
        by_library[library] = sorted(
            by_library.get(library, []),
            key=_task_sort_key,
            reverse=True,
        )

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_per_library: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()

    # Pass 1: ensure one task per required library.
    for library in expected_library_ids:
        options = by_library.get(library, [])
        if not options:
            continue
        candidate = _pick_best_option(
            options,
            selected_ids=selected_ids,
            target_difficulty_counts=_target_difficulty_counts(size=args.target_size),
            current_difficulty_counts=difficulty_counts,
        )
        if candidate is None:
            errors.append(f"library '{library}' has no selectable task")
            continue
        selected.append(candidate)
        selected_ids.add(candidate["id"])
        selected_per_library[library] += 1
        difficulty_counts[candidate.get("difficulty", "")] += 1

    # Pass 2: add one extra task for exactly double-library-count libraries.
    while len(selected) < args.target_size:
        if len([lib for lib, count in selected_per_library.items() if count >= 2]) >= args.double_library_count:
            break

        library = _pick_library_for_second_task(
            expected_libraries=expected_library_ids,
            selected_per_library=selected_per_library,
            by_library=by_library,
            selected_ids=selected_ids,
            current_difficulty_counts=difficulty_counts,
            target_difficulty_counts=_target_difficulty_counts(size=args.target_size),
        )
        if library is None:
            errors.append("could not find additional libraries with selectable second task")
            break

        candidate = _pick_best_option(
            by_library[library],
            selected_ids=selected_ids,
            target_difficulty_counts=_target_difficulty_counts(size=args.target_size),
            current_difficulty_counts=difficulty_counts,
        )
        if candidate is None:
            errors.append(f"no selectable second task for library '{library}'")
            break

        selected.append(candidate)
        selected_ids.add(candidate["id"])
        selected_per_library[library] += 1
        difficulty_counts[candidate.get("difficulty", "")] += 1

    # Pass 3: if still short, fill from remaining valid candidates without exceeding two per library.
    if len(selected) < args.target_size:
        pool: list[dict[str, Any]] = []
        for library in expected_library_ids:
            if selected_per_library[library] >= 2:
                continue
            pool.extend(by_library[library])
        pool = sorted(pool, key=_task_sort_key, reverse=True)

        for candidate in pool:
            if len(selected) >= args.target_size:
                break
            task_id = candidate.get("id")
            library = candidate.get("library")
            if not isinstance(task_id, str) or not isinstance(library, str):
                continue
            if task_id in selected_ids:
                continue
            if selected_per_library[library] >= 2:
                continue
            selected.append(candidate)
            selected_ids.add(task_id)
            selected_per_library[library] += 1
            difficulty_counts[candidate.get("difficulty", "")] += 1

    report = build_report(
        selected=selected,
        selected_per_library=selected_per_library,
        difficulty_counts=difficulty_counts,
        target_size=args.target_size,
        double_library_count=args.double_library_count,
        required_library_ids=expected_library_ids,
        errors=errors,
    )

    strict_ok = True
    if args.strict_difficulty:
        target = _target_difficulty_counts(size=args.target_size)
        for level, expected_count in target.items():
            if difficulty_counts.get(level, 0) != expected_count:
                strict_ok = False
                errors.append(
                    f"difficulty '{level}' count {difficulty_counts.get(level, 0)} != required {expected_count}"
                )

    selection_ok = (
        len(selected) == args.target_size
        and len([library for library, count in selected_per_library.items() if count >= 2])
        == args.double_library_count
        and all(selected_per_library.get(library, 0) >= 1 for library in expected_library_ids)
        and strict_ok
        and not errors
    )

    report["selection_ok"] = selection_ok
    report["errors"] = errors

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    if not selection_ok:
        print(f"Selection failed. Report: {report_path}")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected_sorted = sorted(selected, key=lambda task: str(task.get("id", "")))
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(selected_sorted, handle, indent=2)

    print(f"Selected {len(selected_sorted)} pilot tasks -> {output_path}")
    print(f"Report: {report_path}")
    return 0


def load_json_array(path: Path) -> list[Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a top-level JSON array")
    return payload


def _task_sort_key(task: dict[str, Any]) -> tuple[int, int, int, str]:
    quality = len(str(task.get("why_models_fail_this", "")).strip())
    specificity = len(str(task.get("correct_pattern", "")).strip())
    description = len(str(task.get("task_description", "")).strip())
    task_id = str(task.get("id", ""))
    return quality, specificity, description, task_id


def _pick_best_option(
    options: list[dict[str, Any]],
    *,
    selected_ids: set[str],
    target_difficulty_counts: dict[str, int],
    current_difficulty_counts: Counter[str],
) -> dict[str, Any] | None:
    ranked: list[tuple[tuple[int, int, int, str], dict[str, Any]]] = []

    for task in options:
        task_id = task.get("id")
        difficulty = str(task.get("difficulty", ""))
        if not isinstance(task_id, str) or task_id in selected_ids:
            continue

        deficit = target_difficulty_counts.get(difficulty, 0) - current_difficulty_counts.get(difficulty, 0)
        sort_key = (deficit, *_task_sort_key(task))
        ranked.append((sort_key, task))

    if not ranked:
        return None

    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def _pick_library_for_second_task(
    *,
    expected_libraries: list[str],
    selected_per_library: Counter[str],
    by_library: dict[str, list[dict[str, Any]]],
    selected_ids: set[str],
    current_difficulty_counts: Counter[str],
    target_difficulty_counts: dict[str, int],
) -> str | None:
    candidates: list[tuple[tuple[int, int], str]] = []

    for library in expected_libraries:
        if selected_per_library[library] != 1:
            continue
        options = [task for task in by_library[library] if task.get("id") not in selected_ids]
        if not options:
            continue

        best_option = _pick_best_option(
            options,
            selected_ids=selected_ids,
            target_difficulty_counts=target_difficulty_counts,
            current_difficulty_counts=current_difficulty_counts,
        )
        if best_option is None:
            continue

        difficulty = str(best_option.get("difficulty", ""))
        deficit = target_difficulty_counts.get(difficulty, 0) - current_difficulty_counts.get(difficulty, 0)
        quality = _task_sort_key(best_option)[0]
        candidates.append(((deficit, quality), library))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _target_difficulty_counts(*, size: int) -> dict[str, int]:
    per_bucket = size // 3
    return {"easy": per_bucket, "medium": per_bucket, "hard": per_bucket}


def build_report(
    *,
    selected: list[dict[str, Any]],
    selected_per_library: Counter[str],
    difficulty_counts: Counter[str],
    target_size: int,
    double_library_count: int,
    required_library_ids: list[str],
    errors: list[str],
) -> dict[str, Any]:
    doubles = sorted([library for library, count in selected_per_library.items() if count >= 2])
    missing = sorted([library for library in required_library_ids if selected_per_library.get(library, 0) == 0])

    return {
        "target_size": target_size,
        "selected_count": len(selected),
        "required_library_count": len(required_library_ids),
        "missing_libraries": missing,
        "libraries_with_two_tasks": doubles,
        "libraries_with_two_tasks_count": len(doubles),
        "expected_libraries_with_two_tasks": double_library_count,
        "difficulty_counts": {
            "easy": difficulty_counts.get("easy", 0),
            "medium": difficulty_counts.get("medium", 0),
            "hard": difficulty_counts.get("hard", 0),
        },
        "selected_task_ids": sorted(str(task.get("id", "")) for task in selected),
        "errors": list(errors),
    }


if __name__ == "__main__":
    raise SystemExit(main())
