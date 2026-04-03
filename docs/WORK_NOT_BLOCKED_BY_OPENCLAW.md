# Work Not Blocked By OpenClaw

Status: Archived (historical planning memo)  
Context date: Wednesday, April 1, 2026  
Purpose: identify the highest-value NiaBench work that can move forward immediately without waiting for the current OpenClaw run to finish.

Note: this document is preserved as a historical execution memo. For current benchmark commands and canonical aggregate paths, use `README.md`, `docs/DEPLOYMENT.md`, and `docs/METHODOLOGY.md`.

## Core Point

NiaBench is no longer blocked on new generated tasks for its next meaningful milestone.

The repo already has:

- a locked `30`-task pilot in `dataset/tasks.json`
- a smoke fixture in `dataset/tasks_smoke.json`
- a runnable eval harness
- retry and backoff support
- judge-only scoring
- aggregation and score validation
- dashboard wiring to `results/scores.json`

That means the next meaningful progress comes from real benchmark execution, score generation, failure triage, and founder-facing polish, not from waiting for more raw task generation.

## What Is Still Actually Blocked By OpenClaw

These are the things that benefit from the run finishing later, but do not need to happen now:

- expanding beyond the current locked `30`-task pilot
- replacing manual/hybrid pilot tasks with stronger generated variants
- finding additional exemplar tasks for the public story
- long-term refresh and update flows

## What We Can Do Right Now

## 1. Run A Real `5`-Task Live Slice

Goal: prove the benchmark path works with real model outputs, real retrieval, real judge scoring, and real aggregates.

Why this is unblocked:

- the pilot dataset is already locked
- the harness already supports filtered runs
- aggregation already exists

Recommended approach:

- start with `5` tasks from the locked pilot
- use one provider first to reduce moving parts
- prefer OpenAI first if you want to avoid competing with Anthropic limits while OpenClaw is still running

Suggested commands:

```bash
python3 -m harness.run_eval \
  --provider openai \
  --model gpt-4o-2024-11-20 \
  --judge-provider openai \
  --judge-model gpt-4o-2024-11-20 \
  --tasks dataset/tasks.json \
  --limit 5

python3 scripts/aggregate.py --input results/raw --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

Definition of done:

- real non-dry-run result artifacts exist for `5` pilot tasks
- `judge_result.status` is no longer `skipped`
- `results/scores.json` contains non-null metrics for at least that slice

## 2. Run The Full Locked Pilot For One Model

Goal: generate the first real benchmark result set on the current `30`-task pilot.

Why this is unblocked:

- the pilot lock is already done
- this does not require additional generated tasks

Suggested command:

```bash
python3 -m harness.run_eval \
  --provider openai \
  --model gpt-4o-2024-11-20 \
  --judge-provider openai \
  --judge-model gpt-4o-2024-11-20 \
  --tasks dataset/tasks.json
```

Then:

```bash
python3 scripts/aggregate.py --input results/raw --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

Definition of done:

- the full pilot has real artifacts for one model
- `results/scores.json` shows non-null aggregate metrics
- the dashboard can render real numbers instead of `Pending`

## 3. Run The Second Pinned Model

Goal: turn the benchmark from a single-model internal check into a credible comparative benchmark surface.

Why this is unblocked:

- the dataset is already fixed
- the harness already supports multiple providers

Suggested command:

```bash
python3 -m harness.run_eval \
  --provider anthropic \
  --model claude-sonnet-4-20250514 \
  --judge-provider anthropic \
  --judge-model claude-sonnet-4-20250514 \
  --tasks dataset/tasks.json
```

Important note:

- if OpenClaw is still consuming Anthropic capacity, stage this carefully
- it may be better to finish the OpenAI pilot first, then run Anthropic after the OpenClaw load drops

Definition of done:

- both pinned models have pilot artifacts
- `results/scores.json` includes both model identifiers

## 4. Triage Failures And Do Targeted Reruns

Goal: convert the first live run from “raw output exists” into “results are believable.”

Why this is unblocked:

- this depends on live artifacts from the current locked pilot, not on new task generation

What to inspect:

- provider failures
- retrieval failures
- judge parse/provider failures
- suspiciously empty context
- clearly wrong baseline/treatment deltas
- tasks where both baseline and treatment failed in the same way

What to do:

- classify failures as harness bug, retrieval issue, judge issue, or model miss
- rerun only the tasks that need reruns
- do not rerun the full pilot unless the first run was structurally bad

Definition of done:

- a short list of rerun-worthy tasks exists
- reruns are targeted and documented
- obviously invalid artifacts are replaced by cleaner reruns

## 5. Freeze And Tighten Scoring Semantics

Goal: reduce ambiguity before founder-facing presentation.

Why this is unblocked:

- the scoring path already exists in judge-only mode
- this is a semantics and quality step, not a dataset-generation step

Concrete work:

- verify the current judge-only aggregation math is what you want to stand behind
- confirm how `skipped`, `parse_error`, and `provider_error` rows should affect aggregates
- confirm deduping logic is keeping the intended latest runs
- confirm the `tasks_evaluated` definition matches what you want to say publicly

Files to inspect:

- `grading/composite.py`
- `grading/judge.py`
- `scripts/aggregate.py`
- `results/scores.json`

Definition of done:

- scoring semantics are explicit enough to explain to an external reader
- no obvious ambiguity remains in what the aggregate numbers mean

## 6. Polish The Dashboard Against Real Data

Goal: make the dashboard founder-ready once real scores exist.

Why this is unblocked:

- the dashboard is already wired to `results/scores.json`
- once real results exist, the remaining work is mostly presentation and interpretation

Good work to do:

- confirm the homepage still looks right with real non-null values
- improve copy for pending vs complete states
- add a small note about judge-only mode if needed
- choose whether to surface a couple of example tasks or keep the first version summary-only
- sanity-check mobile and desktop rendering

Definition of done:

- the dashboard reads clearly with real data
- no wording suggests capabilities that are not implemented yet

## 7. Tighten Founder-Facing Docs

Goal: make the project read like an intentional benchmark system instead of an internal prototype.

Why this is unblocked:

- docs quality is independent of the OpenClaw run finishing
- the key current truth is already known

High-value doc work:

- add a short “current benchmark state” note once live results exist
- explain judge-only mode honestly
- explain that sandbox execution is the next integration step, not part of the current sprint slice
- document how to rerun the pilot and regenerate aggregates
- write the founder-facing narrative:
  - what NiaBench measures
  - why the dataset is version-sensitive
  - why the benchmark is auditable
  - what is implemented today vs deferred

Definition of done:

- a technical founder can understand the benchmark path without extra context
- the docs do not overclaim

## 8. Improve CI And Release Confidence

Goal: reduce the chance that the repo looks good locally but breaks when shared.

Why this is unblocked:

- CI and verification do not depend on more generated tasks

Good next steps:

- add dashboard build to CI if not already covered there
- ensure score validation runs in CI against the committed `results/scores.json`
- add a smoke command sequence to docs or a script
- ensure the aggregate path is reproducible from a clean checkout

Definition of done:

- the repo has a clear automated confidence path for tasks, scores, Python modules, and dashboard build

## 9. Prepare The Founder Demo Flow

Goal: be ready to show NiaBench confidently as soon as live pilot scores are available.

Why this is unblocked:

- demo preparation depends more on narrative and artifact selection than on additional generated tasks

Prepare:

- one short repo walkthrough
- one short methodology explanation
- one explanation of why the benchmark is auditable
- one explanation of current limitations:
  - judge-only mode
  - deferred sandbox
  - throughput/rate-limit constraints
- one or two strongest example tasks from the locked pilot

Definition of done:

- you can explain the benchmark in a few minutes without improvising
- the founder sees a coherent system, not just disconnected scripts

## Recommended Order For Today

1. Run a real `5`-task slice.
2. If healthy, run the full pilot for one model.
3. Aggregate and inspect the real scores.
4. Triage failures and do targeted reruns.
5. Run the second model.
6. Re-aggregate and validate.
7. Polish dashboard and docs against the real results.

## Full-Day Completion Plan

If the goal is to complete everything in this document today, use the order below. This sequence is designed to minimize wasted runs, protect against rate-limit collisions, and make sure the founder-facing surface only gets polished after the underlying benchmark evidence is real.

