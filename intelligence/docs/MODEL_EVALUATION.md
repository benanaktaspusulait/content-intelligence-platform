# Model Evaluation

Evaluation is temporal and platform-specific. Use expanding-window backtests so future observations cannot leak into training.

Report MAE, median absolute error, log1p MAE/RMSE, band accuracy, balanced accuracy, macro F1, Brier score, log loss, interval coverage, and trajectory accuracy by platform and horizon. Always compare against platform median, series median, character median, and creative-neighbour baselines.

A training output starts as `CHALLENGER`. Promotion requires sufficient sample size, no material calibration regression, and improvement over the champion and simple baselines. Promotion is an audited human action.

Prediction audits remain separate from immutable prediction payloads. Unexpected wins and failures should become research candidates, not silent training labels.
