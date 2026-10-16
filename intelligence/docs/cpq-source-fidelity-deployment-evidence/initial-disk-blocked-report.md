# Source fidelity corrected-deployment / real retry report

16 October 2026. **Stopped at the pre-deployment disk-safety gate.** No build, deployment, new pilot, authorization, inference or cleanup was performed.

| Required status | Actual result |
| --- | --- |
| DEPLOYMENT | BLOCKED |
| LIVE_REASONING_CONFIGURATION | NOT_VERIFIED — corrected code not deployed |
| MIMI_BINDINGS | BLOCKED for this execution gate; last offline/preflight verification remains preserved |
| OWNER_AUTH | BLOCKED for post-deployment acceptance; helper confirms existing configuration/private permissions |
| NEW_SOURCE_AUTHORIZATION | PENDING |
| REAL_SOURCE_FIDELITY | NOT_EXECUTED |
| CRITIC_A | NOT_EXECUTED |
| CRITIC_B | NOT_EXECUTED |
| REAL_DISPATCH | DISABLED |
| CPQ_GRADING | INACTIVE |
| REAL_B_TO_A_ACCEPTANCE | NOT_VERIFIED |

## Disk safety and exact stopping reason

macOS has approximately **3.3 GiB free**; Docker's internal filesystem has **48.8 GiB free**. VM free blocks do not imply the host has space for Docker.raw growth. Docker.raw occupies approximately 67 GiB on the host and was not modified or deleted.

The ML Dockerfile copies application code before `pip install --no-cache-dir .`. Therefore this source correction invalidates the install layer even though pyproject.toml did not change. The existing install layer is 636 MB; the ML image totals 1,197,286,860 bytes. Backend image size is 421,344,139 bytes with an 89.1 MB application JAR layer. Source contexts are about 3.4 MiB ML and 4.7 MiB backend.

A planning allowance must include installed dependencies, temporary wheel/extraction data, image export/cache staging, backend package/runtime layers and possible moving-base-tag cache misses. A conservative incremental build/staging estimate is roughly **2.5–4 GiB**, with additional operating reserve needed. This is an estimate from existing layer sizes, not a measured successful-build peak or a guaranteed upper bound. **3.3 GiB cannot cover the upper part of that range plus reserve.** The practical minimum proposed before attempting this deployment is **5 GiB available host space**, then recheck immediately before the build. A larger 10–15 GiB operating margin remains preferable when practical.

The user instruction explicitly says: “If disk headroom is insufficient, STOP.” Accordingly no risky build was started and no disk-safety PASS was fabricated. Prior disk readiness applied to bounded no-build preflight, not this ML dependency reinstall.

## Current running services and preserved images

Backend, ML, PostgreSQL and render service report healthy; frontend is running. Frontend has no Docker container healthcheck in the current compose configuration. Flyway remains V65 successful.

| Service | Current pre-deployment image ID |
| --- | --- |
| backend | `sha256:32888e142e59a3e67d1c798e4f6d21aad5289939ea91a3500d887c7fafdfbb87` |
| ML | `sha256:734e76e603c5542e1c4d7d2018b4ad89bceb4c260d65e7b1e8795beb2f0da243` |
| frontend | `sha256:d5191a437f0a7917324a10f8459279a72b79d9655fd196b904cb958b8b8c00c5` |

These are unchanged old running images, not newly deployed identities. Live low reasoning, new authorization binding and new failure-accounting behavior have not passed post-deployment acceptance because deployment has not occurred. No frontend rebuild was started.

## Concrete cleanup proposal — approval required; nothing deleted

The smallest plausible cache-only proposal found is **20 individual reclaimable, non-shared Maven compile cache records**, about 1.894 GB (1.764 GiB) reported by BuildKit. Their descriptions match the current backend Dockerfile's `mvn -q -Dmaven.test.skip=true package` step. They are generated compilation snapshots, not database volumes or provider evidence. Removing them would require recompilation if those old cache entries are needed again. Current runtime images/containers are separate and must be preserved.

Only the exact IDs listed below would be in scope after explicit approval. No broad prune, image deletion, volume deletion, Docker.raw operation, backup deletion or unknown user-file removal is proposed. Revalidate each record's reclaimability immediately before any approved targeted operation.

**Important:** BuildKit's reclaimed byte count is VM/storage-cache accounting. An immediate equal increase in macOS `df` free space is not guaranteed. Cleanup would be followed by a fresh host `df` check; if the host still has less than the required margin, deployment remains blocked.

