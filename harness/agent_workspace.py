"""Workspace isolation helpers for Layer 2 agent runs."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from harness.agent_types import AgentTask


REPO_ROOT = Path(__file__).resolve().parent.parent
AGENT_RESULTS_DIR = REPO_ROOT / "results" / "agent_raw"


class WorkspaceError(RuntimeError):
    """Raised when workspace setup or path enforcement fails."""


@dataclass
class AgentWorkspace:
    run_root: Path
    seed_source: Path
    workspace_root: Path
    workspace_seed_snapshot: Path
    workspace_final_snapshot: Path
    allowed_output_paths: set[str]

    def resolve_read_path(self, relative_path: str) -> Path:
        return _resolve_relative_path(self.workspace_root, relative_path)

    def resolve_write_path(self, relative_path: str) -> Path:
        normalized = _canonical_relative_path(relative_path, allow_root=False)
        if normalized not in self.allowed_output_paths:
            raise WorkspaceError(
                f"Write denied for '{relative_path}'. Must match allowed_output_paths exactly."
            )
        return _resolve_relative_path(self.workspace_root, normalized)


def materialize_workspace(*, task: AgentTask, run_root: Path) -> AgentWorkspace:
    seed_source = (REPO_ROOT / task.workspace_seed.seed_dir).resolve()
    if not seed_source.exists() or not seed_source.is_dir():
        raise WorkspaceError(f"Seed workspace directory does not exist: {task.workspace_seed.seed_dir}")

    workspace_root = run_root / "workspace"
    workspace_seed_snapshot = run_root / "workspace_seed"
    workspace_final_snapshot = run_root / "workspace_final"

    run_root.mkdir(parents=True, exist_ok=True)
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    if workspace_seed_snapshot.exists():
        shutil.rmtree(workspace_seed_snapshot)
    if workspace_final_snapshot.exists():
        shutil.rmtree(workspace_final_snapshot)

    shutil.copytree(seed_source, workspace_root)
    shutil.copytree(seed_source, workspace_seed_snapshot)

    return AgentWorkspace(
        run_root=run_root,
        seed_source=seed_source,
        workspace_root=workspace_root,
        workspace_seed_snapshot=workspace_seed_snapshot,
        workspace_final_snapshot=workspace_final_snapshot,
        allowed_output_paths={_canonical_relative_path(path, allow_root=False) for path in task.allowed_output_paths},
    )


def snapshot_final_workspace(workspace: AgentWorkspace) -> None:
    if workspace.workspace_final_snapshot.exists():
        shutil.rmtree(workspace.workspace_final_snapshot)
    shutil.copytree(workspace.workspace_root, workspace.workspace_final_snapshot)


def _resolve_relative_path(root: Path, relative_path: str) -> Path:
    canonical = _canonical_relative_path(relative_path, allow_root=True)
    raw = Path(canonical)

    resolved = (root / raw).resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise WorkspaceError("Path escapes workspace root") from exc
    return resolved


def _canonical_relative_path(relative_path: str, *, allow_root: bool) -> str:
    raw = Path(relative_path)
    if raw.is_absolute():
        raise WorkspaceError("Absolute paths are not allowed")

    normalized_parts: list[str] = []
    for part in raw.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise WorkspaceError("Path traversal is not allowed")
        normalized_parts.append(part)

    if not normalized_parts:
        if allow_root:
            return "."
        raise WorkspaceError("Path must not be empty")
    return "/".join(normalized_parts)
