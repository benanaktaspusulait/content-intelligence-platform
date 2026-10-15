# CPQ V1 — Original fidelity and calibration report

Date: 2026-10-15. Engineering implementation and backend deployment completed. Production human evidence acquisition remains pending.

| Independent flag | Result |
|---|---|
| ORIGINAL_FIDELITY_WORKFLOW | IMPLEMENTED_AND_VERIFIED |
| CALIBRATION_SOURCE_PREPARATION | PARTIALLY_READY |
| INDEPENDENT_REVIEW | AWAITING_AUTHORIZED_REVIEWERS |
| CPQ_GRADING | INACTIVE |
| REAL_B_TO_A_ACCEPTANCE | NOT_VERIFIED |

## Implementation and exact API contract

Extended the existing `CreativePromptQualityService` and controller, existing reviewer roles, fidelity ledger, calibration importer, blind judgments and readiness/preview flow. No second quality system or scoring engine was added. All routes below have prefix `/api/v1/intelligence/workflow`.

| Method and route | Required trusted role | Result |
|---|---|---|
| POST `/cpq/original-prompts/preflight` | EVIDENCE_REVIEWER or CREATIVE_QUALITY_ARCHITECTURE_APPROVER | Read-only resolution; all independent blockers, exact context, UNKNOWN; never persists approval |
| POST `/cpq/original-prompts/bindings` | CREATIVE_QUALITY_ARCHITECTURE_APPROVER | Immutable exact-scope original subject after authority checks |
| GET `/cpq/original-prompts/{subjectId}/fidelity-review` | EVIDENCE_REVIEWER | Exact story, prompt, settings and protected anchor checklist |
| POST same fidelity-review route | EVIDENCE_REVIEWER | Append-only PASS/FAIL/UNKNOWN with independent authenticated provenance |
| POST `/records/{analysisId}/comparisons/{comparisonId}/candidates/{candidateId}/fidelity-review` | EVIDENCE_REVIEWER | Existing candidate-bound review retained; cannot satisfy original scope |
| POST `/cpq/calibration/corpora/{version}` and `/examples` | CREATIVE_QUALITY_ARCHITECTURE_APPROVER | Existing governed corpus and qualified evidence import |
| GET `/cpq/calibration/examples/{exampleId}/blind-review` | CREATIVE_QUALITY_REVIEWER | Opaque ID, exact prompt, production context, rubric/method; no supervisor labels |
| POST `/cpq/calibration/examples/{exampleId}/judgments` | CREATIVE_QUALITY_REVIEWER | Immutable independent six-dimension judgment |
| GET `/cpq/calibration/corpora/{version}/readiness`; POST `/preview` | Existing readiness access; architecture approver for preview | Current qualified evidence, coverage, disagreement and diagnostic preview; no activation |

Preflight/binding selectors for a saved original: `contentId`, `promptVersionId`, `expectedPromptSha256`. Current persisted studio session supplies authoritative story/approval IDs, including the existing `storyRecordId` convention. Optional explicit IDs must match. Repository selectors: `repositoryRelativePath`, `expectedPromptSha256`, actual `storyId` and `approvalRecordId`. Library root is configured by `pompom.library-root`, deployed `/data/library`; paths must resolve inside it, with bounded valid UTF-8 contents and exact SHA-256. Absolute/traversal/symlink escapes and mismatches are rejected.

Settings resolve from the current saved `PRODUCTION_SETTINGS` event for saved versions. Repository sources require an exact source-identity/hash-bound settings event (`productionSettingsRecordId`), or an existing repository JSON document selected by `productionSettingsSourcePath` and `expectedSettingsSha256`. That document must contain `sourceIdentity`, `sourcePromptSha256`, and `productionSettings`. Binding additionally needs concrete `rationale` of at least 20 characters. Arbitrary inline client story/settings are not authority.

Settings require explicit non-AUTO/non-UNKNOWN `contentProfile`, `generator`, positive finite `desiredDuration` (or compatible `durationSeconds`), and execution `settings.aspectRatio`. Execution config is whitelisted, scalar, and excludes provider/score/quality-label metadata. Saved historical AUTO text remains intact; separate current production settings govern execution.

