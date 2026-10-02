# Model Evaluation

Evaluation is platform- and horizon-specific. Report median absolute error, median absolute log error, interval coverage, band accuracy, trajectory accuracy, and Brier score for categorical probabilities. Always show sample size and evaluation window.

Champion/challenger comparisons use the same time-based holdout. A lower point error does not compensate for badly calibrated intervals. Promotion is explicit and audited; importing a file never silently promotes a model.

