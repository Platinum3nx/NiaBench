# NiaBench Layer 2 Execution Spec

Status: Draft  
Audience: humans and autonomous coding agents  
Companion docs:

- `docs/SECOND_LAYER_DEVELOPMENT_PLAN.md`
- `README.md`
- `docs/METHODOLOGY.md`

Purpose: define the exact architecture, contracts, work order, and command gates for building Layer 2 without weakening Layer 1.

## Mission

Build a second benchmark layer that measures realistic coding-agent behavior while preserving Layer 1 as the clean retrieval-effect benchmark.

Layer 2 v1 should answer one question only:

- "Does the same coding agent perform better when it has the Nia retrieval tool than when it has no external retrieval tool?"

Layer 2 must be:

- additive, not substitutive
- auditable
- bounded
- reproducible
- launch-safe

Layer 2 must not:

- change Layer 1 behavior
- mutate Layer 1 result contracts
- reuse Layer 1 public score files
- blur the benchmark question by comparing different agent loops or prompt shapes

## Decision Defaults

These are the default decisions an implementation agent should make unless a later written spec overrides them.

- Stay in Python and mirror the current repo style.
- Prefer stdlib plus existing repo utilities over new dependencies.
- If a new behavior would require modifying a frozen Layer 1 file, create a parallel `agent_*` module instead.
- Keep temperature at `0` for Layer 2 v1.
- Keep the first live Layer 2 pilot to `12` tasks, `1` agent model, `2` conditions, and `2` repetitions per condition.
- Use an independent judge model for founder-facing reporting.
- Prefer exact relative file paths over glob patterns in task wrappers and output permissions.
- Prefer separate result fields over overloading Layer 1 field names.
- Prefer a separate Layer 2 dashboard page over modifying the Layer 1 homepage.

## Hard Invariants

These rules are non-negotiable.

| Rule | Why | Enforcement |
| --- | --- | --- |
| Layer 1 remains the canonical retrieval benchmark. | This is the current strongest claim in the repo. | Do not change Layer 1 methodology copy, dashboard homepage, or score contract. |
| Layer 2 must use separate commands, paths, and public result files. | Prevents accidental schema and reporting drift. | Use `run_agent_eval.py`, `results/agent_raw/`, `results/agent_scores.json`, and a separate dashboard page. |
| Layer 2 must not extend `BaseLLMClient.generate()` for tool use. | Layer 1 eval and judge code both depend on the text-only client hierarchy. | Build `harness/agent_llm_clients.py` instead. |
| Layer 2 must not reuse Layer 1 answer-bearing retrieval helpers. | `correct_pattern` leakage is already a known Layer 1 issue. | Do not call `build_nia_query()` from Layer 2. |
| Agent conditions must share one prompt template and one loop contract. | Prevents hidden prompt confounds. | Generate both conditions from the same prompt builder and condition registry. |
| Layer 2 scoring must use its own judge prompt and result schema. | Agent outputs are multi-step and artifact-based, not baseline-vs-treatment text pairs. | Build `grading/agent_judge.py` and `grading/agent_types.py`. |
| Layer 2 must not publish self-judged founder-facing scores. | Self-judging bias is higher in agent runs. | Require a distinct judge model before public reporting. |

## Frozen Layer 1 Contract Surfaces

These files are frozen for Layer 2 work unless they are explicitly versioned in parallel. An autonomous implementation agent should treat touching these files as a last resort and stop to justify the change before proceeding.

- `harness/run_eval.py`
- `harness/config.py`
- `harness/llm_clients.py`
- `harness/types.py`
- `harness/prompts.py`
- `harness/nia_client.py`
- `harness/retry.py`
- `grading/judge.py`
- `grading/composite.py`
- `grading/types.py`
- `scripts/aggregate.py`
- `scripts/validate_scores.py`
- `dashboard/lib/load-scores.ts`
- `dashboard/lib/types.ts`
- `dashboard/app/page.tsx`

## Recommended Automated Enforcement

The protections above should be enforced in CI, not left as documentation alone.

Recommended new enforcement script:

- `scripts/check_layer2_boundaries.py`

Recommended responsibilities for that script:

1. Frozen-surface diff check
   - fail if a Layer 2 scoped branch or PR changes any frozen Layer 1 contract surface
   - default comparison target should be the merge base with `main`
   - allow override only through an explicit exception mechanism such as a checked-in allowlist file or a CLI flag used intentionally in non-Layer-2 work

2. Forbidden import and symbol check
   - scan Layer 2 modules and fail if they import or reference:
     - `harness.llm_clients.BaseLLMClient`
     - `harness.prompts.build_nia_query`
     - `grading.judge.JudgeGrader`
     - `grading.composite.CompositeGrader`
     - `dashboard/lib/load-scores.ts`
     - `dashboard/lib/types.ts`
   - allow imports from:
     - `harness.retry`
     - shared non-contract utility modules only when they do not alter Layer 1 behavior

