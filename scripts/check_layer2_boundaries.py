#!/usr/bin/env python3
"""Enforce Layer 2 isolation from frozen Layer 1 contracts."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent

FROZEN_LAYER1_SURFACES = {
    "harness/run_eval.py",
    "harness/config.py",
    "harness/llm_clients.py",
    "harness/types.py",
    "harness/prompts.py",
    "harness/nia_client.py",
    "harness/retry.py",
    "grading/judge.py",
    "grading/composite.py",
    "grading/types.py",
    "scripts/aggregate.py",
    "scripts/validate_scores.py",
    "dashboard/lib/load-scores.ts",
    "dashboard/lib/types.ts",
    "dashboard/app/page.tsx",
}

LAYER2_PYTHON_GLOBS = (
    "harness/agent_*.py",
    "grading/agent_*.py",
    "scripts/*agent*.py",
    "scripts/check_layer2_boundaries.py",
)

LAYER2_DASHBOARD_GLOBS = (
    "dashboard/app/agent/**/*.ts",
    "dashboard/app/agent/**/*.tsx",
    "dashboard/lib/*agent*.ts",
    "dashboard/lib/*agent*.tsx",
)

BANNED_IMPORTS = {
    "harness.llm_clients": "Layer 2 must not use Layer 1 BaseLLMClient hierarchy",
    "grading.judge": "Layer 2 must use grading/agent_judge.py",
    "grading.composite": "Layer 2 must not reuse Layer 1 composite contract",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        default="main",
        help="Git ref used to compute merge-base for frozen-surface diff checks",
    )
    parser.add_argument(
        "--allow-frozen-change",
        action="store_true",
        help="Bypass frozen Layer 1 file diff checks intentionally",
    )
    parser.add_argument(
        "--allowlist",
        default="docs/layer2_frozen_allowlist.txt",
        help="Optional newline-delimited allowlist of frozen files allowed to differ",
    )
    parser.add_argument(
        "--curated-input",
        default="results/agent_raw_curated/combined",
        help="Curated run artifact directory for model/judge independence checks",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    allowlisted = load_allowlist(REPO_ROOT / args.allowlist)
    changed_files = list_changed_files(args.base_ref, errors)

    if not args.allow_frozen_change:
        errors.extend(check_frozen_surface_changes(changed_files, allowlisted))
    errors.extend(check_forbidden_symbols_in_layer2())
    errors.extend(check_output_path_contracts())
    errors.extend(check_dashboard_boundaries(changed_files, allowlisted))
    errors.extend(check_model_judge_independence(REPO_ROOT / args.curated_input))

    if errors:
        print("Layer 2 boundary checks failed:", file=sys.stderr)
        for issue in errors:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    print("Layer 2 boundary checks passed")
    return 0


def load_allowlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    entries: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(line)
    return entries


def list_changed_files(base_ref: str, errors: list[str]) -> list[str]:
    try:
        merge_base = run_git(["merge-base", base_ref, "HEAD"]).strip()
    except RuntimeError as exc:
        errors.append(str(exc))
        return []
    try:
        output = run_git(["diff", "--name-only", f"{merge_base}...HEAD"])
    except RuntimeError as exc:
        errors.append(str(exc))
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def run_git(args: list[str]) -> str:
    command = ["git", *args]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
        raise RuntimeError(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout


def check_frozen_surface_changes(changed_files: list[str], allowlisted: set[str]) -> list[str]:
    violations = sorted(
        path
        for path in changed_files
        if path in FROZEN_LAYER1_SURFACES and path not in allowlisted
    )
    if not violations:
        return []
    return [
        "Frozen Layer 1 surfaces changed without allowlist/override: "
        + ", ".join(violations)
    ]


def check_forbidden_symbols_in_layer2() -> list[str]:
    errors: list[str] = []
    for path in iter_layer2_python_files():
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT)} failed to parse: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in BANNED_IMPORTS:
                        errors.append(
                            f"{path.relative_to(REPO_ROOT)} imports {alias.name}: "
                            f"{BANNED_IMPORTS[alias.name]}"
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in BANNED_IMPORTS:
                    errors.append(
                        f"{path.relative_to(REPO_ROOT)} imports from {module}: "
                        f"{BANNED_IMPORTS[module]}"
                    )
                if module == "harness.prompts":
                    for alias in node.names:
                        if alias.name == "build_nia_query" or alias.name == "*":
                            errors.append(
                                f"{path.relative_to(REPO_ROOT)} imports build_nia_query "
                                "from harness.prompts"
                            )
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    if node.value.id == "harness" and node.attr == "llm_clients":
                        errors.append(
                            f"{path.relative_to(REPO_ROOT)} references harness.llm_clients"
                        )
            elif isinstance(node, ast.Name):
                if node.id in {"BaseLLMClient", "JudgeGrader", "CompositeGrader", "build_nia_query"}:
                    errors.append(
                        f"{path.relative_to(REPO_ROOT)} references forbidden symbol {node.id}"
                    )
    return dedupe(errors)


def check_output_path_contracts() -> list[str]:
    errors: list[str] = []
    for path in iter_layer2_python_files():
        if path == Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT)
        if "results/raw/" in text:
            errors.append(f"{rel} references forbidden Layer 1 output path results/raw/")
        if "results/scores.json" in text:
            errors.append(f"{rel} references forbidden Layer 1 aggregate results/scores.json")

    for path in iter_layer2_dashboard_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT)
        if "results/scores.json" in text:
            errors.append(f"{rel} must not load Layer 1 score file results/scores.json")
    return dedupe(errors)


def check_dashboard_boundaries(changed_files: list[str], allowlisted: set[str]) -> list[str]:
    protected = {
        "dashboard/app/page.tsx",
        "dashboard/lib/load-scores.ts",
        "dashboard/lib/types.ts",
    }
    touched = sorted(path for path in changed_files if path in protected and path not in allowlisted)
    if not touched:
        return []
    return [
        "Layer 2 work touched protected Layer 1 dashboard files without allowlist: "
        + ", ".join(touched)
    ]


def check_model_judge_independence(curated_root: Path) -> list[str]:
    if not curated_root.exists():
        return []

    violations: list[str] = []
    for json_path in curated_root.rglob("*.json"):
        payload = load_json_object(json_path)
        if payload is None:
            continue
        model_provider = payload.get("model_provider")
        model = payload.get("model")
        judge_provider = payload.get("judge_provider")
        judge_model = payload.get("judge_model")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (model_provider, model, judge_provider, judge_model)
        ):
            continue
        if model_provider == judge_provider and model == judge_model:
            rel = json_path.relative_to(REPO_ROOT)
            violations.append(
                f"{rel} uses identical agent/judge model pair {model_provider}:{model}"
            )
    return violations


def load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def iter_layer2_python_files() -> list[Path]:
    paths: set[Path] = set()
    for pattern in LAYER2_PYTHON_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file():
                paths.add(path)
    return sorted(paths)


def iter_layer2_dashboard_files() -> list[Path]:
    paths: set[Path] = set()
    for pattern in LAYER2_DASHBOARD_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file():
                paths.add(path)
    return sorted(paths)


def dedupe(items: list[str]) -> list[str]:
    return sorted(set(items))


if __name__ == "__main__":
    raise SystemExit(main())
