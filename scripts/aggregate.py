#!/usr/bin/env python3
"""Aggregate raw per-task eval artifacts into results/scores.json."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="results/raw_curated/combined",
        help=(
            "Directory containing raw task artifacts. "
            "Use results/raw_curated/combined for founder-facing aggregates."
        ),
    )
    parser.add_argument("--output", default="results/scores.json", help="Aggregate score output path")
    parser.add_argument("--libraries", default="dataset/libraries.json", help="Library metadata path")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow writing an empty aggregate when no raw artifacts are present",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input)
    output_path = Path(args.output)

    result_files = sorted(path for path in input_dir.rglob("*.json") if path.is_file())
    if not result_files and not args.allow_empty:
        raise SystemExit(
            f"No raw result files found under {input_dir}. "
            "Use --allow-empty only when intentionally creating an empty aggregate."
        )

    library_labels = load_library_labels(Path(args.libraries))
    task_rows: list[dict[str, Any]] = []

    for path in result_files:
        payload = load_json(path)
        if payload is None:
            continue
        row = build_task_row(payload=payload, path=path)
        if row is not None:
            task_rows.append(row)

    initial_row_count = len(task_rows)
    task_rows = dedupe_latest_rows(task_rows)
    deduped_count = initial_row_count - len(task_rows)
    if deduped_count > 0:
        print(f"Deduped {deduped_count} stale task rows by keeping latest run per task/model pair")

    scores = build_scores_file(task_rows=task_rows, library_labels=library_labels)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(scores, handle, indent=2)

    print(
        f"Wrote {output_path} with {len(scores['tasks'])} task rows and "
        f"{len(scores['libraries'])} library rows"
    )
    return 0


def load_library_labels(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    labels: dict[str, str] = {}
    if not isinstance(payload, list):
        return labels
    for item in payload:
        if isinstance(item, dict):
            library_id = item.get("id")
            label = item.get("label")
            if isinstance(library_id, str) and isinstance(label, str):
                labels[library_id] = label
    return labels


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def build_task_row(payload: dict[str, Any], path: Path) -> dict[str, Any] | None:
    task_id = payload.get("task_id")
    library = payload.get("library")
    if not isinstance(task_id, str) or not isinstance(library, str):
        return None

    judge = payload.get("judge_result")
    if not isinstance(judge, dict):
        judge = {}

    baseline_score = _coerce_score(judge.get("baseline_score"))
    treatment_score = _coerce_score(judge.get("treatment_score"))
    baseline_pct = _score_to_pct(baseline_score)
    treatment_pct = _score_to_pct(treatment_score)

    delta_pct = None
    if baseline_pct is not None and treatment_pct is not None:
        delta_pct = round(treatment_pct - baseline_pct, 6)

    return {
        "task_id": task_id,
        "library": library,
        "model_provider": payload.get("model_provider"),
        "model": payload.get("model"),
        "run_id": payload.get("run_id"),
        "timestamp": payload.get("timestamp"),
        "judge_status": judge.get("status"),
        "baseline_score": baseline_score,
        "treatment_score": treatment_score,
        "baseline_pct": baseline_pct,
        "treatment_pct": treatment_pct,
        "delta_pct": delta_pct,
        "source_file": str(path),
    }


def build_scores_file(*, task_rows: list[dict[str, Any]], library_labels: dict[str, str]) -> dict[str, Any]:
    valid_rows = [
        row
        for row in task_rows
        if row.get("baseline_pct") is not None and row.get("treatment_pct") is not None
    ]

    overall_without = _mean([row["baseline_pct"] for row in valid_rows])
    overall_with = _mean([row["treatment_pct"] for row in valid_rows])
    improvement_delta = _delta(overall_with, overall_without)

    nonperfect_rows = [row for row in valid_rows if row["baseline_pct"] < 100.0]
    perfect_rows = [row for row in valid_rows if row["baseline_pct"] == 100.0]

    nonperfect_without = _mean([row["baseline_pct"] for row in nonperfect_rows])
    nonperfect_with = _mean([row["treatment_pct"] for row in nonperfect_rows])
    nonperfect_delta = _delta(nonperfect_with, nonperfect_without)

    perfect_without = _mean([row["baseline_pct"] for row in perfect_rows])
    perfect_with = _mean([row["treatment_pct"] for row in perfect_rows])
    perfect_delta = _delta(perfect_with, perfect_without)

    models_tested = sorted(
        {
            f"{row.get('model_provider')}:{row.get('model')}"
            for row in task_rows
            if isinstance(row.get("model_provider"), str) and isinstance(row.get("model"), str)
        }
    )

    by_library: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in task_rows:
        by_library[row["library"]].append(row)

    library_rows: list[dict[str, Any]] = []
    for library_id in sorted(by_library):
        rows = by_library[library_id]
        valid = [
            row
            for row in rows
            if row.get("baseline_pct") is not None and row.get("treatment_pct") is not None
        ]
        without = _mean([row["baseline_pct"] for row in valid])
        with_nia = _mean([row["treatment_pct"] for row in valid])
        delta = _delta(with_nia, without)

        best_example = None
        if valid:
            winner = max(valid, key=lambda row: row.get("delta_pct") or float("-inf"))
            best_example = winner.get("task_id")

        library_rows.append(
            {
                "id": library_id,
                "label": library_labels.get(library_id, library_id),
                "tasks": len(rows),
                "without_nia": without,
                "with_nia": with_nia,
                "delta_pct": delta,
                "best_improvement_example": best_example,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "overall_without_nia": overall_without,
            "overall_with_nia": overall_with,
            "improvement_delta_pct": improvement_delta,
            # Deprecated alias kept for backward compatibility.
            "tasks_evaluated": len(valid_rows),
            "evaluations_count": len(valid_rows),
            "unique_tasks": len(
                {
                    row.get("task_id")
                    for row in task_rows
                    if isinstance(row.get("task_id"), str) and row.get("task_id")
                }
            ),
            "nonperfect_baseline_without_nia": nonperfect_without,
            "nonperfect_baseline_with_nia": nonperfect_with,
            "nonperfect_baseline_delta_pct": nonperfect_delta,
            "nonperfect_baseline_count": len(nonperfect_rows),
            "perfect_baseline_without_nia": perfect_without,
            "perfect_baseline_with_nia": perfect_with,
            "perfect_baseline_delta_pct": perfect_delta,
            "perfect_baseline_count": len(perfect_rows),
            "libraries_covered": len(by_library),
            "models_tested": models_tested,
        },
        "libraries": library_rows,
        "tasks": task_rows,
    }


def dedupe_latest_rows(task_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_by_task: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in task_rows:
        key = (
            str(row.get("task_id", "")),
            str(row.get("model_provider", "")),
            str(row.get("model", "")),
        )
        existing = latest_by_task.get(key)
        if existing is None or _is_newer_row(candidate=row, current=existing):
            latest_by_task[key] = row

    return sorted(
        latest_by_task.values(),
        key=lambda row: (
            str(row.get("model_provider", "")),
            str(row.get("model", "")),
            str(row.get("task_id", "")),
        ),
    )


def _is_newer_row(*, candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_timestamp = _parse_timestamp(candidate.get("timestamp"))
    current_timestamp = _parse_timestamp(current.get("timestamp"))
    if candidate_timestamp != current_timestamp:
        return candidate_timestamp > current_timestamp
    return str(candidate.get("run_id", "")) > str(current.get("run_id", ""))


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def _coerce_score(value: Any) -> int | None:
    if isinstance(value, int) and value in {0, 1, 2}:
        return value
    return None


def _score_to_pct(score: int | None) -> float | None:
    if score is None:
        return None
    return round((score / 2.0) * 100.0, 6)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _delta(with_value: float | None, without_value: float | None) -> float | None:
    if with_value is None or without_value is None:
        return None
    return round(with_value - without_value, 6)


if __name__ == "__main__":
    raise SystemExit(main())