3. Output-path contract check
   - fail if Layer 2 modules write to:
     - `results/raw/`
     - `results/scores.json`
   - fail if Layer 2 dashboard code loads:
     - `results/scores.json`

4. Dashboard-boundary check
   - fail if Layer 2 work modifies:
     - `dashboard/app/page.tsx`
     - `dashboard/lib/load-scores.ts`
     - `dashboard/lib/types.ts`
   - unless an explicit exception file documents why the Layer 1 page or contract must change

5. Model/judge safety check
   - fail Layer 2 founder-facing aggregation if the curated agent model and judge model are identical

Recommended CI additions:

- keep the current Layer 1 checks in `.github/workflows/ci.yml`
- add a Layer 2 boundary job or step that runs:

```bash
python3 scripts/check_layer2_boundaries.py
```

- once Layer 2 implementation exists, extend CI with:

```bash
python3 scripts/validate_agent_tasks.py dataset/tasks_layer2_smoke.json
python3 -m harness.run_agent_eval --provider <provider> --model <model> --tasks dataset/tasks_layer2_smoke.json --condition all --dry-run
python3 scripts/validate_agent_scores.py results/agent_scores.json
```

Recommended philosophy:

- Layer 1 regression protection should fail fast
- import-boundary violations should fail fast
- founder-facing publication should require both Layer 1 and Layer 2 validation paths to pass

## Canonical Layer 2 v1 Scope

### Fixed benchmark question

- compare `no_retrieval_agent` vs `nia_agent`
- same model
- same task wrapper
- same budgets
- same local tools
- same prompt template
- only difference: `nia_agent` has access to the Nia retrieval tool

### Fixed pilot size

- `12` locked tasks
- `1` pinned agent model
- `2` conditions
- `2` repetitions per condition
- `48` total runs

### Fixed model-pair rule

- freeze one agent model id before the first live pilot run
- freeze one distinct judge model id before the first live pilot run
- use pinned snapshot ids only, not moving aliases
- founder-facing Layer 2 reporting may not use the same provider-model pair for both agent and judge
- recommended default pairing:
  - if the agent model is `claude-sonnet-4-20250514`, use `gpt-4o-2024-11-20` as judge
  - if the agent model is `gpt-4o-2024-11-20`, use `claude-sonnet-4-20250514` as judge

### Fixed budget defaults

- max assistant turns per run: `12`
- max wall-clock time per run: `600` seconds
- max completion tokens per turn: `2048`
- max total generated tokens per run: `25000`
- run-level repetitions: `2`
- temperature: `0`

### Fixed condition definitions

`no_retrieval_agent`

- gets workspace tools only
- gets no external retrieval tool
- gets no web search
- gets no package-install path

`nia_agent`

- identical to `no_retrieval_agent`
- plus one structured Nia retrieval tool

### Fixed v1 non-goals

- no `context7_agent`
- no `generic_retrieval_agent`
- no unrestricted shell
- no package installation during runs
- no mutation of Layer 1 task schema
- no blended Layer 1 + Layer 2 leaderboard
- no founder-facing result publication before the `12 x 2 x 2` pilot is complete and curated

## Repository Additions

Layer 2 should land as a parallel vertical slice.

```text
dataset/
  agent_task.schema.json
  tasks_layer2_smoke.json
  tasks_layer2_pilot.json
  agent_seeds/
    <task-id>/
      ...
harness/
  run_agent_eval.py
  agent_runner.py
  agent_conditions.py
  agent_llm_clients.py
  agent_prompts.py
  agent_tools.py
  agent_workspace.py
  agent_types.py
grading/
  agent_judge.py
  agent_failure_taxonomy.py
  agent_types.py
scripts/
  validate_agent_tasks.py
  check_layer2_boundaries.py
  curate_agent_runs.py
  aggregate_agent.py
  validate_agent_scores.py
results/
  agent_raw/
  agent_raw_curated/
    combined/
  agent_scores.json
dashboard/
  app/
    agent/
      page.tsx
  lib/
    load-agent-scores.ts
    agent-types.ts
docs/
  SECOND_LAYER_EXECUTION_SPEC.md
```

## Canonical Contracts

### 1. Agent task wrapper contract

Layer 2 tasks should wrap Layer 1 tasks rather than mutate them.

Suggested dataclass shape:

```python
@dataclass(frozen=True)
class AgentTask:
    id: str
    source_task_id: str
    library: str
    version_introduced: str
    category: str
    difficulty: str
    agent_goal: str
    workspace_seed: WorkspaceSeed
    expected_artifacts: list[ArtifactSpec]
    allowed_output_paths: list[str]
    retrieval_hints: list[str]
    test_command: TestCommand | None = None
    success_notes: str | None = None
```

Required field semantics:

- `id`
  - unique Layer 2 task id
  - may match `source_task_id` if one-to-one
