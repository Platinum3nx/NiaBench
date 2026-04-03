# NiaBench

Simple benchmark project for measuring whether fresh documentation context from Nia helps coding models on fast-moving libraries.

## Summary

NiaBench is a small, reproducible benchmark built around a simple question: if a coding model gets current documentation context through Nia, does it produce better code than it does from the task alone?

The project stays intentionally narrow. It focuses on libraries that change quickly, where stale model knowledge leads to predictable mistakes like deprecated imports, removed methods, outdated config shapes, and wrong type signatures. The repo includes the task dataset, an evaluation harness, grading logic, and a lightweight dashboard for viewing results.

## Project Goals

- Measure with-context versus without-context performance on the same task with the same model settings
- Focus on real version-drift failures instead of generic coding questions
- Keep runs reproducible, inspectable, and easy to rerun
- Store results in a format that is easy to audit and compare over time
- Keep the project small enough to maintain without turning it into a full research platform

## Non-Goals

- This is not a general coding benchmark
- This is not a model leaderboard
- This is not a benchmark for Nia latency, uptime, or pricing
- This is not meant to cover every library or every kind of coding task
- This is not a fully automated system; task quality still depends on review and curation

## Core Idea

Every benchmark task is run twice:

1. Baseline: the model receives only the task description
2. With Nia: the model receives the same task plus current documentation context retrieved through Nia

Everything else should stay the same: model, prompt shape, temperature, task text, and grading flow. That makes the comparison easy to understand and keeps the benchmark focused on the value of fresh context.

## Scope

NiaBench has four main parts:

1. A dataset of version-sensitive tasks
2. A harness that runs baseline and with-context evaluations
3. A grading pipeline that combines execution and rubric-based review
4. A simple dashboard that reads the latest result files

The first version should cover a focused set of high-churn libraries and enough tasks to show a clear pattern without over-optimizing for size. Quality matters more than raw task count.

## Design Principles

- Reproducible: runs should use fixed settings and stable model IDs when possible
- Auditable: prompts, retrieved context, outputs, and scores should be logged
- Narrow: only compare the effect of fresh documentation context
- Practical: tasks should look like normal developer requests, not quiz prompts
- Maintainable: the repo should be easy to update as libraries change

## Dataset Requirements

The dataset lives in [`dataset/tasks.json`](dataset/tasks.json) and is validated against [`dataset/task.schema.json`](dataset/task.schema.json).

Each task should include:

- a stable task ID
- the target library
- the version boundary that matters
- a natural-language task description
- the deprecated or outdated pattern
- the current correct pattern
- a category and difficulty label
- whether the task is executable
- a short note explaining why stale models are likely to fail

Good tasks should:

- target a real API change or current best-practice change
- be specific enough to grade reliably
- be written like a normal request a developer might make
- avoid trivia or edge cases that only exist to trick the model

Weak or ambiguous tasks should be removed instead of kept for volume.

## Task Categories

The dataset should mostly focus on the kinds of failures that show up when library knowledge goes stale:

- API migrations
- import path changes
- config schema changes
- type signature changes
- current best-practice updates

These categories are broad enough to cover common library churn while still being easy to reason about during grading.

## Library Selection

The benchmark should prioritize libraries that meet most of these criteria:

- actively maintained and changing
- widely used enough that the result is interesting
- likely to appear in real coding workflows
- known to have version-sensitive APIs or docs

The initial set can stay focused. A smaller list of good libraries with clear tasks is better than a large list padded with weak examples.

## Evaluation Harness

The evaluation harness lives in [`harness/run_eval.py`](harness/run_eval.py) with supporting code in the rest of the [`harness`](harness) package.

For each task, the harness should:

1. build a baseline prompt from the task description
2. retrieve relevant documentation context from Nia
3. build a treatment prompt that injects the retrieved context clearly
4. call the same model with the same settings for both runs
5. save outputs and metadata to result files

Required harness behavior:

