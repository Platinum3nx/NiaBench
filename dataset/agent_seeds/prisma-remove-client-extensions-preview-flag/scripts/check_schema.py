#!/usr/bin/env python3
"""Simple local schema guard used by Layer 2 smoke runs."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    schema = Path("schema.prisma")
    if not schema.exists():
        print("schema.prisma not found", file=sys.stderr)
        return 1

    text = schema.read_text(encoding="utf-8")
    if "previewFeatures" in text:
        print("previewFeatures still present", file=sys.stderr)
        return 1
    print("schema check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
