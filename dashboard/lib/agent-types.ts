export type AgentConditionId = "no_retrieval_agent" | "nia_agent";

export type AgentRateMap = Record<AgentConditionId, number | null>;

export type AgentSummary = {
  delta_completed_only_pct: number | null;
  delta_crash_aware_pct: number | null;
  run_level_completion_rate: AgentRateMap;
  run_level_crash_rate: AgentRateMap;
  run_level_timeout_rate: AgentRateMap;
  run_level_no_artifact_rate: AgentRateMap;
  run_level_judge_error_rate: AgentRateMap;
  nia_usage_rate: number | null;
  avg_nia_calls_per_nia_run: number | null;
  unique_tasks: number;
  total_runs: number;
  model_provider: string | null;
  model: string | null;
  judge_provider: string | null;
  judge_model: string | null;
};

export type AgentConditionRow = {
  condition: AgentConditionId;
  total_runs: number;
  unique_tasks: number;
  completed_runs: number;
  task_macro_completed_only_avg_quality_pct: number | null;
  task_macro_crash_aware_avg_quality_pct: number | null;
  run_level_completion_rate: number | null;
  run_level_crash_rate: number | null;
  run_level_timeout_rate: number | null;
  run_level_no_artifact_rate: number | null;
  run_level_judge_error_rate: number | null;
  avg_tool_calls_per_run: number | null;
  avg_nia_calls_per_run: number | null;
  nia_usage_rate: number | null;
  avg_nia_calls_per_nia_run: number | null;
};

export type AgentTaskConditionStats = {
  repetitions: number;
  completed_only_avg_quality_pct: number | null;
  crash_aware_avg_quality_pct: number | null;
  completion_rate: number | null;
  completed_only_min_pct: number | null;
  completed_only_max_pct: number | null;
  completed_only_stddev_pct: number | null;
};

export type AgentTaskRow = {
  task_id: string;
  library: string;
  difficulty: string;
  by_condition: Record<AgentConditionId, AgentTaskConditionStats>;
  delta_completed_only_pct: number | null;
  delta_crash_aware_pct: number | null;
};

export type AgentLibraryConditionStats = {
  tasks: number;
  completed_only_avg_quality_pct: number | null;
  crash_aware_avg_quality_pct: number | null;
};

export type AgentLibraryRow = {
  library: string;
  tasks: number;
  by_condition: Record<AgentConditionId, AgentLibraryConditionStats>;
  delta_completed_only_pct: number | null;
  delta_crash_aware_pct: number | null;
};

export type AgentScoresFile = {
  generated_at: string | null;
  schema_version: "nia.layer2.aggregate.v1";
  summary: AgentSummary;
  conditions: AgentConditionRow[];
  libraries: AgentLibraryRow[];
  tasks: AgentTaskRow[];
};