Original fidelity submission fields: `decision`, concrete `rationale`, `reviewMethodVersion: human-original-fidelity-v2`, `validUntil` (future and at most 180 days), exact `citations` with `side` APPROVED_STORY or ORIGINAL_PROMPT and `quote`, plus `sourceEventMapping` entries containing `anchor`, `sourceQuote`, `promptQuote`. PASS must map all six anchors: CHARACTER_IDENTITY, APPROVED_EVENTS, EVENT_ORDER, PHYSICAL_RULE, TEMPORAL_CONSTRAINTS, REQUIRED_ENDING. These checks support authenticated human judgment; they do not pretend substring matching proves semantics. Uncertain interpretation stays UNKNOWN. Optional `supersedesEvidenceId` must identify the same immutable subject; superseded records remain stored.

## Source authority, evidence isolation and persistence

`WorkflowService.approvedStoryForCpq` reads the existing saved story/candidate and latest matching STORY_APPROVAL contract. It preserves the existing FNV revision fingerprint while storing separate full-story SHA-256. It creates no story or approval. Missing authority returns SOURCE_APPROVAL_REQUIRED. Prompt text equal to its own supposed approved story is rejected as INDEPENDENT_SOURCE_REQUIRED. Binding verifies prompt bytes, source identity, actual approval, revision, production version where available, and settings provenance; stale changes invalidate review/import/packet/preview reuse.

V64 adds immutable `cpq_original_subjects` and typed ORIGINAL_PROMPT / OPTIMIZATION_CANDIDATE scope to the existing ledger. Repository originals need no synthetic content, analysis or comparison. Original rows have no canonical analysis binding and use NOT_APPLICABLE for ruleset; canonical compliance stays independent. Candidate rows retain their required content/prompt/analysis/comparison binding. V62/V63 were not edited. V64 adds explicit same-subject supersession and import source/mechanic/settings provenance fields. Existing candidate rows default to the prior candidate contract. Disposable V63→V64 upgrade verifies legacy decision, rationale, fingerprints and revision remain unchanged. Append-only database triggers remain enforced.

Identity and authority come from servlet authenticated principal/roles, never JSON claims. An original reviewer cannot certify their own source binding or a known own approval. Existing legacy approvals can lack `approvedBy`; that identity cannot be reconstructed, and the new source binder is recorded and barred from self-review. No production identity or role was created. Fidelity producers cannot also provide that example's independent quality judgment. Authentic quality review requires at least two separate qualified identities. No API provides other reviewers' judgments in the blind packet.

Importer independently re-resolves current unexpired, non-superseded, non-conflicting PASS evidence and checks exact prompt/story/revision/settings/type/version scope. FAIL, UNKNOWN, missing, wrong-scope and stale evidence cannot qualify. Requires DRAFT/REVIEWING corpus, valid split, prompt version label and explicit `leakageGroup`; derives source group from approved story ID. Corpus locking plus duplicate and story/mechanic grouping checks prevent same-corpus calibration/held-out leakage. Opaque blind packets omit corpus labels, source/candidate type, provider, canonical scores, historical outcomes, popularity and supervisor manifest. Raw source prompt text is preserved, rather than silently edited for blinding.

New judgments use version `cpq-human-blind-review-v2`, preserving legacy records. Every dimension requires level EXCELLENT/STRONG/ADEQUATE/WEAK/UNKNOWN, exact prompt citations, concrete rationale, `strengthOrWeakness`, `productionConstraint`, and explicit `uncertainty` for UNKNOWN. Duplicate reviewer submission is rejected. Top-level evidence citations are validated or derived from the six validated dimension citations; preview reads the same nested fidelity evidence binding as its producer. A reviewer quality anchor is an opinion, never an activated aggregate grade.

## Six real originals and frozen inventory

Nine frozen golden source files were rehashed against their authoritative originals: 9/9 match. No source was rewritten. The six prior exact blind drafts remain unchanged. Each new `original-source-review-packages/P0n.json` contains exact original path/hash, textual production declarations, missing authority, all blockers, selectors for future preflight and protected-anchor checklist.