- `source_task_id`
  - the Layer 1 task this wrapper came from
  - lets grading pull Layer 1 rubric context without rewriting the source dataset
- `agent_goal`
  - the agent-facing goal statement
  - written as a realistic task, not as direct code completion prose
- `workspace_seed`
  - object pointing to a seed directory under `dataset/agent_seeds/<task-id>/`
  - v1 should use seed directories, not huge inline code blobs in JSON
- `expected_artifacts`
  - exact files grading should inspect
  - must be a subset of `allowed_output_paths`
- `allowed_output_paths`
  - exact relative file paths only in v1
  - no glob patterns
- `retrieval_hints`
  - optional non-answer-bearing hints
  - may be visible to the agent only if they do not encode the solution
- `test_command`
  - optional predefined command the agent may execute through a constrained tool
- `success_notes`
  - harness/judge-only metadata
  - never shown to the benchmarked agent

Agent-visible fields:

- `agent_goal`
- `library`
- `version_introduced`
- `allowed_output_paths`
- tool availability

Agent-hidden fields:

- Layer 1 `correct_pattern`
- Layer 1 `deprecated_pattern`
- Layer 1 `reference_solution`
- Layer 1 `why_models_fail_this`
- rubric text
- `success_notes`

Recommended artifact spec:

```python
@dataclass(frozen=True)
class ArtifactSpec:
    path: str
    kind: str  # code_file | config_file | text_file | json_file
    required: bool = True
    max_bytes: int | None = None
```

Recommended test command spec:

```python
@dataclass(frozen=True)
class TestCommand:
    argv: list[str]
    cwd: str = "."
    timeout_seconds: int = 30
```

### 2. Prompt contract

Layer 2 must use one prompt template for both conditions.

Prompt inputs:

- fixed system instructions
- task goal
- workspace rules
- allowed output paths
- tool list generated from the active condition
- completion contract

Prompt rules:

- never hand-write a special "Nia is powerful" suffix for `nia_agent`
- the only prompt difference between conditions should be the rendered tool inventory
- require the agent to inspect workspace state before editing
- require the agent to stay within `allowed_output_paths`
- instruct the agent to run the predefined task command before finishing when one exists
- request a structured final response

Structured final response contract:

```json
{
  "status": "completed",
  "summary": "short explanation of what changed",
  "artifact_paths": ["relative/path.py"]
}
```

This final JSON is helpful but not required for scoring. If it fails to parse, artifact extraction still drives evaluation.

### 3. Tool contract

Layer 2 v1 tool surface should be minimal and explicit.

| Tool | Conditions | Purpose | Notes |
| --- | --- | --- | --- |
| `list_files(path=".")` | both | enumerate workspace files | path must stay within workspace root |
| `read_file(path)` | both | inspect a workspace file | return text plus truncation metadata |
| `search_workspace(pattern, path=".")` | both | text search inside workspace | local only; no external retrieval |
| `write_file(path, content)` | both | create or overwrite an allowed output file | exact-path enforcement only |
| `run_task_command()` | both when defined | run one predefined validation command | no arbitrary shell arguments |
| `nia_search_docs(query, library, version, top_k)` | `nia_agent` only | retrieve current documentation chunks | returns chunks directly; v1 does not need a second read tool |

Tool rules:

- all tool paths are relative to isolated workspace root
- path traversal must be rejected
- `write_file()` must reject paths not listed in `allowed_output_paths`
- `run_task_command()` must reject execution when the task has no command
- `search_workspace()` must only inspect local workspace files
- `nia_search_docs()` must log raw arguments, returned chunks, timestamps, and provider metadata

Recommended Nia tool output:

```json
{
  "query": "anthropic messages endpoint role content",
  "library": "anthropic-sdk",
  "version": "2024",
  "results": [
    {
      "title": "Messages API",
      "url": "https://...",
      "source": "docs",
      "text": "..."
    }
  ]
}
```

### 4. Agent client contract

Layer 2 needs a separate normalized client layer for tool-use turns.

Recommended interface:

```python
class BaseAgentLLMClient:
    def run_turn(
        self,
        *,
        model: str,
        system_prompt: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
        temperature: float,
        max_tokens: int,
    ) -> AgentTurnResult:
        ...
```

Normalized turn result:

```python
@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, object]

@dataclass(frozen=True)
class AgentTurnResult:
    text: str
    tool_calls: list[ToolCallRequest]
    stop_reason: str
    request_id: str | None
    tokens_in: int | None
    tokens_out: int | None
    raw_response: dict[str, object]
```

Implementation rules:

- OpenAI and Anthropic normalization happens here, not in the runner
- provider-specific stop reasons must be normalized into this closed set:
  - `completed`
  - `tool_calls`
  - `max_tokens_truncated`
  - `unexpected`
- this client layer may reuse `harness.retry.post_json_with_retry()`
- this client layer must not modify `BaseLLMClient.generate()`
- transient HTTP retries stay inside the client layer
- no semantic retries here; only transport-level retry logic

