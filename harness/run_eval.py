#!/usr/bin/env python3
"""Run baseline and with-Nia eval calls for a task set."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from grading.composite import CompositeGrader
from grading.judge import JudgeGrader
from grading.types import JudgeResult
from harness.config import load_config
from harness.llm_clients import BaseLLMClient, LLMClientError, create_llm_client
from harness.nia_client import NiaClient, NiaClientError
from harness.prompts import build_nia_query, build_prompts
from harness.types import Task


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="dataset/tasks.json", help="Path to the task file")
    parser.add_argument("--provider", required=True, choices=["anthropic", "openai"])
    parser.add_argument("--model", required=True, help="Model id to evaluate")
    parser.add_argument("--judge-provider", choices=["anthropic", "openai"], help="Judge provider")
    parser.add_argument("--judge-model", help="Judge model id")
    parser.add_argument("--skip-judge", action="store_true", help="Skip judge scoring")
    parser.add_argument("--task-id", help="Run only one task id")
    parser.add_argument("--library", help="Run only tasks for one library id")
    parser.add_argument("--limit", type=int, help="Run only the first N matching tasks")
    parser.add_argument("--run-id", help="Optional run id. Defaults to a timestamped identifier.")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--dry-run", action="store_true", help="Write prompts without calling APIs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    tasks = load_tasks(Path(args.tasks))
    tasks = filter_tasks(tasks, task_id=args.task_id, library=args.library, limit=args.limit)
    if not tasks:
        raise SystemExit(
            "No tasks matched the supplied filters. "
            "If your task file is empty, generate or supply tasks before running eval."
        )

    judge_provider = args.judge_provider or args.provider
    judge_model = args.judge_model or args.model

    run_id = args.run_id or build_run_id(args.provider, args.model)
    llm_client = None
    judge_client = None
    nia_client = None

    if not args.dry_run:
        llm_client = create_llm_client(args.provider, _api_key_for_provider(config, args.provider))
        nia_client = NiaClient(
            api_key=config.nia_api_key,
            search_endpoint=config.nia_search_endpoint,
            index_endpoint=config.nia_index_endpoint,
            cache_dir=config.nia_cache_dir,
        )
        if not args.skip_judge:
            judge_client = create_llm_client(
                judge_provider,
                _api_key_for_provider(config, judge_provider),
            )

    judge_grader = JudgeGrader()

    output_dir = config.results_dir / slugify(f"{args.provider}-{args.model}") / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for task in tasks:
        try:
            result = evaluate_task(
                task=task,
                provider=args.provider,
                model=args.model,
                judge_provider=judge_provider,
                judge_model=judge_model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                run_id=run_id,
                llm_client=llm_client,
                judge_client=judge_client,
                judge_grader=judge_grader,
                nia_client=nia_client,
                dry_run=args.dry_run,
                skip_judge=args.skip_judge,
            )
            destination = output_dir / f"{task.id}.json"
            with destination.open("w", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2)
            print(f"Wrote {destination}")
        except (LLMClientError, NiaClientError, OSError, ValueError) as exc:
            failures += 1
            print(f"[ERROR] {task.id}: {exc}")

    return 1 if failures else 0


def _api_key_for_provider(config: Any, provider: str) -> str | None:
    if provider == "anthropic":
        return config.anthropic_api_key
    if provider == "openai":
        return config.openai_api_key
    return None


def load_tasks(path: Path) -> list[Task]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON array of tasks")
    return [Task.from_dict(item) for item in payload]


def filter_tasks(
    tasks: list[Task],
    *,
    task_id: str | None,
    library: str | None,
    limit: int | None,
) -> list[Task]:
    filtered = tasks
    if task_id:
        filtered = [task for task in filtered if task.id == task_id]
    if library:
        filtered = [task for task in filtered if task.library == library]
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def evaluate_task(
    *,
    task: Task,
    provider: str,
    model: str,
    judge_provider: str,
    judge_model: str,
    temperature: float,
    max_tokens: int,
    run_id: str,
    llm_client: BaseLLMClient | None,
    judge_client: BaseLLMClient | None,
    judge_grader: JudgeGrader,
    nia_client: NiaClient | None,
    dry_run: bool,
    skip_judge: bool,
) -> dict[str, Any]:
    if dry_run:
        context_chunks: list[Any] = []
        nia_query = build_nia_query(task)
        response_time_ms = None
    else:
        if nia_client is None:
            raise ValueError("nia_client is required for non-dry runs")
        context_chunks, nia_query, response_time_ms = nia_client.fetch_context(task)

    baseline_prompt, treatment_prompt = build_prompts(task, context_chunks)

    baseline_response: str | None
    treatment_response: str | None
    baseline_tokens_in: int | None
    baseline_tokens_out: int | None
    treatment_tokens_in: int | None
    treatment_tokens_out: int | None
    baseline_raw: dict[str, Any]
    treatment_raw: dict[str, Any]
    baseline_request_id: str | None
    treatment_request_id: str | None

    if dry_run:
        baseline_response = None
        treatment_response = None
        baseline_tokens_in = None
        baseline_tokens_out = None
        treatment_tokens_in = None
        treatment_tokens_out = None
        baseline_raw = {}
        treatment_raw = {}
        baseline_request_id = None
        treatment_request_id = None
    else:
        if llm_client is None:
            raise ValueError("llm_client is required for non-dry runs")

        baseline = llm_client.generate(
            model=model,
            system_prompt=baseline_prompt["system"],
            user_prompt=baseline_prompt["user"],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        treatment = llm_client.generate(
            model=model,
            system_prompt=treatment_prompt["system"],
            user_prompt=treatment_prompt["user"],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        baseline_response = baseline.text
        treatment_response = treatment.text
        baseline_tokens_in = baseline.tokens_in
        baseline_tokens_out = baseline.tokens_out
        treatment_tokens_in = treatment.tokens_in
        treatment_tokens_out = treatment.tokens_out
        baseline_raw = baseline.raw_response
        treatment_raw = treatment.raw_response
        baseline_request_id = baseline.request_id
        treatment_request_id = treatment.request_id

    judge_result = _score_with_judge(
        task=task,
        baseline_output=baseline_response,
        treatment_output=treatment_response,
        judge_provider=judge_provider,
        judge_model=judge_model,
        judge_client=judge_client,
        judge_grader=judge_grader,
        dry_run=dry_run,
        skip_judge=skip_judge,
    )

    composite = CompositeGrader.judge_only_bundle(
        baseline_judge_score=judge_result.baseline_score if judge_result.status == "ok" else None,
        treatment_judge_score=judge_result.treatment_score if judge_result.status == "ok" else None,
        reason=None if judge_result.status == "ok" else f"judge_status={judge_result.status}",
    )

    sandbox_result = {
        "status": "deferred",
        "reason": "Sandbox execution deferred for current sprint",
        "executed": False,
        "exit_code": None,
        "stdout": None,
        "stderr": None,
        "error_type": "Deferred",
    }

    return {
        "task_id": task.id,
        "library": task.library,
        "version_introduced": task.version_introduced,
        "category": task.category,
        "difficulty": task.difficulty,
        "model_provider": provider,
        "model": model,
        "judge_provider": judge_provider,
        "judge_model": judge_model,
        "temperature": temperature,
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "baseline_prompt": baseline_prompt,
        "baseline_response": baseline_response,
        "baseline_tokens_in": baseline_tokens_in,
        "baseline_tokens_out": baseline_tokens_out,
        "baseline_request_id": baseline_request_id,
        "baseline_raw_response": baseline_raw,
        "nia_context_retrieved": [chunk.to_dict() for chunk in context_chunks],
        "nia_query_used": nia_query,
        "nia_response_time_ms": response_time_ms,
        "nia_mode": "dry_run_placeholder" if dry_run else "live",
        "treatment_prompt": treatment_prompt,
        "treatment_response": treatment_response,
        "treatment_tokens_in": treatment_tokens_in,
        "treatment_tokens_out": treatment_tokens_out,
        "treatment_request_id": treatment_request_id,
        "treatment_raw_response": treatment_raw,
        "sandbox_result": sandbox_result,
        "judge_result": judge_result.to_dict(),
        "composite_score": composite,
    }


def _score_with_judge(
    *,
    task: Task,
    baseline_output: str | None,
    treatment_output: str | None,
    judge_provider: str,
    judge_model: str,
    judge_client: BaseLLMClient | None,
    judge_grader: JudgeGrader,
    dry_run: bool,
    skip_judge: bool,
) -> JudgeResult:
    if dry_run:
        return JudgeResult(
            baseline_score=None,
            treatment_score=None,
            baseline_rationale=None,
            treatment_rationale=None,
            status="skipped",
            error="Judge skipped in dry-run mode",
            model_provider=judge_provider,
            model=judge_model,
        )

    if skip_judge:
        return JudgeResult(
            baseline_score=None,
            treatment_score=None,
            baseline_rationale=None,
            treatment_rationale=None,
            status="skipped",
            error="Judge explicitly skipped via --skip-judge",
            model_provider=judge_provider,
            model=judge_model,
        )

    if judge_client is None:
        return JudgeResult(
            baseline_score=None,
            treatment_score=None,
            baseline_rationale=None,
            treatment_rationale=None,
            status="provider_error",
            provider_error="Judge client is not configured",
            model_provider=judge_provider,
            model=judge_model,
        )

    if baseline_output is None or treatment_output is None:
        return JudgeResult(
            baseline_score=None,
            treatment_score=None,
            baseline_rationale=None,
            treatment_rationale=None,
            status="pending",
            error="Missing model outputs for judge scoring",
            model_provider=judge_provider,
            model=judge_model,
        )

    return judge_grader.grade(
        client=judge_client,
        model_provider=judge_provider,
        model=judge_model,
        category=task.category,
        task_description=task.task_description,
        reference_solution=task.reference_solution,
        baseline_output=baseline_output,
        treatment_output=treatment_output,
    )


def build_run_id(provider: str, model: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{slugify(provider)}-{slugify(model)}-{timestamp}"


def slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