| Draft | Source | Exact SHA-256 | Independent blockers |
|---|---|---|---|
| P01 | Sticky Ball | `378a39e7d625d5e4e36cd23436b53b0d410b326f02a3c77406853cc51e965e01` | SOURCE_APPROVAL_REQUIRED; PRODUCTION_SETTINGS_BINDING_REQUIRED; REVIEW_AUTHORIZATION_REQUIRED |
| P02 | Upside-Down Chair | `6db5f744f51dca45b4be2133e8d88648b839e5d1fb5b742be5f1aaa3d016502a` | SOURCE_APPROVAL_REQUIRED; PRODUCTION_SETTINGS_BINDING_REQUIRED; REVIEW_AUTHORIZATION_REQUIRED |
| P03 | Lamp | `e2a4c2b2e3ab5ed7927831c2c264e779c9d9b251b6e979e997c1c271bd7ff0bc` | SOURCE_APPROVAL_REQUIRED; PRODUCTION_SETTINGS_BINDING_REQUIRED; REVIEW_AUTHORIZATION_REQUIRED |
| P04 | Missing Shoe | `016c6728e5d8b18c564748d439c88f56a635a64cf69a1f77c4162bd74fbeac75` | SOURCE_APPROVAL_REQUIRED; PRODUCTION_SETTINGS_BINDING_REQUIRED; REVIEW_AUTHORIZATION_REQUIRED |
| P05 | Missing Carrot | `0bb1d77c7939949543be6f12e8ca3ecb086e15dffceda973c6f3382360f523d8` | SOURCE_APPROVAL_REQUIRED; PRODUCTION_SETTINGS_BINDING_REQUIRED; REVIEW_AUTHORIZATION_REQUIRED |
| P06 | Island Journal | `2ef992226b13e968e43f065a6cad606039c3d7af27e92577ec754d9d342830de` | SOURCE_APPROVAL_REQUIRED; PRODUCTION_SETTINGS_BINDING_REQUIRED; REVIEW_AUTHORIZATION_REQUIRED |

All six are applicable to the new original workflow but none is currently eligible for import. No separately approved platform story revision or authoritative settings binding was established for these sources; exact-hash production prompt-version lookup returned none. Embedded events/narrative are available for human source preparation, not automatically approved story evidence. Text durations are declarations only: P01 15s timeline, P02 15–18s, P03 15s, P04 15–18s, P05 17s timeline, P06 25.5s. Generator/profile authority must be supplied legitimately. Proposed splits remain provisional; source variants stay grouped. Other golden originals remain future candidates.

## Mimi original and authentic candidate preparation

Prepared exact neutral offline files Q01–Q04 under `mimi-comparative-drafts/`; supervisor-only provenance maps Q02 to original, Q01/Q03 to comparison 9275c94b-fc35-4207-8648-dfd8d166e502 A/B, Q04 to e651eb75-b894-477d-ae77-0fe6e05236da A. It preserves hashes, approved story/revision, exact differences/changed-beat and reconstruction evidence, canonical outcomes and historical assessments. Supervisor metadata must not go to blind reviewers. All four belong in the same split. These are preparation drafts, not official API review packets or randomized study evidence.

Mimi has actual approved story SHA-256 `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`, story ID bc1cf798-d20b-4b98-8b73-56e1581c3afc, approval 20b77d13-848d-46d0-ab4b-bb9b6efb0836, revision candidate-2-revision-7c63cc86. Original Prompt 10/version 1 SHA-256 remains `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`. Current saved context is ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15 seconds / image2video / 480p / 9:16. Analysis f0d36feb-ee0f-4da8-ae21-2071a3ddea18 remains Ruleset 1.11, 88.40625/B. Current candidate binding API still returns COMPATIBLE. Each original/candidate separately needs independent fidelity evidence and qualified import. No source PASS or superiority is inferred from compatibility. NO_REAL_IMPROVEMENT_PAIR_AVAILABLE remains true.

## Actual production readiness measures