## Phase 0: Preflight And Run Strategy

Goal: start the day with a clean execution plan rather than jumping straight into expensive model runs.

Checklist:

- [ ] Confirm the locked pilot and smoke fixture both validate.
- [ ] Confirm core Python modules still compile.
- [ ] Confirm local environment has the required API keys and Nia endpoint configuration.
- [ ] Inspect the current `results/raw/` tree so you know what is smoke data versus candidate live data.
- [ ] Decide whether OpenAI or Anthropic goes first.

Do this first:

- confirm API keys and Nia endpoints are available locally
- confirm OpenClaw is still the only competing background workload
- decide whether Anthropic capacity is safe to use today or whether OpenAI should go first
- decide where run logs and notes for failures/reruns will live
- check the current `results/raw/` tree so you know which prior runs are smoke artifacts and which are candidate live artifacts

Outputs:

- one chosen first provider for live pilot execution
- one short written note for the day’s sequencing, especially whether Anthropic runs are delayed until OpenClaw quiets down

Exit condition:

- you know which provider goes first and why
- you know whether today’s plan includes both models or whether Anthropic work is a later-day risk

Commands:

```bash
python3 scripts/validate_tasks.py dataset/tasks_smoke.json
python3 scripts/validate_tasks.py dataset/tasks.json
python3 -m compileall harness grading scripts

python3 - <<'PY'
import os
for key in ["NIA_API_KEY", "NIA_SEARCH_ENDPOINT", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
    print(f"{key}={'set' if os.getenv(key) else 'missing'}")
PY

find results/raw -maxdepth 3 -type f | sort | tail -n 50
```

## Phase 1: Prove The Live Path On A Small Real Slice

Goal: get real benchmark evidence on a small slice before committing to the full pilot.

Checklist:

- [ ] Run a real `5`-task live slice with judge enabled.
- [ ] Aggregate immediately afterward.
- [ ] Validate the scores contract.
- [ ] Inspect a few raw result artifacts directly.
- [ ] Confirm the slice is healthy before expanding.

Order:

1. Run a live `5`-task slice on the locked pilot with judge enabled.
2. Aggregate immediately after the run.
3. Validate the scores contract.
4. Open a handful of raw result files and inspect them directly.

What to verify immediately:

- baseline and treatment responses are non-null
- Nia context is non-empty or at least behaving intentionally
- judge status is `ok` rather than `skipped`, `provider_error`, or `parse_error`
- aggregate summary fields are non-null for the completed slice
- the dashboard can read the resulting `scores.json`

If healthy:

- continue to Phase 2

If unhealthy:

- stop the expansion
- classify the problem as inference, retrieval, judge, aggregation, or dashboard
- fix that class of issue before scaling up

Exit condition:

- a real `5`-task live slice exists with believable outputs and valid aggregate data

Commands:

```bash
python3 -m harness.run_eval \
  --provider openai \
  --model gpt-4o-2024-11-20 \
  --judge-provider openai \
  --judge-model gpt-4o-2024-11-20 \
  --tasks dataset/tasks.json \
  --limit 5

python3 scripts/aggregate.py --input results/raw --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

Inspection:

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path
obj = json.loads(Path("results/scores.json").read_text())
print("summary:", obj["summary"])
print("judge_status_counts:", Counter(task["judge_status"] for task in obj["tasks"]))
PY

find results/raw -maxdepth 3 -type f | sort | tail -n 10
```

## Phase 2: Run The Full Pilot For The First Model

Goal: produce the first real benchmark result set for the full locked `30`-task pilot.

Checklist:

- [ ] Run the full pilot for the first model.
- [ ] Aggregate the resulting artifacts.
- [ ] Validate `results/scores.json`.
- [ ] Snapshot the overall and per-library metrics.

Order:

1. Run the full pilot on the first chosen model.
2. Aggregate immediately after the run finishes.
3. Validate `results/scores.json`.
4. Snapshot the resulting overall metrics and the per-library breakdown.

What to capture:

- total completed tasks
- count of judge failures or skipped rows
- count of retrieval failures or empty-context rows
- overall baseline score
- overall with-Nia score
- overall delta
- best and worst library deltas

