# NiaBench Dashboard

Next.js dashboard for the current NiaBench launch artifact set.

## Data Source

- Reads committed benchmark aggregate from `results/scores.json`
- Founder-facing aggregate must be regenerated from `results/raw_curated/combined`

## Local Build

```bash
cd dashboard
npm ci
npm run build
```

## Vercel Deploy Path

```bash
npx vercel pull --yes --environment preview --cwd dashboard
npx vercel build --yes --prod --cwd dashboard
npx vercel deploy --prebuilt --prod --yes --cwd dashboard
```
