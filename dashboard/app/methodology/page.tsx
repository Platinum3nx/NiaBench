export default function MethodologyPage() {
  return (
    <section className="page">
      <p className="eyebrow">Methodology</p>
      <h1>Reproducible by design</h1>
      <article className="panel">
        <h2>Dataset</h2>
        <p>
          The benchmark dataset targets fast-moving libraries where stale training data causes
          confident but outdated code generation. Every task records both the deprecated pattern
          and the correct current pattern.
        </p>
      </article>
      <article className="panel">
        <h2>Harness</h2>
        <p>
          Baseline and treatment runs use identical model settings. The only variable is the
          presence of Nia-retrieved documentation context, injected into the system prompt as an
          auditable block.
        </p>
      </article>
      <article className="panel">
        <h2>Grading</h2>
        <p>
          Current sprint scoring is judge-only. All tasks are reviewed by a rubric-aware judge
          step, and sandbox execution is explicitly deferred to the next integration phase.
        </p>
      </article>
      <article className="panel">
        <h2>Limitations</h2>
        <p>
          NiaBench measures context quality impact, not provider latency, pricing, or model-vs-model
          supremacy. Result files keep both successful and unsuccessful runs so reruns stay auditable.
        </p>
      </article>
    </section>
  );
}
