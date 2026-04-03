#!/usr/bin/env python3
"""Run Layer 2 agent benchmark conditions with isolated artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grading.agent_judge import AgentJudgeGrader
from harness.agent_conditions import resolve_conditions
from harness.agent_llm_clients import create_agent_llm_client
from harness.agent_runner import run_agent_task
from harness.agent_tools import Layer2NiaSearchTool
from harness.agent_types import AGENT_RUN_SCHEMA_VERSION, AgentTask
from harness.config import REPO_ROOT, load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", required=True, help="Path to Layer 2 task wrapper file")
    parser.add_argument("--provider", required=True, choices=["anthropic", "openai"])
    parser.add_argument("--model", required=True, help="Pinned agent model id")
    parser.add_argument("--judge-provider", required=True, choices=["anthropic", "openai"])
    parser.add_argument("--judge-model", required=True, help="Pinned judge model id")
    parser.add_argument(
        "--condition",
        default="all",
        choices=["all", "no_retrieval_agent", "nia_agent"],
        help="Run one condition or both",
    )
    parser.add_argument("--repetitions", type=int, default=2, help="Repetitions per condition")
    parser.add_argument("--repetition-index", type=int, help="Run only one repetition index")
    parser.add_argument("--task-id", help="Run only one task id")
    parser.add_argument("--library", help="Run only one library")
    parser.add_argument("--limit", type=int, help="Limit number of matching tasks")
    parser.add_argument("--run-id", help="Optional run id prefix")
    parser.add_argument("--dry-run", action="store_true", help="Render artifacts without provider calls")
    parser.add_argument("--skip-judge", action="store_true", help="Skip judge grading")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--max-total-tokens", type=int, default=25000)
    parser.add_argument(
        "--results-root",
        default="results/agent_raw",
        help="Layer 2 raw artifact root (must not point to Layer 1 results/raw)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    tasks = load_agent_tasks(Path(args.tasks))
    tasks = filter_tasks(tasks, task_id=args.task_id, library=args.library, limit=args.limit)
    if not tasks:
        raise SystemExit("No tasks matched the supplied filters")

    if args.repetitions <= 0:
        raise SystemExit("--repetitions must be positive")
    if args.repetition_index is not None and args.repetition_index < 0:
        raise SystemExit("--repetition-index must be >= 0")

    if not args.dry_run and args.provider == args.judge_provider and args.model == args.judge_model:
        raise SystemExit(
            "Layer 2 founder-facing runs require distinct agent and judge model pairs. "
            "Choose different --provider/--model and --judge-provider/--judge-model."
        )

    results_root = (REPO_ROOT / args.results_root).resolve()
    if str(results_root).endswith("results/raw"):
        raise SystemExit("Layer 2 outputs must not write into results/raw")

    conditions = resolve_conditions(args.condition)
    repetition_indexes = (
        [args.repetition_index]
        if args.repetition_index is not None
        else list(range(args.repetitions))
    )

    invocation_id = args.run_id or build_invocation_id(args.provider, args.model)
    provider_slug = slugify(f"{args.provider}-{args.model}")

    agent_client = None
    judge_callable = None
    nia_tool = None
    if not args.dry_run:
        agent_client = create_agent_llm_client(args.provider, api_key_for_provider(config, args.provider))
        if not args.skip_judge:
            judge_client = create_agent_llm_client(
                args.judge_provider,
                api_key_for_provider(config, args.judge_provider),
            )
            judge_grader = AgentJudgeGrader()
            judge_callable = judge_grader.build_runner_callable(
                judge_client=judge_client,
                judge_provider=args.judge_provider,
                judge_model=args.judge_model,
                skip_judge=args.skip_judge,
            )
        nia_tool = Layer2NiaSearchTool(
            api_key=config.nia_api_key,
            search_endpoint=config.nia_search_endpoint,
            index_endpoint=config.nia_index_endpoint,
        )

    failures = 0
    completed = 0
    for condition in conditions:
        for task in tasks:
            for repetition_index in repetition_indexes:
                cell_run_id = (
                    f"{invocation_id}-{condition.id}-{task.id}-rep-{repetition_index:02d}"
                )
                run_dir = (
                    results_root
                    / provider_slug
                    / cell_run_id
                    / condition.id
                    / task.id
                    / f"rep-{repetition_index:02d}"
                )
                try:
                    result = run_agent_task(
                        task=task,
                        condition=condition,
                        provider=args.provider,
                        model=args.model,
                        judge_provider=args.judge_provider,
                        judge_model=args.judge_model,
                        run_id=cell_run_id,
                        repetition_index=repetition_index,
                        output_root=run_dir,
                        agent_client=agent_client,
                        nia_search_callable=(
                            nia_tool.search_docs
                            if (nia_tool is not None and condition.include_nia_tool and not args.dry_run)
                            else None
                        ),
                        judge_callable=judge_callable,
                        dry_run=args.dry_run,
                        skip_judge=args.skip_judge,
                        temperature=args.temperature,
                        max_steps=args.max_steps,
                        timeout_seconds=args.timeout_seconds,
                        max_tokens_per_turn=args.max_tokens,
                        max_total_tokens=args.max_total_tokens,
                    )
                    completed += 1
                    print(
                        f"[ok] {condition.id} {task.id} rep={repetition_index} "
                        f"status={result.get('status')} -> {run_dir / 'run.json'}"
                    )
                except Exception as exc:  # pragma: no cover - defensive fallback
                    failures += 1
                    write_runner_exception_artifact(
                        output_dir=run_dir,
                        run_id=cell_run_id,
                        task=task,
                        condition=condition.id,
                        repetition_index=repetition_index,
                        provider=args.provider,
                        model=args.model,
                        judge_provider=args.judge_provider,
                        judge_model=args.judge_model,
                        error=str(exc),
                    )
                    print(
                        f"[error] {condition.id} {task.id} rep={repetition_index}: {exc} "
                        f"-> {run_dir / 'run.json'}"
                    )

    print(f"Layer 2 run complete: completed={completed} failures={failures}")
    return 1 if failures else 0


def api_key_for_provider(config: Any, provider: str) -> str | None:
    if provider == "anthropic":
        return config.anthropic_api_key
    if provider == "openai":
        return config.openai_api_key
    return None


def load_agent_tasks(path: Path) -> list[AgentTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array")
    tasks: list[AgentTask] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Task entries must be objects")
        tasks.append(AgentTask.from_dict(item))
    return tasks


def filter_tasks(
    tasks: list[AgentTask],
    *,
    task_id: str | None,
    library: str | None,
    limit: int | None,
) -> list[AgentTask]:
    filtered = tasks
    if task_id:
        filtered = [task for task in filtered if task.id == task_id]
    if library:
        filtered = [task for task in filtered if task.library == library]
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def build_invocation_id(provider: str, model: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{slugify(provider)}-{slugify(model)}-{timestamp}"


def slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


def write_runner_exception_artifact(
    *,
    output_dir: Path,
    run_id: str,
    task: AgentTask,
    condition: str,
    repetition_index: int,
    provider: str,
    model: str,
    judge_provider: str,
    judge_model: str,
    error: str,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": AGENT_RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "task_id": task.id,
        "source_task_id": task.source_task_id,
        "condition": condition,
        "repetition_index": repetition_index,
        "model_provider": provider,
        "model": model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "timestamp": now,
        "status": "runner_exception",
        "budgets": {},
        "timings_ms": {"started_at": now, "finished_at": now, "wall_clock_ms": 0},
        "prompt": {"system_prompt": "", "initial_user_prompt": "", "available_tools": []},
        "steps": [],
        "tool_calls": [],
        "final_response_text": None,
        "final_response_parse_error": None,
        "artifacts": {
            "expected_artifacts": [artifact.to_dict() for artifact in task.expected_artifacts],
            "found_artifacts": [],
            "missing_artifacts": [artifact.path for artifact in task.expected_artifacts],
            "extracted_text": {},
        },
        "task_command": {
            "exists": task.test_command is not None,
            "ran": False,
            "argv": task.test_command.argv if task.test_command is not None else None,
            "cwd": task.test_command.cwd if task.test_command is not None else None,
            "timeout_seconds": task.test_command.timeout_seconds if task.test_command is not None else None,
            "exit_code": None,
            "stdout": None,
            "stderr": None,
            "error": None,
        },
        "judge_result": None,
        "scores": {"quality_score_pct": None, "crash_aware_score_pct": 0.0, "pass_bool": None},
        "failure": {"kind": "runner_exception", "detail": error},
    }
    (output_dir / "run.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
