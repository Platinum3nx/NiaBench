# NiaBench Execution Board

Status: Active  
Revised on: March 31, 2026 evening  
Engineering target: April 2-3, 2026

## Hard Gates

- [ ] Only count OpenClaw outputs that pass `python3 scripts/validate_tasks.py <file>`.
- [ ] The pilot is fixed at exactly `30 tasks`: all `20 libraries` represented, `10` libraries get a second task, and the set is balanced across `easy`, `medium`, and `hard`.
- [ ] The auto-update pipeline ships with the first usable benchmark build, not as an undefined follow-up.
- [ ] Before any large eval run, confirm the harness handles Nia rate limiting with logging, retries, and backoff.
- [ ] Do not wait idly for `dataset/tasks_raw.json`. Build harness, grading, dashboard, docs, and workflow scaffolding in parallel.
- [ ] If fewer than `30` valid high-signal tasks exist by `12pm ET` on Wednesday, April 1, 2026, assemble the fixed `30-task` pilot manually from the highest-signal libraries and keep the benchmark moving.

## Current Status

- [x] Repo scaffolding is in place.
- [ ] OpenClaw is running remotely in `tmux`, but Anthropic org limits observed on March 31, 2026 (`10,000` input TPM and `5` RPM) are forcing repeated backoff.
- [ ] Existing invalid partial task files were cleared; only validator-passing outputs count as progress.
- [ ] The fastest path is still parallel development: keep dataset generation running in the background while core benchmark components move forward.

## Phase 1: Foundation and Dataset Tooling

### Goal

Lock the repo structure, validation flow, and bulk task-generation workflow.

### Requirements

- [ ] Library list confirmed
- [ ] Repo structure stable
- [ ] API keys available for local development

### Codex Owns

- [ ] Maintain repo structure and module boundaries
- [ ] Keep `dataset/task.schema.json` aligned with the task format
- [ ] Keep `.env.example` current
- [ ] Maintain the OpenClaw task-generation brief
- [ ] Maintain task validation scripts

### You Own

- [ ] Provide or create `NIA_API_KEY`
- [ ] Provide or create `E2B_API_KEY`
- [ ] Provide or create `ANTHROPIC_API_KEY`
- [ ] Provide or create `OPENAI_API_KEY`
- [x] Start the OpenClaw run

### Done When

- [ ] Bulk task generation can run unattended
- [ ] Validator-passing task batches can be merged cleanly
- [ ] API and account blockers are known

## Phase 2: Core Harness and Grading

### Goal

Build the evaluation path end to end before the dataset is fully ready.

### Requirements

- [ ] API keys are available
- [x] Target models are decided: Claude uses `claude-sonnet-4-20250514`; GPT-4o uses `gpt-4o-2024-11-20`

### Codex Owns

- [ ] Build [`harness/run_eval.py`](/Users/arjunmalghan/NiaBench/harness/run_eval.py)
- [ ] Build [`harness/nia_client.py`](/Users/arjunmalghan/NiaBench/harness/nia_client.py) against Nia's direct `search` and `index` API
- [ ] Extract context chunks programmatically from Nia responses
- [ ] Inject retrieved context into the system prompt as a clearly labeled block
- [ ] Log the retrieved context chunks verbatim in the result file
- [ ] Log the full prompt sent in the result file
- [ ] Build the grading pipeline skeleton
- [ ] Build output schema and result directory structure
- [ ] Build dashboard shell and static data plumbing
- [ ] Draft and maintain README, methodology, and contributing docs
- [ ] Scaffold GitHub Actions and auto-update plumbing
- [ ] Keep the remote OpenClaw batch script validator-aware and retry-safe so bad partials are not mistaken for progress

### You Own

- [ ] Verify `.env` and API keys work
- [ ] Add required GitHub or deployment secrets if preview deployments are used
- [ ] Make final judgment calls on borderline tasks where benchmark quality is subjective
- [ ] Confirm model scope if there is any ambiguity

### Done When

- [ ] Harness can produce baseline and treatment outputs with deterministic prompts at `temperature=0`
- [ ] Grading pipeline skeleton is implemented
- [ ] Dashboard and docs skeletons exist
- [ ] A `5-task` smoke test runs end to end
- [ ] Execution errors are classified correctly
- [ ] Judge output is parsed reliably

## Phase 3: Pilot Dataset Lock

### Goal

Turn raw task generation into a stable, reviewed pilot dataset.

### Requirements

