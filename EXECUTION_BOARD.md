# NiaBench Execution Board

Status: Launch Track  
Last updated: Thursday, April 2, 2026 early morning ET  
Engineering target: Thursday, April 2, 2026 morning  
Dashboard target: Thursday, April 2, 2026 morning  
Current sprint plan: [`docs/CURRENT_SPRINT_PLAN.md`](/Users/arjunmalghan/NiaBench/docs/CURRENT_SPRINT_PLAN.md)

## Mission

Ship a credible first public build of NiaBench: a reproducible benchmark that isolates the effect of fresh Nia-retrieved documentation on coding-agent performance for version-sensitive library tasks.

Operating principle: keep the benchmark narrow, deterministic, and inspectable so every improvement claim can be traced to concrete retrieval context, prompts, outputs, and grading artifacts.

## Current Build Mode (Truth Surface)

- Benchmark path now includes a locked pilot dataset, live pilot results for both pinned models, a synced full OpenClaw raw corpus, and a dashboard that builds successfully against validated scores.
- The launch artifact should use the current locked `30`-task pilot and validated aggregate unless a clear defect is found tonight.
- The full OpenClaw raw corpus is now synced locally at `dataset/tasks_raw.json` with `324` validator-passing tasks; it is useful evidence and expansion material, but it is no longer a blocker for a Thursday, April 2, 2026 morning launch.
- A pilot candidate selected from the full raw corpus exists, but it differs materially from the current locked pilot and would require reruns if adopted tonight.
- Full sandbox-backed execution remains deferred for this sprint slice.
- Judge-first / judge-only scoring mode is the active bridge until sandbox integration lands.
- Empty task lists do not count as readiness.
- Smoke readiness requires a non-empty validator-passing smoke fixture such as `dataset/tasks_smoke.json`.
- Pilot readiness requires a non-empty validator-passing locked benchmark file.

## Launch Posture

- The benchmark core is already in place: locked pilot, live runs, validated aggregate, and successful dashboard production build.
- Tonight's job is packaging, consistency, and deployment readiness, not rebuilding the benchmark from scratch.
- Do not reopen the locked pilot tonight unless one of three things happens:
  - a validation failure appears
  - the full OpenClaw corpus exposes a clear duplicate, weak task, or coverage bug in the locked `30`
  - a founder-facing claim in docs or dashboard is contradicted by the actual artifacts
- The remote OpenClaw merge has landed, been synced locally, and passed validation; it should now be treated as a provenance and expansion asset rather than an active blocker.

## Final Sprint Checklist

- [x] Deployment target is fixed to a concrete launch path.
  Default launch assumption: Vercel preview/production using the committed `results/scores.json` and Next.js build-time prerendering.
- [x] Canonical founder-facing aggregate source is fixed to `results/raw_curated/combined`.
  `results/raw` remains exploratory history and should not be treated as the launch aggregate input.
- [x] Final launch validation is run locally even though CI already enforces task validation, score validation, and dashboard build on push/PR.
- [x] Auto-update stance is explicit: shipped in draft mode only via weekly `--dry-run`, not as a live task-writing updater.
- [x] Founder-facing/public copy is finalized against the current truthful release scope.

## Full Repo Progress Snapshot

- Dataset:
  - [x] Full OpenClaw raw corpus synced locally at `dataset/tasks_raw.json`
  - [x] Raw corpus validates at `324` tasks with `20` libraries represented
  - [x] Locked launch pilot remains `dataset/tasks.json` at `30` tasks
  - [x] Full-corpus candidate pilot exists at `dataset/tasks_candidate_pilot_openclaw_full.json`
- Harness and grading:
  - [x] Repo-root harness entrypoint works
  - [x] Retry/backoff is in place for Nia/provider calls
  - [x] Judge-only scoring path is live on both pinned models
- Results and aggregation:
  - [x] Live pilot runs exist for Claude and GPT-4o
  - [x] `results/scores.json` validates
  - [x] Aggregate covers `60` evaluations across the locked `30`-task pilot
  - [x] Canonical launch aggregate source exists under `results/raw_curated/combined`