| Exact BuildKit cache resource ID | Reported size | Last used |
| --- | --- | --- |
| `uf8u36380uhepwi7dtewzbmpp` | 94.54MB | 2 days ago |
| `b7z7jiws9z9qwjk9ma2593he0` | 94.54MB | 2 days ago |
| `p8jc44bshx6whvme1utmuzbzt` | 94.54MB | 2 days ago |
| `v8fx49ghlowfu437dh7zh7v8z` | 94.58MB | 2 days ago |
| `pii1xors1srpqwm7yrr5lelz8` | 94.58MB | 2 days ago |
| `xzt7pdsum6ffeektgn6ivxhdi` | 94.6MB | 2 days ago |
| `b9hum25r6tzkt81u6o4bzd5yw` | 94.6MB | 2 days ago |
| `wjlr6vn0z541fmed50d4i51kp` | 94.6MB | 2 days ago |
| `yx7gxy8ruz9cndigst329f4tg` | 94.6MB | 2 days ago |
| `absyy3jcgqs14jw2qpulokzah` | 94.61MB | 2 days ago |
| `kbp5fouxck0mtmhztbz66ogo5` | 94.61MB | 2 days ago |
| `lzpsn8os04bex8tvhhpkmq8y7` | 94.61MB | 2 days ago |
| `zh797bpdff0obqkto1z594tcx` | 94.88MB | 4 days ago |
| `uonenj360ox3ra45ay9t8sfv1` | 94.88MB | 4 days ago |
| `u0nl2yut8dqro8mqxnyyufg0q` | 94.88MB | 4 days ago |
| `jciy3btkww7g6bgpcm5zb3wsg` | 94.88MB | 4 days ago |
| `tqsrumub7jqxroaygfrv3bfwe` | 94.88MB | 4 days ago |
| `bt6ml4sjggzl29deti58tde97` | 94.95MB | 4 days ago |
| `sin7rhimin4lrnon6h83h95a6` | 94.95MB | 4 days ago |
| `g49olm0uq4l1gudijdf73cu3n` | 94.96MB | 4 days ago |

Other concrete project-generated outputs, all unmodified:

| Exact path relative to repository root | Size | Recovery / recommendation |
| --- | ---: | --- |
| intelligence/frontend/.angular | 26 MiB | Reproducible cache; too small to resolve the gap alone |
| intelligence/frontend/dist | 25 MiB | Rebuildable output; too small alone |
| intelligence/backend/target | 14 MiB | Includes test evidence; preserve reports; not recommended for this gap |
| intelligence/frontend/node_modules | 384 MiB | Reinstall from package lock required; removes useful development dependencies |
| intelligence/ml-service/.venv | 711 MiB | Reinstall Python environment required; preserve current test tooling |
| intelligence/creative-render-service/target | 75 MiB | Rebuild required; unaffected service, preserve |
| /tmp/cpq-output-tokenizer | 6.7 MiB | Disposable sizing tool; too small to matter |

Deleting development environments is not proposed as the first action. No deletion has occurred.

## Owner, source and production integrity

`setup-cpq-owner.sh --check` confirms owner authentication configured=True, credential exists=True and owner-only permissions=True. It performed no login, deployment or inference. No secret was read for these diagnostics or placed in a report.

Both backend and ML runtime environment flags remain false. Database inspection still shows exactly one FAILED_OR_AMBIGUOUS machine request. The entire prior failed request row was compared with its saved archive and is unchanged. Historical events remain 75 with payload digest `6b270d6f3ed3646ef1dcbab8692de0c44d9f52d1302c813be4d8215fd14ee3d8`.

Previous pilot `2485b1a4-a011-4456-aae6-a37badd98245` and source request `3a55b29a-48c6-44c0-a003-da11af0f7069` were not reused. No new pilot/request/provider ID exists for this task. There is no new token usage, visible output, finish reason, JSON result, citation result, semantic judgment or cost to report. No fabricated zero-cost successful review is inferred.

The previously verified original/three-candidate bindings, story, Ruleset 1.11 score 88.40625/B and production settings remain the intended future scope. This task stopped before the fresh post-deployment binding/runtime verification; prior success is not relabeled as current acceptance.

## Next exact action and authorization boundary

1. Obtain specific approval for the **20 cache IDs above**, or have the operator independently restore host free space to at least 5 GiB without touching protected data. The target is a conservative deployment planning margin, not a universal platform requirement.
2. After any approved cleanup, measure actual host free space; continue only if disk safety is supported by the result.
3. Use the official `./intelligence/scripts/deploy.sh ml-service backend` mechanism with the existing owner configuration preserved and CPQ_PILOT_REAL_ENABLED=false. It restarts frontend nginx without rebuilding its image.
4. Verify the running image changes, source-specific low capability, unchanged critics, authentication/security, V65, hashes and historical records.
5. Only after all those checks pass, request fresh explicit approval for **one** OpenAI/gpt-6.1-sol SOURCE_FIDELITY inference: reasoning_effort=low, strict json_schema, 4,000 completion tokens, $0.30 maximum, no retries/fallback/critics. The current attachment and the earlier experiment's “yes” are not this new financial authorization.

The two critics are not yet eligible for a new execution authorization: the fresh source review has not been performed. No architecture, score, story, candidate, grading, approval, render, publishing, commit or push change occurred.

Evidence: `cpq-source-fidelity-deployment-evidence/pre-deployment-state.json` and `proposed-reproducible-build-cache.json`.
