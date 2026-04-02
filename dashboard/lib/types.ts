export type ScoreSummary = {
  overall_without_nia: number | null;
  overall_with_nia: number | null;
  improvement_delta_pct: number | null;
  // Deprecated, kept for backward compatibility with existing snapshots.
  tasks_evaluated: number;
  evaluations_count: number;
  unique_tasks: number;
  nonperfect_baseline_without_nia: number | null;
  nonperfect_baseline_with_nia: number | null;
  nonperfect_baseline_delta_pct: number | null;
  nonperfect_baseline_count: number;
  perfect_baseline_without_nia: number | null;
  perfect_baseline_with_nia: number | null;
  perfect_baseline_delta_pct: number | null;
  perfect_baseline_count: number;
  libraries_covered: number;
  models_tested: string[];
};

export type LibraryScore = {
  id: string;
  label: string;
  tasks: number;
  without_nia: number | null;
  with_nia: number | null;
  delta_pct: number | null;
  best_improvement_example?: string;
};

export type ScoresFile = {
  generated_at: string | null;
  summary: ScoreSummary;
  libraries: LibraryScore[];
  tasks: Array<Record<string, unknown>>;
};
