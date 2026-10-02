# Backtesting Strategy

Backtesting replays history in publication order. For each video, the system reconstructs the dataset exactly as known immediately before publication, creates a forecast, and compares it only with later observations. This prevents future imports, final totals, and later creative labels from leaking backward.

Reports are segmented by platform, horizon, model version, series, and confidence. Backtests retain failed and low-confidence cases. No model is promoted from an in-sample score.

