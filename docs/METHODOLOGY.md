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

## Eval harness

For each task, the harness makes two model calls:

1. Baseline: task description only
2. Treatment: identical task, plus a clearly labeled `CURRENT DOCUMENTATION CONTEXT (retrieved via Nia)` block injected into the system prompt

The harness calls Nia's direct `search` and `index` API endpoints, not the MCP server, so retrieved context can be logged verbatim and audited later. The full prompt sent to the model is written to the result file for both baseline and treatment runs.

## Grading

Executable tasks go through a sandbox step that captures:

- exit code
- stdout / stderr
- typed failure category

All tasks also go through a rubric-aware judge pass. Composite scoring weights execution more heavily for executable tasks and uses the judge signal to capture partial correctness.

## Reproducibility principles

NiaBench is only useful if it is trusted. That means:

- prompts are logged
- retrieved context is logged
- failures are stored alongside successful runs
- reruns are targeted and auditable
