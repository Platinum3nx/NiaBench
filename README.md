# NiaBench

Context retrieval benchmark for AI coding agents.

NiaBench measures how much coding models improve when they get fresh, indexed documentation context for fast-moving libraries instead of relying on stale training data alone.

## Current Status

The repo is in active buildout. Current scaffolding includes:

- benchmark task schema and rubrics
- a direct Nia API harness skeleton
- grading pipeline skeletons
- result schemas and score plumbing
- a Next.js dashboard shell
- docs, contribution guidance, and workflow scaffolding

## Repo Layout

- `dataset/`: benchmark tasks, rubrics, and target library metadata
- `harness/`: baseline and with-Nia evaluation harness
- `grading/`: sandbox, judge, and composite scoring logic
- `results/`: raw outputs, caches, and aggregated score files
- `dashboard/`: Next.js results dashboard
- `docs/`: methodology and development docs
- `scripts/`: validation and automation utilities

## Quickstart

Validate the task file:

```bash
python3 scripts/validate_tasks.py dataset/tasks.json
```

Run the eval harness in dry-run mode:

```bash
python3 harness/run_eval.py --provider anthropic --model claude-sonnet-4-20250514 --dry-run
```

## Pinned Model IDs

Use pinned snapshot IDs rather than moving aliases so the benchmark stays reproducible:

- Claude: `claude-sonnet-4-20250514`
- GPT-4o: `gpt-4o-2024-11-20`

Example commands:

```bash
python3 harness/run_eval.py --provider anthropic --model claude-sonnet-4-20250514
python3 harness/run_eval.py --provider openai --model gpt-4o-2024-11-20
```

## Key Docs

- `docs/METHODOLOGY.md`
- `CONTRIBUTING.md`
- `EXECUTION_BOARD.md`
