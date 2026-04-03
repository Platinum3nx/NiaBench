import { loadAgentScores } from "@/lib/load-agent-scores";
import type { AgentScoresFile } from "@/lib/agent-types";

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return `${value.toFixed(1)}%`;
}

function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return value.toFixed(1);
}

function formatInt(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Pending";
  }
  return value.toString();
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

function mean(values: Array<number | null>): number | null {
  const filtered = values.filter((value): value is number => value !== null);
  if (filtered.length === 0) {
    return null;
  }
  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}

function delta(left: number | null, right: number | null): number | null {
  if (left === null || right === null) {
    return null;
  }
  return left - right;
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

function formatPairwiseOutcome(
  niaWins: number | null | undefined,
  ties: number | null | undefined,
  noRetrievalWins: number | null | undefined,
): string {
  if (
    niaWins === null ||
    niaWins === undefined ||
    ties === null ||
    ties === undefined ||
    noRetrievalWins === null ||
    noRetrievalWins === undefined
  ) {
    return "Pending";
  }
  return `${niaWins} / ${ties} / ${noRetrievalWins}`;
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
  const libraryCompletionDelta = new Map<string, number | null>(
    libraries.map((library) => {
      const libraryTasks = tasks.filter((task) => task.library === library.library);
      const noRetrievalCompletion = mean(
        libraryTasks.map((task) => task.by_condition.no_retrieval_agent.completion_rate),
      );
      const niaCompletion = mean(
        libraryTasks.map((task) => task.by_condition.nia_agent.completion_rate),
      );
      return [library.library, delta(niaCompletion, noRetrievalCompletion)];
    }),
  );

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
          Metrics stay isolated from the Layer 1 benchmark, and pairwise outcomes help disambiguate
          score ties from data gaps.
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
            <p>Avg Nia calls in Nia runs: {formatCount(summary.avg_nia_calls_per_nia_run)}</p>
          </article>
          <article className="stat-card">
            <p>Pairwise outcomes (W/T/L)</p>
            <strong>
              {formatPairwiseOutcome(
                summary.pairwise_nia_wins,
                summary.pairwise_ties,
                summary.pairwise_no_retrieval_wins,
              )}
            </strong>
            <p>Tie rate: {formatPercent(summary.pairwise_tie_rate)}</p>
          </article>
          <article className="stat-card">
            <p>Task deltas (Nia/Tie/Base)</p>
            <strong>
              {formatInt(summary.task_delta_nia_positive)} / {formatInt(summary.task_delta_ties)} /{" "}
              {formatInt(summary.task_delta_no_retrieval_positive)}
            </strong>
            <p>Across {summary.unique_tasks} tasks</p>
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
                <th>Retrieval error</th>
                <th>Workspace tool error</th>
                <th>Nia tool error runs</th>
                <th>Avg tool calls</th>
                <th>Avg tool errors</th>
              </tr>
            </thead>
            <tbody>
              {conditions.map((row) => (
                <tr key={`${row.condition}-ops`}>
                  <td>{conditionLabel(row.condition)}</td>
                  <td>{formatPercent(row.run_level_timeout_rate)}</td>
                  <td>{formatPercent(row.run_level_no_artifact_rate)}</td>
                  <td>{formatPercent(row.run_level_judge_error_rate)}</td>
                  <td>{formatPercent(row.run_level_retrieval_error_rate)}</td>
                  <td>{formatPercent(row.run_level_workspace_tool_error_rate)}</td>
                  <td>{formatPercent(row.run_level_nia_tool_error_rate)}</td>
                  <td>{formatCount(row.avg_tool_calls_per_run)}</td>
                  <td>{formatCount(row.avg_tool_error_calls_per_run)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Library summary</h2>
          <p>
            Completed-only ties are common with coarse pass/fail style outcomes, so crash-aware and
            completion-gap deltas provide additional signal.
          </p>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Library</th>
                <th>Tasks</th>
                <th>No retrieval quality</th>
                <th>Nia quality</th>
                <th>Completed-only delta</th>
                <th>Crash-aware delta</th>
                <th>Completion gap</th>
                <th>Pairwise W/T/L</th>
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
                  <td className={deltaClass(library.delta_crash_aware_pct)}>
                    {formatSignedPercent(library.delta_crash_aware_pct)}
                  </td>
                  <td className={deltaClass(libraryCompletionDelta.get(library.library) ?? null)}>
                    {formatSignedPercent(libraryCompletionDelta.get(library.library) ?? null)}
                  </td>
                  <td>
                    {formatPairwiseOutcome(
                      library.pairwise_nia_wins,
                      library.pairwise_ties,
                      library.pairwise_no_retrieval_wins,
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>

        <article className="panel">
          <h2>Task summary</h2>
          <p>
            Completed-only quality is preserved for comparability, while crash-aware delta and
            completion gap highlight operational differences between conditions.
          </p>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Task</th>
                <th>Difficulty</th>
                <th>No retrieval quality</th>
                <th>Nia quality</th>
                <th>Completed-only delta</th>
                <th>Crash-aware delta</th>
                <th>Completion gap</th>
                <th>Pairwise W/T/L</th>
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
                  <td className={deltaClass(task.delta_crash_aware_pct)}>
                    {formatSignedPercent(task.delta_crash_aware_pct)}
                  </td>
                  <td
                    className={deltaClass(
                      delta(
                        task.by_condition.nia_agent.completion_rate,
                        task.by_condition.no_retrieval_agent.completion_rate,
                      ),
                    )}
                  >
                    {formatSignedPercent(
                      delta(
                        task.by_condition.nia_agent.completion_rate,
                        task.by_condition.no_retrieval_agent.completion_rate,
                      ),
                    )}
                  </td>
                  <td>
                    {formatPairwiseOutcome(
                      task.pairwise_nia_wins,
                      task.pairwise_ties,
                      task.pairwise_no_retrieval_wins,
                    )}
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