- Dashboard and docs:
  - [x] Dashboard production build succeeds
  - [x] Deployment target and health check are confirmed
  - [x] Public-facing docs consistency pass is complete across README, methodology, sprint plan, and execution board
- CI and automation:
  - [x] CI workflow validates tasks, validates scores, and builds the dashboard
  - [x] Auto-update workflow exists, but currently runs `scripts/auto_update.py --dry-run` only
- Launch package:
  - [x] Founder-facing package and public copy are finalized for current launch scope
  - [x] Final launch-safe repo/deployment check has been run

## Remaining Before Launch

- [x] Confirm the dashboard deployment target is configured and healthy.
- [x] Lock the canonical founder-facing aggregate source to `results/raw_curated/combined` in launch steps and copy.
- [x] Keep the current locked pilot as the launch artifact unless a concrete defect is found in tonight's final review.
- [x] Run the final validation trio on the launch artifact set:
- [x] `python3 scripts/validate_tasks.py dataset/tasks.json`
- [x] `python3 scripts/validate_scores.py results/scores.json`
- [x] `cd dashboard && npm run build`
- [x] Keep auto-update described as weekly draft-mode only, not live automatic task mutation.
- [x] Finalize founder-facing copy and public benchmark framing.

## Deployment Evidence

- Vercel project linked: `rare-tech/dashboard`
- Build verification: `npx vercel build --yes --cwd dashboard` -> success (`status: ok`)
- Deployment verification: `npx vercel deploy --prebuilt --prod --yes --cwd dashboard` -> ready production deployment
- Inspector URL: `https://vercel.com/rare-tech/dashboard/69ZpJ56bM3WFq58Wtawh2ubPzRQJ`
- Deployment URL: `https://dashboard-46i21bqj1-rare-tech.vercel.app`
- Alias: `https://dashboard-rare-tech.vercel.app`
- Access note: project deployment protection has been disabled (`ssoProtection: null`), and alias access is public (`HTTP 200`).

## P0 Stop-The-Line Outcomes

These must be true before large pilot runs:

- [x] Harness entrypoint mismatch is fixed and standardized to `python3 -m harness.run_eval ...`.
- [x] Dry-run can execute without external API dependency.
- [x] `dataset/tasks_smoke.json` exists with `2-3` schema-valid synthetic tasks.
- [x] Judge wiring emits parsed grade outputs with explicit parse/provider status handling.
- [x] Aggregation command emits populated `results/scores.json` from smoke artifacts.

## Hard Gates

- [x] Only count task batches that pass `python3 scripts/validate_tasks.py <file>`.
- [x] Lock pilot at exactly `30 tasks`: all `20 libraries` represented, `10` libraries represented twice, balanced across `easy`, `medium`, and `hard`.
- [x] Use pinned model snapshots, not moving aliases.
- [x] Keep prompts deterministic (`temperature=0`, stable baseline/treatment structure).
- [x] Use direct Nia `search`/`index` retrieval paths and preserve auditable context payloads.
- [x] Preserve immutable run artifacts: prompts, retrieval payloads, model outputs, grading outputs, aggregates.
- [x] Ship auto-update path with first usable benchmark build or explicitly document deferral.
- [x] Auto-update status is explicit: weekly draft-mode only for this launch slice.
- [x] Verify retry/backoff/rate-limit behavior before large eval runs.
- [x] Keep harness, grading, dashboard, and automation moving while OpenClaw generation runs.
- [x] If fewer than `30` high-signal validator-passing tasks exist by Wednesday, April 1, 2026 `12pm ET`, pivot immediately to manually curated pilot assembly.
- [x] Smoke readiness is validated against `dataset/tasks_smoke.json` or another non-empty validator-passing smoke fixture.
- [x] `dataset/tasks.json` must contain exactly `30` validator-passing tasks for pilot lock.

## Progress Board

Status legend: `not_started`, `in_progress`, `blocked`, `done`.

