# Learning Algorithm

The first production model is intentionally interpretable. It uses platform- and horizon-specific historical baselines plus feature-neighbour evidence. Small samples shrink toward the platform baseline; wide empirical intervals expose uncertainty.

Training uses time-ordered data only. A dataset snapshot has an `as_of` cutoff, and no observation after that cutoff may enter its features or labels. Challengers are evaluated with walk-forward splits and cannot replace a champion until minimum sample, interval coverage, and error thresholds are met.

Manual creative weights are priors, not labels. Updates are regularised and gradual. Character, series, and creative-mechanism statistics are observational associations. The model must never report them as causal effects.