| Measure | Verified result |
|---|---|
| Frozen originals inventoried / exact matches | 9 / 9 |
| Prepared initial repository originals | 6 |
| Initial six with approved story/settings bindings | 0 / 0 |
| Prepared Mimi prompts with authentic common approved-source context | 4 (one original, three historical candidates) |
| Persisted original CPQ subjects | 0 |
| Current independent fidelity PASS / all fidelity records | 0 / 0 |
| Legitimately imported examples / corpora | 0 / 0 |
| Official blind packets currently issuable | 0; six plus four offline preparation drafts only |
| Source prompts awaiting new independent fidelity evidence | All six repository originals plus four Mimi prompts, after prerequisites |
| Actual completed human judgments / participating reviewer identities | 0 / 0 observable submissions; current principal unauthenticated |
| Quality dimension coverage / approved anchors | 0 / 0 |
| Reviewer disagreement | Not measurable in production; deterministic disagreement detection tested |
| Held-out grouping | Enforced in import; no production split/corpus frozen |
| Threshold readiness | Incomplete; no new thresholds chosen |
| Independent B→A acceptance | None |

No global directory claim about nonexistent reviewers is made: the observed application principal lacks all four CPQ capabilities and there are no submitted reviewer identities. CPQ grading remains INACTIVE / CALIBRATION_INCOMPLETE. Visual adherence remains UNVERIFIED and audience effect UNMEASURED. No A/A+ or canonical label has been manufactured.

## Verification and limits

Focused backend: **44 passed, 0 failures/errors/skips**: OriginalCpqFidelityIntegrationTest 17, PlatformIntegrationTest 26, CpqV62MigrationTest 1. Actual Spring controller/service/persistence with disposable PostgreSQL and mocked ML transport exercised source binding → original PASS → importer → blind packet → two different authenticated fixture reviewers → disagreement/readiness → preview with activation still false. Fixture identities are not real humans. Positive/negative coverage includes missing source/config/authority, unsafe paths/hash mismatch, self-source and reviewer conflicts, required citations/anchors/rationale, expiry, stale approval/config, FAIL/UNKNOWN/missing evidence, original/candidate isolation, story/revision/version/settings mismatch, duplicate import/reviewer, split leakage, metadata removal, supersession and append-only constraints, frozen corpus, no fabricated optimization record, and unchanged workflow event count.

Frontend Step 6 focused regression: **73 passed**. ML CPQ/Adaptive V3 focused: **30 passed** with correct POMPOM_DATA_ROOT. Initial ML invocation without that environment produced 27 passes and 3 missing-profile-file errors; corrected configuration passed without code changes. ML emitted datetime deprecation warnings. Backend emitted Testcontainers/Hikari teardown diagnostics and Surefire fork shutdown timeout messages after passing assertions; Maven exit status was 0. No claim of a clean full-suite baseline: earlier backend 19 view/TRUNCATE errors, two saved-story retry assertions and prompt-lineage null-version failure, ML escalation/story-duplicate failures, frontend seven failures and eight video-detail fixture errors remain known and were not reclassified as unrelated or rerun here. No ML/frontend production logic changed in this task.

Authorized positive production review was not attempted: no legitimate reviewer session is available, and production review writes were explicitly outside this authorization. Positive workflow behavior is established by actual controller/service/disposable persistence tests; deployed anonymous denial and runtime identity are established separately. Mobile UI acceptance from the preceding task remains VERIFIED; no UI redesign was required.

## Deployment and history integrity

Ran `./intelligence/scripts/deploy.sh backend` after checks. Script built backend and restarted frontend to refresh nginx backend routing; no ML/render build. Running backend image: `sha256:dd73b57f02097fe7382cd9293b257afe53d487c5ce2507c96657e4f9d358b74c`. Flyway V64 successfully applied. Backend actuator/database and ML health UP; frontend root and nginx API checks passed. Frontend image stays `sha256:f99af82c3721a9b7b8905ba6c0c084a6b198d21f9e042402247a34725d958da5`; ML stays `sha256:dbfa934a00d13b376869710de27a739c19b29e86d31e5a955a825bc79a428488`.

