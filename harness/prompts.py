"""Prompt helpers for baseline and treatment eval calls."""

from __future__ import annotations

from typing import Iterable

from harness.types import NiaChunk, Task


BASELINE_SYSTEM_PROMPT = (
    "You are a coding assistant. Return only code. "
    "Do not include explanations, markdown fences, or commentary."
)


def build_nia_query(task: Task) -> str:
    return (
        f"{task.library} {task.version_introduced} {task.category} "
        f"{task.correct_pattern} documentation"
    )


def format_context_block(chunks: Iterable[NiaChunk]) -> str:
    rendered: list[str] = []
    for chunk in chunks:
        label_bits = [part for part in (chunk.title, chunk.source, chunk.url) if part]
        header = " | ".join(label_bits) if label_bits else "Context chunk"
        rendered.append(f"{header}\n{chunk.text.strip()}")
    if not rendered:
        return "CURRENT DOCUMENTATION CONTEXT (retrieved via Nia)\nNo context returned."
    return (
        "CURRENT DOCUMENTATION CONTEXT (retrieved via Nia)\n"
        + "\n---\n".join(rendered)
    )


def build_prompts(task: Task, context_chunks: list[NiaChunk]) -> tuple[dict[str, str], dict[str, str]]:
    baseline = {
        "system": BASELINE_SYSTEM_PROMPT,
        "user": task.task_description,
    }
    treatment = {
        "system": BASELINE_SYSTEM_PROMPT + "\n\n" + format_context_block(context_chunks),
        "user": task.task_description,
    }
    return baseline, treatment