### 5. Agent loop contract

One run means:

- one isolated workspace
- one condition
- one task wrapper
- one agent session
- one bounded multi-turn loop
- one terminal status

Definition of a step:

- one assistant turn equals one step
- multiple tool calls emitted in that assistant turn still count as one step

Recommended loop pseudocode:

```python
initialize workspace
load condition tool registry
build system prompt and initial user message
messages = [system, user]

while not terminal:
    enforce wall-clock and token budgets
    turn = agent_client.run_turn(...)
    log turn
    if turn.tool_calls:
        execute tool calls in emitted order
        append tool results to messages
        step_count += 1
        continue
    if turn.stop_reason == "max_tokens_truncated":
        final_response_text = turn.text
        terminal_status = "max_tokens_truncated"
        terminal = True
        step_count += 1
        continue
    if turn.stop_reason == "unexpected":
        final_response_text = turn.text
        terminal_status = "unexpected_stop_reason"
        terminal = True
        step_count += 1
        continue
    if turn.stop_reason != "completed":
        final_response_text = turn.text
        terminal_status = "unexpected_stop_reason"
        terminal = True
        step_count += 1
        continue
    final_response_text = turn.text
    terminal_status = "ok"
    terminal = True
    step_count += 1

extract expected artifacts
run task command result is already captured if used
derive terminal status
grade if possible
write run artifact
```

Termination statuses:

- `ok`
- `max_steps_exhausted`
- `timeout`
- `provider_error`
- `max_tokens_truncated`
- `unexpected_stop_reason`
- `workspace_tool_error`
- `retrieval_error`
- `no_artifacts`
- `judge_error`
- `runner_exception`
- `dry_run`

Retry semantics:

- repetitions are not retries
- HTTP retries happen inside client/tool wrappers only
- runner-level replay is disallowed after a tool side effect
- if a provider call fails before any tool side effect in that turn, one turn-level retry is allowed
- if that retry fails, terminate the run with the appropriate operational status

### 6. Workspace contract

Workspace rules:

- every run gets its own isolated working directory
- seed files are copied from the task's `workspace_seed.seed_dir`
- both the seeded workspace and the final workspace snapshot are preserved
- editable files are limited to `allowed_output_paths`
- a run may read any file in the seeded workspace
- a run may only modify or create files in `allowed_output_paths`

Recommended artifact layout:

```text
results/agent_raw/<provider-model>/<run-id>/<condition>/<task-id>/rep-00/
  run.json
  prompt_system.txt
  prompt_initial_user.txt
  workspace_seed/
  workspace_final/
```

`run.json` should be the canonical machine-readable artifact. Text prompt files and workspace snapshots are supporting evidence.

### 7. Run artifact contract

Recommended top-level run artifact shape:

```json
{
  "schema_version": "nia.layer2.run.v1",
  "run_id": "openai-gpt-4o-...-20260402T...",
  "task_id": "anthropic-sdk-completions-to-messages",
  "source_task_id": "anthropic-sdk-completions-to-messages",
  "condition": "nia_agent",
  "repetition_index": 0,
  "model_provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "judge_provider": "openai",
  "judge_model": "gpt-4o-2024-11-20",
  "timestamp": "2026-04-02T...",
  "status": "ok",
  "budgets": {...},
  "timings_ms": {...},
  "prompt": {...},
  "steps": [...],
  "tool_calls": [...],
  "final_response_text": "...",
  "final_response_parse_error": null,
  "artifacts": {...},
  "task_command": {...},
  "judge_result": {...},
  "scores": {...},
  "failure": {...}
}
```

Required sub-objects:

- `budgets`
  - step limit, timeout, token limits
- `timings_ms`
  - wall-clock duration and per-provider timings when available
- `prompt`
  - rendered system prompt
  - rendered initial user prompt
  - list of available tools
- `steps`
  - normalized transcript by assistant turn
- `tool_calls`
  - flat list of every tool invocation with arguments and outputs
- `artifacts`
  - expected artifact manifest
  - found artifacts
  - missing artifacts
  - extracted text passed to judge
- `task_command`
  - whether command existed, whether it was run, exit code, stdout, stderr
- `scores`
  - quality score percent
  - crash-aware score percent
  - pass boolean
- `failure`
  - operational failure class and detail if non-`ok`

### 8. Retrieval safety contract

Layer 2 must not inherit answer leakage from Layer 1.

Never pass these fields into the agent prompt or harness-generated Nia queries:

- `correct_pattern`
- `reference_solution`
- rubric score descriptions
- `why_models_fail_this`
- common hallucination hints

Allowed harness-provided retrieval context:

- `library`
- `version_introduced`
- `category`
- `agent_goal`
- safe `retrieval_hints`

Important note:

- if the agent itself chooses to include solution-like words in its own Nia query, that is agent behavior, not benchmark leakage
- the benchmark's job is to avoid injecting hidden answer-bearing query terms on the agent's behalf