- temperature stays fixed at `0`
- model IDs should be pinned when possible
- retrieved context should be logged verbatim
- full prompts should be saved for both baseline and treatment runs
- Nia responses should be cached when it helps keep reruns stable
- reruns should create new result artifacts instead of overwriting older ones

## Grading

The grading pipeline lives in [`grading`](grading).

Current Layer 1 release mode is judge-only. Execution-backed scoring is deferred to a later layer.

Target-state grading uses two signals:

1. Execution, when the task is executable
2. Rubric-based review for all tasks

Executable tasks should run in a clean sandbox so the benchmark can capture whether the produced code actually works on the target version. Useful outputs include:

- exit code
- stdout and stderr
- a typed failure category when execution fails

All tasks should also go through a judge pass with a clear rubric so partially correct answers can be distinguished from confidently outdated ones.

When execution scoring is enabled in a later layer, composite scoring should favor execution when execution is available, while still keeping the judge pass for nuance and traceability.

## Failure Signals

When code fails, the benchmark should preserve the reason instead of reducing everything to a generic failure. Common categories include:

- missing or outdated imports
- removed or renamed methods
- wrong argument signatures
- invalid config shapes
- malformed output
- timeouts

These details make the results easier to interpret and help show whether fresh documentation is fixing the kinds of mistakes the benchmark is supposed to measure.

## Results Format

Each run should produce structured results under [`results`](results).

At minimum, result artifacts should include:

- task metadata
- model and run metadata
- full baseline prompt and response
- full with-context prompt and response
- retrieved context and retrieval metadata
- grading details
- final per-task scores and deltas

Aggregate output should make it easy to answer a few basic questions:

- What is the overall improvement with Nia?
- Which libraries benefit the most?
- Which tasks still fail even with fresh context?
- What kinds of failures remain common?

## Dashboard

The dashboard lives in [`dashboard`](dashboard) and should stay lightweight.

It does not need to be a full application. A simple static site is enough as long as it can show:

- overall baseline score
- overall with-context score
- the improvement delta
- per-library breakdowns
- a small number of example tasks or drill-down views
- the timestamp or run ID for the current result set

The goal is readability, not polish for its own sake.

## Validation and Maintenance

Task validation and automation live in [`scripts`](scripts) and [`.github/workflows`](.github/workflows).

The project should include:

- schema validation for tasks
- basic CI checks for data and code integrity
- a simple path for adding new tasks
- an update workflow for libraries that release meaningful changes

Automation can draft new tasks or flag version updates, but task acceptance should stay reviewed. Benchmarks get noisy quickly if low-quality tasks are allowed in.

## Success Criteria

The project is in good shape when:

- the dataset validates cleanly
- the harness can run baseline and with-context passes end to end
- the grading pipeline produces consistent structured outputs
- result files are easy to inspect after a run
- the dashboard can render the latest aggregate scores
- adding or updating a task is straightforward

The benchmark does not need to be huge to be useful. A smaller benchmark with clear tasks, clean logging, and believable results is better than a larger one that is hard to trust.

## Repo Map

- [`dataset`](dataset): tasks, rubrics, schema, and library metadata
- [`harness`](harness): evaluation flow, prompts, provider clients, and Nia integration
- [`grading`](grading): sandbox, judge, and composite scoring
- [`results`](results): raw outputs, caches, and aggregate score files
- [`dashboard`](dashboard): static results UI
- [`scripts`](scripts): validation and update utilities
- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md): benchmark framing and grading notes

## Nice-to-Haves

These are useful, but not required for the first solid version:

- per-library trend tracking across runs
- better drill-down pages for individual tasks
- richer error summaries
- a smoother workflow for proposing new tasks from library release notes
- scheduled refresh runs for a small subset of libraries

## Final Notes

NiaBench works best when it stays simple. The project should be easy to explain in one sentence, easy to rerun from the repo, and easy to inspect when a result looks surprising. If a feature does not help with that, it is probably outside the scope of the benchmark.
