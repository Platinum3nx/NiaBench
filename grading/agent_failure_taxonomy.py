"""Layer 2 quality and operational failure taxonomies."""

from __future__ import annotations

from grading.agent_types import ALLOWED_OPERATIONAL_FAILURES, ALLOWED_QUALITY_FAILURES


QUALITY_FAILURES = tuple(ALLOWED_QUALITY_FAILURES)
OPERATIONAL_FAILURES = tuple(ALLOWED_OPERATIONAL_FAILURES)


def is_operational_failure(status: str) -> bool:
    return status in {
        "timeout",
        "provider_error",
        "max_tokens_truncated",
        "unexpected_stop_reason",
        "retrieval_error",
        "workspace_tool_error",
        "runner_exception",
        "no_artifacts",
        "judge_error",
    }