### 9. Judge contract

Layer 2 judge input should be artifact-based, not baseline-vs-treatment text comparison.

Judge inputs:

- source Layer 1 task metadata
- Layer 2 `agent_goal`
- extracted artifact texts
- task command result if present
- reference solution
- category rubric
- operational status

Judge output contract:

```json
{
  "score": 0,
  "rationale": "brief explanation",
  "quality_failures": ["wrong_import_path"],
  "artifact_findings": [
    {"path": "request.py", "status": "incorrect"}
  ],
  "confidence": "medium"
}
```

Rules:

- `score` must be `0`, `1`, or `2`
- `pass` is derived as `score == 2`
- `confidence` is required and must be one of `low`, `medium`, or `high`
- `confidence` is informational only in v1 and does not mechanically change the score
- any curated founder-facing run with judge confidence `low` must be flagged for manual review before publication
- `quality_failures` values must come from the fixed Layer 2 quality taxonomy
- `score` is a holistic judge assessment across all supplied evidence
- `artifact_findings` are supporting evidence for the rationale, not a mechanical scoring formula
- judge errors must be surfaced separately from agent failures

### 10. Aggregate contract

Layer 2 aggregation must distinguish run-level operational rates from task-level quality averages.

Aggregation rules:

1. Validate run artifacts first.
2. Group by `task_id + condition`.
3. Average repetitions within each task-condition pair.
4. Compute condition-level scores as macro-averages across tasks.
5. Report run-level rates separately.

Explicit delta definitions:

- `delta_completed_only_pct = task_macro_completed_only_avg_quality_pct(nia_agent) - task_macro_completed_only_avg_quality_pct(no_retrieval_agent)`
- `delta_crash_aware_pct = task_macro_crash_aware_avg_quality_pct(nia_agent) - task_macro_crash_aware_avg_quality_pct(no_retrieval_agent)`
- task-row deltas should use the same order:
  - task score under `nia_agent`
  - minus the same task score under `no_retrieval_agent`

Primary published summary metrics:

- `task_macro_completed_only_avg_quality_pct`
- `task_macro_crash_aware_avg_quality_pct`
- `delta_completed_only_pct` between `nia_agent` and `no_retrieval_agent`
- `delta_crash_aware_pct`
- `run_level_completion_rate`
- `run_level_crash_rate`
- `run_level_timeout_rate`
- `run_level_no_artifact_rate`
- `run_level_judge_error_rate`
- `nia_usage_rate`
- `avg_nia_calls_per_nia_run`
- `unique_tasks`
- `total_runs`

Recommended aggregate file shape:

```json
{
  "generated_at": "2026-04-02T...",
  "schema_version": "nia.layer2.aggregate.v1",
  "summary": {...},
  "conditions": [...],
  "tasks": [...]
}
```

Condition rows should include:

- condition id
- run counts
- task counts
- task-macro completed-only quality
- task-macro crash-aware quality
- completion rate
- crash rate
- timeout rate
- no-artifact rate
- judge-error rate
- average tool calls
- average Nia calls
- Nia usage rate

Task rows should include:

- `task_id`
- `library`
- `difficulty`
- per-condition repetition counts
- per-condition completed-only quality
- per-condition crash-aware quality
- per-condition completion rate
- per-condition min / max / stddev when available
- deltas between conditions

## Phase-by-Phase Execution Plan

Work must happen in order. Do not skip forward if a phase's acceptance gates are not met.

### Phase 0: Freeze and Protect Layer 1

Goal:

- make Layer 2 implementation physically unable to drift into Layer 1 contracts by accident

Work:

- confirm the frozen Layer 1 surface list in this spec and in `docs/SECOND_LAYER_DEVELOPMENT_PLAN.md`
- keep `results/scores.json` as the Layer 1 public score file
- keep the Layer 1 homepage as the canonical Layer 1 dashboard
- implement `scripts/check_layer2_boundaries.py` before substantial Layer 2 coding begins
- wire `scripts/check_layer2_boundaries.py` into CI before the first Layer 2 implementation PR is treated as launch-track work
- create a small written checklist for Layer 1 regression gates:
  - `python3 scripts/validate_scores.py results/scores.json`
  - `cd dashboard && npm run build`
- do not start agent-runner coding until the new Layer 2 file tree is chosen

Files allowed in this phase:

- docs only

Definition of done:

- the Layer 2 work order is documented before implementation starts
- the boundary checker exists and passes on the current repo state
- no Layer 1 command, result file, or dashboard path has changed

### Phase 1: Define Layer 2 Schemas and Types

Goal:

- remove ambiguity before code is written

Files to create:

- `dataset/agent_task.schema.json`
- `dataset/tasks_layer2_smoke.json`
- `harness/agent_types.py`
- `grading/agent_types.py`
- `scripts/validate_agent_tasks.py`

Work:

- write the Layer 2 task wrapper JSON schema
- encode the dataclasses for:
  - task wrapper
  - artifact spec
  - test command
  - tool call records
  - turn results
  - run artifact
  - aggregate rows
- build a validator script for Layer 2 task files
- create a `2-3` task smoke fixture with tiny seed workspaces

Important implementation choices:

- task wrappers point to seed directories, not inline code blobs
- `allowed_output_paths` are exact relative paths only
- `expected_artifacts` are exact relative paths only
- task ids remain stable across repetitions and conditions

Command gates:

```bash
python3 scripts/validate_agent_tasks.py dataset/tasks_layer2_smoke.json
```

Definition of done:

- task schema validates
- smoke fixture validates
- dataclasses exist for all core Layer 2 artifacts

### Phase 2: Build Workspace Isolation and Local Tools

Goal:

- create a deterministic local execution surface before adding live model calls

Files to create:

- `harness/agent_workspace.py`
- `harness/agent_tools.py`

Work:

- implement isolated workspace creation from `workspace_seed.seed_dir`
- preserve seeded and final workspace snapshots
- implement:
  - `list_files`
  - `read_file`
  - `search_workspace`
  - `write_file`
  - `run_task_command`
- enforce path rules
- enforce exact-path output permissions
- capture structured logs for every tool call

Important implementation choices:

- `search_workspace` should use `rg` if available and a safe fallback otherwise
- `read_file` should return truncation metadata rather than silently clipping
- `write_file` should reject writes outside `allowed_output_paths`
- `run_task_command` must execute a predeclared argv list, not a free-form shell string

Command gates:

- add a small local dry-run harness or scriptable smoke check that exercises each tool against the smoke fixtures

Definition of done:

- workspace seeding works
- tool permissions are enforced
- final workspace snapshot is preserved after a run

### Phase 3: Build the Separate Agent Client Layer

Goal:

- support tool-use turns without touching Layer 1 text-only clients

Files to create:

- `harness/agent_llm_clients.py`

Work:

- implement a normalized `BaseAgentLLMClient`
- implement provider-specific clients for OpenAI and Anthropic tool-use turns
- normalize provider outputs into `AgentTurnResult`
- reuse `harness.retry.post_json_with_retry()` internally where helpful
- keep transport retries inside this layer

Important implementation choices:

- do not import or subclass `BaseLLMClient`
- do not change `harness/llm_clients.py`
- expose only the normalized interface to the runner

Command gates:

- add a dry-run or mocked turn path that proves the client normalization contract works without the full runner

Definition of done:

- the runner can depend only on normalized `AgentTurnResult`
- Layer 1 client hierarchy remains unchanged

### Phase 4: Build Conditions, Prompt Builder, and Nia Tool

Goal:

- make the two benchmark conditions explicit and mechanically comparable

Files to create:

- `harness/agent_conditions.py`
- `harness/agent_prompts.py`

Files to extend:

- `harness/agent_tools.py`

Work:

- define a condition object for `no_retrieval_agent`
- define a condition object for `nia_agent`
- render one prompt template from the active tool list
- add `nia_search_docs()` as a structured tool in `harness/agent_tools.py`
- ensure Nia tool logging captures arguments, timestamps, returned chunks, and metadata

Important implementation choices:

- do not use prompt-only retrieval injection for Layer 2
- do not create condition-specific persuasive wording
- the prompt builder should render the tool inventory from a registry

Command gates:

- verify that both conditions render the same prompt structure except for tool availability
- verify that Nia tool calls are impossible in `no_retrieval_agent`

Definition of done:

- both conditions are encoded as separate but comparable configurations
- Nia exists as a real callable tool rather than injected context

### Phase 5: Build the Agent Runner and CLI

Goal:

- run one complete Layer 2 benchmark attempt and always write a structured artifact

Files to create:

- `harness/agent_runner.py`
- `harness/run_agent_eval.py`

Work:

- implement the bounded turn loop
- enforce step, timeout, and token budgets
- execute tool calls in emitted order
- capture every assistant turn and tool result
- extract artifacts from the workspace at the end
- emit a canonical `run.json` plus prompt files and workspace snapshots
- add CLI flags analogous to Layer 1 where appropriate

Recommended CLI:

```text
python3 -m harness.run_agent_eval \
  --tasks dataset/tasks_layer2_pilot.json \
  --provider anthropic \
  --model claude-sonnet-4-20250514 \
  --judge-provider openai \
  --judge-model gpt-4o-2024-11-20 \
  --condition all \
  --repetitions 2 \
  --temperature 0 \
  --max-steps 12 \
  --timeout-seconds 600 \
  --dry-run
```

Required flags / behaviors:

- `--tasks`
- `--provider`
- `--model`
- `--judge-provider`
- `--judge-model`
- `--condition`
- `--repetitions`
- `--repetition-index`
- `--task-id`
- `--library`
- `--limit`
- `--run-id`
- `--dry-run`
- `--skip-judge`

