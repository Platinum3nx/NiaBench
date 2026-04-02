"""Core datatypes for the evaluation harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Task:
    id: str
    library: str
    version_introduced: str
    task_description: str
    deprecated_pattern: str
    correct_pattern: str
    reference_solution: str | None
    difficulty: str
    category: str
    executable: bool
    why_models_fail_this: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Task":
        return cls(
            id=payload["id"],
            library=payload["library"],
            version_introduced=payload["version_introduced"],
            task_description=payload["task_description"],
            deprecated_pattern=payload["deprecated_pattern"],
            correct_pattern=payload["correct_pattern"],
            reference_solution=payload.get("reference_solution"),
            difficulty=payload["difficulty"],
            category=payload["category"],
            executable=payload["executable"],
            why_models_fail_this=payload["why_models_fail_this"],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NiaChunk:
    text: str
    title: str | None = None
    url: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelResponse:
    text: str
    tokens_in: int | None
    tokens_out: int | None
    raw_response: dict[str, Any]
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
