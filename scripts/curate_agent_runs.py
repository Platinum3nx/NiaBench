#!/usr/bin/env python3
"""Curate Layer 2 run artifacts into a launch-safe combined input tree."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "nia.layer2.run.v1"
ALLOWED_CONDITIONS = {"no_retrieval_agent", "nia_agent"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Raw Layer 2 artifact root (results/agent_raw)")
    parser.add_argument(
        "--output",
        required=True,
        help="Curated output directory (results/agent_raw_curated/combined)",
    )
    parser.add_argument("--tasks-file", default="dataset/tasks_layer2_pilot.json")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--agent-provider", help="Pinned agent provider")
    parser.add_argument("--agent-model", help="Pinned agent model id")
    parser.add_argument("--judge-provider", help="Pinned judge provider")
    parser.add_argument("--judge-model", help="Pinned judge model id")
    parser.add_argument(
        "--allow-missing-cells",
        action="store_true",
        help="Do not fail when required pilot cells are missing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_root = Path(args.input)
    output_root = Path(args.output)
    if not input_root.exists():
        raise SystemExit(f"Input directory does not exist: {input_root}")

    locked_tasks = load_locked_task_ids(Path(args.tasks_file))
    artifacts = discover_run_artifacts(input_root)

    filtered = [
        artifact
        for artifact in artifacts
        if is_candidate_artifact(artifact=artifact.payload, locked_tasks=locked_tasks)
    ]
    if not filtered:
        raise SystemExit("No valid Layer 2 run artifacts matched curation filters")

    pinned_pair = resolve_pinned_pair(
        artifacts=filtered,
        explicit={
            "model_provider": args.agent_provider,
            "model": args.agent_model,
            "judge_provider": args.judge_provider,
            "judge_model": args.judge_model,
        },
    )
    filtered = [artifact for artifact in filtered if matches_pair(artifact.payload, pinned_pair)]

    curated = select_latest_per_cell(filtered)
    missing_cells = find_missing_cells(
        artifacts=curated,
        locked_tasks=locked_tasks,
        repetitions=args.repetitions,
        pair=pinned_pair,
    )

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    copied = 0
    for artifact in curated:
        source_dir = artifact.path.parent
        destination_dir = output_root / source_dir.relative_to(input_root)
        destination_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_dir, destination_dir, dirs_exist_ok=False)
        copied += 1

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "nia.layer2.curation.v1",
        "input_root": str(input_root),
        "output_root": str(output_root),
        "tasks_file": args.tasks_file,
        "locked_task_count": len(locked_tasks),
        "selected_runs": copied,
        "missing_cells": [list(cell) for cell in missing_cells],
        "pinned_pair": pinned_pair,
    }
    (output_root / "_curation_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if missing_cells and not args.allow_missing_cells:
        print(
            f"Curated {copied} runs, but {len(missing_cells)} required pilot cells are missing. "
            "Use --allow-missing-cells for exploratory curation.",
        )
        return 1

    print(f"Curated {copied} run(s) into {output_root}")
    return 0


class RunArtifact:
    def __init__(self, path: Path, payload: dict[str, Any]) -> None:
        self.path = path
        self.payload = payload


def discover_run_artifacts(input_root: Path) -> list[RunArtifact]:
    artifacts: list[RunArtifact] = []
    for path in input_root.rglob("run.json"):
        payload = load_json(path)
        if payload is None:
            continue
        if payload.get("schema_version") != SCHEMA_VERSION:
            continue
        artifacts.append(RunArtifact(path=path, payload=payload))
    return artifacts


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def load_locked_task_ids(path: Path) -> set[str]:
    payload = load_json_array(path)
    task_ids: set[str] = set()
    for item in payload:
        if isinstance(item, dict):
            task_id = item.get("id")
            if isinstance(task_id, str):
                task_ids.add(task_id)
    if not task_ids:
        raise ValueError(f"No task ids found in {path}")
    return task_ids


def load_json_array(path: Path) -> list[Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    return payload


def is_candidate_artifact(*, artifact: dict[str, Any], locked_tasks: set[str]) -> bool:
    task_id = artifact.get("task_id")
    condition = artifact.get("condition")
    repetition_index = artifact.get("repetition_index")
    if not isinstance(task_id, str) or task_id not in locked_tasks:
        return False
    if condition not in ALLOWED_CONDITIONS:
        return False
    if not isinstance(repetition_index, int) or repetition_index < 0:
        return False
    return True


def resolve_pinned_pair(
    *,
    artifacts: list[RunArtifact],
    explicit: dict[str, str | None],
) -> dict[str, str]:
    required_keys = ("model_provider", "model", "judge_provider", "judge_model")
    if all(explicit.get(key) for key in required_keys):
        return {key: str(explicit[key]) for key in required_keys}

    pair_values = {
        (
            str(artifact.payload.get("model_provider", "")),
            str(artifact.payload.get("model", "")),
            str(artifact.payload.get("judge_provider", "")),
            str(artifact.payload.get("judge_model", "")),
        )
        for artifact in artifacts
    }
    pair_values = {row for row in pair_values if all(part and part != "None" for part in row)}
    if len(pair_values) != 1:
        raise ValueError(
            "Could not infer one pinned model/judge pair from artifacts. "
            "Pass --agent-provider/--agent-model/--judge-provider/--judge-model explicitly."
        )
    model_provider, model, judge_provider, judge_model = next(iter(pair_values))
    return {
        "model_provider": model_provider,
        "model": model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
    }


def matches_pair(payload: dict[str, Any], pair: dict[str, str]) -> bool:
    return (
        payload.get("model_provider") == pair["model_provider"]
        and payload.get("model") == pair["model"]
        and payload.get("judge_provider") == pair["judge_provider"]
        and payload.get("judge_model") == pair["judge_model"]
    )


def select_latest_per_cell(artifacts: list[RunArtifact]) -> list[RunArtifact]:
    latest: dict[tuple[Any, ...], RunArtifact] = {}
    for artifact in artifacts:
        payload = artifact.payload
        key = (
            payload.get("task_id"),
            payload.get("condition"),
            payload.get("repetition_index"),
            payload.get("model_provider"),
            payload.get("model"),
            payload.get("judge_provider"),
            payload.get("judge_model"),
        )
        current = latest.get(key)
        if current is None or is_newer(artifact.payload, current.payload):
            latest[key] = artifact
    return sorted(
        latest.values(),
        key=lambda item: (
            str(item.payload.get("task_id", "")),
            str(item.payload.get("condition", "")),
            int(item.payload.get("repetition_index", 0)),
        ),
    )


def is_newer(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    candidate_time = parse_timestamp(candidate.get("timestamp"))
    current_time = parse_timestamp(current.get("timestamp"))
    if candidate_time != current_time:
        return candidate_time > current_time
    return str(candidate.get("run_id", "")) > str(current.get("run_id", ""))


def parse_timestamp(value: Any) -> datetime:
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


def find_missing_cells(
    *,
    artifacts: list[RunArtifact],
    locked_tasks: set[str],
    repetitions: int,
    pair: dict[str, str],
) -> list[tuple[Any, ...]]:
    present = {
        (
            artifact.payload.get("task_id"),
            artifact.payload.get("condition"),
            artifact.payload.get("repetition_index"),
            artifact.payload.get("model_provider"),
            artifact.payload.get("model"),
            artifact.payload.get("judge_provider"),
            artifact.payload.get("judge_model"),
        )
        for artifact in artifacts
    }

    missing: list[tuple[Any, ...]] = []
    for task_id in sorted(locked_tasks):
        for condition in sorted(ALLOWED_CONDITIONS):
            for repetition_index in range(repetitions):
                key = (
                    task_id,
                    condition,
                    repetition_index,
                    pair["model_provider"],
                    pair["model"],
                    pair["judge_provider"],
                    pair["judge_model"],
                )
                if key not in present:
                    missing.append(key)
    return missing


if __name__ == "__main__":
    raise SystemExit(main())