Dry-run semantics:

- create workspace
- render prompts
- write a structured `run.json`
- do not call providers or Nia
- mark status as `dry_run`

Definition of done:

- one dry-run invocation produces stable Layer 2 artifacts
- one live single-task run can complete in each condition
- every terminal path writes `run.json`

### Phase 6: Build Layer 2 Grading and Failure Taxonomy

Goal:

- grade agent outputs honestly without mutating Layer 1 grading

Files to create:

- `grading/agent_judge.py`
- `grading/agent_failure_taxonomy.py`

Work:

- define the Layer 2 quality failure taxonomy
- define the Layer 2 operational failure taxonomy
- implement artifact extraction for judge input
- implement the Layer 2 judge prompt
- parse strict JSON judge output
- derive:
  - `quality_score_pct`
  - `pass`
  - `crash_aware_score_pct`
- keep judge failures separate from agent failures

Quality failure taxonomy:

- `outdated_api`
- `wrong_import_path`
- `wrong_parameter_or_signature`
- `invented_method_or_object`
- `mixed_version_answer`
- `artifact_missing_required_change`

Operational failure taxonomy:

- `timeout`
- `provider_error`
- `max_tokens_truncated`
- `unexpected_stop_reason`
- `retrieval_error`
- `workspace_tool_error`
- `runner_exception`
- `no_artifacts`
- `judge_error`

Scoring rules:

- `quality_score_pct = (score / 2) * 100`
- `pass = score == 2`
- `crash_aware_score_pct = 0` for terminal operational failures that prevent grading
- judge failures produce `judge_error` and should block founder-facing publication if non-zero

Definition of done:

- Layer 2 can distinguish "bad code" from "agent did not finish"
- judge output is machine-validated and separate from operational status

### Phase 7: Build the Locked Pilot Dataset

Goal:

- create a representative but tractable Layer 2 task set

Files to create:

- `dataset/tasks_layer2_pilot.json`
- `dataset/agent_seeds/<task-id>/...`

Selection rules:

- exactly `12` tasks
- minimum `8` libraries
- target `4 easy`, `4 medium`, `4 hard`
- no more than `2` tasks from one library
- every task must have:
  - a seed workspace
  - at least one expected artifact
  - an exact allowed output path list
- prefer tasks from Layer 1 where stale knowledge is likely to matter
- avoid tasks that require package installation or network access
- prefer tasks whose expected output fits in `1-3` files

Task-shaping rules:

- if the Layer 1 prompt already maps cleanly to an agent workflow, reuse the same source task id
- otherwise write a Layer 2-specific `agent_goal`
- keep source Layer 1 tasks unmodified

Command gates:

```bash
python3 scripts/validate_agent_tasks.py dataset/tasks_layer2_pilot.json
python3 scripts/validate_agent_tasks.py dataset/tasks_layer2_smoke.json
```

Definition of done:

- smoke and pilot task files validate
- every pilot task has a seed workspace on disk

### Phase 8: Build Aggregation, Validation, and Curation

Goal:

- turn many run artifacts into a trusted public Layer 2 summary

Files to create:

- `scripts/curate_agent_runs.py`
- `scripts/aggregate_agent.py`
- `scripts/validate_agent_scores.py`

Work:

- validate raw run artifacts before aggregation
- build a curation step that copies or selects launch-safe runs into `results/agent_raw_curated/combined/`
- aggregate from curated input, not from the entire exploratory raw tree
- output `results/agent_scores.json`
- validate the aggregate contract

Curation rules:

- include only the locked pilot task ids
- include only the frozen agent model id
- include only the frozen judge model id
- include only `no_retrieval_agent` and `nia_agent`
- include only runs with the expected schema version
- include both repetitions for every task-condition pair before founder-facing publication
- define the curation cell key as:
  - `task_id`
  - `condition`
  - `repetition_index`
  - `model_provider`
  - `model`
  - `judge_provider`
  - `judge_model`
- treat a cell as complete when at least one valid run artifact exists for that exact key
- if multiple artifacts exist for the same cell, curation must select the latest by timestamp and break ties by `run_id`
- founder-facing publication is blocked only when a required cell has no valid artifact
- a cell with a curated operational failure artifact still counts as present and should contribute to crash-aware metrics

Command gates:

```bash
python3 scripts/curate_agent_runs.py --input results/agent_raw --output results/agent_raw_curated/combined
python3 scripts/aggregate_agent.py --input results/agent_raw_curated/combined --output results/agent_scores.json
python3 scripts/validate_agent_scores.py results/agent_scores.json
```

Definition of done:

- Layer 2 has a curated public input path
- the aggregate validates from curated input only

### Phase 9: Build Dashboard Support

Goal:

- make Layer 2 understandable without touching Layer 1's story

Files to create:

- `dashboard/lib/load-agent-scores.ts`
- `dashboard/lib/agent-types.ts`
- `dashboard/app/agent/page.tsx`

