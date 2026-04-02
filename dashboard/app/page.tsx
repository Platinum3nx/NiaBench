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

  return (
    <>
      <section className="hero">
        <div>
          <p className="eyebrow">Benchmark for context retrieval</p>
          <h1>NiaBench</h1>
        </div>
        <p className="hero-copy">
          NiaBench measures how much frontier coding models improve when they get fresh,
          indexed documentation context instead of relying on stale training knowledge.
        </p>
        <div className="stats">
          <article className="stat-card">
            <p>Without Nia</p>
            <strong>{formatPercent(summary.overall_without_nia)}</strong>
          </article>
          <article className="stat-card">
            <p>With Nia</p>
            <strong>{formatPercent(summary.overall_with_nia)}</strong>
          </article>
          <article className="stat-card">
            <p>Delta</p>
            <strong>{formatPercent(summary.improvement_delta_pct)}</strong>
          </article>
          <article className="stat-card">
            <p>Evaluations / Libraries</p>
            <strong>
              {evaluationsCount} / {summary.libraries_covered}
            </strong>
            <p>
              ({uniqueTasks} unique tasks x {modelCount} models)
            </p>
          </article>
        </div>

        <div className="stats">
          <article className="stat-card">
            <p>Non-perfect baseline</p>
            <strong>
              {formatPercent(summary.nonperfect_baseline_without_nia)} -&gt;{" "}
              {formatPercent(summary.nonperfect_baseline_with_nia)}
            </strong>
            <p>Baseline scored below rubric maximum</p>
            <p>
              {summary.nonperfect_baseline_count} of {evaluationsCount} evaluations
            </p>
            <p>
              Delta:{" "}
              <span className={deltaClass(summary.nonperfect_baseline_delta_pct)}>
                {formatSignedPercent(summary.nonperfect_baseline_delta_pct)}
              </span>
            </p>
          </article>

          <article className="stat-card">
            <p>Perfect baseline</p>
            <strong>
              {formatPercent(summary.perfect_baseline_without_nia)} -&gt;{" "}
              {formatPercent(summary.perfect_baseline_with_nia)}
            </strong>
            <p>Baseline scored rubric maximum</p>
            <p>
              {summary.perfect_baseline_count} of {evaluationsCount} evaluations
            </p>
            <p>
              Delta:{" "}
              <span className={deltaClass(summary.perfect_baseline_delta_pct)}>
                {formatSignedPercent(summary.perfect_baseline_delta_pct)}
              </span>
            </p>
          </article>
        </div>

        <div className="callout">
          The overall delta ({formatSignedPercent(summary.improvement_delta_pct)}) blends two
          evaluation populations. In {summary.perfect_baseline_count} evaluations, the baseline
          scored the rubric maximum (2/2) and the average delta with context was{" "}
          <span className={deltaClass(summary.perfect_baseline_delta_pct)}>
            {formatSignedPercent(summary.perfect_baseline_delta_pct)}
          </span>
          . In {summary.nonperfect_baseline_count} evaluations where baseline was below maximum,
          the average delta with context was{" "}
          <span className={deltaClass(summary.nonperfect_baseline_delta_pct)}>
            {formatSignedPercent(summary.nonperfect_baseline_delta_pct)}
          </span>
          . This is a descriptive split on observed baseline score, not a direct measure of model
          knowledge. Because {uniqueTasks} unique tasks are evaluated across {modelCount} models (
          {evaluationsCount} evaluations total), the same task can appear in different segments.
        </div>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h2>Library leaderboard</h2>
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Library</th>
                <th>Tasks</th>
                <th>Without</th>
                <th>With</th>
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
                    <td>{formatPercent(library.without_nia)}</td>
                    <td>{formatPercent(library.with_nia)}</td>
                    <td
                      className={
                        library.delta_pct === null
                          ? ""
                          : library.delta_pct >= 0
                            ? "delta-positive"
                            : "delta-negative"
                      }
                    >
                      {formatPercent(library.delta_pct)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </article>

        <article className="panel">
          <h2>Method</h2>
          <p>
            Each task is run twice with identical model parameters: once without external
            context and once with a clearly labeled block of current documentation chunks
            retrieved directly from Nia&apos;s search and index APIs.
          </p>
          <p>
            Raw prompts, retrieved context, and model outputs are all written to disk so the
            evaluation is auditable rather than purely anecdotal.
          </p>
          <div className="callout">
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
