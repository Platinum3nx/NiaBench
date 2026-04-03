#!/usr/bin/env python3
"""Exercise Layer 2 local tools against smoke task fixtures."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from harness.agent_tools import AgentTools
from harness.agent_types import AgentTask
from harness.agent_workspace import AGENT_RESULTS_DIR, materialize_workspace, snapshot_final_workspace


def load_tasks(path: Path) -> list[AgentTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Expected a top-level task array")
    tasks: list[AgentTask] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Task entries must be objects")
        tasks.append(AgentTask.from_dict(item))
    return tasks


def main(argv: list[str]) -> int:
    tasks_path = Path(argv[1]) if len(argv) > 1 else REPO_ROOT / "dataset/tasks_layer2_smoke.json"
    tasks = load_tasks(tasks_path)

    smoke_root = AGENT_RESULTS_DIR / "_tool_smoke"
    if smoke_root.exists():
        shutil.rmtree(smoke_root)
    smoke_root.mkdir(parents=True, exist_ok=True)

    for task in tasks:
        run_root = smoke_root / task.id
        workspace = materialize_workspace(task=task, run_root=run_root)
        tools = AgentTools(workspace=workspace, task=task, include_nia=False)

        listed = tools.execute(name="list_files", arguments={"path": "."})
        if not isinstance(listed.get("count"), int):
            raise RuntimeError(f"{task.id}: list_files did not return count")

        first_artifact = task.expected_artifacts[0].path
        read_result = tools.execute(name="read_file", arguments={"path": first_artifact})
        if "content" not in read_result:
            raise RuntimeError(f"{task.id}: read_file did not return content")

        tools.execute(name="search_workspace", arguments={"pattern": "import", "path": "."})

        updated_content = str(read_result["content"]) + "\n"
        tools.execute(
            name="write_file",
            arguments={"path": first_artifact, "content": updated_content},
        )

        if task.test_command is not None:
            tools.execute(name="run_task_command", arguments={})

        snapshot_final_workspace(workspace)

    print(f"{tasks_path}: local tool smoke checks passed ({len(tasks)} task(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
