# NiaBench Second Layer Development Plan

## Purpose

NiaBench already has a strong first layer:

- Layer 1 answers a clean question: "Does fresh Nia context improve model output when everything else stays the same?"
- Layer 1 is valuable because it is simple, easy to explain, and easy to trust.

This document defines a second layer that adds more real-world agent behavior without weakening the first layer.

Implementation-grade build instructions now live in `docs/SECOND_LAYER_EXECUTION_SPEC.md`.

In plain English:

- Layer 1 is the clean science experiment.
- Layer 2 will be the realistic workflow benchmark.

Layer 2 should answer a different question:

- "How well does an actual coding agent perform when it has to use tools, retrieve context, handle failures, and complete the task end to end?"

## Non-Negotiable Rule

Layer 2 must complement Layer 1, not replace it.

That means:

- Layer 1 stays frozen as the canonical retrieval-effect benchmark.
- Layer 2 is built as a separate benchmark track with separate commands, separate outputs, and separate reporting.
- We never blend Layer 1 and Layer 2 into one headline number.
- We never change Layer 1 scoring rules just to make Layer 2 easier to implement.

## What Layer 2 Should Do Better

Layer 2 should improve NiaBench in the areas where a real agent benchmark is stronger:

- Test full agent behavior, not just prompt injection
- Measure tool usage and whether the agent actually used Nia well
- Track crashes, retries, timeouts, and empty-output failures
- Capture richer failure modes
- Produce a more realistic "what happens in practice?" result

## What Layer 2 Must Not Break

Layer 2 must not damage the strengths of Layer 1:

- Clear causal comparison
- Same-model / same-task / same-settings discipline
- Easy explanation for external readers
- Launch-safe aggregate reporting
- Reproducible, auditable result artifacts

## Layer Definitions

### Layer 1: Retrieval Benchmark

Current state:

- Same model, same task, same prompt shape
- Only intended variable is whether fresh Nia context is injected
- Judge-first / judge-only scoring today
- Public result artifact lives in `results/scores.json`

Primary question:

- "Did fresh Nia context help?"

### Layer 2: Agent Workflow Benchmark

Planned state:

- The model operates as a coding agent, not just a direct text completion
- The agent can choose tools, retrieve docs, and produce task artifacts
- Runs are crash-aware and retry-aware
- We capture operational behavior as well as correctness

Primary question:

- "How well does a coding agent perform with Nia in a realistic workflow?"

## Separation Strategy

To protect Layer 1, Layer 2 should be isolated in five ways.

### 1. Separate commands

Examples:

- Layer 1: `python3 -m harness.run_eval ...`
- Layer 2: `python3 -m harness.run_agent_eval ...`

### 2. Separate output directories

Examples:

- Layer 1 raw outputs: `results/raw/`
- Layer 2 raw outputs: `results/agent_raw/`

### 3. Separate aggregates

Examples:

- Layer 1 aggregate: `results/scores.json`
- Layer 2 aggregate: `results/agent_scores.json`

### 4. Separate dashboard views

Examples:

- Main page remains Layer 1 unless explicitly expanded
- Layer 2 gets its own page, tab, or clearly labeled section
- Layer 2 gets its own dashboard data loader and TypeScript types rather than widening the Layer 1 dashboard contract

### 5. Separate success criteria

Examples:

- Layer 1 success is about clean causal evidence
- Layer 2 success is about realistic end-to-end agent quality and reliability

## Recommended Scope for Layer 2 v1

The first version of Layer 2 should stay narrow.

Recommended v1 scope:

- Compare `no_retrieval_agent` vs `nia_agent`
- Reuse the current pinned model IDs when possible
- Start with a small locked Layer 2 pilot instead of the full task pool
- Reuse Layer 1 infrastructure only below a Layer 2-specific grading contract
- Add reliability and tool-usage metrics before adding more benchmark conditions
- Keep v1 limited to one pinned model during the stabilization phase

Recommended v1 pilot size:

