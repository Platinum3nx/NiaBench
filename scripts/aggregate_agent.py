#!/usr/bin/env python3
"""Aggregate curated Layer 2 run artifacts into results/agent_scores.json."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_SCHEMA_VERSION = "nia.layer2.run.v1"
AGGREGATE_SCHEMA_VERSION = "nia.layer2.aggregate.v1"
CONDITIONS = ("no_retrieval_agent", "nia_agent")
CRASH_STATUSES = {
    "provider_error",
    "workspace_tool_error",
    "retrieval_error",
    "runner_exception",
    "max_tokens_truncated",
    "unexpected_stop_reason",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Curated Layer 2 artifact root")
    parser.add_argument("--output", required=True, help="Aggregate output path")
    parser.add_argument("--tasks-file", default="dataset/tasks_layer2_pilot.json")
    parser.add_argument("--allow-empty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_root = Path(args.input)
    output_path = Path(args.output)
    task_meta = load_task_metadata(Path(args.tasks_file))

    run_rows = load_run_rows(input_root)
    if not run_rows and not args.allow_empty:
        raise SystemExit(f"No run artifacts found in {input_root}")

    conditions = build_condition_rows(run_rows)
    tasks = build_task_rows(run_rows, task_meta)
    libraries = build_library_rows(tasks)
    summary = build_summary(run_rows, conditions, tasks)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": AGGREGATE_SCHEMA_VERSION,
        "summary": summary,
        "conditions": conditions,
        "libraries": libraries,
        "tasks": tasks,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"Wrote {output_path} with {len(run_rows)} run(s), "
        f"{len(conditions)} condition row(s), {len(tasks)} task row(s)"
    )
    return 0


def load_task_metadata(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    rows: dict[str, dict[str, str]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        task_id = item.get("id")
        library = item.get("library")
        difficulty = item.get("difficulty")
        if isinstance(task_id, str):
            rows[task_id] = {
                "library": library if isinstance(library, str) else "unknown",
                "difficulty": difficulty if isinstance(difficulty, str) else "unknown",
            }
    return rows


def load_run_rows(input_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in input_root.rglob("run.json"):
        payload = load_json(path)
        if payload is None:
            continue
        if payload.get("schema_version") != RUN_SCHEMA_VERSION:
            continue
        row = normalize_run_row(payload, source_file=path)
        if row is not None:
            rows.append(row)
    return rows


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def normalize_run_row(payload: dict[str, Any], *, source_file: Path) -> dict[str, Any] | None:
    task_id = payload.get("task_id")
    condition = payload.get("condition")
    status = payload.get("status")
    repetition_index = payload.get("repetition_index")
    if not isinstance(task_id, str) or condition not in CONDITIONS or not isinstance(status, str):
        return None
    if not isinstance(repetition_index, int):
        return None

    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    quality_score_pct = coerce_number(scores.get("quality_score_pct"))
    crash_aware_score_pct = coerce_number(scores.get("crash_aware_score_pct"))
    if crash_aware_score_pct is None:
        crash_aware_score_pct = 0.0 if status != "ok" else quality_score_pct

    tool_calls = payload.get("tool_calls")
    tool_call_list = tool_calls if isinstance(tool_calls, list) else []
    nia_calls = sum(
        1
        for item in tool_call_list
        if isinstance(item, dict) and item.get("name") == "nia_search_docs"
    )
    tool_error_calls = sum(
        1
        for item in tool_call_list
        if isinstance(item, dict) and item.get("status") == "error"
    )
    nia_tool_error_calls = sum(
        1
        for item in tool_call_list
        if isinstance(item, dict)
        and item.get("name") == "nia_search_docs"
        and item.get("status") == "error"
    )

    return {
        "task_id": task_id,
        "library": payload.get("library"),
        "difficulty": payload.get("difficulty"),
        "condition": condition,
        "repetition_index": repetition_index,
        "run_id": payload.get("run_id"),
        "timestamp": payload.get("timestamp"),
        "status": status,
        "quality_score_pct": quality_score_pct,
        "crash_aware_score_pct": crash_aware_score_pct,
        "pass_bool": bool(scores.get("pass_bool")) if isinstance(scores.get("pass_bool"), bool) else None,
        "tool_calls": len(tool_call_list),
        "tool_error_calls": tool_error_calls,
        "nia_calls": nia_calls,
        "nia_used": nia_calls > 0,
        "nia_tool_error_calls": nia_tool_error_calls,
        "model_provider": payload.get("model_provider"),
        "model": payload.get("model"),
        "judge_provider": payload.get("judge_provider"),
        "judge_model": payload.get("judge_model"),
        "source_file": str(source_file),
    }


def build_condition_rows(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        grouped[str(row["condition"])].append(row)

    task_condition_stats = compute_task_condition_stats(run_rows)
    rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        condition_runs = grouped.get(condition, [])
        if not condition_runs:
            continue

        task_ids = {str(row["task_id"]) for row in condition_runs}
        completed_runs = [row for row in condition_runs if row["status"] == "ok"]
        nia_runs = [row for row in condition_runs if row["nia_used"]]

        macro_completed = mean(
            [
                stats["completed_only_avg_quality_pct"]
                for (task_id, condition_id), stats in task_condition_stats.items()
                if condition_id == condition
                and isinstance(stats["completed_only_avg_quality_pct"], (int, float))
            ]
        )
        macro_crash_aware = mean(
            [
                stats["crash_aware_avg_quality_pct"]
                for (task_id, condition_id), stats in task_condition_stats.items()
                if condition_id == condition
                and isinstance(stats["crash_aware_avg_quality_pct"], (int, float))
            ]
        )

        rows.append(
            {
                "condition": condition,
                "total_runs": len(condition_runs),
                "unique_tasks": len(task_ids),
                "completed_runs": len(completed_runs),
                "task_macro_completed_only_avg_quality_pct": macro_completed,
                "task_macro_crash_aware_avg_quality_pct": macro_crash_aware,
                "run_level_completion_rate": rate(len(completed_runs), len(condition_runs)),
                "run_level_crash_rate": rate(
                    sum(1 for row in condition_runs if row["status"] in CRASH_STATUSES),
                    len(condition_runs),
                ),
                "run_level_timeout_rate": rate(
                    sum(1 for row in condition_runs if row["status"] == "timeout"),
                    len(condition_runs),
                ),
                "run_level_no_artifact_rate": rate(
                    sum(1 for row in condition_runs if row["status"] == "no_artifacts"),
                    len(condition_runs),
                ),
                "run_level_judge_error_rate": rate(
                    sum(1 for row in condition_runs if row["status"] == "judge_error"),
                    len(condition_runs),
                ),
                "run_level_retrieval_error_rate": rate(
                    sum(1 for row in condition_runs if row["status"] == "retrieval_error"),
                    len(condition_runs),
                ),
                "run_level_workspace_tool_error_rate": rate(
                    sum(1 for row in condition_runs if row["status"] == "workspace_tool_error"),
                    len(condition_runs),
                ),
                "run_level_nia_tool_error_rate": rate(
                    sum(1 for row in condition_runs if row["nia_tool_error_calls"] > 0),
                    len(condition_runs),
                ),
                "avg_tool_calls_per_run": mean([float(row["tool_calls"]) for row in condition_runs]) or 0.0,
                "avg_tool_error_calls_per_run": mean(
                    [float(row["tool_error_calls"]) for row in condition_runs]
                )
                or 0.0,
                "avg_nia_calls_per_run": mean([float(row["nia_calls"]) for row in condition_runs]) or 0.0,
                "avg_nia_tool_error_calls_per_run": mean(
                    [float(row["nia_tool_error_calls"]) for row in condition_runs]
                )
                or 0.0,
                "nia_usage_rate": rate(len(nia_runs), len(condition_runs)),
                "avg_nia_calls_per_nia_run": mean([float(row["nia_calls"]) for row in nia_runs]),
            }
        )
    return rows


def compute_task_condition_stats(run_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        key = (str(row["task_id"]), str(row["condition"]))
        grouped[key].append(row)

    stats_map: dict[tuple[str, str], dict[str, Any]] = {}
    for key, rows in grouped.items():
        completed_scores = [
            row["quality_score_pct"]
            for row in rows
            if row["status"] == "ok" and isinstance(row["quality_score_pct"], (int, float))
        ]
        crash_aware_scores = [
            row["crash_aware_score_pct"]
            for row in rows
            if isinstance(row["crash_aware_score_pct"], (int, float))
        ]
        stats_map[key] = {
            "repetitions": len(rows),
            "completed_only_avg_quality_pct": mean(completed_scores),
            "crash_aware_avg_quality_pct": mean(crash_aware_scores),
            "completion_rate": rate(sum(1 for row in rows if row["status"] == "ok"), len(rows)),
            "completed_only_min_pct": min(completed_scores) if completed_scores else None,
            "completed_only_max_pct": max(completed_scores) if completed_scores else None,
            "completed_only_stddev_pct": stddev(completed_scores),
        }
    return stats_map


def build_task_rows(
    run_rows: list[dict[str, Any]],
    task_meta: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    task_condition_stats = compute_task_condition_stats(run_rows)
    task_runs_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        task_runs_by_id[str(row["task_id"])].append(row)
    task_ids = sorted(task_runs_by_id.keys())
    rows: list[dict[str, Any]] = []
    for task_id in task_ids:
        condition_map: dict[str, dict[str, Any]] = {}
        for condition in CONDITIONS:
            condition_map[condition] = task_condition_stats.get(
                (task_id, condition),
                {
                    "repetitions": 0,
                    "completed_only_avg_quality_pct": None,
                    "crash_aware_avg_quality_pct": None,
                    "completion_rate": None,
                    "completed_only_min_pct": None,
                    "completed_only_max_pct": None,
                    "completed_only_stddev_pct": None,
                },
            )

        no_retrieval = condition_map["no_retrieval_agent"]["completed_only_avg_quality_pct"]
        nia = condition_map["nia_agent"]["completed_only_avg_quality_pct"]
        crash_no = condition_map["no_retrieval_agent"]["crash_aware_avg_quality_pct"]
        crash_nia = condition_map["nia_agent"]["crash_aware_avg_quality_pct"]
        pairwise = compute_pairwise_outcomes(task_runs_by_id.get(task_id, []))

        rows.append(
            {
                "task_id": task_id,
                "library": task_meta.get(task_id, {}).get("library", infer_library(run_rows, task_id)),
                "difficulty": task_meta.get(task_id, {}).get("difficulty", infer_difficulty(run_rows, task_id)),
                "by_condition": condition_map,
                "delta_completed_only_pct": delta(nia, no_retrieval),
                "delta_crash_aware_pct": delta(crash_nia, crash_no),
                "pairwise_comparisons": pairwise["comparisons"],
                "pairwise_nia_wins": pairwise["nia_wins"],
                "pairwise_ties": pairwise["ties"],
                "pairwise_no_retrieval_wins": pairwise["no_retrieval_wins"],
            }
        )
    return rows


def infer_library(run_rows: list[dict[str, Any]], task_id: str) -> str:
    for row in run_rows:
        if row["task_id"] == task_id and isinstance(row.get("library"), str):
            return str(row["library"])
    return "unknown"


def infer_difficulty(run_rows: list[dict[str, Any]], task_id: str) -> str:
    for row in run_rows:
        if row["task_id"] == task_id and isinstance(row.get("difficulty"), str):
            return str(row["difficulty"])
    return "unknown"


def build_library_rows(task_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in task_rows:
        grouped[str(row["library"])].append(row)

    rows: list[dict[str, Any]] = []
    for library in sorted(grouped):
        task_rows_for_library = grouped[library]
        by_condition: dict[str, dict[str, Any]] = {}
        for condition in CONDITIONS:
            completed_values = [
                task_row["by_condition"][condition]["completed_only_avg_quality_pct"]
                for task_row in task_rows_for_library
                if isinstance(
                    task_row["by_condition"][condition]["completed_only_avg_quality_pct"],
                    (int, float),
                )
            ]
            crash_values = [
                task_row["by_condition"][condition]["crash_aware_avg_quality_pct"]
                for task_row in task_rows_for_library
                if isinstance(task_row["by_condition"][condition]["crash_aware_avg_quality_pct"], (int, float))
            ]
            by_condition[condition] = {
                "tasks": len(task_rows_for_library),
                "completed_only_avg_quality_pct": mean(completed_values),
                "crash_aware_avg_quality_pct": mean(crash_values),
            }

        rows.append(
            {
                "library": library,
                "tasks": len(task_rows_for_library),
                "by_condition": by_condition,
                "delta_completed_only_pct": delta(
                    by_condition["nia_agent"]["completed_only_avg_quality_pct"],
                    by_condition["no_retrieval_agent"]["completed_only_avg_quality_pct"],
                ),
                "delta_crash_aware_pct": delta(
                    by_condition["nia_agent"]["crash_aware_avg_quality_pct"],
                    by_condition["no_retrieval_agent"]["crash_aware_avg_quality_pct"],
                ),
                "pairwise_comparisons": sum(
                    int(task_row.get("pairwise_comparisons", 0)) for task_row in task_rows_for_library
                ),
                "pairwise_nia_wins": sum(
                    int(task_row.get("pairwise_nia_wins", 0)) for task_row in task_rows_for_library
                ),
                "pairwise_ties": sum(int(task_row.get("pairwise_ties", 0)) for task_row in task_rows_for_library),
                "pairwise_no_retrieval_wins": sum(
                    int(task_row.get("pairwise_no_retrieval_wins", 0)) for task_row in task_rows_for_library
                ),
            }
        )
    return rows


def build_summary(
    run_rows: list[dict[str, Any]],
    condition_rows: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    condition_map = {row["condition"]: row for row in condition_rows}
    no_row = condition_map.get("no_retrieval_agent", {})
    nia_row = condition_map.get("nia_agent", {})

    model_pairs = {
        (
            row.get("model_provider"),
            row.get("model"),
            row.get("judge_provider"),
            row.get("judge_model"),
        )
        for row in run_rows
    }
    model_pairs = {pair for pair in model_pairs if all(isinstance(part, str) and part for part in pair)}
    if len(model_pairs) == 1:
        model_provider, model, judge_provider, judge_model = next(iter(model_pairs))
    else:
        model_provider = model = judge_provider = judge_model = None

    comparable_task_deltas = [
        row.get("delta_completed_only_pct")
        for row in task_rows
        if isinstance(row.get("delta_completed_only_pct"), (int, float))
    ]
    task_delta_ties = sum(1 for value in comparable_task_deltas if is_close_to_zero(float(value)))
    task_delta_nia_positive = sum(1 for value in comparable_task_deltas if float(value) > 0.0)
    task_delta_no_retrieval_positive = sum(1 for value in comparable_task_deltas if float(value) < 0.0)

    pairwise_comparisons = sum(int(row.get("pairwise_comparisons", 0)) for row in task_rows)
    pairwise_nia_wins = sum(int(row.get("pairwise_nia_wins", 0)) for row in task_rows)
    pairwise_ties = sum(int(row.get("pairwise_ties", 0)) for row in task_rows)
    pairwise_no_retrieval_wins = sum(int(row.get("pairwise_no_retrieval_wins", 0)) for row in task_rows)

    return {
        "delta_completed_only_pct": delta(
            nia_row.get("task_macro_completed_only_avg_quality_pct"),
            no_row.get("task_macro_completed_only_avg_quality_pct"),
        ),
        "delta_crash_aware_pct": delta(
            nia_row.get("task_macro_crash_aware_avg_quality_pct"),
            no_row.get("task_macro_crash_aware_avg_quality_pct"),
        ),
        "run_level_completion_rate": {
            "no_retrieval_agent": no_row.get("run_level_completion_rate"),
            "nia_agent": nia_row.get("run_level_completion_rate"),
        },
        "run_level_crash_rate": {
            "no_retrieval_agent": no_row.get("run_level_crash_rate"),
            "nia_agent": nia_row.get("run_level_crash_rate"),
        },
        "run_level_timeout_rate": {
            "no_retrieval_agent": no_row.get("run_level_timeout_rate"),
            "nia_agent": nia_row.get("run_level_timeout_rate"),
        },
        "run_level_no_artifact_rate": {
            "no_retrieval_agent": no_row.get("run_level_no_artifact_rate"),
            "nia_agent": nia_row.get("run_level_no_artifact_rate"),
        },
        "run_level_judge_error_rate": {
            "no_retrieval_agent": no_row.get("run_level_judge_error_rate"),
            "nia_agent": nia_row.get("run_level_judge_error_rate"),
        },
        "nia_usage_rate": nia_row.get("nia_usage_rate"),
        "avg_nia_calls_per_nia_run": nia_row.get("avg_nia_calls_per_nia_run"),
        "task_delta_ties": task_delta_ties,
        "task_delta_nia_positive": task_delta_nia_positive,
        "task_delta_no_retrieval_positive": task_delta_no_retrieval_positive,
        "pairwise_comparisons": pairwise_comparisons,
        "pairwise_nia_wins": pairwise_nia_wins,
        "pairwise_ties": pairwise_ties,
        "pairwise_no_retrieval_wins": pairwise_no_retrieval_wins,
        "pairwise_tie_rate": rate_or_null(pairwise_ties, pairwise_comparisons),
        "unique_tasks": len({str(row["task_id"]) for row in run_rows}),
        "total_runs": len(run_rows),
        "model_provider": model_provider,
        "model": model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
    }


def coerce_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    return None


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def delta(left: Any, right: Any) -> float | None:
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return None
    return round(float(left) - float(right), 6)


def rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 6)


def rate_or_null(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round((numerator / denominator) * 100.0, 6)


def stddev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    return round(float(statistics.pstdev(values)), 6)


def compute_pairwise_outcomes(task_rows: list[dict[str, Any]]) -> dict[str, int]:
    scores_by_condition_rep: dict[str, dict[int, list[float]]] = {
        "no_retrieval_agent": defaultdict(list),
        "nia_agent": defaultdict(list),
    }
    for row in task_rows:
        condition = str(row.get("condition"))
        repetition_index = row.get("repetition_index")
        quality_score = row.get("quality_score_pct")
        if condition not in scores_by_condition_rep:
            continue
        if not isinstance(repetition_index, int) or not isinstance(quality_score, (int, float)):
            continue
        scores_by_condition_rep[condition][repetition_index].append(float(quality_score))

    no_retrieval_reps = set(scores_by_condition_rep["no_retrieval_agent"].keys())
    nia_reps = set(scores_by_condition_rep["nia_agent"].keys())
    shared_reps = sorted(no_retrieval_reps & nia_reps)

    outcomes = {"comparisons": 0, "nia_wins": 0, "ties": 0, "no_retrieval_wins": 0}
    for rep in shared_reps:
        no_scores = scores_by_condition_rep["no_retrieval_agent"][rep]
        nia_scores = scores_by_condition_rep["nia_agent"][rep]
        if not no_scores or not nia_scores:
            continue
        no_value = sum(no_scores) / len(no_scores)
        nia_value = sum(nia_scores) / len(nia_scores)
        outcomes["comparisons"] += 1
        if nia_value > no_value:
            outcomes["nia_wins"] += 1
        elif nia_value < no_value:
            outcomes["no_retrieval_wins"] += 1
        else:
            outcomes["ties"] += 1
    return outcomes


def is_close_to_zero(value: float, epsilon: float = 1e-9) -> bool:
    return -epsilon <= value <= epsilon


if __name__ == "__main__":
    raise SystemExit(main())
