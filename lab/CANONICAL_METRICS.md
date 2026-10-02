# Canonical Metrics

Canonical observations support nullable views, reach, unique viewers, 3-second views, 15-second views, average/total watch seconds, likes, comments, shares, saves, follows, recommendation percentages, follower/non-follower percentages, and country distribution.

Metric semantics are `DAILY_INCREMENT`, `CUMULATIVE`, `SNAPSHOT`, or `UNKNOWN`. `Views`, `plays`, `reach`, and short-view metrics are not interchangeable. A missing metric stays `NULL`; it is never inferred from another metric.

Ratios and velocities live in the derived layer. Their denominator and source checkpoint must be inspectable.

