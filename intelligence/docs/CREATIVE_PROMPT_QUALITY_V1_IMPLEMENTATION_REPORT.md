# Creative Prompt Quality V1 — historical candidate acceptance report

Date: 2026-10-15
Status: `MOBILE_STEP6_ACCEPTANCE=VERIFIED`; `CALIBRATION_INTAKE=INCOMPLETE`; `CPQ_GRADING=INACTIVE`; `REAL_B_TO_A_ACCEPTANCE=NOT_VERIFIED`

## Root cause and implementation

Step 6 previously requested only `/creative-optimization/latest`. Since the latest immutable comparison (`2e2adcea-31de-4817-8fc8-8e301396fa50`) has zero candidates, the UI could not expose the existing candidate-bound CPQ preview. The CPQ write route also resolved candidates through the latest comparison, so historical candidates could not be safely assessed by exact comparison identity.

Added a read-only, analysis-scoped history endpoint and a compact selector inside the existing Step 6 Creative Optimization section. The latest comparison is the default; historical records are only displayed after deliberate selection. The selector includes created time, model, candidate count, current/historical label and prior decision. Empty latest state remains explicit. Candidate inspection and CPQ candidate selection are separate from revision selection or approval.

The exact historical assessment route is comparison- and candidate-scoped. Both the preview binding and POST write path re-check the persisted source and authenticated operator. The POST cannot trust frontend eligibility claims and requires the production operator role. Saved assessments are looked up by the same comparison and candidate. V63 adds nullable comparison identity to new CPQ assessment and fidelity-review records so evidence cannot bleed between comparisons; legacy rows remain readable without a comparison binding. These routes do not re-evaluate or rewrite historical optimization records.

## Historical bindings and live candidates

Every candidate is checked against the current authoritative analysis and immutable prompt: content ID, source prompt ID/version and SHA-256, approved story revision and SHA-256, analysis ID, Ruleset 1.11, production profile/generator/duration/settings, comparison ID, provider-role record, candidate ID and exact prompt fingerprint. The provider role must contain the exact candidate once. Candidate canonical evidence must have evaluation status `EVALUATED` and the same ruleset. Where the provider attempt came from an older run, a valid persisted revalidation chain is required. Missing or conflicting evidence yields `READ_ONLY` with reasons; there is no current-binding substitution.

The first deployed-browser pass exposed two integration defects. The compatibility check looked for `EVALUATED` on the candidate review wrapper, while persisted candidates put that status in `review.canonicalRuleEvaluation`; it now reads the stored contract. A subsequent live capability check also found a duplicate `canAssessTextQuality` map key, which made the reviewer-capabilities endpoint return `INVALID_REQUEST` and left the button unavailable. The duplicate was removed and the focused test now asserts ordinary-versus-authorized capability values. The integration fixture matches the persisted candidate contract.

Current saved evidence is:

- Analysis: `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, Content 10, Prompt 10/version 1, Ruleset 1.11, 88.40625/B.
- Latest comparison: `2e2adcea-31de-4817-8fc8-8e301396fa50`, zero candidates; selected by default on initial Step 6 load.
- Historical comparison: `e651eb75-b894-477d-ae77-0fe6e05236da`, one candidate (`candidate-a`), now `COMPATIBLE` with no binding reasons. Candidate SHA-256: `90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495`.
- Historical comparison: `9275c94b-fc35-4207-8648-dfd8d166e502`, two candidates (`candidate-a`, `candidate-b`), both `COMPATIBLE` with no binding reasons after the verified revalidation chain from `7291a6c5-07a0-4b4e-b033-09680889224a`. Candidate SHA-256 values: `218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749` and `2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746`.
- All three comparisons bind source prompt SHA-256 `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`, approved-story SHA-256 `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`, and Ruleset 1.11.

Binding compatibility permits only a candidate-bound CPQ text assessment. It does not mark the candidate revalidated for approval; the historical comparison remains `CURRENT VALIDATION REQUIRED`, and no historical candidate is recommended or approved automatically.

## CPQ behavior and actual browser acceptance

The real deployed Chrome page was opened at Content 10 / Prompt 10, Step 6. On initial entry the latest zero-candidate comparison was shown. The historical selector labels the chosen record as historical; a previously deliberate historical choice remained selected after one browser reload, so the latest record was reselected explicitly to verify the zero-candidate empty state again. This did not change stored data. I intentionally selected the one-candidate historical comparison, then selected `Enhanced Contact Clarity` for the CPQ preview. The live binding displayed `COMPATIBLE`, the exact source/story hashes and Ruleset 1.11. The panel displayed all six established dimensions:

- `SCROLL_STOP_VISUAL_PROMISE`
- `CAUSAL_PROGRESSION`
- `VISUAL_STORYTELLING`
- `PRODUCTION_EXECUTABILITY`
- `ENDING_REPLAY`
- `DISTINCTIVE_CREATIVE_VALUE`

It also displayed four separate domains: Creative Prompt Quality (preview only, no numeric grade), Canonical Validation (Ruleset 1.11, 88.40625/B), Independent Source Fidelity (`UNKNOWN`), and Render Readiness (`BLOCKED_PENDING_EVIDENCE`, no CPQ authorization). Visual adherence remained `UNVERIFIED`; audience outcomes remained `UNMEASURED`. The six dimensions were unassessed; no A/A+ grade was shown. Historical candidate comparisons retain their saved values and are not presented as fresh CPQ canonical evaluations.

The actual deployed page was inspected in Chrome responsive-device emulation at **390 × 844** and **320 × 844**. Workflow cards reflow into two columns; content cards remain within the viewport; long binding hashes wrap; and all six dimension labels are accessible by vertical scrolling. The real page reported `innerWidth=clientWidth=documentWidth=bodyWidth=390` at 390px and the same equality at 320px, confirming no horizontal document overflow. Browser state verified historical selection; screenshots showed the compatible binding, four assessment domains, one-column dimensions and candidate evidence disclosures without clipping. Desktop layout was rechecked after resetting responsive mode. The live reviewer-capabilities endpoint returns `authenticated=false` and all four capabilities false for the current local browser session; the assessment button remained disabled. Read-only GETs returned zero calibration examples, judgments and current fidelity passes, `activated=false`, and an empty saved-assessment response for the authoritative analysis. Navigation and selection created no assessment, fidelity review, calibration judgment, prompt version, approval or render record. The authorized assessment path is covered only by the isolated backend integration test with a disposable `PRODUCTION_OPERATOR` principal. That test persists a six-dimension mocked assessment, retains `UNKNOWN` source fidelity and inactive grading, and rejects unauthorized access and cross-analysis binding. No live provider call was involved. DevTools Console showed no page errors or warnings; the Issues surface listed 11 generic “possible improvements,” not attributed to Step 6. Browser screenshots were captured in this task's tool evidence and visually inspected; no screenshot files were exported to the repository.

No prompt version, story approval, candidate approval, canonical evaluation, render authorization, F8 authorization, or publication was created. The saved analysis remains 88.40625/B. Missing verified Mimi reference and accepted start frame continue to block render readiness.

## Tests and regression status

- Backend focused command `mvn -q -Dtest=PlatformIntegrationTest,CpqV62MigrationTest test`: **26 passed, 0 failed** (25 integration tests plus one migration test) on disposable PostgreSQL; includes compatible exact binding, stale/cross-analysis and unauthorized rejection, assessment persistence, inactive grading, unknown fidelity, and capability reporting for ordinary versus authorized roles.
- Frontend focused command `npm test -- --watch=false --include src/app/pages/quality-validator/post-family-workflow.spec.ts`: **73 passed, 0 failed**. Covers latest empty history, historical one-/two-candidate selection, current/historical state, stale response handling, read-only selection, and CPQ display contract.
- ML focused CPQ/Adaptive V3 suite: **30 passed** in the earlier acceptance run; no ML files changed or rebuilt in this task.
- The full suites were not rerun for this acceptance. The last recorded broader runs were not green: backend included 19 operational-guard errors (`TRUNCATE` attempted on a view), two saved-story retry record-ID assertions, and one video prompt-lineage null-version failure; ML had two failures in escalation applicability and story-duplicate classification; frontend had seven failures and eight errors in video-detail fixtures (`getCaptionVersionsByVideo` missing). No suitable clean baseline run was available, so these are tracked as known, unproven baseline issues rather than labeled unrelated. Focused CPQ tests pass; no test was skipped or weakened for this task.

## Deployment and persistent-data integrity

After focused backend tests, the official minimal deployment command `./intelligence/scripts/deploy.sh backend frontend` was run twice: once for history UI/backend delivery and again after correcting the persisted-status field lookup. The final backend-only script invocation rebuilt the changed service and restarted the compatible frontend, then verified backend health, frontend availability, provider-capabilities HTTP response, and container image identity. ML was unchanged and remained healthy.

Final runtime images:

- Backend: `sha256:ba3ef2777903a648ebf94964c050d5d5dc06cfd7f93221d009b325f3b19c60e2` — healthy; `/actuator/health` UP.
- Frontend: `sha256:f99af82c3721a9b7b8905ba6c0c084a6b198d21f9e042402247a34725d958da5` — deployed; `/` and provider-capabilities API checks passed.
- ML (unchanged): `sha256:dbfa934a00d13b376869710de27a739c19b29e86d31e5a955a825bc79a428488` — healthy; `/health` UP.
- PostgreSQL: healthy, Flyway version **63** (V62 CPQ schema plus V63 comparison binding).

Read-only integrity checks after deployment: prompt SHA-256 unchanged; approved story SHA-256 unchanged; authoritative analysis and score unchanged; 75 workflow events; 8 optimization comparison records; CPQ assessment count 0; fidelity-review count 0. History API returned the same comparison IDs, role record IDs and prompt fingerprints; no persisted optimization or provider response was modified. The V63 schema migration is the only production database mutation. Docker volumes were preserved; no prune or cleanup was run.

Calibration endpoint reports zero corpora, zero examples, zero judgments, zero independent fidelity passes, `CALIBRATION_INCOMPLETE`, and `activated=false`. No corpus or production review was fabricated. The earlier volume backup remains preserved at `/Users/benanaktas/Library/Application Support/Pompom Hills/Recovery Backups/cpq-v1-20261015/intelligence_postgres-data.tgz` (SHA-256 `b7e24fe3db2c198fefe2598e9db318386f9d45c8d805684120cb47e067eba191`).

## Calibration intake and remaining production gates

Use the existing calibration workflow only:

1. Import approved prompts as **ungraded** examples only after checking each prompt's immutable source-story binding; Mimi Prompt 10 can be considered after the existing approved story revision is confirmed. Do not assign a quality grade on import.
2. Give reviewers blind packets with prompt/candidate identities randomized and pair order counterbalanced. Keep source-fidelity review separate: an `EVIDENCE_REVIEWER` must map candidate claims and story events to exact approved-source evidence; unsupported claims remain `UNKNOWN`.
3. Obtain independent rubric judgments from qualified `CREATIVE_QUALITY_REVIEWER` users. The current historical Mimi candidates are not known A/A+ exemplars, and real independently reviewed improvement-versus-baseline pairs plus regression examples are missing.
4. Have a `CREATIVE_QUALITY_ARCHITECTURE_APPROVER` review corpus composition, held-out false-positive/false-negative analysis, reviewer agreement and full-pipeline B-to-A golden acceptance before any separately authorized activation. Grading stays inactive until that record exists.
5. For Step 7, separately acquire and verify the Mimi character reference and an accepted start frame. Satisfy every existing independent visual and render gate. CPQ compatibility or text acceptance does not authorize F8 or rendering.

Mobile browser acceptance is complete for 390×844 and 320×844. The next product action is evidence preparation in the existing calibration workflow. The current fidelity-creation endpoint is saved-candidate/comparison-bound; repository originals and the baseline cannot be qualified by a file/hash alone, and their supported source-evidence path must be confirmed before import: an authenticated `EVIDENCE_REVIEWER` must independently bind selected exact prompts to approved story revisions, then an authenticated `CREATIVE_QUALITY_ARCHITECTURE_APPROVER` can create a draft corpus and submit only examples with current fidelity evidence. Two distinct `CREATIVE_QUALITY_REVIEWER` identities must provide blind, citation-backed judgments. The local session has none of these roles, and the existing workflow is API-backed without a calibration-management frontend. Exact source inventory, hashes, blockers and operator steps are in [CPQ_V1_CALIBRATION_INTAKE_REPORT.md](CPQ_V1_CALIBRATION_INTAKE_REPORT.md). No production imports or judgments were written, no service code changed, and no deployment was needed for this documentation and acceptance-only turn. No commit or push was made.

## Mobile acceptance addendum — 2026-10-15

- **MOBILE_STEP6_ACCEPTANCE: `VERIFIED`** at Chrome responsive viewport **390 × 844**; the optional **320 × 844** check also passed.
- No horizontal overflow: at 390px, viewport/client/document/body widths were all 390px; at 320px, all were 320px.
- Historical selection: latest zero-candidate comparison is the default; selecting the two-candidate and one-candidate history is explicit; stale candidate selection clears when switching comparisons; returning to latest restores its empty state.
- CPQ panel: selected historical candidate binding displayed `COMPATIBLE`; all six dimension names were visible; no numeric CPQ grade appeared; canonical 88.40625/B remained unchanged; source fidelity remained `UNKNOWN`; render readiness remained `BLOCKED_PENDING_EVIDENCE`; visual adherence remained `UNVERIFIED`; audience outcomes remained `UNMEASURED`.
- The assessment action remained disabled for the unauthenticated browser principal. Calibration API state remains 0 corpora, 0 examples, 0 judgments, 0 current fidelity passes, inactive. No assessment or review write occurred.
- Focused verification rerun: frontend Step 6 spec **73 passed**; backend `PlatformIntegrationTest,CpqV62MigrationTest` **27 passed**. The previous ML CPQ/Adaptive suite remains **30 passed**. Full-suite historical failures are recorded above and were not rerun because this turn changed no application code.

## Independent final statuses

- `MOBILE_STEP6_ACCEPTANCE: VERIFIED`
- `CALIBRATION_INTAKE: INCOMPLETE`
- `CPQ_GRADING: INACTIVE`
- `REAL_B_TO_A_ACCEPTANCE: NOT_VERIFIED`

## Calibration-path verification addendum

Prepared six exact offline blind-prompt drafts with a separate supervisor provenance manifest; imported zero production examples and submitted zero production judgments. All nine frozen golden originals match their source files byte-for-byte. The existing fidelity-creation API accepts only saved comparison candidates; arbitrary repository originals and baseline prompts have no general fidelity-submission path in this controller. This specific intake limitation and missing authenticated reviewer authority remain explicit blockers. No workaround record was fabricated.

The expanded disposable PostgreSQL assessment/calibration integration test passed **1/1** after the earlier **27/27** focused backend run. It exercises corpus-management authorization, missing fidelity rejection, exact prompt/story fingerprints, blind-packet access and metadata redaction, reviewer independence, two-reviewer readiness, UNKNOWN fidelity/anchors and inactive grading. Fixture reviewers and judgments are isolated test data and are not real quality evidence.

CPQ-focused ML rerun: `tests/test_creative_prompt_quality_v1.py` — **5 passed** in 1.76 seconds; no real inference.
