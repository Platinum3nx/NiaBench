#!/usr/bin/env python3
"""Verify Layer 2 condition parity and tool-boundary invariants."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.agent_conditions import NIA_AGENT, NO_RETRIEVAL_AGENT  # noqa: E402
from harness.agent_prompts import build_agent_prompts  # noqa: E402
from harness.agent_tools import AgentToolError, AgentTools, NIA_TOOL_NAME, build_tool_inventory  # noqa: E402
from harness.agent_types import AgentTask  # noqa: E402
from harness.agent_workspace import materialize_workspace  # noqa: E402


def load_first_task(path: Path) -> AgentTask:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Expected at least one task")
    first = payload[0]
    if not isinstance(first, dict):
        raise ValueError("Task must be an object")
    return AgentTask.from_dict(first)


def prompt_prefix(system_prompt: str) -> str:
    marker = "\nAvailable tools:\n"
    if marker not in system_prompt:
        return system_prompt
    return system_prompt.split(marker, maxsplit=1)[0]


def main() -> int:
    task = load_first_task(REPO_ROOT / "dataset/tasks_layer2_smoke.json")

    no_tools = build_tool_inventory(
        include_nia=NO_RETRIEVAL_AGENT.include_nia_tool,
        task_has_test_command=task.test_command is not None,
    )
    nia_tools = build_tool_inventory(
        include_nia=NIA_AGENT.include_nia_tool,
        task_has_test_command=task.test_command is not None,
    )
    if NIA_TOOL_NAME in no_tools:
        raise RuntimeError("nia_search_docs should not be present in no_retrieval_agent tool inventory")
    if NIA_TOOL_NAME not in nia_tools:
        raise RuntimeError("nia_search_docs should be present in nia_agent tool inventory")

    no_system, no_user = build_agent_prompts(task=task, tool_inventory=no_tools)
    nia_system, nia_user = build_agent_prompts(task=task, tool_inventory=nia_tools)

    if no_user != nia_user:
        raise RuntimeError("User prompt differs between conditions")
    if prompt_prefix(no_system) != prompt_prefix(nia_system):
        raise RuntimeError("System prompt differs outside tool inventory")

    run_root = REPO_ROOT / "results/agent_raw/_condition_check"
    workspace = materialize_workspace(task=task, run_root=run_root)
    tools = AgentTools(workspace=workspace, task=task, include_nia=False)
    try:
        tools.execute(
            name=NIA_TOOL_NAME,
            arguments={"query": "x", "library": task.library, "version": task.version_introduced},
        )
    except AgentToolError:
        pass
    else:
        raise RuntimeError("nia_search_docs should fail in no_retrieval_agent condition")

    print("Layer 2 condition checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
