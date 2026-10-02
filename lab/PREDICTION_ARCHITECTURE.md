# Prediction Architecture

Two modes are distinct:

- `PRE_PUBLISH`: only information available before publication.
- `EARLY_LIVE`: may include observations up to an explicit knowledge cutoff.

Every forecast stores video/variant/platform, model version, feature version, dataset snapshot, creative fingerprint snapshot, planned publish time, creation time, knowledge cutoff, comparable sample size, confidence, intervals, band probabilities, trajectory probabilities, factors, and uncertainty reasons.

Once `locked_at` is set, database triggers reject updates, deletes, and child-table changes. A later forecast is a new record. Original pre-publish accuracy always uses the original locked record.

