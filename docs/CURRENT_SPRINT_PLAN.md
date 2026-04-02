# NiaBench Current Sprint Plan

Status: Active
Last updated: Wednesday, April 1, 2026
Primary objective: Add segmented analysis to the dashboard so the benchmark transparently shows both the overall delta and the per-segment deltas, without misrepresenting the data.

## Motivation

The current dashboard shows a single overall delta of +10.8%. This number is accurate but structurally compressed: 60% of evaluations (36/60) already score 100% at baseline under the current judge rubric, so retrieval context can only hurt or maintain those scores. The blended average mixes two populations with opposite dynamics:

- **Non-perfect-baseline evaluations** (baseline < 100%): 24 evals where the model scored below the rubric maximum without context. Delta: **+47.9%** (37.5% → 85.4%).
- **Perfect-baseline evaluations** (baseline = 100%): 36 evals where the model already scored the rubric maximum without context. Delta: **-13.9%** (100.0% → 86.1%).

This is a descriptive split on observed baseline score, not a validated claim about model knowledge state. A model scoring 100% at baseline may have gotten lucky or matched the judge rubric without deep understanding; a model scoring below 100% may have partial knowledge that the rubric penalized. The split is useful for reading the data but should not be presented as a causal explanation.

Both numbers are real. Showing only the blended +10.8% obscures the structural composition. Showing only +47.9% would cherry-pick. The goal is to show all three transparently so a technical reader can draw their own conclusions.

### Important caveats the UI must communicate

1. **Evaluations, not tasks.** The benchmark has 30 unique tasks evaluated on 2 models = 60 evaluations. The current dashboard mislabels this as "Tasks" — it should say "Evaluations" (or show both "30 tasks / 60 evaluations").

2. **The segment split is per-evaluation, not per-task.** 14 of the 30 unique tasks are mixed: one model scores perfectly at baseline while the other does not. A single task can appear in both segments depending on the model. The UI copy must not imply a clean task-level partition.

3. **Segment labels must be descriptive, not causal.** Use "non-perfect baseline" / "perfect baseline" (what the data shows), not "needed help" / "already knew the answer" (an interpretation the data does not validate).

## Implementation Plan

### Step 1: Extend `scripts/aggregate.py` with segmented summary fields

File: `scripts/aggregate.py`, function `build_scores_file()`

After computing the existing `overall_*` fields, partition `valid_rows` into two segments:

```python
nonperfect_rows = [r for r in valid_rows if r["baseline_pct"] < 100.0]
perfect_rows = [r for r in valid_rows if r["baseline_pct"] == 100.0]
```

Add to the `summary` dict:

| Field | Type | Value |
|---|---|---|
| `nonperfect_baseline_without_nia` | `float \| None` | Mean baseline_pct of non-perfect rows |
| `nonperfect_baseline_with_nia` | `float \| None` | Mean treatment_pct of non-perfect rows |
| `nonperfect_baseline_delta_pct` | `float \| None` | `with - without` for non-perfect rows |
| `nonperfect_baseline_count` | `int` | Number of non-perfect-baseline evaluations |
| `perfect_baseline_without_nia` | `float \| None` | Mean baseline_pct of perfect rows (always 100.0) |
| `perfect_baseline_with_nia` | `float \| None` | Mean treatment_pct of perfect rows |
| `perfect_baseline_delta_pct` | `float \| None` | `with - without` for perfect rows |
| `perfect_baseline_count` | `int` | Number of perfect-baseline evaluations |
| `evaluations_count` | `int` | Total evaluation rows (replaces `tasks_evaluated` as canonical name) |
| `unique_tasks` | `int` | Count of distinct task_ids across all rows |

Use the same `_mean()` helper. No new dependencies.

Add `evaluations_count` as the canonical field for the number of evaluation rows. Keep `tasks_evaluated` for backward compatibility but treat it as deprecated — new code and docs should use `evaluations_count`. Add `unique_tasks` for the distinct task count.

Definition of done:
- `python3 scripts/aggregate.py --input results/raw_curated/combined --output results/scores.json` exits 0.
- Output contains all 9 new summary fields.
- `nonperfect_baseline_count + perfect_baseline_count == tasks_evaluated`.

### Step 2: Extend `dashboard/lib/types.ts`

Add the 9 new fields to `ScoreSummary`:

```typescript
export type ScoreSummary = {
  // existing fields unchanged
  overall_without_nia: number | null;
  overall_with_nia: number | null;
  improvement_delta_pct: number | null;
  tasks_evaluated: number;       // deprecated, kept for back-compat
  evaluations_count: number;     // canonical evaluation row count
  libraries_covered: number;
  models_tested: string[];

  // segmented analysis (descriptive split on baseline score)
  nonperfect_baseline_without_nia: number | null;
  nonperfect_baseline_with_nia: number | null;
  nonperfect_baseline_delta_pct: number | null;
  nonperfect_baseline_count: number;
  perfect_baseline_without_nia: number | null;
  perfect_baseline_with_nia: number | null;
  perfect_baseline_delta_pct: number | null;
  perfect_baseline_count: number;
  unique_tasks: number;
};
```