- `12` locked tasks
- `1` pinned model
- `2` conditions
- `2` repetitions per condition
- total planned pilot volume: `48` agent runs

This smaller pilot is intentional.

- It reduces debugging noise while the agent runner is still immature.
- It avoids creating pressure to weaken Layer 1 just to move faster.
- It gives enough data to validate the Layer 2 architecture before expanding to more models.

Repetition policy for Layer 2 v1:

- Layer 2 v1 should keep temperature at `0`
- repetitions exist to measure workflow-level non-determinism, not sampling-temperature variance
- likely sources of run-to-run variation include model service nondeterminism, retrieval ordering, and tool-use path variation
- Layer 2 aggregation should average repeated runs for the primary score view
- Layer 2 reporting should also expose spread metrics such as min, max, and standard deviation when run counts allow
- per-run artifacts must always be preserved, even when aggregate reporting averages them

Recommended v1 non-goals:

- Do not add many competing tool providers at once
- Do not redesign Layer 1 tasks purely for agent mode
- Do not build a giant new dashboard before the data model is stable
- Do not merge Layer 2 numbers into the current founder-facing score

## Design Principles

### Additive, not substitutive

Layer 2 is a new track beside Layer 1.

### Reuse existing infrastructure when it helps

Use current task metadata, LLM client plumbing, validators, and reporting ideas where possible.

Do not reuse the exact Layer 1 grading contract unchanged.
Do not extend the existing Layer 1 `BaseLLMClient` hierarchy to add agent tool use.

### Explicitly different benchmark question

Layer 2 v1 is not a replacement for Layer 1's clean causal comparison.

Layer 2 v1 should explicitly measure:

- "Does a Nia-enabled agent outperform the same agent when it has no external retrieval tool?"

Layer 2 v1 should not be described as:

- "Nia vs all other retrieval approaches"
- "Nia vs equivalent non-Nia retrieval"

If the project later wants that comparison, it should add a third condition such as:

- `generic_retrieval_agent`
- `context7_agent`

### Constrained realism

Layer 2 should be realistic enough to matter, but constrained enough to remain interpretable.

That means:

- one defined agent loop
- one defined tool interface
- pinned step budgets
- pinned timeout behavior
- pinned termination rules
- structured artifact capture

### No answer leakage into retrieval

Layer 2 must not inherit the current `correct_pattern` query-leakage issue from Layer 1.

Retrieval queries in Layer 2 must not include:

- `correct_pattern`
- `reference_solution`
- rubric criteria
- common hallucination hints

Allowed retrieval inputs should be limited to fields such as:

- library
- target version
- agent goal text
- high-level task category

### Log everything important

Every Layer 2 run should preserve:

- task metadata
- prompt(s)
- tool calls
- retrieved context
- agent output
- retries
- failures
- grading details

### Keep the first public story simple

Layer 1 remains the clean story.
Layer 2 becomes the realism story.

## Proposed Architecture

Layer 2 should fit the current repo style instead of introducing a parallel stack in another language.

Recommended new files and directories:

- `harness/run_agent_eval.py`
- `harness/agent_runner.py`
- `harness/agent_conditions.py`
- `harness/agent_llm_clients.py`
- `harness/agent_types.py`
- `harness/agent_prompts.py`
- `grading/agent_judge.py`
- `grading/agent_failure_taxonomy.py`
- `grading/agent_types.py`
- `scripts/aggregate_agent.py`
- `scripts/validate_agent_scores.py`
- `results/agent_raw/`
- `results/agent_scores.json`
- `dataset/tasks_layer2_pilot.json`
- `dataset/agent_task.schema.json`
- `dashboard/lib/load-agent-scores.ts`
- `dashboard/lib/agent-types.ts`
- `dashboard/app/agent/page.tsx`
- `docs/SECOND_LAYER_DEVELOPMENT_PLAN.md`

If agent-specific task wrappers are needed later:

- keep the core task identity shared with Layer 1 when possible
- add agent-only fields in a separate task file rather than mutating the Layer 1 schema first

