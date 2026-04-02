"""Judge grader with rubric-aware prompt construction and strict JSON parsing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from grading.types import JudgeResult
from harness.llm_clients import BaseLLMClient, LLMClientError


JUDGE_SYSTEM_PROMPT = (
    "You are a strict benchmark judge. "
    "Return valid JSON only with the required fields and no extra commentary."
)


class JudgeGrader:
    def __init__(self, rubrics_path: str = "dataset/rubrics.json") -> None:
        with Path(rubrics_path).open("r", encoding="utf-8") as handle:
            self.rubrics = json.load(handle)

    def build_prompt(
        self,
        *,
        category: str,
        task_description: str,
        reference_solution: str | None,
        baseline_output: str | None,
        treatment_output: str | None,
    ) -> str:
        rubric = self.rubrics[category]
        return (
            "You are grading two model outputs for API-version correctness.\n\n"
            f"Task description:\n{task_description}\n\n"
            f"Reference solution:\n{reference_solution or 'N/A'}\n\n"
            f"Category rubric focus:\n{rubric['focus']}\n\n"
            f"Score 2:\n{rubric['score_2']}\n\n"
            f"Score 1:\n{rubric['score_1']}\n\n"
            f"Score 0:\n{rubric['score_0']}\n\n"
            f"Baseline output:\n{baseline_output or 'N/A'}\n\n"
            f"Treatment output:\n{treatment_output or 'N/A'}\n\n"
            "Return JSON with these exact keys: "
            "baseline_score, treatment_score, baseline_rationale, treatment_rationale. "
            "Scores must be integers in [0, 1, 2]."
        )

    def grade(
        self,
        *,
        client: BaseLLMClient,
        model_provider: str,
        model: str,
        category: str,
        task_description: str,
        reference_solution: str | None,
        baseline_output: str | None,
        treatment_output: str | None,
    ) -> JudgeResult:
        prompt = self.build_prompt(
            category=category,
            task_description=task_description,
            reference_solution=reference_solution,
            baseline_output=baseline_output,
            treatment_output=treatment_output,
        )

        try:
            response = client.generate(
                model=model,
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0,
                max_tokens=900,
            )
        except LLMClientError as exc:
            return JudgeResult(
                baseline_score=None,
                treatment_score=None,
                baseline_rationale=None,
                treatment_rationale=None,
                status="provider_error",
                provider_error=str(exc),
                judge_prompt=prompt,
                model_provider=model_provider,
                model=model,
            )

        parsed, parse_error = self._parse_response(response.text)
        if parse_error is not None:
            return JudgeResult(
                baseline_score=None,
                treatment_score=None,
                baseline_rationale=None,
                treatment_rationale=None,
                status="parse_error",
                parse_error=parse_error,
                judge_prompt=prompt,
                judge_raw_response=response.text,
                request_id=response.request_id,
                tokens_in=response.tokens_in,
                tokens_out=response.tokens_out,
                model_provider=model_provider,
                model=model,
            )

        return JudgeResult(
            baseline_score=int(parsed["baseline_score"]),
            treatment_score=int(parsed["treatment_score"]),
            baseline_rationale=str(parsed["baseline_rationale"]),
            treatment_rationale=str(parsed["treatment_rationale"]),
            status="ok",
            judge_prompt=prompt,
            judge_raw_response=response.text,
            request_id=response.request_id,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            model_provider=model_provider,
            model=model,
        )

    def _parse_response(self, text: str) -> tuple[dict[str, Any] | None, str | None]:
        candidate = _strip_code_fence(text)
        payload: dict[str, Any] | None = None

        try:
            decoded = json.loads(candidate)
            if isinstance(decoded, dict):
                payload = decoded
        except json.JSONDecodeError:
            pass

        if payload is None:
            json_blob = _extract_balanced_json_object(candidate)
            if json_blob is None:
                return None, "Could not find a JSON object in judge response"
            try:
                decoded = json.loads(json_blob)
            except json.JSONDecodeError as exc:
                return None, f"Invalid judge JSON: {exc}"
            if not isinstance(decoded, dict):
                return None, "Judge JSON payload must be an object"
            payload = decoded

        required_fields = {
            "baseline_score",
            "treatment_score",
            "baseline_rationale",
            "treatment_rationale",
        }
        missing = [field for field in required_fields if field not in payload]
        if missing:
            return None, f"Judge JSON missing required fields: {', '.join(sorted(missing))}"

        for key in ("baseline_score", "treatment_score"):
            value = payload.get(key)
            score = _coerce_integral_score(value)
            if score is None or score not in {0, 1, 2}:
                return None, f"{key} must be an integer in [0, 1, 2]"
            payload[key] = score

        for key in ("baseline_rationale", "treatment_rationale"):
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                return None, f"{key} must be a non-empty string"

        return payload, None


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _extract_balanced_json_object(text: str) -> str | None:
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


def _coerce_integral_score(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None