Deployed POST preflight, binding and original fidelity review with anonymous identity each returned 403, not a simulated local permission decision. GET reviewer capabilities confirms unauthenticated/all capabilities false. GET calibration returns originalSubjects/fidelityReviews/examples/judgments/currentFidelityPasses all zero, no corpora, activated=false. No production positive evidence was submitted.

Pre-migration custom-format PostgreSQL backup was created and archive list verified at `/Users/benanaktas/Library/Application Support/Pompom Hills/Recovery Backups/cpq-original-fidelity-v64-20261015/pompom-before-v64.dump`, SHA-256 `303bcb0b35ab74179d28b66906b4c70bb7ee6a1c85f63d6bd6ef910a42f12901`. No prune or destructive cleanup occurred. Host free space was 4.2GiB before deployment; Docker VM retained about 53GB free.

Read-only before/after comparison: Prompt 10 hash unchanged; 75 workflow events and 8 CREATIVE_OPTIMIZATION records unchanged; complete ordered workflow payload digest remains `e7e55725c68f7c27d61183b854b4b1b7799b410814acde27ca2db69fa3190275`. All preexisting CPQ counts remain zero and activated=false; only schema moves 63→64. This protects stories, saved approvals, provider outputs and historical comparisons as a whole. Audit query initially used an incorrect comparison kind and returned zero; corrected to actual CREATIVE_OPTIMIZATION, verified eight and identical whole-event digest. No history was deleted or repaired.

Evidence is in `cpq-v1-calibration-intake-2026-10-15/evidence/original-task-*.json`, focused logs and deploy log. No paid calls, new candidates, prompt/story mutation, production review/import/corpus creation, reviewer role creation, canonical changes, image/video work, publishing, commit or push occurred.

## Exact operator continuation

1. Use legitimate existing authentication provisioned by the operator for an architecture approver, an independent evidence reviewer and at least two distinct creative-quality reviewers. Do not pass roles or reviewer identity in JSON.
2. For P01–P06, a human identifies a separately authoritative source narrative and approved revision through existing story governance. Existing story approval route is POST `/creative-role/{id}/approve-story` with actual candidateId/approvedText/revisionId/contentFingerprint; this task neither creates those sources nor treats prompt copies as approvals. Establish actual source-bound production configuration; repository config JSON is an existing-provenance input, not permission to fabricate defaults.
3. Using each prepared preflightRequest, fill only actual approval/settings selectors and invoke preflight. Resolve every blocker. Architecture approver submits binding with concrete rationale. For Mimi use contentId=10, promptVersionId=10 and exact original hash with current persisted context. Binding is not fidelity PASS.
4. A different authorized evidence reviewer retrieves exact subject packet and records an honest PASS/FAIL/UNKNOWN with required six-anchor mappings, exact quotes, rationale and expiry. Review all three historical Mimi candidates separately through their existing candidate routes. UNKNOWN/FAIL stay ineligible.
5. Architecture approver creates a real corpus through the existing route. Import each genuinely qualified example with `sourceFidelityEvidenceId`, exact `promptText`, `approvedStoryText`, `sourceStoryId`, `sourceRevision`, correct `subjectType` (and originalSubjectId/promptVersionId where relevant), `promptVersionLabel`, authoritative settings, `split`, explicit `leakageGroup` and provenance. Keep same-story/mechanic variants, including Mimi, in one split. Do not freeze provisional split assignments prematurely.
6. Two independent quality reviewers separately GET official blind packets and POST all six dimensions, sourceFidelityDecision and versioned review method. Use UNKNOWN plus uncertainty where unsupported. Optional quality anchors are reviewer observations, not final grading. Review coordinator must withhold supervisor manifest and other judgments; disagreements require independent adjudication before claiming accepted anchors.
7. Read readiness, inspect disagreement and qualified coverage, run authorized diagnostic preview. Gather genuine quality anchors, held-out error estimates, justified thresholds and a full-pipeline independently accepted B→A case before requesting formal activation. No activation authority is granted by this engineering completion.

The software gap is closed. The remaining limits are legitimate source approvals/settings and independent human evidence; no creative grade or B→A success is proven.
