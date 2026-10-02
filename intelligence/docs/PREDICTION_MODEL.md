# Prediction Model

Pre-publish forecasts may use only information available at `knowledgeCutoff`. Live forecasts are a separate model family and evaluation cohort.

Post-publish platform states, including Reach Further, are forbidden in pre-publish features. A live forecast may use the state only when its first-observed timestamp is at or before that forecast's knowledge cutoff. See [REACH_FURTHER_ANALYSIS.md](REACH_FURTHER_ANALYSIS.md).

The cold-start model deliberately returns no fabricated expected view count. It emits uniform band and trajectory priors, low confidence, sample size zero, and explicit uncertainty reasons. Training is refused below 30 completed historical rows.

Target horizons are 30m, 1h, 2h, 3h, 6h, 12h, 24h, 48h, and 7d. Each target supports expected value, 50% and 80% intervals, performance-band probabilities, and trajectory probabilities.

The progression is platform median, grouped medians, regularized models, then hierarchical or boosted models only when temporal validation justifies added complexity.
