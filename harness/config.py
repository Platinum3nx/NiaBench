"""Shared harness configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = REPO_ROOT / "results"
RAW_RESULTS_DIR = RESULTS_DIR / "raw"
NIA_CACHE_DIR = RESULTS_DIR / "cache" / "nia"


@dataclass(frozen=True)
class HarnessConfig:
    nia_api_key: str | None
    nia_search_endpoint: str | None
    nia_index_endpoint: str | None
    anthropic_api_key: str | None
    openai_api_key: str | None
    results_dir: Path = RAW_RESULTS_DIR
    nia_cache_dir: Path = NIA_CACHE_DIR


def load_config() -> HarnessConfig:
    return HarnessConfig(
        nia_api_key=os.getenv("NIA_API_KEY"),
        nia_search_endpoint=os.getenv("NIA_SEARCH_ENDPOINT"),
        nia_index_endpoint=os.getenv("NIA_INDEX_ENDPOINT"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )
