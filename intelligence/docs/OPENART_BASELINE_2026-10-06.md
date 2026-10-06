# OpenArt Integration Baseline — 2026-10-06

## Checkpoint

- Baseline commit: `4f76ac6` (`chore: checkpoint OpenArt integration`)
- Branch: `master`
- Unrelated user/generated working-tree changes were not staged or modified.

## Validation results

### Backend reactor tests

Command:

```bash
mvn -B -ntp -pl backend,creative-render-service test
```

Result: **FAILURE — pre-existing/unrelated repository failures.**

- Backend test run reached 129 tests before failure: 5 failures, 4 errors.
- Main reported failures include `PlatformIntegrationTest`, `AnalysisJobServiceIdempotencyTest`, `VideoControllerAnalysisTest`, and `RuleGovernanceServiceTest`.
- The failure output includes PostgreSQL/schema/test-fixture issues such as `intervention_events` SQL syntax, existing analysis idempotency expectations, and unrelated strict-stubbing failures.

The render-service module was also run separately:

```bash
mvn -B -ntp -pl creative-render-service test
```

Result: **FAILURE — 328 tests, 1 failure, 12 errors**, primarily existing PostgreSQL JSONB/entity-fixture and legacy migration issues plus `TemporalBeatAlignmentServiceTest`.

### Java package

Command:

```bash
mvn -B -ntp -pl backend,creative-render-service -DskipTests package
```

Result: **BUILD SUCCESS**.

### Frontend production build

Command:

```bash
CI=1 NG_CLI_ANALYTICS=false npm run build -- --configuration production
```

Result: **BUILD SUCCESS** with existing Angular bundle/style budget warnings.

### OpenArt-focused checkpoint

The currently implemented OpenArt-focused suite was green before this baseline was recorded, including the real CLI fixture, reference resolver, submission safety, credit tracking, upscale runner, asset registration, and render orchestration tests.

## Interpretation

The OpenArt code checkpoint packages successfully and the frontend production bundle builds. The full repository test gate is not green at baseline because failures are outside the OpenArt changes and were present in unrelated backend/render persistence fixtures. Those failures must remain visible and are not silently reclassified as OpenArt passes.
