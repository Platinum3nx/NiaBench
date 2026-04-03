# Deployment and Release Readiness

## 1. Canonical Artifacts

Use this artifact set for Layer 1 release and reruns:

- Tasks: `dataset/tasks.json`
- Aggregate input: `results/raw_curated/combined`
- Aggregate output: `results/scores.json`
- Dashboard app: `dashboard/`

Regenerate and validate scores:

```bash
python3 scripts/aggregate.py --input results/raw_curated/combined --output results/scores.json
python3 scripts/validate_scores.py results/scores.json
```

## 2. Dashboard Build Validation

Run before any deployment:

```bash
python3 scripts/validate_tasks.py dataset/tasks.json
python3 scripts/validate_scores.py results/scores.json
cd dashboard
npm install
npm run lint
npm run build
```

Expected result: all commands exit `0` with no validation or build errors.

## 3. Vercel Deployment (Example)

If you deploy with Vercel, target the `dashboard/` directory:

```bash
npx vercel pull --yes --environment preview --cwd dashboard
npx vercel build --yes --prod --cwd dashboard
npx vercel deploy --prebuilt --prod --yes --cwd dashboard
```

After deploy, verify that the configured preview/production URL returns `HTTP 200`.

## 4. Release Scope Notes

- Layer 1 scoring is judge-only.
- Sandbox-backed scoring is deferred to a later layer.
- The larger raw task corpus is retained for future expansion, but the release artifact set above is the source of truth for current published metrics.
