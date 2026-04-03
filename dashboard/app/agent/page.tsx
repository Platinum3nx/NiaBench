import { loadAgentScores } from "@/lib/load-agent-scores";
import type { AgentScoresFile } from "@/lib/agent-types";

function formatPercent(value: number | null): string {
  if (value === null) {
    return "Pending";
  }
  return `${value.toFixed(1)}%`;
}

function formatCompletedOnlyPercent(value: number | null): string {
  if (value === null) {
    return "No completed runs";
  }
  return `${value.toFixed(1)}%`;
}

function formatSignedPercent(value: number | null): string {
  if (value === null) {
    return "Pending";
  }
  if (value > 0) {
    return `+${value.toFixed(1)}%`;
  }
  return `${value.toFixed(1)}%`;
}

function formatCompletedOnlyDelta(value: number | null): string {
  if (value === null) {
    return "Needs completed runs";
  }
  if (value > 0) {
    return `+${value.toFixed(1)}%`;
  }
  return `${value.toFixed(1)}%`;
}

function deltaClass(value: number | null): string {
  if (value === null) {
    return "";
  }
  return value >= 0 ? "delta-positive" : "delta-negative";
}

function completedOnlyDeltaClass(value: number | null): string {
  if (value === null) {
    return "delta-muted";
  }
  return deltaClass(value);
}

function conditionLabel(condition: string): string {
  if (condition === "nia_agent") {
    return "Nia Agent";
  }
  if (condition === "no_retrieval_agent") {
    return "No Retrieval Agent";
  }
  return condition;
}

export default function AgentPage() {
  const scores = safeLoadAgentScores();
  if (scores === null) {
    return (
      <section className="hero">
        <div>
          <p className="eyebrow">Layer 2 benchmark</p>
          <h1>Agent Workflow Track</h1>
        </div>
        <p className="hero-copy">
          Layer 2 data is not available yet. Generate and validate{" "}
          <code>results/agent_scores.json</code> to render this page.
        </p>
        <div className="callout">
          This fallback keeps the Layer 1 dashboard build independent from Layer 2 data
          availability.
        </div>
      </section>
    );
  }
  const { summary, conditions, libraries, tasks } = scores;

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Layer 2 benchmark</p>
          <h1>Agent Workflow Track</h1>
        </div>
        <p className="hero-copy">
          Layer 2 asks a separate question from Layer 1: does the same coding agent perform
          better with a structured Nia retrieval tool than with no external retrieval tool?
          Metrics stay isolated from the Layer 1 benchmark.
        </p>
        <div className="stats">
          <article className="stat-card">
            <p>Completed-only delta</p>
            <strong className={deltaClass(summary.delta_completed_only_pct)}>
              {formatSignedPercent(summary.delta_completed_only_pct)}
            </strong>
          </article>
          <article className="stat-card">
            <p>Crash-aware delta</p>
            <strong className={deltaClass(summary.delta_crash_aware_pct)}>
              {formatSignedPercent(summary.delta_crash_aware_pct)}
            </strong>
          </article>
          <article className="stat-card">
            <p>Total runs / Tasks</p>
            <strong>
              {summary.total_runs} / {summary.unique_tasks}
            </strong>
          </article>
          <article className="stat-card">
            <p>Nia usage rate</p>
            <strong>{formatPercent(summary.nia_usage_rate)}</strong>
            <p>Avg Nia calls in Nia runs: {formatPercent(summary.avg_nia_calls_per_nia_run)}</p>
          </article>
        </div>
        <div className="callout">
          Agent model: <code>{summary.model_provider ?? "unknown"}:{summary.model ?? "unknown"}</code>
          {" | "}
          Judge model:{" "}
          <code>{summary.judge_provider ?? "unknown"}:{summary.judge_model ?? "unknown"}</code>
        </div>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Condition metrics</h2>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Condition</th>
                <th>Runs</th>
                <th>Completed-only quality</th>
                <th>Crash-aware quality</th>
                <th>Completion</th>
                <th>Crash</th>
              </tr>
            </thead>
            <tbody>
              {conditions.map((row) => (
                <tr key={row.condition}>
                  <td>{conditionLabel(row.condition)}</td>
                  <td>{row.total_runs}</td>
                  <td>{formatCompletedOnlyPercent(row.task_macro_completed_only_avg_quality_pct)}</td>
                  <td>{formatPercent(row.task_macro_crash_aware_avg_quality_pct)}</td>
                  <td>{formatPercent(row.run_level_completion_rate)}</td>
                  <td>{formatPercent(row.run_level_crash_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="panel">
          <h2>Operational rates</h2>
          <p>
            Rates below are run-level percentages by condition. These metrics remain Layer 2-only
            and are not blended into Layer 1 reporting.
          </p>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Condition</th>
                <th>Timeout</th>
                <th>No artifact</th>
                <th>Judge error</th>
                <th>Avg tool calls</th>
              </tr>
            </thead>
            <tbody>
              {conditions.map((row) => (
                <tr key={`${row.condition}-ops`}>
                  <td>{conditionLabel(row.condition)}</td>
                  <td>{formatPercent(row.run_level_timeout_rate)}</td>
                  <td>{formatPercent(row.run_level_no_artifact_rate)}</td>
                  <td>{formatPercent(row.run_level_judge_error_rate)}</td>
                  <td>{formatPercent(row.avg_tool_calls_per_run)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Library summary</h2>
          <p>Completed-only fields require at least one successful run for the row and condition.</p>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Library</th>
                <th>Tasks</th>
                <th>No retrieval</th>
                <th>Nia</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              {libraries.map((library) => (
                <tr key={library.library}>
                  <td>{library.library}</td>
                  <td>{library.tasks}</td>
                  <td>
                    {formatCompletedOnlyPercent(
                      library.by_condition.no_retrieval_agent.completed_only_avg_quality_pct,
                    )}
                  </td>
                  <td>
                    {formatCompletedOnlyPercent(
                      library.by_condition.nia_agent.completed_only_avg_quality_pct,
                    )}
                  </td>
                  <td className={completedOnlyDeltaClass(library.delta_completed_only_pct)}>
                    {formatCompletedOnlyDelta(library.delta_completed_only_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="panel">
          <h2>Task summary</h2>
          <p>Rows without successful runs still count in crash-aware metrics above.</p>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Task</th>
                <th>Difficulty</th>
                <th>No retrieval</th>
                <th>Nia</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.task_id}>
                  <td>{task.task_id}</td>
                  <td>{task.difficulty}</td>
                  <td>
                    {formatCompletedOnlyPercent(
                      task.by_condition.no_retrieval_agent.completed_only_avg_quality_pct,
                    )}
                  </td>
                  <td>
                    {formatCompletedOnlyPercent(task.by_condition.nia_agent.completed_only_avg_quality_pct)}
                  </td>
                  <td className={completedOnlyDeltaClass(task.delta_completed_only_pct)}>
                    {formatCompletedOnlyDelta(task.delta_completed_only_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>
    </>
  );
}

function safeLoadAgentScores(): AgentScoresFile | null {
  try {
    return loadAgentScores();
  } catch {
    return null;
  }
}
