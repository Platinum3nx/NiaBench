#!/usr/bin/env python3
"""Draft weekly update candidates for benchmark libraries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libraries", default="dataset/libraries.json")
    parser.add_argument("--tasks", default="dataset/tasks.json")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    args = parse_args()
    libraries = load_json(args.libraries)
    tasks = load_json(args.tasks)

    latest_versions: dict[str, str] = {}
    for task in tasks:
      latest_versions[task["library"]] = max(
          task["version_introduced"],
          latest_versions.get(task["library"], ""),
      )

    candidates = []
    for library in libraries:
        candidates.append(
            {
                "library": library["id"],
                "label": library["label"],
                "github_repo": library["github_repo"],
                "highest_version_in_tasks": latest_versions.get(library["id"]),
                "status": "pending_release_check",
            }
        )

    output = {
        "mode": "dry-run" if args.dry_run else "live",
        "libraries_considered": len(candidates),
        "candidates": candidates,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
