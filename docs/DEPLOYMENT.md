# Deployment and Launch Readiness

Last updated: Thursday, April 2, 2026 early morning ET

## Canonical Launch Artifacts

- Locked pilot tasks: `dataset/tasks.json` (`30` validator-passing tasks)
- Canonical aggregate input: `results/raw_curated/combined`
- Published aggregate output: `results/scores.json`
- Dashboard build target: `dashboard/` (Next.js static prerender)

Founder-facing aggregation command:

```bash
python3 scripts/aggregate.py --input results/raw_curated/combined --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

## Deployment Target

- Platform: Vercel
- Project: `rare-tech/dashboard`
- Working directory: `dashboard`
- Deploy path: prebuilt artifact deployment from `.vercel/output`

Commands:

```bash
npx vercel pull --yes --environment preview --cwd dashboard
npx vercel build --yes --prod --cwd dashboard
npx vercel deploy --prebuilt --prod --yes --cwd dashboard
```

Latest deployment evidence:

- Deployment ID: `dpl_69ZpJ56bM3WFq58Wtawh2ubPzRQJ`
- Inspector URL: `https://vercel.com/rare-tech/dashboard/69ZpJ56bM3WFq58Wtawh2ubPzRQJ`
- Deployment URL: `https://dashboard-46i21bqj1-rare-tech.vercel.app`
- Alias: `https://dashboard-rare-tech.vercel.app`
- `vercel inspect` status: `Ready`
- Access note: deployment protection is disabled (`ssoProtection: null` on project config) and both deployment URL and alias return `HTTP 200`.

## Final Validation Trio (Launch-Safe Pass)

```bash
python3 scripts/validate_tasks.py dataset/tasks.json
python3 scripts/validate_scores.py results/scores.json
cd dashboard && npm run build
```

Expected result: all commands exit `0` with no contract or build errors.

## Scope Statement For This Release

- This is the first credible public benchmark build.
- Scoring is intentionally judge-only for this sprint slice.
- Sandbox-backed scoring is deferred and should be added in the next integration phase.
- The full `dataset/tasks_raw.json` OpenClaw corpus is retained as provenance and expansion material, not a blocker for this launch artifact.