Recommended Layer 2 task wrapper fields:

- `source_task_id`
- `agent_goal`
- `workspace_seed`
- `expected_artifacts`
- `allowed_output_paths`
- `retrieval_hints` using non-answer-bearing information only

Required semantics for those fields:

- `workspace_seed`
  - files and folder structure that should be materialized before the run begins
  - may include starter code, config files, fixtures, or failing examples
- `expected_artifacts`
  - the specific output files or structured outputs the grading adapter should inspect
  - this is the primary bridge between task execution and evaluation
- `allowed_output_paths`
  - the only paths the agent is allowed to create or modify for benchmark-scored outputs
  - helps keep extraction deterministic and avoids scoring random side files
- `retrieval_hints`
  - non-answer-bearing search guidance only
  - may help formulate retrieval but may not contain the answer pattern itself

## Condition Definitions

Layer 2 v1 must define its conditions precisely.

### `no_retrieval_agent`

This is the Layer 2 baseline condition.

It should have:

- the same model as `nia_agent`
- the same agent loop
- the same local workspace tools
- the same file-editing permissions
- no external retrieval tool

It should not have:

- Nia retrieval
- generic web search
- alternative documentation retrieval tools

This condition is intentionally a "no external retrieval" baseline.
It is not an "equivalent non-Nia retrieval" baseline.

### `nia_agent`

This condition should be identical to `no_retrieval_agent` except that it also has access to the Layer 2 Nia retrieval tool interface.

### Future optional conditions

Only after Layer 2 v1 is stable:

- `generic_retrieval_agent`
- `context7_agent`

Those future conditions would answer a different question:

- "Is Nia better than other retrieval options?"

## Agent Contract

Layer 2 needs a concrete definition of what "agent" means.

For Layer 2 v1, one run should mean:

- one isolated workspace
- one agent session
- one goal-oriented prompt
- one bounded tool-use loop
- one structured final output or terminal failure state

Proposed Layer 2 v1 loop:

1. Initialize isolated workspace and task wrapper
2. Send system prompt plus `agent_goal`
3. Agent may use allowed tools and inspect workspace state
4. Loop continues until explicit completion or termination condition
5. Extract produced artifacts and evaluate them

Proposed hard limits for Layer 2 v1:

- max steps: `12`
- max wall-clock time per run: `10` minutes
- max completion tokens per model turn: `2048`
- max total generated tokens per run: `25000`

These defaults should be frozen before the first public Layer 2 pilot run.

Definition of a step:

- one step equals one assistant turn
- a single assistant turn may include multiple tool calls
- all tool calls emitted within that assistant turn still count as one step

This definition should be enforced consistently in the runner and reporting.

Termination conditions:

- explicit completion with at least one extractable artifact
- step budget exhausted
- wall-clock timeout
- unrecoverable process crash
- retry budget exhausted

## Nia Tool Interface

Layer 2 tool-use metrics only make sense if Nia is exposed as a real callable tool.

For Layer 2 v1, Nia should be exposed through a thin internal tool wrapper over the direct Nia API, not through prompt-only injection.

Recommended reason:

- it matches Layer 1's preference for direct API control and auditability
- it gives structured logs
- it reduces ambiguity about what the agent actually used

Recommended initial Layer 2 tool surface:

- `nia_search_docs(query, library, version, top_k)`
- `nia_read_chunk(source_id, chunk_id)` or an equivalent follow-up read tool if needed

The first tool should be mandatory for v1.
The second should be added only if retrieval quality needs it.

Every call should log:

- tool name
- query arguments
- returned chunks
- source metadata
- timestamp

## Local Tool Surface

Layer 2 must define the local capability surface clearly so the baseline is interpretable.

Allowed local tools for Layer 2 v1:

- read workspace files
- write or edit files only within `allowed_output_paths`
- list directories inside the isolated workspace
- run a constrained test command only if the task wrapper explicitly defines one

Disallowed local tools for Layer 2 v1:

- unrestricted shell access
- package installation during a run
- web search
- fetching remote URLs outside the Nia tool path
- reading documentation from globally installed packages

Reason:

- this keeps `no_retrieval_agent` meaningfully "no external retrieval"
- it avoids giving the baseline hidden retrieval channels
- it keeps the capability surface stable and auditable

## Layer 2 Grading Contract

Layer 2 should not force agent artifacts through the exact Layer 1 judge interface unchanged.

Layer 1 today scores two text outputs side by side.
Layer 2 needs a separate contract because it may evaluate:

- extracted files
- structured final summaries
- multi-file outputs
- operational metadata

Layer 2 should therefore get:

- its own judge prompt
- its own result schema
- its own grading adapter

Layer 2 may still reuse:

- the underlying LLM client code
- JSON parsing helpers
- existing rubric concepts

But Layer 2 should not directly reuse `JudgeGrader.grade()` unchanged as the public grading contract.

## Judge Independence

Layer 2 should not silently carry forward self-judging as if it were harmless.

Because agent outputs are longer and more complex, self-judging risk is higher in Layer 2 than in Layer 1.

Recommendation:

- founder-facing Layer 2 reporting should use one fixed independent judge model
- the judge model should not be the same model being benchmarked as the agent

If self-judging is used temporarily during internal iteration, it should be labeled:

- internal-only
- non-launch-safe

## Recommended Layer 2 Metrics

Layer 2 should measure both correctness and operational quality.

### Core quality metrics

- pass rate
- average judge score
- average composite score
- per-library score
- per-task score

### Reliability metrics

- crash rate
- timeout rate
- retry rate
- empty-output rate
- completion rate

### Tool-use metrics

- percent of runs where Nia was actually used
- number of Nia calls per run
- number of total tool calls per run
- percent of runs where retrieval returned usable content

### Quality failure taxonomy

- outdated API
- wrong import path
- wrong parameter or signature
- invented method or object
- mixed-version answer

### Operational failure taxonomy

- retrieval failure
- agent execution failure
- timeout
- crash
- empty output
- judge failure

These metrics should live in Layer 2 reporting only unless they are explicitly added to Layer 1 later.

## Development Phases

## Phase 0: Freeze and Protect Layer 1

Goal:

- Make sure Layer 2 cannot accidentally change Layer 1 behavior.

Work:

- Document Layer 1 as the frozen core benchmark
- Keep `results/scores.json` and existing Layer 1 scripts as the source of truth
- Treat these as frozen Layer 1 contract surfaces unless they are explicitly versioned separately:
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
- Add an automated Layer 2 boundary checker and wire it into CI before substantial Layer 2 implementation begins
- Add explicit regression checks that confirm Layer 1 outputs and dashboard behavior have not changed:
  - `python3 scripts/validate_scores.py results/scores.json`
  - `cd dashboard && npm run build`
  - one stable smoke check or snapshot for the Layer 1 homepage data contract and copy
- Avoid reusing Layer 1 output paths for any Layer 2 artifact

Definition of done:

- Layer 2 code can be added and run without changing any Layer 1 output file or dashboard number

## Phase 1: Write the Layer 2 Spec

Goal:

- Define exactly what Layer 2 runs, stores, and reports.

Work:

- Define Layer 2 conditions:
  - `no_retrieval_agent`
  - `nia_agent`
- State explicitly that Layer 2 v1 measures "Nia retrieval vs no external retrieval"
- Define future optional comparison conditions separately, not in v1
- Define result JSON schema for a single run
- Define aggregate schema for `results/agent_scores.json`
- Define operational metrics and split failure taxonomy into quality vs operational failures
- Define a Layer 2-specific judge prompt and grading contract
- Define Layer 2 task wrapper schema or agent-goal adapter
- Define the agent loop contract:
  - step limit
  - step definition
  - timeout
  - token budget
  - termination rules
- Define repetition semantics:
  - why repetitions exist at temperature `0`
  - how repeated runs are aggregated
  - what spread metrics are reported
