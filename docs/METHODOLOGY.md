# NiaBench Methodology

## 1. Benchmark Objective

Brief explanation: NiaBench measures the causal effect of fresh documentation context on coding-task performance for fast-moving libraries.

Detailed explanation: NiaBench is an A/B benchmark, not a general model leaderboard. For each task, we compare the same model on the same prompt twice: once without retrieved docs context and once with retrieved docs context. This isolates the contribution of context retrieval rather than differences between models.

## 2. Dataset Design

Brief explanation: Tasks are version-sensitive migration and usage problems where stale knowledge causes realistic failures.

Detailed explanation: Each task records the version boundary, deprecated pattern, correct current pattern, and a short rationale for why a model might fail without up-to-date documentation. The public Layer 1 set is `dataset/tasks.json` with `30` tasks across `20` libraries. A larger raw corpus is retained separately in `dataset/tasks_raw.json` for future expansion.

## 3. Experimental Conditions

Brief explanation: Each task is run in baseline and treatment modes under matched runtime settings.

Detailed explanation: Baseline runs receive only the task instructions. Treatment runs receive the same task instructions plus a labeled retrieved-context block (`CURRENT DOCUMENTATION CONTEXT (retrieved via Nia)`) appended in the system prompt. Model ID, temperature, and other runtime controls are held fixed within each baseline/treatment pair.

## 4. Retrieval And Execution Flow

Brief explanation: Retrieval is performed through Nia APIs and written to artifacts for later audit.

Detailed explanation: For treatment runs, the harness retrieves documentation chunks and injects them into the prompt. Retrieved chunks, final prompts, model outputs, and error states are stored in result artifacts. If retrieval is transiently unavailable, the run is preserved with explicit retrieval status so failures are visible rather than silently dropped.

## 5. Scoring (Current Layer 1)

Brief explanation: Current scoring is judge-only; sandbox execution is deferred.

Detailed explanation: Layer 1 uses rubric-aware judge scoring for baseline and treatment outputs. Composite scores are derived from judge outputs for this release. Sandbox-backed execution scoring is intentionally deferred and will be reintroduced in a later layer as an additional signal.

## 6. Reliability And Auditability

Brief explanation: NiaBench is designed so every claim is traceable to concrete artifacts.

Detailed explanation: Run artifacts include prompt text, retrieved context, model responses, and grading outputs. Aggregates are regenerated from raw artifacts using deterministic scripts and validated against schema contracts before dashboard publish. This keeps metric claims reproducible and reviewable.

## 7. Interpreting Reported Deltas

Brief explanation: Segment deltas carry different meaning and should be read together.

Detailed explanation: `nonperfect_baseline_delta_pct` captures improvement where baseline rows had room to improve. `perfect_baseline_delta_pct` captures movement on rows where baseline was already perfect; negative values indicate context occasionally introduced distraction. `improvement_delta_pct` is the blended effect across all rows.

## 8. Current Layer 1 Snapshot

Current aggregate (`results/scores.json`):

- Evaluations: `60` (`30` tasks x `2` models)
- Libraries covered: `20`
- `overall_without_nia`: `75.0`
- `overall_with_nia`: `85.833333`
- `improvement_delta_pct`: `+10.833333`
- `nonperfect_baseline_delta_pct`: `+47.916667`
- `perfect_baseline_delta_pct`: `-13.888889`