No other type changes needed.

### Step 3: Update `scripts/validate_scores.py`

Add the 9 new fields to `REQUIRED_SUMMARY`. Apply the same validation rules:
- `nonperfect_baseline_without_nia`, `nonperfect_baseline_with_nia`, `nonperfect_baseline_delta_pct`: number or null
- `nonperfect_baseline_count`: integer
- `perfect_baseline_without_nia`, `perfect_baseline_with_nia`, `perfect_baseline_delta_pct`: number or null
- `perfect_baseline_count`: integer
- `evaluations_count`: integer
- `unique_tasks`: integer

Definition of done:
- `python3 scripts/validate_scores.py results/scores.json` exits 0 with new fields present.
- Validation fails if any of the 9 new fields are missing.

### Step 4: Update `dashboard/app/page.tsx`

#### Fix the denominator label

Change the existing stat card from "Tasks / Libraries" to "Evaluations / Libraries" and add a subtitle or secondary line showing unique task count:

```
Evaluations / Libraries
60 / 20
(30 unique tasks × 2 models)
```

#### Add segmented analysis section

Below the overall stats, add a new section with two side-by-side cards:

Card 1 — "Non-perfect baseline" segment:
- Label: "Baseline scored below rubric maximum"
- Count: N of 60 evaluations
- Without Nia → With Nia
- Delta: +X.X%

Card 2 — "Perfect baseline" segment:
- Label: "Baseline scored rubric maximum"
- Count: N of 60 evaluations
- Without Nia → With Nia
- Delta: -X.X%

#### Add explanatory callout

Below the segmented cards, a callout that communicates all three caveats:

> "The overall delta (+X.X%) blends two evaluation populations. In N evaluations, the model already scored the rubric maximum (2/2) without retrieval context; adding context reduced scores on average by X.X percentage points. In N evaluations where the baseline score was below maximum, retrieval context improved scores by +X.X percentage points. This is a descriptive split on observed baseline score — not a measure of model knowledge. Because each of the 30 tasks is evaluated on 2 models, the same task can appear in different segments depending on which model is evaluated."

Styling: use the existing `.stat-card`, `.panel`, and `.callout` CSS classes. Use `delta-positive` / `delta-negative` for color coding. No new CSS framework or component library needed.

Definition of done:
- `cd dashboard && npm run build` exits 0.
- The rendered page shows overall stats with corrected denominator label, segmented stats, and the explanatory callout.
- All numbers are computed from `scores.json` at build time, not hardcoded.
- Copy uses descriptive language ("non-perfect baseline" / "perfect baseline"), not causal claims.

### Step 5: Regenerate and validate

Run in order:

```bash
python3 scripts/aggregate.py --input results/raw_curated/combined --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
cd dashboard && npm run build
```

All three must exit 0. Spot-check that `nonperfect_baseline_count + perfect_baseline_count == evaluations_count` in the output file.

### Step 6: Docs consistency pass

Update all docs that reference "tasks evaluated" when the actual count is evaluation rows, not unique tasks. Known locations:

- `docs/METHODOLOGY.md` line 58: "tasks evaluated: `60`" → "evaluations: `60` (30 unique tasks × 2 models)"
- `EXECUTION_BOARD.md`: any reference to "60 evaluations" or "tasks evaluated" should use the correct terminology
- `README.md`: check for any similar mislabeling

Also verify that segment descriptions in docs use "non-perfect baseline" / "perfect baseline" language consistently, with no causal framing.

Definition of done:
- No doc refers to 60 as a task count without clarifying it is evaluations.
- Segment language is descriptive everywhere it appears.

## Out of scope

- Altering the raw evaluation data or re-running evaluations.
- Changing the scoring rubric or judge logic.
- Adding per-model segmented breakdowns (useful but separate from this sprint).
- Changing the library leaderboard table structure.
- Adding retrieval-quality filtering (e.g., excluding irrelevant-context evals) — this would alter the data rather than display it transparently.

## Strict work order

1. `aggregate.py` — compute the new fields (including `evaluations_count`)
2. `types.ts` — add the types
3. `validate_scores.py` — enforce the new contract
4. Regenerate `scores.json` and validate
5. `page.tsx` — render the segmented UI with corrected labels and caveats
6. Docs consistency pass — fix terminology in `METHODOLOGY.md`, `EXECUTION_BOARD.md`, `README.md`
7. Final build and validation pass
