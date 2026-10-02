# Calibration Strategy

Reliability is measured by predicted-probability buckets against observed frequency. Brier score evaluates band and trajectory distributions. Prediction-interval coverage is compared with its nominal 50% and 80% levels.

With small samples, probabilities shrink toward empirical platform priors and confidence remains low. Recalibration is fitted only on historical training windows and evaluated on later windows. Calibration tables must include sample size; empty buckets are omitted rather than invented.