Work:

- load `results/agent_scores.json`
- render a separate Layer 2 page
- explain the benchmark question in plain language
- show:
  - completed-only delta
  - crash-aware delta
  - completion rate by condition
  - crash rate by condition
  - Nia usage rate
  - per-library and per-task summaries
- keep the Layer 1 homepage unchanged

Dashboard rules:

- no blended Layer 1 + Layer 2 score
- no homepage takeover
- no reuse of `dashboard/lib/load-scores.ts`
- no widening of `dashboard/lib/types.ts`

Command gates:

```bash
cd dashboard && npm run build
```

Definition of done:

- dashboard build passes
- Layer 1 homepage still renders Layer 1 only
- Layer 2 has its own route and data loader

### Phase 10: Pilot Execution and Stabilization

Goal:

- run Layer 2 in increasing confidence tiers instead of jumping straight to the full pilot

Execution order:

1. dry-run smoke tasks
2. live single smoke task in `no_retrieval_agent`
3. live single smoke task in `nia_agent`
4. inspect one run artifact from each condition manually
5. run `2-4` pilot tasks end to end
6. inspect aggregation output
7. run full `12 x 2 x 2` pilot
8. curate, aggregate, validate, and build dashboard

Stabilization checks:

- no path-permission bugs in workspace tools
- no schema drift between runs
- no judge parse errors in founder-facing artifact set
- condition prompt shape remains identical except tool availability
- Nia usage logs look credible

Targeted rerun policy:

- targeted reruns are allowed for missing cells and transient operational failures
- recommended rerun triggers:
  - `provider_error`
  - `timeout`
  - `retrieval_error`
  - `judge_error`
  - `runner_exception`
  - missing `run.json`
- low quality score alone is not a rerun trigger in v1
- targeted reruns must preserve the same cell key and use a new `run_id`
- use `--task-id`, `--condition`, and `--repetition-index` for targeted reruns
- after a targeted rerun, curation selects the latest artifact for that cell key
- do not block forever on a cell once a valid terminal artifact exists; block only on missing cells

Definition of done:

- `48` curated runs exist for the locked pilot
- `results/agent_scores.json` validates
- dashboard build passes

### Phase 11: Expansion Gates

Goal:

- prevent premature scope creep

Do not expand beyond Layer 2 v1 until all of these are true:

- Layer 1 remains unchanged
- the full `12 x 2 x 2` pilot is complete
- judge error rate is `0` in curated founder-facing results
- the agent run schema and aggregate schema have survived at least one rerun without changes
- the Layer 2 dashboard page explains the benchmark clearly

Only after that may the project consider:

- a second pinned agent model
- `generic_retrieval_agent`
- `context7_agent`
- executable sandbox scoring
- larger task pools

## Strict Autonomous Work Order

An autonomous implementation agent should follow this exact order.

1. Read `docs/SECOND_LAYER_DEVELOPMENT_PLAN.md` and this spec.
2. Do not edit frozen Layer 1 surfaces unless a written exception exists.
3. Implement Phase 1 schemas and validators first.
4. Implement workspace isolation and tools before live model clients.
5. Implement the separate tool-use client layer before the runner.
6. Implement conditions and prompt builder before the first live run.
7. Implement dry-run runner support before live runs.
8. Implement Layer 2 grading before full pilot runs.
9. Lock smoke tasks before pilot tasks.
10. Create curated input flow before founder-facing aggregation.
11. Build the separate dashboard page last.
12. Never publish or summarize Layer 2 using exploratory raw artifacts.

## Publish Gates

Layer 2 is not launch-safe until all of the following pass:

```bash
python3 scripts/check_layer2_boundaries.py
python3 scripts/validate_agent_tasks.py dataset/tasks_layer2_pilot.json
python3 -m harness.run_agent_eval --provider <provider> --model <model> --tasks dataset/tasks_layer2_smoke.json --condition all --dry-run
python3 scripts/curate_agent_runs.py --input results/agent_raw --output results/agent_raw_curated/combined
python3 scripts/aggregate_agent.py --input results/agent_raw_curated/combined --output results/agent_scores.json
python3 scripts/validate_agent_scores.py results/agent_scores.json
cd dashboard && npm run build
python3 scripts/validate_scores.py results/scores.json
```

The last command is intentionally a Layer 1 regression check.

## Explicit Out of Scope

The following items are not part of Layer 2 v1 implementation:

- changing Layer 1 methodology or dashboard homepage
- building a retrieval-vs-retrieval benchmark
- adding unrestricted shell access
- adding package installation during runs
- adding a live-updating Layer 2 dataset refresh system
- replacing judge scoring with sandbox-only scoring
- merging Layer 1 and Layer 2 into one benchmark number

## Final Rule

If any Layer 2 implementation step creates pressure to weaken Layer 1, stop and solve it by adding a parallel Layer 2 module, path, schema, or page instead.