- Define the Nia tool interface and logging contract
- Define the allowed local tool surface and the disallowed hidden-retrieval paths
- Define how `workspace_seed`, `expected_artifacts`, and `allowed_output_paths` drive extraction and grading
- Define retrieval-query safety rules that forbid answer-bearing fields
- Define a separate tool-use-aware agent client contract instead of extending Layer 1 `BaseLLMClient`

Definition of done:

- There is a written contract for Layer 2 artifacts, tool surfaces, extraction rules, repetition handling, and metrics before implementation begins

## Phase 2: Build the Agent Runner

Goal:

- Execute tasks through an agent-style interface while keeping runs auditable.

Work:

- Build an agent runner wrapper with:
  - isolated working directory
  - run ID
  - timeout handling
  - retry handling
  - transcript capture
  - tool-call capture
- Build a separate agent-facing LLM client layer for tool-use turns
- Keep Layer 1 `BaseLLMClient.generate()` unchanged for text-only eval and judge calls
- Build separate condition setup for:
  - no external Nia usage
  - Nia-enabled agent mode
- Implement the defined bounded agent loop instead of an open-ended session
- Implement the structured Nia tool wrapper rather than prompt-only retrieval injection
- Save artifacts per run instead of overwriting

Definition of done:

- A Layer 2 run produces a structured artifact even when the agent crashes or times out

## Phase 3: Add Crash-Aware and Retry-Aware Evaluation

Goal:

- Score Layer 2 honestly, including operational failures.

Work:

- Build a Layer 2 grading adapter with its own prompt contract
- Reuse only lower-level components from Layer 1 where appropriate
- Add Layer 2 result statuses such as:
  - `ok`
  - `timeout`
  - `crash`
  - `empty_output`
  - `retrieval_error`
  - `judge_error`
- Decide how crashes affect reporting:
  - include crash-aware summary metrics
  - keep crash-free quality metrics visible too
- Preserve failure reason in every run artifact

Definition of done:

- Layer 2 can tell the difference between "bad code" and "agent failed to complete"

## Phase 4: Start with a Small Locked Pilot

Goal:

- Prove the Layer 2 system on a tractable, representative subset.

Work:

- Create `dataset/tasks_layer2_pilot.json`
- Use exactly `12` locked tasks
- Use one pinned model in the first Layer 2 pilot
- Run two conditions with two repetitions each
- Target a pilot volume of about `48` total runs
- Ensure coverage across:
  - multiple libraries
  - multiple difficulty levels
  - at least a few tasks where stale knowledge is likely to matter
- Prefer tasks from Layer 1 first so comparisons remain interpretable
- If a Layer 1 prompt is not agent-shaped, wrap it in Layer 2 agent framing or write a Layer 2-specific `agent_goal`

Definition of done:

- There is a locked Layer 2 pilot task set that can be rerun consistently

## Phase 5: Add Aggregation and Reporting

Goal:

- Turn raw Layer 2 runs into a clear report without touching Layer 1 reporting.

Work:

- Build `scripts/aggregate_agent.py`
- Build `scripts/validate_agent_scores.py`
- Produce:
  - overall quality metrics
  - crash-aware metrics
  - tool-usage metrics
  - per-library summaries
  - per-task summaries
- Keep output in `results/agent_scores.json`

Definition of done:

- A full Layer 2 pilot run can be aggregated and validated in a repeatable way

## Phase 6: Add Dashboard Support

Goal:

- Make Layer 2 understandable without confusing it with Layer 1.

Work:

- Add a separate Layer 2 page or explicitly labeled dashboard section
- Prefer a separate Layer 2 page for v1 instead of extending the existing homepage
- Build separate Layer 2 dashboard modules such as:
  - `dashboard/lib/load-agent-scores.ts`
  - `dashboard/lib/agent-types.ts`
  - `dashboard/app/agent/page.tsx`
- Explain in plain language:
  - Layer 1 = clean retrieval benchmark
  - Layer 2 = realistic agent workflow benchmark