| Workstream | Status | Last Updated (ET) | Evidence / Notes |
| --- | --- | --- | --- |
| 1. Harness runnability and smoke fixture | done | Apr 1, 2026 3:40 PM | Smoke fixture landed; module entrypoint and dry-run artifact generation verified. |
| 2. Retries and backoff | done | Apr 1, 2026 3:40 PM | Retry logic and retrieval fallback hardened to avoid runaway retry loops under Nia limits. |
| 3. Judge execution | done | Apr 1, 2026 3:40 PM | Judge scoring/parser contract is complete and live on both pinned models. |
| 4. Aggregation and dashboard contract | done | Apr 1, 2026 3:40 PM | Curated aggregate path validated; `results/scores.json` now contains live non-null metrics. |
| 5. Raw-task ingest and pilot selection | done | Apr 1, 2026 late evening | Full OpenClaw corpus (`324` valid tasks) synced locally; locked `dataset/tasks.json` still stands as the launch pilot. |
| 6. Verification and handoff | done | Apr 1, 2026 late evening | Full live runs complete (OpenAI + Anthropic), targeted reruns complete, aggregate validates, and dashboard build is green. |
| 7. Launch packaging and deploy readiness | done | Apr 2, 2026 early morning | Vercel target fixed (`rare-tech/dashboard`), `vercel build`/deploy verified, launch copy finalized, and validation trio rerun successfully. |

## Critical Path

1. Preserve the current locked pilot and validated aggregate as the default launch artifact.
2. Finish docs-consistency pass across `README.md`, `docs/METHODOLOGY.md`, `EXECUTION_BOARD.md`, and `docs/CURRENT_SPRINT_PLAN.md`.
3. Preserve the synced full OpenClaw raw corpus as evidence and future expansion material without reopening launch scope by default.
4. Fix the canonical aggregate story: founder-facing scores come from `results/raw_curated/combined`, not the entire exploratory `results/raw` tree.
5. Finalize deploy target, repo polish, and public-facing copy.
6. Launch Thursday, April 2, 2026 morning unless a concrete defect is discovered.

## Command Gate Checklist

### Harness and smoke

- [x] `python3 scripts/validate_tasks.py dataset/tasks_smoke.json` -> `OK (2-3 task(s))`
- [x] `python3 -m harness.run_eval --provider openai --model gpt-4o-2024-11-20 --dry-run --tasks dataset/tasks_smoke.json` -> artifacts under `results/raw/...`, exit `0`

### Retry and resiliency

- [x] Controlled retry path logs provider, attempt number, delay, and terminal reason
- [x] Single-task failures do not abort full run

### Judge and aggregation

- [x] Smoke artifacts include structured judge fields and explicit status metadata
- [x] `python3 scripts/aggregate.py --input results/raw_curated/combined --output results/scores.json` -> exit `0`
- [x] `python3 scripts/validate_scores.py results/scores.json` -> `OK`

### Dashboard contract

- [x] `cd dashboard && npm run build` succeeds against validated `results/scores.json`

CI note: these checks are also enforced in `.github/workflows/ci.yml`; the launch-eve local rerun is a final smoke pass, not the only enforcement point.

## Docs-Consistency Gate

Before marking sprint readiness, these docs must match the same ground truth:

- [`README.md`](/Users/arjunmalghan/NiaBench/README.md)
- [`docs/METHODOLOGY.md`](/Users/arjunmalghan/NiaBench/docs/METHODOLOGY.md)
- [`EXECUTION_BOARD.md`](/Users/arjunmalghan/NiaBench/EXECUTION_BOARD.md)
- [`docs/CURRENT_SPRINT_PLAN.md`](/Users/arjunmalghan/NiaBench/docs/CURRENT_SPRINT_PLAN.md)

Required checks:

- entry commands are valid from repo root
- judge-only/deferred sandbox mode is described consistently where applicable
- dashboard claims match aggregate contract and file location

## Launch Gates (Closed)

These were the launch blockers for a Thursday, April 2, 2026 morning public launch and are now closed:

- [x] `dataset/tasks.json`, `dataset/tasks_candidate_pilot.json`, and `results/scores.json` still validate after the full corpus sync.
- [x] Dashboard deployment target is configured and a production build or preview deployment is healthy.
- [x] Deployment path is explicit and consistent with the dashboard's build-time file access pattern.
- [x] README, methodology, sprint plan, and execution board all describe the same current truth: locked `30`-task pilot, judge-only scoring for this sprint slice, and live pilot results on both pinned models.
- [x] Canonical aggregate source for founder-facing scores is documented as `results/raw_curated/combined`, not generic `results/raw`.
- [x] Public-facing copy is explicit that the current release is a credible first benchmark build, not the final long-run expanded corpus.
- [x] Auto-update is described precisely as weekly draft-mode only (`--dry-run`) for this launch slice.
- [x] Founder-facing package is assembled from the validated artifact set already in the repo, not from ad hoc reruns.

## Anthropic Throughput Scheduling Policy

Three queues share constrained throughput:

- `generation` (OpenClaw)
- `benchmark_inference`
- `judge`

Rules:

- Do not saturate all three simultaneously.
- Run at most one high-volume queue plus one low-volume queue at a time.
- Throughput priority under pressure: `benchmark_inference` > `judge` > `generation`.
- Batch judge scoring after inference artifact generation when throttled.
- Log queue start/end windows, concurrency level, and rate-limit incidents.
- If repeated `429` occurs in one queue, reduce only that queue first.
- If org-wide limits are hit, pause `generation` before pausing benchmark inference.

## Timeline To Launch Tomorrow Morning

### Wednesday, April 1, 2026 Evening

- [x] Locked `30`-task pilot exists and validates.
- [x] Live pilot runs for both pinned models exist.
- [x] `results/scores.json` validates and the dashboard production build succeeds.
- [x] Sync the full OpenClaw raw corpus into the repo and preserve it as evidence.
- [x] Re-run ingestion and pilot-selection tooling against the synced raw corpus; no defect has forced the pilot to reopen.
- [x] Decide the exact launch artifact set: current locked `30`-task pilot, current validated `results/scores.json`, dashboard, and aligned docs.
- [x] Finish docs-consistency pass and remove any stale “Friday target” framing from user-facing docs.

### Overnight: Wednesday, April 1, 2026 -> Thursday, April 2, 2026

- [x] Keep OpenClaw non-blocking. The full generation run is complete, synced, and no longer a blocker to deployment work.
- [x] Avoid new long benchmark reruns unless a concrete defect is found in the locked pilot or current scores.
- [x] Stage deployment configuration, preview deploy if needed, and make sure the dashboard launch path is the intended one.
- [x] Lock founder-facing aggregation to `results/raw_curated/combined` and avoid treating `results/raw` as the canonical launch input.
- [x] Prepare launch copy and benchmark framing around the current truthful scope: locked pilot, pinned models, judge-only scoring for this sprint slice.

### Thursday, April 2, 2026 Early Morning

- [x] Final validation pass:
- [x] `python3 scripts/validate_tasks.py dataset/tasks.json`
- [x] `python3 scripts/validate_scores.py results/scores.json`
- [x] `cd dashboard && npm run build`
- [x] Confirm public repo state is coherent and launch-safe.
- [x] Confirm deployment is healthy.

### Thursday, April 2, 2026 Morning Launch Window

- [x] Publish the first usable NiaBench dashboard.
- [x] Publish the founder-facing benchmark package.
- [x] Publish the docs set that explains methodology, current limitations, and rerun evidence trail.
- [x] Keep the expanded raw corpus and post-launch benchmark enlargement as follow-on work, not a blocker.

## Release Criteria

- [x] Baseline and treatment conditions run end-to-end using pinned model snapshots.
- [x] Retrieval context and metadata are auditable and inspectable.
- [x] Pilot dataset is publicly defensible.
- [x] Aggregate deltas trace cleanly to task-level artifacts.
- [x] Dashboard reflects same artifacts produced by harness and aggregator.
- [x] External technical readers can understand and rerun benchmark flow from repo docs.
- [x] Public release package is internally consistent and honest about the current scope: locked pilot now, expanded corpus later.