Why this phase matters:

- this is the first point where NiaBench becomes a real benchmark rather than an infrastructure project

Exit condition:

- one full-model pilot run exists with real aggregate metrics and enough artifact quality to inspect deltas seriously

Commands:

```bash
python3 -m harness.run_eval \
  --provider openai \
  --model gpt-4o-2024-11-20 \
  --judge-provider openai \
  --judge-model gpt-4o-2024-11-20 \
  --tasks dataset/tasks.json

python3 scripts/aggregate.py --input results/raw --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

Snapshot:

```bash
python3 - <<'PY'
import json
from pathlib import Path
obj = json.loads(Path("results/scores.json").read_text())
print("summary:", obj["summary"])
for row in obj["libraries"][:10]:
    print(row["id"], row["without_nia"], row["with_nia"], row["delta_pct"])
PY
```

## Phase 3: Failure Triage And Targeted Reruns

Goal: make the first model’s results believable before adding more benchmark volume.

Checklist:

- [ ] Build a short list of invalid or suspicious artifacts.
- [ ] Classify each issue before rerunning anything.
- [ ] Rerun only task IDs that need reruns.
- [ ] Re-aggregate and confirm the latest artifacts are being used.

Order:

1. Review the first model’s raw task artifacts and aggregate output.
2. Build a short failure list grouped by root cause.
3. Separate issues into:
   - harness bug
   - retrieval issue
   - judge issue
   - provider failure
   - genuine model miss
4. Rerun only the tasks that need reruns.
5. Re-aggregate after reruns and confirm the aggregate now reflects the latest valid artifacts.

What counts as rerun-worthy:

- provider failures
- judge parse failures
- obvious retrieval failures
- tasks where baseline and treatment are both clearly missing or corrupt
- tasks where the artifact is incomplete enough that you cannot defend the result

What should not trigger reruns by default:

- genuine low-scoring tasks that still produced coherent outputs
- small deltas you simply do not like
- cases where the model appears to have genuinely failed despite context

Exit condition:

- the first model’s run is clean enough to stand behind
- the rerun list is exhausted or intentionally deferred

Commands:

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path
obj = json.loads(Path("results/scores.json").read_text())
print("judge_status_counts:", Counter(task["judge_status"] for task in obj["tasks"]))
print("tasks_with_missing_scores:")
for task in obj["tasks"]:
    if task["baseline_score"] is None or task["treatment_score"] is None:
        print(task["task_id"], task["judge_status"], task["source_file"])
PY
```

Targeted rerun template:

```bash
python3 -m harness.run_eval \
  --provider openai \
  --model gpt-4o-2024-11-20 \
  --judge-provider openai \
  --judge-model gpt-4o-2024-11-20 \
  --tasks dataset/tasks.json \
  --task-id <task-id>

python3 scripts/aggregate.py --input results/raw --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

## Phase 4: Run The Second Model

Goal: turn the benchmark into a credible founder-facing comparison surface instead of a one-model experiment.

Checklist:

- [ ] Decide whether Anthropic capacity is safe enough to use now.
- [ ] If yes, run the full pilot on the second model.
- [ ] Aggregate immediately after the run.
- [ ] Validate the combined score file.
- [ ] Confirm both models now appear in `summary.models_tested`.

Order:

1. Decide whether Anthropic throughput is safe enough to run now.
2. If yes, run the full pilot on the second pinned model.
3. Aggregate immediately after the run.
4. Validate the combined `results/scores.json`.
5. Check that both models now appear in `summary.models_tested`.

Risk management:

- if OpenClaw is still actively consuming Anthropic capacity, do not blindly start the Anthropic run
- if Anthropic remains constrained, finish every non-Anthropic founder-facing task today and leave only the second-model execution as the external bottleneck

Exit condition:

- both pinned models have pilot artifacts and the aggregate file reflects both, or
- one model is complete and the only remaining blocker is external Anthropic throughput

Commands:

```bash
python3 -m harness.run_eval \
  --provider anthropic \
  --model claude-sonnet-4-20250514 \
  --judge-provider anthropic \
  --judge-model claude-sonnet-4-20250514 \
  --tasks dataset/tasks.json

