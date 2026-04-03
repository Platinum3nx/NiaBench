import { loadScores } from "@/lib/load-scores";

function formatPercent(value: number | null): string {
  if (value === null) {
    return "Pending";
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

function deltaClass(value: number | null): string {
  if (value === null) {
    return "";
  }
  return value >= 0 ? "delta-positive" : "delta-negative";
}

export default function HomePage() {
  const scores = loadScores();
  const { summary, libraries } = scores;
  const evaluationsCount = summary.evaluations_count;
  const uniqueTasks = summary.unique_tasks;
  const modelCount = summary.models_tested.length;
  const perfectSharePct =
    evaluationsCount > 0
      ? (summary.perfect_baseline_count / evaluationsCount) * 100
      : null;
  const nonperfectSharePct =
    evaluationsCount > 0
      ? (summary.nonperfect_baseline_count / evaluationsCount) * 100
      : null;

  return (
    <>
      <section className="hero animate-in">
        <div>
          <p className="eyebrow">Benchmark for context retrieval</p>
          <h1>NiaBench</h1>
        </div>
        <p className="hero-copy">
          NiaBench measures how much frontier coding models improve when they get fresh,
          indexed documentation context instead of relying on stale training knowledge.
        </p>
        <div className="hero-stat">
          <strong className={deltaClass(summary.nonperfect_baseline_delta_pct)}>
            {formatSignedPercent(summary.nonperfect_baseline_delta_pct)}
          </strong>
          <p>
            improvement when the baseline scored below the rubric maximum
            ({summary.nonperfect_baseline_count} of {evaluationsCount} evaluations,{" "}
            {formatPercent(summary.nonperfect_baseline_without_nia)} &rarr;{" "}
            {formatPercent(summary.nonperfect_baseline_with_nia)})
          </p>
        </div>

        <div className="stats">
          <article className="stat-card animate-in delay-1">
            <p>Segment composition</p>
            <strong className="metric-col">
              {summary.perfect_baseline_count} / {summary.nonperfect_baseline_count}
            </strong>
            <p>
              Perfect / non-perfect evaluations
            </p>
            <p>
              {formatPercent(perfectSharePct)} / {formatPercent(nonperfectSharePct)}
            </p>
          </article>
          <article className="stat-card animate-in delay-1" style={{ animationDelay: '0.15s' }}>
            <p>Perfect baseline delta</p>
            <strong className={`metric-col ${deltaClass(summary.perfect_baseline_delta_pct)}`}>
              {formatSignedPercent(summary.perfect_baseline_delta_pct)}
            </strong>
            <p>
              {formatPercent(summary.perfect_baseline_without_nia)} &rarr;{" "}
              {formatPercent(summary.perfect_baseline_with_nia)}
            </p>
            <p>
              {summary.perfect_baseline_count} of {evaluationsCount} evaluations
            </p>
          </article>
          <article className="stat-card animate-in delay-1" style={{ animationDelay: '0.2s' }}>
            <p>Evaluations / Libraries</p>
            <strong className="metric-col">
              {evaluationsCount} / {summary.libraries_covered}
            </strong>
            <p>
              ({uniqueTasks} tasks &times; {modelCount} models)
            </p>
          </article>
        </div>

        <div className="callout animate-in delay-2">
          Segment deltas should be interpreted separately. In{" "}
          {summary.nonperfect_baseline_count} evaluations where the baseline scored below the
          rubric maximum, context improved scores by{" "}
          <span className={deltaClass(summary.nonperfect_baseline_delta_pct)}>
            {formatSignedPercent(summary.nonperfect_baseline_delta_pct)}
          </span>
          . In {summary.perfect_baseline_count} evaluations where the baseline already scored
          the maximum (2/2), adding context changed scores by{" "}
          <span className={deltaClass(summary.perfect_baseline_delta_pct)}>
            {formatSignedPercent(summary.perfect_baseline_delta_pct)}
          </span>
          . This is a descriptive split on observed baseline score. Because {uniqueTasks} tasks
          are evaluated across {modelCount} models ({evaluationsCount} evaluations total), the
          same task can appear in different segments depending on the model. For completeness, the
          blended overall delta across all evaluations is{" "}
          <span className={deltaClass(summary.improvement_delta_pct)}>
            {formatSignedPercent(summary.improvement_delta_pct)}
          </span>
          .
        </div>
      </section>

      <section className="panel-grid">
        <article className="panel animate-in delay-2">
          <h2>Library leaderboard</h2>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Library</th>
                <th>Tasks</th>
                <th>Without Context</th>
                <th>With Context</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              {libraries.length === 0 ? (
                <tr>
                  <td colSpan={5}>Scores will appear here after the first full evaluation run.</td>
                </tr>
              ) : (
                libraries.map((library) => (
                  <tr key={library.id}>
                    <td>{library.label}</td>
                    <td>{library.tasks}</td>
                    
                    <td className="metric-col">
                      <div className="score-cell">
                        <span style={{ width: '45px', display: 'inline-block' }}>{formatPercent(library.without_nia)}</span>
                        <div className="score-bar-bg">
                           <div className="score-bar-fill" style={{ width: library.without_nia ? `${library.without_nia}%` : '0%', background: 'var(--muted)' }} />
                        </div>
                      </div>
                    </td>
                    
                    <td className="metric-col">
                      <div className="score-cell">
                        <span style={{ width: '45px', display: 'inline-block' }}>{formatPercent(library.with_nia)}</span>
                        <div className="score-bar-bg">
                           <div className="score-bar-fill" style={{ width: library.with_nia ? `${library.with_nia}%` : '0%' }} />
                        </div>
                      </div>
                    </td>

                    <td
                      className={`metric-col ${
                        library.delta_pct === null
                          ? ""
                          : library.delta_pct >= 0
                            ? "delta-positive"
                            : "delta-negative"
                      }`}
                    >
                      {formatSignedPercent(library.delta_pct)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </article>

        <article className="panel animate-in delay-2" style={{ animationDelay: '0.3s' }}>
          <h2>Method</h2>
          <p>
            Each task is run twice with the same model and runtime settings: once without
            external context and once with a clearly labeled block of current documentation
            chunks retrieved directly from Nia&apos;s search and index APIs.
          </p>
          <p>
            Raw prompts, retrieved context, and model outputs are all written to disk so the
            evaluation is auditable rather than purely anecdotal.
          </p>
          <div className="callout" style={{ marginTop: '24px' }}>
            Current status: this dashboard renders committed pilot scores from
            <code> results/scores.json</code> (generated from
            <code> results/raw_curated/combined</code>). Scoring for this sprint is judge-only
            while sandbox execution remains deferred.
          </div>
        </article>
      </section>
    </>
  );
}
