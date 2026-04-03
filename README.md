# NiaBench

NiaBench is a reproducible benchmark for measuring how much coding models improve when they receive fresh documentation context from Nia.

## What NiaBench Measures

Each task is evaluated twice:

1. Baseline: model answers without external documentation context.
2. Treatment: model answers with a labeled retrieved-context block injected into the system prompt.

The model, task, and runtime settings are held constant across both runs. The only intentional variable is whether retrieved documentation context is present.

## Layer 1 Snapshot

Source artifacts:

- Dataset: `dataset/tasks.json` (`30` tasks, `20` libraries)
- Aggregate: `results/scores.json` (`60` evaluations = `30` tasks x `2` models)

Current aggregate metrics:

- `overall_without_nia`: `75.0`
- `overall_with_nia`: `85.833333`
- `improvement_delta_pct`: `+10.833333`
- `nonperfect_baseline_delta_pct`: `+47.916667` (`24` evaluations)
- `perfect_baseline_delta_pct`: `-13.888889` (`36` evaluations)

## How To Interpret The Delta Metrics

- `nonperfect_baseline_delta_pct` is the cleanest signal for value-add, because it isolates rows where the baseline had room to improve.
- `perfect_baseline_delta_pct` can be negative when context introduces distraction on rows that were already solved perfectly.
- `improvement_delta_pct` is the blended overall delta across all rows.

## Repo Layout

- `dataset/`: benchmark tasks, schema, and library metadata
- `harness/`: baseline/treatment execution harness
- `grading/`: judge and composite scoring logic
- `results/`: raw artifacts and aggregate score outputs
- `dashboard/`: Next.js benchmark dashboard
- `docs/`: public benchmark methodology and deployment docs
- `scripts/`: validation and aggregation utilities

## Quickstart

Validate tasks:

```bash
python3 scripts/validate_tasks.py dataset/tasks.json
```

Run smoke dry-run (no external calls required):

```bash
python3 scripts/validate_tasks.py dataset/tasks_smoke.json
python3 -m harness.run_eval --provider openai --model gpt-4o-2024-11-20 --dry-run --tasks dataset/tasks_smoke.json
```

Run a live pilot task with explicit eval and judge models:

```bash
set -a; source .env; set +a
python3 -m harness.run_eval \
  --provider openai \
  --model gpt-4o-2024-11-20 \
  --judge-provider anthropic \
  --judge-model claude-sonnet-4-20250514 \
  --tasks dataset/tasks.json \
  --task-id openai-sdk-chatcompletions-to-responses \
  --run-id live-example-20260403
```

Judge note: using a different judge model is recommended when you want stronger independence between generation and grading.

Aggregate and validate scores:

```bash
python3 scripts/aggregate.py --input results/raw_curated/combined --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

Build the dashboard:

```bash
cd dashboard
npm install
npm run lint
npm run build
```

## Pinned Model IDs

Use pinned snapshots for reproducibility:

- Claude: `claude-sonnet-4-20250514`
- GPT-4o: `gpt-4o-2024-11-20`

## Key Docs

- `docs/METHODOLOGY.md`
- `docs/DEPLOYMENT.md`
- `CONTRIBUTING.md`
