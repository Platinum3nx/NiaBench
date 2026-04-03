# Layer 2 Regression Checklist

Run these checks before treating Layer 2 output as launch-track:

```bash
python3 scripts/check_layer2_boundaries.py
python3 scripts/validate_scores.py results/scores.json
cd dashboard && npm run build
```

Layer 1 is considered protected only when all commands above pass.
