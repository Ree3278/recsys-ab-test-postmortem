# A/B Test Evaluation of a Recommendation Engine (Simulated)

> **All data in this repo is synthetic.** Effect sizes (novelty decay, segment lifts,
> exposure concentration) are parameters set in `src/ab_rec_eval/simulate.py`.
> The point of the project is the analysis pipeline: it should recover the planted effects
> and flag the planted problems (SRM, novelty, heterogeneity, long-tail concentration).

## Quick start

```bash
uv sync
uv run pytest
uv run python -m ab_rec_eval.simulate data/raw   # writes parquet files
uv run python -m ab_rec_eval.analysis            # -> reports/results.json
uv run python -m ab_rec_eval.validate 1000       # A/A + CI coverage -> reports/validation.json
uv run python -m ab_rec_eval.site                # charts + index -> site/ (open site/index.html)
```

## What's inside

| Module | Purpose |
|---|---|
| `simulate.py` | Synthetic users / daily GMV / SKU exposure, with optional SRM injection |
| `analysis.py` | Overall / subgroup (BH-adjusted) / cumulative / daily / early-vs-late window, SRM, Gini, sizing |
| `validate.py` | Repeated-simulation checks: A/A false-positive rate, CI coverage of the known planted lift |
| `site.py` | Narrative `index.html` that embeds the charts and pulls its numbers from the results files |
| `charts.py` | Four interactive Plotly pages (novelty, heterogeneity, long tail, SRM) with light/dark themes and data tables |
| `stats.py` | SRM chi-square, Welch t-test (+delta-method relative lift CI), CUPED, sample size / MDE, Lorenz & Gini, BH/Bonferroni |

## Methodological notes
- Decision uses the pre-registered 14-day window only; the cumulative CI plot is a diagnostic (peeking inflates false positives).
- Power is computed *before* the experiment (sample size / MDE), not post hoc.
- Subgroup effects are exploratory and corrected for multiple comparisons.

## Current findings (simulated, seed 42, 200k users)
- 14-day GMV lift +7.5% (CUPED), but days 1–3 average +17.7% vs days 8–14 +2.7%: most of the headline is novelty.
- Heterogeneity: high-activity returning +15%, new users −4.6% (BH-adjusted p=0.02).
- Impression Gini 0.68 → 0.81; top 1% of SKUs take 34% → 52% of impressions.
- Injected logging loss (8% of Android treatment users) trips SRM (p≈2e-12) and localizes to Android.
- CUPED cuts variance ~27%; new users have no pre-period, so it does nothing for them.

## Publish on GitHub Pages
1. Create a GitHub repo and push `main`.
2. Settings → Pages → Source: **GitHub Actions**. The `Deploy site` workflow publishes `site/`.
3. Set `REPO_URL` in `src/ab_rec_eval/site.py`, rebuild with the command above, commit `site/`.

Regenerate everything from scratch: `simulate` → `analysis` → `validate` → `site`.
