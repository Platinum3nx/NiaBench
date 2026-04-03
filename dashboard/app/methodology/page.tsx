export default function MethodologyPage() {
  return (
    <section className="page">
      <p className="eyebrow">Methodology</p>
      <h1>NiaBench Methodology</h1>
      <p className="hero-copy">
        Our evaluation framework is designed for maximum transparency and reproducibility. We employ a rigorous, layered protocol to measure the exact impact of fresh context retrieval on foundation models, isolating variables to ensure highly accurate, auditable capability assessments.
      </p>

      <article className="panel">
        <h2>1. Dataset Construction</h2>
        <h3>Quick Read</h3>
        <p className="method-brief">
          NiaBench focuses on version-sensitive library tasks where stale model knowledge is likely
          to fail.
        </p>
        <h3>Detailed Explanation</h3>
        <p>
          Tasks are built around concrete migration or version-boundary breakpoints, such as
          renamed methods, removed options, changed API shapes, or deprecated patterns that still
          look plausible. Each task includes enough structure to evaluate correctness against the
          current documentation rather than style preference.
        </p>
        <p>
          This design avoids generic coding trivia and concentrates the benchmark on the core
          hypothesis: context retrieval is most useful when the model needs fresh, factual library
          information that may not be reliably represented in pretraining.
        </p>
      </article>

      <article className="panel">
        <h2>2. Evaluation Protocol</h2>
        <h3>Quick Read</h3>
        <p className="method-brief">
          Every evaluation runs twice with the same model/runtime settings, and the treatment run
          adds retrieved Nia context to the system prompt.
        </p>
        <h3>Detailed Explanation</h3>
        <p>
          The benchmark isolates one variable: whether retrieved documentation is injected. Model
          provider, model ID, prompts, and runtime settings are kept fixed between baseline and
          treatment for each task/model pair. This helps attribute differences to context rather
          than unrelated parameter drift.
        </p>
        <p>
          Because each task is evaluated across multiple models, a single task can land in
          different score segments depending on model behavior. Segment analysis is therefore
          evaluation-level, not task-level.
        </p>
      </article>

      <article className="panel">
        <h2>3. Retrieval and Prompting</h2>
        <h3>Quick Read</h3>
        <p className="method-brief">
          Retrieved context is explicitly labeled in the prompt and logged so results are auditable.
        </p>
        <h3>Detailed Explanation</h3>
        <p>
          Treatment prompts include a clearly separated documentation block sourced from Nia
          retrieval. The benchmark records what was retrieved and what was sent to the model so
          readers can audit whether retrieval was relevant, noisy, truncated, or version-misaligned.
        </p>
        <p>
          This transparency is critical for diagnosing negative deltas. If context hurts a run, the
          artifact trail makes it possible to inspect whether the issue came from retrieval quality,
          context selection, or model interpretation.
        </p>
      </article>

      <article className="panel">
        <h2>4. Scoring and Segmentation</h2>
        <h3>Quick Read</h3>
        <p className="method-brief">
          Scores are shown by segment (non-perfect baseline vs perfect baseline) because blended
          deltas can hide opposite dynamics.
        </p>
        <h3>Detailed Explanation</h3>
        <p>
          The dashboard reports both segment deltas: evaluations where baseline scored below the
          rubric maximum, and evaluations where baseline already scored the maximum. This prevents
          the benchmark from over-indexing on a single aggregate number that mixes groups with
          different headroom.
        </p>
        <p>
          Segment labels are descriptive, not causal. A perfect baseline score does not prove full
          model knowledge, and a non-perfect baseline score does not prove total ignorance. The
          split is a practical readout of observed behavior under the rubric.
        </p>
      </article>

      <article className="panel">
        <h2>5. Grading and Reliability</h2>
        <h3>Quick Read</h3>
        <p className="method-brief">
          Current scoring is judge-only for this sprint, with strict output validation and
          reproducible artifacts.
        </p>
        <h3>Detailed Explanation</h3>
        <p>
          Judge outputs are normalized into structured scores so aggregation is deterministic and
          contract-validated before rendering. The benchmark uses explicit schema checks for task
          files and score files to reduce silent data drift.
        </p>
        <p>
          Sandbox execution remains a deferred integration point in the current sprint scope. This
          limitation is documented so readers understand exactly what the current results represent
          and what they do not represent yet.
        </p>
      </article>

      <article className="panel">
        <h2>6. Limitations and Interpretation</h2>
        <h3>Quick Read</h3>
        <p className="method-brief">
          NiaBench measures context impact for version-sensitive tasks, not general coding ability
          or provider ranking.
        </p>
        <h3>Detailed Explanation</h3>
        <p>
          Results should be interpreted as evidence about retrieval-conditioned performance in this
          benchmark design. They are not direct claims about model intelligence, cost efficiency, or
          production latency.
        </p>
        <p>
          The benchmark intentionally preserves successful and unsuccessful runs for post-hoc
          inspection. That auditability lets readers challenge, reproduce, or refine conclusions as
          the benchmark evolves.
        </p>
      </article>
    </section>
  );
}
