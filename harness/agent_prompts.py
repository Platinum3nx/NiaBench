"""Prompt builder for Layer 2 conditions."""

from __future__ import annotations

import json

from harness.agent_types import AgentTask


SYSTEM_PROMPT_TEMPLATE = """You are a coding agent running inside an isolated benchmark workspace.

Follow these rules exactly:
1. Inspect current workspace state before editing files.
2. Only write files listed in allowed_output_paths.
3. Prefer minimal, targeted changes that satisfy the task goal.
4. If run_task_command is available, run it before finishing.
5. If a tool fails, adapt and continue within budget.
6. When you finish, return JSON only with keys: status, summary, artifact_paths.
7. status must be one of: completed, blocked.

Available tools:
{tool_list}
"""


def build_agent_prompts(*, task: AgentTask, tool_inventory: list[str]) -> tuple[str, str]:
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        tool_list="\n".join(f"- {tool_name}" for tool_name in tool_inventory)
    ).strip()

    user_payload = {
        "task_id": task.id,
        "library": task.library,
        "version_introduced": task.version_introduced,
        "category": task.category,
        "difficulty": task.difficulty,
        "agent_goal": task.agent_goal,
        "allowed_output_paths": task.allowed_output_paths,
        "expected_artifacts": [artifact.path for artifact in task.expected_artifacts],
        "retrieval_hints": task.retrieval_hints,
        "completion_contract": {
            "status": "completed",
            "summary": "short explanation of what changed",
            "artifact_paths": ["relative/path.py"],
        },
    }
    if task.test_command is not None:
        user_payload["task_command"] = {
            "argv": task.test_command.argv,
            "cwd": task.test_command.cwd,
            "timeout_seconds": task.test_command.timeout_seconds,
        }
    else:
        user_payload["task_command"] = None

    user_prompt = (
        "Complete the following Layer 2 coding task. "
        "Use tool calls as needed and then emit the required JSON completion payload.\n\n"
        + json.dumps(user_payload, indent=2)
    )
    return system_prompt, user_prompt