python3 scripts/aggregate.py --input results/raw --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

Verification:

```bash
python3 - <<'PY'
import json
from pathlib import Path
obj = json.loads(Path("results/scores.json").read_text())
print("models_tested:", obj["summary"]["models_tested"])
print("tasks_evaluated:", obj["summary"]["tasks_evaluated"])
PY
```

## Phase 5: Freeze Scoring And Interpret The Results

Goal: stop the benchmark from shifting under your feet once real numbers exist.

Checklist:

- [ ] Review judge-only composite semantics.
- [ ] Confirm how failed or skipped rows affect aggregate math.
- [ ] Confirm dedupe behavior is doing what you want.
- [ ] Confirm `tasks_evaluated` matches the story you want to tell.
- [ ] If changes are needed, make them now and stop changing semantics afterward.

Order:

1. Review the current judge-only composite semantics.
2. Confirm how missing or failed judge rows are represented in aggregate output.
3. Confirm how stale rows are deduped.
4. Confirm how `tasks_evaluated` is counted.
5. Decide whether the current semantics are what you want to explain publicly.
6. If any semantics need adjustment, make the adjustment now, rerun aggregation, and stop changing semantics afterward.

Important rule:

- do not keep changing scoring semantics after founder-facing charts or claims are drafted

Exit condition:

- the score definitions are stable enough to explain in docs and in conversation

Commands:

```bash
sed -n '1,220p' grading/composite.py
sed -n '1,260p' grading/judge.py
sed -n '1,280p' scripts/aggregate.py
sed -n '1,120p' results/scores.json
```

