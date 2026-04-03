"""Layer 2 artifact-based judge grader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from grading.agent_failure_taxonomy import QUALITY_FAILURES, is_operational_failure
from grading.agent_types import AgentJudgeResult, ArtifactFinding
from harness.agent_llm_clients import AgentLLMClientError, BaseAgentLLMClient
from harness.agent_types import (
    AgentScoreBundle,
    AgentTask,
    AgentTerminalStatus,
    ArtifactCapture,
    FailureDetail,
    TaskCommandResult,
)


JUDGE_SYSTEM_PROMPT = (
    "You are a strict benchmark judge for coding-agent artifacts. "
    "Return valid JSON only and never include markdown."
)


class AgentJudgeGrader:
    def __init__(
        self,
        *,
        tasks_path: str = "dataset/tasks.json",
        rubrics_path: str = "dataset/rubrics.json",
    ) -> None:
        self.source_tasks = _load_source_tasks(Path(tasks_path))
        with Path(rubrics_path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        self.rubrics = payload if isinstance(payload, dict) else {}

    def build_runner_callable(
        self,
        *,
        judge_client: BaseAgentLLMClient,
        judge_provider: str,
        judge_model: str,
        skip_judge: bool,
    ):
        def _run(
            task: AgentTask,
            final_response_text: str | None,
            artifact_capture: ArtifactCapture,
            task_command_result: TaskCommandResult,
            terminal_status: AgentTerminalStatus,
        ) -> tuple[dict[str, Any] | None, AgentScoreBundle, AgentTerminalStatus, FailureDetail | None]:
            return self.grade_for_runner(
                judge_client=judge_client,
                judge_provider=judge_provider,
                judge_model=judge_model,
                task=task,
                final_response_text=final_response_text,
                artifact_capture=artifact_capture,
                task_command_result=task_command_result,
                terminal_status=terminal_status,
                skip_judge=skip_judge,
            )

        return _run

    def grade_for_runner(
        self,
        *,
        judge_client: BaseAgentLLMClient,
        judge_provider: str,
        judge_model: str,
        task: AgentTask,
        final_response_text: str | None,
        artifact_capture: ArtifactCapture,
        task_command_result: TaskCommandResult,
        terminal_status: AgentTerminalStatus,
        skip_judge: bool,
    ) -> tuple[dict[str, Any] | None, AgentScoreBundle, AgentTerminalStatus, FailureDetail | None]:
        if skip_judge:
            return (
                {
                    "status": "skipped",
                    "error": "Judge explicitly skipped via --skip-judge",
                    "model_provider": judge_provider,
                    "model": judge_model,
                },
                AgentScoreBundle(
                    quality_score_pct=None,
                    crash_aware_score_pct=0.0 if terminal_status != "ok" else None,
                    pass_bool=None,
                ),
                terminal_status,
                None,
            )

        if terminal_status != "ok":
            return (
                {
                    "status": "skipped_operational",
                    "error": f"Run status is {terminal_status}; judge skipped",
                    "model_provider": judge_provider,
                    "model": judge_model,
                },
                AgentScoreBundle(quality_score_pct=None, crash_aware_score_pct=0.0, pass_bool=None),
                terminal_status,
                None,
            )

        if not artifact_capture.found_artifacts:
            return (
                {
                    "status": "skipped_no_artifacts",
                    "error": "No extracted artifacts were available for judging",
                    "model_provider": judge_provider,
                    "model": judge_model,
                },
                AgentScoreBundle(quality_score_pct=None, crash_aware_score_pct=0.0, pass_bool=None),
                "no_artifacts",
                FailureDetail(kind="no_artifacts", detail="No expected artifacts found for judging"),
            )

        prompt = self.build_prompt(
            task=task,
            final_response_text=final_response_text,
            artifact_capture=artifact_capture,
            task_command_result=task_command_result,
            terminal_status=terminal_status,
        )

        try:
            response = judge_client.run_turn(
                model=judge_model,
                system_prompt=JUDGE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                tools=[],
                temperature=0,
                max_tokens=900,
            )
        except AgentLLMClientError as exc:
            return (
                AgentJudgeResult(
                    score=None,
                    rationale=None,
                    quality_failures=[],
                    artifact_findings=[],
                    confidence=None,
                    status="provider_error",
                    provider_error=str(exc),
                    judge_prompt=prompt,
                    model_provider=judge_provider,
                    model=judge_model,
                ).to_dict(),
                AgentScoreBundle(quality_score_pct=None, crash_aware_score_pct=0.0, pass_bool=None),
                "judge_error",
                FailureDetail(kind="judge_error", detail=str(exc)),
            )

        parsed, parse_error = self._parse_response(response.text)
        if parse_error is not None:
            return (
                AgentJudgeResult(
                    score=None,
                    rationale=None,
                    quality_failures=[],
                    artifact_findings=[],
                    confidence=None,
                    status="parse_error",
                    parse_error=parse_error,
                    judge_prompt=prompt,
                    judge_raw_response=response.text,
                    request_id=response.request_id,
                    tokens_in=response.tokens_in,
                    tokens_out=response.tokens_out,
                    model_provider=judge_provider,
                    model=judge_model,
                ).to_dict(),
                AgentScoreBundle(quality_score_pct=None, crash_aware_score_pct=0.0, pass_bool=None),
                "judge_error",
                FailureDetail(kind="judge_error", detail=parse_error),
            )

        judge_result = AgentJudgeResult(
            score=parsed["score"],
            rationale=parsed["rationale"],
            quality_failures=parsed["quality_failures"],
            artifact_findings=[
                ArtifactFinding(path=item["path"], status=item["status"])
                for item in parsed["artifact_findings"]
            ],
            confidence=parsed["confidence"],
            status="ok",
            judge_prompt=prompt,
            judge_raw_response=response.text,
            request_id=response.request_id,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            model_provider=judge_provider,
            model=judge_model,
        )
        score_bundle = AgentScoreBundle(
            quality_score_pct=judge_result.quality_score_pct,
            crash_aware_score_pct=judge_result.quality_score_pct,
            pass_bool=judge_result.pass_bool,
        )
        payload = judge_result.to_dict()
        payload["manual_review_required"] = judge_result.confidence == "low"
        return payload, score_bundle, terminal_status, None

    def build_prompt(
        self,
        *,
        task: AgentTask,
        final_response_text: str | None,
        artifact_capture: ArtifactCapture,
        task_command_result: TaskCommandResult,
        terminal_status: AgentTerminalStatus,
    ) -> str:
        source = self.source_tasks.get(task.source_task_id, {})
        rubric = self.rubrics.get(task.category, {})

        artifact_sections: list[str] = []
        for artifact_path in artifact_capture.found_artifacts:
            text = artifact_capture.extracted_text.get(artifact_path, "")
            artifact_sections.append(
                f"Artifact: {artifact_path}\n{truncate(text, limit=6000)}"
            )
        artifacts_block = "\n\n---\n\n".join(artifact_sections) if artifact_sections else "None"

        task_command_summary = {
            "exists": task_command_result.exists,
            "ran": task_command_result.ran,
            "exit_code": task_command_result.exit_code,
            "stderr": truncate(task_command_result.stderr or "", limit=1000),
            "stdout": truncate(task_command_result.stdout or "", limit=1000),
            "error": task_command_result.error,
        }

        return (
            "Grade this Layer 2 coding-agent run.\n\n"
            f"Source task id: {task.source_task_id}\n"
            f"Task category: {task.category}\n"
            f"Task difficulty: {task.difficulty}\n"
            f"Library: {task.library} ({task.version_introduced})\n\n"
            f"Source task description:\n{source.get('task_description', 'N/A')}\n\n"
            f"Agent goal:\n{task.agent_goal}\n\n"
            f"Reference solution:\n{source.get('reference_solution', 'N/A')}\n\n"
            f"Rubric focus:\n{rubric.get('focus', 'N/A')}\n\n"
            f"Score 2:\n{rubric.get('score_2', 'N/A')}\n\n"
            f"Score 1:\n{rubric.get('score_1', 'N/A')}\n\n"
            f"Score 0:\n{rubric.get('score_0', 'N/A')}\n\n"
            f"Terminal status: {terminal_status}\n"
            f"Found artifacts: {artifact_capture.found_artifacts}\n"
            f"Missing artifacts: {artifact_capture.missing_artifacts}\n\n"
            f"Task command result:\n{json.dumps(task_command_summary, indent=2)}\n\n"
            f"Final response text:\n{truncate(final_response_text or '', limit=2000)}\n\n"
            f"Artifact contents:\n{artifacts_block}\n\n"
            "Return JSON with exact keys:\n"
            "- score (integer 0, 1, or 2)\n"
            "- rationale (non-empty string)\n"
            "- quality_failures (array of strings from this set: "
            + ", ".join(QUALITY_FAILURES)
            + ")\n"
            "- artifact_findings (array of {path, status})\n"
            "- confidence (one of: low, medium, high)\n"
        )

    def _parse_response(self, text: str) -> tuple[dict[str, Any] | None, str | None]:
        candidate = strip_code_fence(text.strip())
        payload: dict[str, Any] | None = None

        try:
            decoded = json.loads(candidate)
            if isinstance(decoded, dict):
                payload = decoded
        except json.JSONDecodeError:
            pass

        if payload is None:
            blob = extract_balanced_json_object(candidate)
            if blob is None:
                return None, "Could not find a JSON object in judge response"
            try:
                decoded = json.loads(blob)
            except json.JSONDecodeError as exc:
                return None, f"Invalid judge JSON: {exc}"
            if not isinstance(decoded, dict):
                return None, "Judge payload must be an object"
            payload = decoded

        required = {"score", "rationale", "quality_failures", "artifact_findings", "confidence"}
        missing = [field for field in required if field not in payload]
        if missing:
            return None, f"Judge JSON missing required fields: {', '.join(sorted(missing))}"

        score = coerce_integral_score(payload.get("score"))
        if score is None or score not in {0, 1, 2}:
            return None, "score must be an integer in [0, 1, 2]"

        rationale = payload.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            return None, "rationale must be a non-empty string"

        confidence = payload.get("confidence")
        if confidence not in {"low", "medium", "high"}:
            return None, "confidence must be one of low, medium, high"

        quality_failures_raw = payload.get("quality_failures")
        if not isinstance(quality_failures_raw, list) or not all(
            isinstance(item, str) for item in quality_failures_raw
        ):
            return None, "quality_failures must be an array of strings"
        quality_failures: list[str] = []
        for failure in quality_failures_raw:
            if failure not in QUALITY_FAILURES:
                return None, f"Unknown quality failure '{failure}'"
            if failure not in quality_failures:
                quality_failures.append(failure)

        findings_raw = payload.get("artifact_findings")
        if not isinstance(findings_raw, list):
            return None, "artifact_findings must be an array"
        artifact_findings: list[dict[str, str]] = []
        for index, item in enumerate(findings_raw):
            if not isinstance(item, dict):
                return None, f"artifact_findings[{index}] must be an object"
            path = item.get("path")
            status = item.get("status")
            if not isinstance(path, str) or not path.strip():
                return None, f"artifact_findings[{index}].path must be a non-empty string"
            if not isinstance(status, str) or not status.strip():
                return None, f"artifact_findings[{index}].status must be a non-empty string"
            artifact_findings.append({"path": path.strip(), "status": status.strip()})

        return {
            "score": score,
            "rationale": rationale.strip(),
            "quality_failures": quality_failures,
            "artifact_findings": artifact_findings,
            "confidence": confidence,
        }, None


def _load_source_tasks(path: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        task_id = item.get("id")
        if isinstance(task_id, str):
            rows[task_id] = item
    return rows


def truncate(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return text


def extract_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def coerce_integral_score(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def default_crash_aware_score(status: str, quality_score_pct: float | None) -> float | None:
    if is_operational_failure(status):
        return 0.0
    return quality_score_pct