- [ ] Enough valid tasks exist to lock the pilot, whether from OpenClaw output, manual curation, or a hybrid of both

### Codex Owns

- [ ] Count validator-passing task parts and decide by `12pm ET` on Wednesday, April 1, 2026 whether to keep waiting or pivot fully to manual pilot assembly
- [ ] Normalize and clean pilot tasks
- [ ] Review raw tasks and cut weak items aggressively
- [ ] Validate and clean [`dataset/tasks.json`](/Users/arjunmalghan/NiaBench/dataset/tasks.json)
- [ ] Select the fixed `30-task` pilot
- [ ] Run a `5-task` smoke test
- [ ] If OpenClaw output is still not usable by the cutoff, assemble a manual `30-task` pilot from the highest-signal libraries

### You Own

- [ ] Make final calls on whether to cut weak tasks or libraries instead of forcing them through

### Done When

- [ ] The `30-task` pilot is locked
- [ ] Task quality is high enough to trust the results
- [ ] The benchmark can move from scaffolding into real evaluation runs

## Phase 4: Evaluation and Aggregation

### Goal

Run the strongest available dataset slice, stabilize failures, and aggregate results cleanly.

### Requirements

- [ ] Pilot is clean
- [ ] Dataset is strong enough to stand behind, even if it remains a curated pilot rather than the full stretch dataset
- [ ] Budgets are acceptable

### Codex Owns

- [ ] Kick off the full eval if the dataset is ready; otherwise run the fixed pilot and preserve a path to expand later
- [ ] Analyze pilot failures once the pilot run exists
- [ ] Separate harness bugs from weak tasks from genuine model failures
- [ ] Tighten retries and timeouts
- [ ] Fix sandbox install issues
- [ ] Freeze the scoring logic
- [ ] Run GPT-4o in parallel with Claude for whichever dataset slice is locked
- [ ] Perform selective reruns
- [ ] Aggregate scores
- [ ] Flag odd deltas that need manual review

### You Own

- [ ] Monitor quota or billing constraints
- [ ] Step in only if external limits block progress

### Done When

- [ ] Full-run or pilot outputs exist for both models
- [ ] Only targeted reruns remain
- [ ] Suspicious deltas are identified for review
- [ ] Aggregate score files are stable and reproducible

## Phase 5: Dashboard, Docs, and Automation

### Goal

Finish the benchmark surface area around the core runs.

### Requirements

- [ ] Final or near-final scores are available

### Codex Owns

- [ ] Finish dashboard pages
- [ ] Finish task drilldowns if they remain in scope
- [ ] Finish the methodology page
- [ ] Wire `scores.json`
- [ ] Draft or polish [`README.md`](/Users/arjunmalghan/NiaBench/README.md)
- [ ] Draft or polish [`CONTRIBUTING.md`](/Users/arjunmalghan/NiaBench/CONTRIBUTING.md)
- [ ] Implement the GitHub Actions auto-update workflow
- [ ] Implement release-detection logic
- [ ] Implement draft-task PR flow
- [ ] Set up licensing
- [ ] Set up deployment config if the dashboard is being deployed

### You Own

- [ ] Enable required secrets in GitHub and any deployment platform
- [ ] Approve scope cuts if drilldowns or automation need to be deferred

### Done When

- [ ] Dashboard renders the latest aggregate scores
- [ ] Docs explain how to run, validate, and extend the project
- [ ] Weekly auto-update workflow is implemented or explicitly deferred with a clear note

## Phase 6: Finish Pass

### Goal

Do final QA on the software itself.

### Codex Owns

- [ ] Final documentation pass
- [ ] Reproducibility check
- [ ] Configuration cleanup
- [ ] Result file sanity check
- [ ] CI and workflow sanity check

### You Own

- [ ] Review final task quality decisions
- [ ] Review any remaining deployment or secret-management steps

### Done When

- [ ] The repo is coherent and runnable
- [ ] The benchmark path is reproducible
- [ ] Development docs match the implementation

## Ownership Summary

### Codex Can Own

- [ ] Repo setup
- [ ] Dataset tooling
- [ ] Eval harness
- [ ] Direct Nia API integration
- [ ] Grading pipeline
- [ ] Dashboard
- [ ] Docs
- [ ] Auto-update workflow
- [ ] Reproducibility and integration cleanup

### You Own

- [ ] API keys
- [ ] Account setup
- [ ] Final quality calls on questionable tasks
- [ ] Deployment ownership where account access is required
