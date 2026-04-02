# NiaBench

Context retrieval benchmark for AI coding agents.

NiaBench measures how much coding models improve when they get fresh, indexed documentation context for fast-moving libraries instead of relying on stale training data alone.

## Current Status (April 2, 2026 early morning ET)

The locked 30-task pilot has now been run live on both pinned models in judge-only mode. The latest aggregate in `results/scores.json` contains:

- `evaluations_count`: `60` (`30` unique tasks x `2` models)
- `tasks_evaluated`: `60` (deprecated alias kept for back-compat)
- `libraries_covered`: `20`
- `overall_without_nia`: `75.0`
- `overall_with_nia`: `85.833333`
- `improvement_delta_pct`: `10.833333`
- `nonperfect_baseline_delta_pct`: `+47.916667` across `24` evaluations
- `perfect_baseline_delta_pct`: `-13.888889` across `36` evaluations

Current implementation highlights:

- benchmark task schema and validator are in place
- full OpenClaw raw corpus has been synced locally at `dataset/tasks_raw.json` with `324` validator-passing tasks
- the launch artifact remains the locked `30`-task pilot in `dataset/tasks.json`; a full-corpus-selected pilot candidate exists, but switching to it would require reruns
- direct Nia API retrieval harness is implemented with resilient fallback behavior
- grading modules run in active judge-only scoring mode; full sandbox integration is deferred
- Next.js dashboard is wired to `results/scores.json` and renders live pilot metrics
- deployment target is fixed to Vercel project `rare-tech/dashboard`; `vercel build` and deployment health checks are passing
- sprint execution is tracked in `docs/CURRENT_SPRINT_PLAN.md`

## Current Build Mode

To keep progress unblocked while infrastructure lands:

- `dataset/tasks_raw.json` is now the full validated raw task pool (`324` tasks) sourced from the completed OpenClaw run
- `dataset/tasks.json` remains the locked pilot used for the current public benchmark build
- scoring is currently treated as judge-first / judge-only for the active sprint slice
- full sandbox-backed execution is explicitly deferred for this sprint slice
- smoke readiness requires a non-empty validated smoke fixture
- pilot readiness requires a locked non-empty validated `dataset/tasks.json`

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
python3 scripts/validate_tasks.py <tasks-file>.json
```

Run the smoke fixture in dry-run mode (no external API calls required):

```bash
python3 scripts/validate_tasks.py dataset/tasks_smoke.json
python3 -m harness.run_eval --provider openai --model gpt-4o-2024-11-20 --dry-run --tasks dataset/tasks_smoke.json
```

Run a live pilot task with an explicit run id:

```bash
set -a; source .env; set +a
python3 -m harness.run_eval \
  --provider openai \
  --model gpt-4o-2024-11-20 \
  --judge-provider openai \
  --judge-model gpt-4o-2024-11-20 \
  --tasks dataset/tasks.json \
  --task-id openai-sdk-chatcompletions-to-responses \
  --run-id live-openai-example-20260401
```

Run the eval harness (repo-root entrypoint):

```bash
python3 -m harness.run_eval --provider anthropic --model claude-sonnet-4-20250514 --dry-run --tasks <tasks-file>.json
```

Filter runs as needed:

```bash
python3 -m harness.run_eval --provider openai --model gpt-4o-2024-11-20 --tasks <tasks-file>.json --library openai-sdk --limit 5
```

Aggregate and validate dashboard scores:

```bash
# Founder-facing scores should be generated from the curated launch input,
# not from the entire exploratory results/raw tree.
python3 scripts/aggregate.py --input results/raw_curated/combined --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

Current launch note:

- `results/raw_curated/combined` is the canonical aggregate input for the current public build
- `results/raw` contains exploratory history and reruns and should not be treated as the founder-facing source of truth

Final launch-safe validation trio:

```bash
python3 scripts/validate_tasks.py dataset/tasks.json
python3 scripts/validate_scores.py results/scores.json
cd dashboard && npm run build
```

Ingest and assess raw task batches:

```bash
python3 scripts/ingest_tasks.py --raw dataset/tasks_raw.json --report results/reports/intake.json
python3 scripts/select_pilot.py --input dataset/tasks_raw.normalized.json --output dataset/tasks_candidate_pilot.json --report results/reports/pilot_selection.json --strict-difficulty
```

## Pinned Model IDs

Use pinned snapshot IDs rather than moving aliases so benchmark runs stay reproducible:

- Claude: `claude-sonnet-4-20250514`
- GPT-4o: `gpt-4o-2024-11-20`

## Key Docs

- `docs/CURRENT_SPRINT_PLAN.md`
- `EXECUTION_BOARD.md`
- `docs/METHODOLOGY.md`
- `docs/DEPLOYMENT.md`
- `CONTRIBUTING.md`

## Auto-Update Status

The weekly auto-update workflow is shipped in draft mode only for this release slice. `.github/workflows/auto-update.yml` runs:

```bash
python3 scripts/auto_update.py --dry-run
```

That means it produces update candidates, but it does not automatically rewrite benchmark tasks or publish live dataset changes yet.

## Deployment Target (Vercel)

The launch deployment path is the Vercel `dashboard` project under team/account `rare-tech`, with Next.js prerendering from committed benchmark artifacts.

Deploy commands:

```bash
npx vercel pull --yes --environment preview --cwd dashboard
npx vercel build --yes --prod --cwd dashboard
npx vercel deploy --prebuilt --prod --yes --cwd dashboard
```

Latest healthy deployment alias:

- `https://dashboard-rare-tech.vercel.app`
- publicly accessible (`HTTP 200` verified)
