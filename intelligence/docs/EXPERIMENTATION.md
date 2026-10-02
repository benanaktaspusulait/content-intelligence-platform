# Experimentation

Every planned publication test should preregister one hypothesis, one primary metric, a platform, and the variable being changed. Types are `EXPLOIT`, `ADJACENT`, `EXPLORE`, and `CHARACTER_CONTROL_TEST`.

The default capacity allocation is 60/20/20 for exploit/adjacent/explore. Character allocation should trend toward 70% established, 20% limited-data, and 10% new or untested. These are planning constraints, not model labels.

Avoid changing hook, duration, CTA, and character simultaneously. Intervention events such as paid promotion or coordinated engagement must be timestamped so later analysis can exclude or stratify affected observations.

`GET /api/v1/test-planner` reports the current allocation and coverage gaps. `POST /api/v1/experiments` records the preregistration.