Quick semantic check:

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path
obj = json.loads(Path("results/scores.json").read_text())
print("summary:", obj["summary"])
print("judge_status_counts:", Counter(task["judge_status"] for task in obj["tasks"]))
print("non_null_task_count:", sum(task["delta_pct"] is not None for task in obj["tasks"]))
PY
```

## Phase 6: Polish Dashboard Against Real Data

Goal: make the benchmark look intentional and technically trustworthy once the numbers are live.

Checklist:

- [ ] Build the dashboard with the latest `results/scores.json`.
- [ ] Inspect the overview with real values.
- [ ] Fix any copy that still assumes pending-only data.
- [ ] Check desktop and mobile rendering.
- [ ] Confirm no UI text overclaims current capabilities.

Order:

1. Build the dashboard with the real aggregate file.
2. Inspect the overview with actual non-null metrics.
3. Fix any text that still assumes scores are pending.
4. Add or refine copy that explains judge-only mode if needed.
5. Check layout quality on desktop and mobile.
6. Confirm the visible claims match the current implementation truth.

Focus areas:

- clarity over decoration
- no wording that implies sandbox execution is already live
- no wording that implies the benchmark is larger than the actual current pilot

Exit condition:

- the dashboard looks coherent and defensible with real pilot data

Commands:

```bash
cd dashboard && npm run build
```

Review files:

```bash
sed -n '1,260p' dashboard/app/page.tsx
sed -n '1,220p' dashboard/app/methodology/page.tsx
sed -n '1,260p' results/scores.json
```

## Phase 7: Tighten Docs And Founder Narrative

Goal: make the repo and benchmark story easy to understand for the Nia founder.

Checklist:

- [ ] Update README to reflect real benchmark state after live runs.
- [ ] Update methodology if scoring or caveats changed.
- [ ] Update execution board with what was actually completed.
- [ ] Write a short founder-facing summary note.

Order:

1. Update README with the actual current benchmark state after live runs.
2. Update methodology with the current scoring mode and any important caveats.
3. Update the execution board to reflect what was actually completed today.
4. Write a short founder-facing narrative note covering:
   - what NiaBench measures
   - why the pilot dataset is meaningful
   - what the first real results show
   - what is implemented now
   - what is intentionally deferred

Good outputs to prepare:

- one-paragraph project summary
- one-paragraph methodology summary
- one-paragraph “current state and next step” summary

Exit condition:

- the docs and the spoken narrative match the actual repo truth

Review commands:

```bash
sed -n '1,200p' README.md
sed -n '1,220p' docs/METHODOLOGY.md
sed -n '1,220p' EXECUTION_BOARD.md
sed -n '1,260p' docs/CURRENT_SPRINT_PLAN.md
```

## Phase 8: CI And Release Confidence

Goal: end the day with more than just local success.

Checklist:

- [ ] Re-run the task validator.
- [ ] Re-run the scores validator.
- [ ] Re-run the dashboard build.
- [ ] Confirm CI reflects the current most important checks.
- [ ] Decide whether any additional reproducibility command should be captured.

Order:

1. Confirm the task validator still passes.
2. Confirm the scores validator still passes.
3. Confirm the dashboard build still passes.
4. Confirm CI reflects the most important current checks.
5. Decide whether any final script or command should be added to make reruns reproducible for others.

Exit condition:

- the repo has a credible verification path that supports the founder-facing story

Commands:

```bash
python3 scripts/validate_tasks.py dataset/tasks_smoke.json
python3 scripts/validate_tasks.py dataset/tasks.json
python3 scripts/validate_scores.py results/scores.json
python3 -m compileall harness grading scripts
cd dashboard && npm run build
```

CI review:

```bash
sed -n '1,220p' .github/workflows/ci.yml
sed -n '1,220p' .github/workflows/auto-update.yml
```

## Phase 9: Demo Prep And Final Packaging

Goal: be ready to present NiaBench immediately after the work is done.

Checklist:

- [ ] Pick one or two representative tasks.
- [ ] Pick one or two representative deltas.
- [ ] Prepare the short walkthrough order.
- [ ] Prepare the limitations section.
- [ ] Prepare the “what happens next” section.

Order:

1. Pick one or two representative pilot tasks.
2. Pick one or two representative benchmark deltas.
3. Prepare a short walkthrough:
   - dataset
   - harness
   - retrieval
   - judge-only scoring
   - aggregate dashboard
4. Prepare one honest limitations section:
   - sandbox deferred
   - judge-only scoring in current sprint slice
   - throughput constraints
5. Prepare one “what happens next” section.

Exit condition:

- you can walk the founder through the benchmark without improvising the technical story

Artifact gathering commands:

```bash
python3 - <<'PY'
import json
from pathlib import Path
obj = json.loads(Path("results/scores.json").read_text())
print("summary:", obj["summary"])
valid = [task for task in obj["tasks"] if task["delta_pct"] is not None]
valid = sorted(valid, key=lambda row: row["delta_pct"], reverse=True)
print("\\nTop deltas:")
for row in valid[:5]:
    print(row["task_id"], row["library"], row["delta_pct"])
print("\\nBottom deltas:")
for row in valid[-5:]:
    print(row["task_id"], row["library"], row["delta_pct"])
PY
```

## Full Completion Definition For Today

You can treat this document as fully completed today if all of the following are true:

- a real `5`-task live slice exists and looks healthy
- a full pilot run exists for at least one pinned model
- targeted reruns have been completed for clearly invalid artifacts
- `results/scores.json` contains real non-null benchmark metrics
- the dashboard renders real pilot results
- scoring semantics are frozen for the current sprint slice
- docs match the current implementation truth
- the founder demo flow is prepared

Best-case full completion:

- both pinned models are complete today

Acceptable near-full completion if Anthropic remains constrained:

- everything above is complete for one model
- the only remaining blocker is the second model’s live run due to external quota pressure

## Fastest Path To Full Completion Today

If you want the shortest practical route through the full plan, use this sequence:

1. Live `5`-task slice on OpenAI
2. Full `30`-task OpenAI pilot
3. Aggregate and validate
4. Triage and targeted reruns
5. Re-aggregate and freeze scoring semantics
6. Dashboard polish with real data
7. Docs and founder narrative
8. Anthropic full pilot if quotas allow
9. Final aggregate refresh and demo prep

## Bottom Line

The highest-value work right now is benchmark execution and packaging, not waiting for more OpenClaw output.

If OpenClaw finishes later, that output can still improve the dataset or expand the benchmark. But it is no longer required for the next serious milestone: generating real pilot results from the locked `30`-task benchmark and turning them into a founder-ready benchmark surface.
