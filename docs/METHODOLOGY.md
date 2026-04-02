# NiaBench Methodology

## Benchmark framing

NiaBench is a with-context versus without-context benchmark for coding models operating on fast-moving libraries. It is not a general coding benchmark and it is not a model leaderboard. The comparison is always the same model, same parameters, same task, with the only variable being whether fresh documentation context is injected.

## Dataset construction

The dataset focuses on high-churn libraries where stale model knowledge predictably leads to deprecated imports, removed methods, outdated config shapes, and wrong type signatures. Every task records:

- the version boundary
- the deprecated pattern
- the correct current pattern
- why a model would confidently fail without fresh context

The dataset quality gate is strict by design. Weak or ambiguous tasks are excluded rather than padded into the benchmark.

Current sprint state:

- `dataset/tasks_raw.json` now contains the full synced OpenClaw raw corpus (`324` validator-passing tasks)
- `dataset/tasks.json` is locked at `30` validator-passing pilot tasks with all `20` tracked libraries represented, `10` libraries represented twice, and balanced easy/medium/hard difficulty buckets
- the current public benchmark build uses the locked pilot, not the entire raw corpus directly
- founder-facing aggregate regeneration is locked to `results/raw_curated/combined`

## Eval harness

For each task, the harness makes two model calls:

1. Baseline: task description only
2. Treatment: identical task, plus a clearly labeled `CURRENT DOCUMENTATION CONTEXT (retrieved via Nia)` block injected into the system prompt

The harness calls Nia's direct API endpoints (not the MCP server) so retrieved context can be logged verbatim and audited later. The full prompt sent to the model is written to the result file for both baseline and treatment runs.

When retrieval is rate-limited or transiently unavailable, the harness records the retrieval error in run artifacts and continues the task with an empty context block rather than entering uncontrolled retry loops.

## Grading

Current sprint mode is judge-first/judge-only so pilot artifacts remain usable while sandbox execution is being integrated.

- Judge grading is rubric-aware and returns baseline/treatment scores with rationales.
- Composite scoring is currently derived from judge scores in judge-only mode.
- Sandbox execution remains an explicit deferred integration point for executable tasks in this sprint slice.

## Reproducibility principles

NiaBench is only useful if it is trusted. That means:

- prompts are logged
- retrieved context is logged
- judge prompt/response traces are logged
- failures are stored alongside successful runs
- reruns are targeted and auditable

## Current live pilot snapshot

Current aggregate (`results/scores.json`) from the locked 30-task pilot on both pinned models:

- evaluations: `60` (`30` unique tasks x `2` models)
- libraries covered: `20`
- overall without Nia: `75.0`
- overall with Nia: `85.833333`
- delta: `+10.833333`

The expanded raw corpus is retained as provenance and future benchmark expansion material, but the release artifact for this sprint slice remains the locked 30-task pilot plus its corresponding run artifacts and aggregate.