- Show Layer 2 metrics separately from Layer 1 metrics
- Never combine both into one blended score on the main page

Definition of done:

- A reader can understand both layers and why both exist

## Phase 7: Expand Carefully

Goal:

- Only expand once the first Layer 2 version is stable and interpretable.

Possible future expansions:

- add a second pinned model after the one-model pilot is stable
- add a third condition such as `context7_agent`
- add a `generic_retrieval_agent` condition for fairer retrieval-vs-retrieval comparison
- add larger Layer 2 task sets
- add executable sandbox scoring for agent-produced code
- add retrieval-quality diagnostics
- add per-model Layer 2 comparisons

Definition of done:

- Expansion happens only after the pilot produces stable, credible results

## Recommended Build Order

The safest implementation order is:

1. Freeze Layer 1 contracts
2. Write Layer 2 result schema and reporting spec
3. Build the agent runner and artifact logging
4. Add crash-aware evaluation statuses
5. Create the small locked Layer 2 pilot
6. Aggregate and validate Layer 2 results
7. Add dashboard support
8. Expand only after the first pilot is trusted

## Specific Guardrails To Prevent Layer 1 Damage

These guardrails should be treated as engineering requirements.

- Do not change `harness/run_eval.py` behavior to support Layer 2 shortcuts
- Do not extend `harness/llm_clients.py` or `BaseLLMClient.generate()` to support Layer 2 tool use
- Do not reuse `results/raw/` for Layer 2 runs
- Do not reuse `results/scores.json` for Layer 2 aggregates
- Do not replace the Layer 1 dashboard summary with Layer 2 metrics
- Do not widen `dashboard/lib/load-scores.ts` or `dashboard/lib/types.ts` to carry Layer 2 data
- Do not change `dashboard/app/page.tsx` from being the canonical Layer 1 page in Layer 2 v1
- Do not alter Layer 1 task definitions just to make agent execution easier
- Do not change Layer 1 headline methodology wording when Layer 2 ships
- Do not merge Layer 1 and Layer 2 into one leaderboard
- Do not include `correct_pattern` or equivalent answer-bearing fields in Layer 2 retrieval calls
- Do not reuse the exact Layer 1 judge prompt for Layer 2 runs
- Do not allow founder-facing Layer 2 reporting to default to self-judging
- Do not reinterpret `HarnessConfig.results_dir` or other Layer 1 default paths to route Layer 2 outputs; add Layer 2-specific path handling instead
- Do not reuse `CompositeGrader.judge_only_bundle()` as the public Layer 2 result contract

## Risks and Mitigations

### Risk: Layer 2 becomes noisy and hard to interpret

Mitigation:

- keep Layer 2 separate
- keep the first pilot small
- show crash-aware metrics separately from quality metrics

### Risk: Layer 2 accidentally changes Layer 1 outputs

Mitigation:

- separate scripts, paths, and aggregates
- regression checks for Layer 1 outputs

### Risk: Too many conditions at once

Mitigation:

- start with `no_retrieval_agent` vs `nia_agent`
- add more conditions only after the first pilot is stable

### Risk: Building a whole new benchmark stack

Mitigation:

- reuse current Python harness style
- reuse current lower-level grading components where possible
- add only the new pieces that agent mode actually needs

## Success Criteria

Layer 2 is successful when:

- Layer 1 remains unchanged and trustworthy
- Layer 2 can run a locked pilot end to end
- Layer 2 reports both correctness and reliability
- Layer 2 clearly shows whether Nia helps in realistic agent workflows
- readers can understand the difference between both layers without confusion

## Final Recommendation

NiaBench should become a two-layer benchmark:

- Layer 1: clean causal benchmark for retrieval impact
- Layer 2: realistic agent workflow benchmark for practical performance

That combination is stronger than either one alone.

Layer 1 gives the clean proof.
Layer 2 gives the real-world story.

Built this way, the second layer increases the benchmark's usefulness without weakening the benchmark's current strengths.
