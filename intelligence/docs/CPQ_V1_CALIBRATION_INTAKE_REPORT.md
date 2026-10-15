# CPQ V1 — mobile acceptance and real calibration intake

Date: 2026-10-15

| Independent status | Result |
|---|---|
| MOBILE_STEP6_ACCEPTANCE | VERIFIED |
| CALIBRATION_INTAKE | INCOMPLETE |
| CPQ_GRADING | INACTIVE |
| REAL_B_TO_A_ACCEPTANCE | NOT_VERIFIED |

## Completed work and boundary

The actual deployed Step 6 page passed narrow-viewport inspection. Six exact production prompts are prepared as offline blind-prompt drafts, with a separate provenance manifest. None has been imported into production and no human judgment has been supplied. The current browser identity is unauthenticated and has no CPQ write/reviewer authority. Source-story approvals, independent fidelity evidence and human reviewers must be established before these drafts can become official calibration examples and review packets.

This task changed documentation, offline preparation files and a disposable-database integration test. It changed no application behavior or runtime artifact. No new deployment was required. The previously deployed backend/frontend remain healthy. No provider, candidate generation, prompt/story mutation, score/ruleset change, rendering, publishing, approval, grading activation, direct production SQL mutation, commit or push occurred.

## Actual mobile browser acceptance

Application: `http://localhost:4200/quality/detail?contentId=10&promptVersionId=10&studio=1`, Step 6 Repair → Creative Optimization. Browser: real Google Chrome, responsive device emulation, not a unit-test DOM.

| Check | Evidence/result |
|---|---|
| Primary viewport | 390 × 844 CSS pixels; Chrome device toolbar values inspected |
| Additional viewport | 320 × 844 CSS pixels |
| Horizontal overflow | Real-page Console measurement at 390: `innerWidth=390`, `clientWidth=390`, `documentWidth=390`, `bodyWidth=390`. At 320 all four were 320. |
| Latest default | Latest comparison `2e2adcea-31de-4817-8fc8-8e301396fa50`, zero candidates, explicit empty state and saved KEEP_ORIGINAL decision |
| History navigation | Explicitly selected the two-candidate comparison `9275c94b-fc35-4207-8648-dfd8d166e502` and one-candidate comparison `e651eb75-b894-477d-ae77-0fe6e05236da` |
| Stale state | Selecting a different comparison reset the CPQ candidate to “Choose a candidate”; returning to latest removed the candidate panel and restored the empty state |
| Candidate binding | Selected historical Candidate A displayed COMPATIBLE, the exact source/story hashes and Ruleset 1.11 |
| Dimensions | All six established dimension names visible and accessible by vertical scrolling, explicitly “not assessed” |
| Independent domains | CPQ preview/no numeric grade; canonical 88.40625/B; source fidelity UNKNOWN; render readiness BLOCKED_PENDING_EVIDENCE |
| Layout | At 390px workflow cards reflowed, panels and selects fit, long hashes wrapped and all dimensions remained readable. The 320px spot-check covered candidate/evidence details and document overflow; no horizontal clipping was observed |
| Evidence limits | No independent human assessment or quality grade exists. This verifies UI access and layout, not creative quality. |
| Desktop regression | Normal desktop rendering was checked again after resetting responsive mode; no UI fix was necessary |
| Browser diagnostics | Console showed no page errors/warnings. Chrome Issues showed 11 “possible improvements”; these were not diagnosed as Step 6 defects. |

Real screenshots were captured and visually inspected in this task's browser-tool transcript: 390px overview; 390px CPQ domain cards and selected candidate; 390px six dimensions and canonical card; 320px candidate/evidence disclosures; restored desktop layout. The screenshot API captures were displayed inline and were not exported as repository PNG files. The six dimensions were `SCROLL_STOP_VISUAL_PROMISE`, `CAUSAL_PROGRESSION`, `VISUAL_STORYTELLING`, `PRODUCTION_EXECUTABILITY`, `ENDING_REPLAY` and `DISTINCTIVE_CREATIVE_VALUE`.

## Runtime and production integrity

Verified running images:

- Backend: `sha256:ba3ef2777903a648ebf94964c050d5d5dc06cfd7f93221d009b325f3b19c60e2`; actuator UP.
- Frontend: `sha256:f99af82c3721a9b7b8905ba6c0c084a6b198d21f9e042402247a34725d958da5`; deployed page inspected.
- ML: `sha256:dbfa934a00d13b376869710de27a739c19b29e86d31e5a955a825bc79a428488`; health UP.
- PostgreSQL remained healthy; deployed schema V63 from the preceding delivery. Docker storage was preserved.

The final read-only transaction returned Prompt ID 10/version 1 SHA-256 `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`, 75 workflow events, 8 optimization comparisons, 0 CPQ assessments, 0 fidelity reviews, 0 corpora, 0 examples, 0 judgments and `activated=false`. These match the preceding deployment snapshot. The binding API still returned approved-story SHA-256 `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`, approved revision `20b77d13-848d-46d0-ab4b-bb9b6efb0836`, Ruleset 1.11 and the same candidate fingerprints. The authoritative analysis remains `f0d36feb-ee0f-4da8-ae21-2071a3ddea18` at 88.40625/B.

GET `/api/v1/intelligence/workflow/cpq/calibration` returned CALIBRATION_INCOMPLETE, no corpora and zero examples/judgments/current fidelity passes. GET the analysis's `/creative-prompt-quality` returned an empty assessment list, INACTIVE and `renderAuthorized=false`. Reviewer capabilities were unauthenticated, with all four CPQ capabilities false. The production assessment action stayed disabled. Browsing did not create a persisted record.

## Frozen golden inventory

Authoritative source root: `/Users/benanaktas/project/video/yuvarlak-dunya`. The nine `sourceLocation` paths in `intelligence/data/golden/pompom-golden-v1/manifest.yaml` were read and rehashed. Every original source file matches the frozen copy and approved hash byte-for-byte.

For **each** row below: full exact production prompt available = yes; fingerprint available = yes; repository source lineage = HIGH according to the frozen manifest; separate platform-bound approved story ID/revision = not established by this mounted corpus; authoritative platform profile/generator/duration binding = not established; independent CPQ judgments = none; current independent CPQ fidelity record = none; import/blind review eligibility now = pending source evidence. Narrative/production instructions embedded in the prompt and canonical Gold Truth are available, but neither substitutes for a separately bound approved story revision or CPQ human review. Textual duration instructions, where present, must be reconciled with authoritative production settings before import. These are originals, not known original/improvement pairs.

| Golden ID | Character / mechanic | Exact SHA-256 | Eligibility |
|---|---|---|---|
| sticky-ball-01 | Luca / sticky deformation | 378a39e7d625d5e4e36cd23436b53b0d410b326f02a3c77406853cc51e965e01 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| ball-crocodile-01 | Luca / quantity multiplication | a4f76d88158463b989250ddfec943677d1f848db3a86bbae9200871516c8ccba | SOURCE_FIDELITY_REVIEW_REQUIRED |
| upside-chair-01 | Kiko / spatial inversion recurrence | 6db5f744f51dca45b4be2133e8d88648b839e5d1fb5b742be5f1aaa3d016502a | SOURCE_FIDELITY_REVIEW_REQUIRED |
| lamp-01 | Kiko / observation-dependent state | e2a4c2b2e3ab5ed7927831c2c264e779c9d9b251b6e979e997c1c271bd7ff0bc | SOURCE_FIDELITY_REVIEW_REQUIRED |
| snack-box-01 | Mimi / changing contents | 513554d245fefa31659587f26144ec53cbc099b867da9180114305dc845b1154 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| box-cat-01 | Luca / animal claims box | d93add25456b009ad9937920d1d40d56cbbd517ba6883b743f99a6c6f60bb854 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| spot-cat-01 | Kiko / repeated target claim | 76ea701ceb81d9bc4bc0ac6b9ed6998cea84c8423bb4fa1fa9793d9c523622e5 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| sneaky-door-01 | Mimi / archived multi-clip continuity | f85635f1f10b4834ade72f8091a4a2f2698525d474f02285fa374b56c9c14392 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| island-journal-01 | Luca / montage and late reveal | 2ef992226b13e968e43f065a6cad606039c3d7af27e92577ec754d9d342830de | SOURCE_FIDELITY_REVIEW_REQUIRED |

Known parser caveats remain recorded in the frozen manifest: crocodile structured timeline gap; chair discovery timeout; lamp/snack partial evidence; box/spot timestamp incompatibility; archived door continuation complexity; journal 25.5-second long form and unclear central mechanic. These do not justify inventing creative grades or excluding a prompt solely because the current parser struggles. Manifest WINNER/MIDDLE/NEGATIVE labels and canonical Gold Truth are not CPQ A/A+ labels and must not appear in blind packets.

## Requested production concepts

Paths in this table are relative to the authoritative source root above. Exact prompt files exist for seven of the eight named concepts. No separate approved story revision or independent CPQ judgment was found for these repository-only examples. Profile/generator settings are not bound to current platform evidence. They are source material for review preparation, not automatically authorized imports.

| Concept | Full source prompt | SHA-256 | Eligibility |
|---|---|---|---|
| Spoon | `POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/3-The Giant Spoon/prompt.md` | f191e44aae623bfc0124f1684821ad679179f9b823b6d6a333a094135fdea132 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| Upside-Down Chair | Frozen upside-chair-01 above; same authoritative source hash | 6db5f744f51dca45b4be2133e8d88648b839e5d1fb5b742be5f1aaa3d016502a | SOURCE_FIDELITY_REVIEW_REQUIRED |
| Tiny Door | `POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/What’s Wrong? uploaded/4-The Tiny Door/prompt.md` | 8270013d8030e43e862a4c51992cfcce6576795a1baf30a9091d729a2f47f3fe | SOURCE_FIDELITY_REVIEW_REQUIRED |
| Missing Shoe | `POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/english learning uploaded/3-“Where is it?” — Luca’s Missing Shoe/prompt.md` | 016c6728e5d8b18c564748d439c88f56a635a64cf69a1f77c4162bd74fbeac75 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| Faucet | No exact faucet concept prompt established. Water-up/down v1/v2 files exist, but theme similarity is insufficient to identify the requested original. | Not established | SOURCE_PROMPT_MISSING |
| Dirty Hands | `POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/opposites-2/05_clean_dirty_mimi_hands/01_video_prompt.txt` | c3341621241e61d8b502ecd7798c21f10eb905a55da81c626d605a640f32ca15 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| Balloon | `POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/easy uploaded/1- Arda and the Balloon That Won’t Come Down/prompt.md` | 7a9d3ef6c22d4b7a921ed61e7aa6e05ab5f9d149aa42496fd694758bc4c2770b | SOURCE_FIDELITY_REVIEW_REQUIRED |
| Carrot | `POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Can You Find It?/02_mimis_missing_carrot/01_video_prompt.txt` | 0bb1d77c7939949543be6f12e8ca3ecb086e15dffceda973c6f3382360f523d8 | SOURCE_FIDELITY_REVIEW_REQUIRED |
| Carrot alternate | `POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/What’s Missing?/2/02_mimis_missing_carrot_prompt.txt` | 7129c6e03b69745f90a9c4d35342d56a91e83cf04421d78ff22c039d3a3cdc78 | SOURCE_FIDELITY_REVIEW_REQUIRED |

The nearby water-up/down files have hashes `f212886ed85dec8ff38bdca2ebd3f0f9ae0175ea07ed10f03c1f0436409ebc43` (v1) and `620e6dae7c8b2dced83ecb37562defbbee9e057501f4c55dd5870f54e9b798ca` (v2). They were not selected as faucet substitutes. No view counts were used or copied into the prepared review materials.

## Current saved Mimi original and historical candidates

The original has a real platform prompt/version, approved story revision and authoritative production settings: ABSURD_PHYSICS, SEEDANCE_2_0_MINI, 15 seconds, image2video, 480p, 9:16. Its prompt/story hashes and analysis are listed above. It has no independent CPQ fidelity record or blind human quality judgments. Its eligibility remains SOURCE_FIDELITY_REVIEW_REQUIRED.

| Comparison | Candidate | SHA-256 | Binding / eligibility |
|---|---|---|---|
| e651eb75-b894-477d-ae77-0fe6e05236da | candidate-a, Enhanced Contact Clarity | 90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495 | COMPATIBLE; SOURCE_FIDELITY_REVIEW_REQUIRED |
| 9275c94b-fc35-4207-8648-dfd8d166e502 | candidate-a, Enhanced Initial Contact Clarity | 218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749 | COMPATIBLE; SOURCE_FIDELITY_REVIEW_REQUIRED |
| 9275c94b-fc35-4207-8648-dfd8d166e502 | candidate-b, Dynamic Action-Consequences and Progression | 2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746 | COMPATIBLE; SOURCE_FIDELITY_REVIEW_REQUIRED |

These are authentic persisted original/candidate relationships with exact story, settings and source fingerprints. They are not independently established improvement pairs: saved canonical values remain 88.40625/B with zero delta; live comparison displays CURRENT VALIDATION REQUIRED, NOT_REVALIDATED, no current material-change assessment and unknown story/production evidence. COMPATIBLE permits the explicit CPQ assessment path; it does not imply a source-fidelity PASS, material superiority or approval. No candidate is a qualified A/A+ exemplar.

`NO_REAL_IMPROVEMENT_PAIR_AVAILABLE` under the requested acceptance criteria. Existing pairs can be submitted for independent comparison after legitimate fidelity evidence and human review; their superiority must be determined rather than assumed. All Mimi originals/candidates must remain in one split. No additional generation is necessary merely to expose this evidence gap.

## Prepared first cohort — offline only

Six exact prompt copies are in `cpq-v1-calibration-intake-2026-10-15/blind-prompt-drafts/`, under neutral P01–P06 filenames. A separate supervisor manifest records exact source paths, fingerprints, pending evidence, grouping and proposed split. The prompt bytes were checked against their authoritative files. These are preparation artifacts, not a new review system and not API-issued persisted packets.

| Draft | Source | Coverage | Provisional split/group |
|---|---|---|---|
| P01 | Sticky Ball | Physical causality, deformation and same-rule ending | CALIBRATION / sticky-deformation |
| P02 | Upside-Down Chair | Opening anomaly and recurring spatial inversion | CALIBRATION / observation-dependent-recurrence |
| P03 | Lamp | Observation-dependent state and continuity | CALIBRATION / observation-dependent-recurrence |
| P04 | Missing Shoe | Search, dialogue and reveal | HELD_OUT / search-reveal |
| P05 | Missing Carrot | Audience-visible hidden object, two characters and tower interaction | HELD_OUT / search-reveal |
| P06 | Island Journal | Montage, longer duration and late reveal | HELD_OUT / montage-late-reveal |

Splits are **proposed and unfrozen**. Related stories/variants/mechanics stay together; quality balance and production-setting coverage must be reviewed before freezing. The carrot alternate stays with P05's family if admitted. Canonical scores, popularity, model/provider, audience metrics and presumed superiority are absent from the blind draft files; only complete protected source prompt text is copied. The supervisor manifest must not be supplied to blind reviewers. No intended CPQ grade or human review was authored.

Prepared drafts: **6**. Production imports: **0**. Eligible for immediate official blind packets under the current evidence/authentication state: **0**. Every prepared draft awaits approved story/settings binding and independent fidelity evidence; all original/candidate pairs await real comparative review. No quality anchor has been established. A small unreviewed cohort cannot justify thresholds.

## Existing API workflow and exact operator actions

Base route: `/api/v1/intelligence/workflow`. There is no calibration-management page in the current frontend; the existing management/reviewer workflow is API-backed. Do not invent a UI route or bypass authentication with client-supplied role fields.

1. Establish real authenticated accounts with `EVIDENCE_REVIEWER`, `CREATIVE_QUALITY_REVIEWER` and `CREATIVE_QUALITY_ARCHITECTURE_APPROVER` through normal identity administration. Current GET `/cpq/reviewer-capabilities` returned no principal and every capability false. No real reviewer identities or human judgments were available in this task.
2. For an existing compatible saved candidate, the evidence reviewer uses POST `/records/{analysisId}/comparisons/{comparisonId}/candidates/{candidateId}/fidelity-review`. Supply a real PASS/FAIL/UNKNOWN decision, concrete rationale, exact approved-story/candidate citations, source-event mappings, and explicit expiry within 180 days. PASS must map every changed beat. The server derives the exact approved story, hashes, ruleset, production settings and authenticated reviewer; missing evidence remains UNKNOWN.
3. **Repository-original limitation:** this is currently the only fidelity-creation route and requires a saved analysis/comparison/candidate. It cannot qualify arbitrary golden originals or the baseline by supplying a path/hash alone. For those sources, an operator must first establish their legitimate approved story/version context and confirm a supported existing evidence path. Do not fabricate a candidate, approval, fidelity record or direct SQL insert. This is an intake blocker, not authorization to build a parallel evidence system.
4. The architecture approver creates a DRAFT corpus with POST `/cpq/calibration/corpora/{version}`, then imports eligible examples with POST `/cpq/calibration/corpora/{version}/examples`. Required evidence includes complete exact prompt/story text, matching source identity/revision, a current independent fidelity evidence ID, version label, authoritative duration, profile/generator, split and provenance. Use GENERAL_PROMPT until human review supports a more specific quality case label. Imported examples are ungraded. The existing importer binds exact prompt and story fingerprints; an UNKNOWN fidelity record does not establish final source fidelity or A/A+ eligibility.
5. At least two distinct authenticated creative-quality reviewers receive official packets through GET `/cpq/calibration/examples/{exampleId}/blind-review`. That endpoint exposes prompt/settings/duration and hides provider, scores, audience metrics, case label and existing judgments. Each reviewer submits POST `/cpq/calibration/examples/{exampleId}/judgments` with exactly six dimensions, evidence quotes from that prompt and concrete rationales. A fidelity-evidence producer cannot act as the sole independent calibration reviewer. Do not submit generated or proxy human judgments.
6. Use GET `/cpq/calibration/corpora/{version}/readiness` after import/review to inspect reviewer coverage, agreement and held-out gaps. POST `/cpq/calibration/corpora/{version}/preview` requires architecture authority and persists a provisional report; it was not invoked on production. No grading activation is justified now.

The task stops at this explicitly requested production-write boundary. No corpus exists to query for live per-corpus readiness; global calibration state was queried successfully. Corpus-specific readiness/import/blind access were exercised only in disposable PostgreSQL tests. No production example or review was fabricated to make the endpoint return a fuller report.

## Readiness and remaining product evidence

| Requirement | Current evidence |
|---|---|
| Exact golden originals | 9/9 source files available and hashes verified |
| Offline first-cohort material | 6 exact neutral prompt drafts prepared |
| Production corpus/examples | 0 / 0 |
| Independent CPQ judgments/reviewer coverage | 0 judgments; 0 reviewed examples; no authenticated reviewer in this session |
| Current independent fidelity passes | 0 |
| Approved quality anchors | None; A/A+/B/C/F anchors unqualified |
| Profile/generator coverage | Mimi saved binding known; repository examples lack platform-authoritative settings bindings |
| Held-out evidence | Proposed grouped splits only; no imported/reviewed held-out examples |
| Agreement / false positives / false negatives | Not available; no valid thresholds or held-out results |
| Full-pipeline B→A | NOT_VERIFIED |
| Calibration readiness | CALIBRATION_INCOMPLETE |
| Grading activation | Not justified; INACTIVE |

Text-level A/A+ calibration does not require rendering. Independent source fidelity and real creative judgments are still required. Visual adherence remains UNVERIFIED and audience outcomes UNMEASURED; they do not become text-grade prerequisites. Step 7/F8 remain independently blocked by missing verified Mimi reference, accepted start frame and all other effective admission requirements. This intake grants no render permission.

## Tests and deployment

- Frontend Step 6 focused spec: 73 passed. Covers historical navigation, state clearing, panel visibility and read-only selection; actual mobile rendering was separately inspected as above.
- Backend focused `PlatformIntegrationTest,CpqV62MigrationTest`: 27 passed before the additional calibration-path assertions. The assessment integration test was extended to exercise corpus authority, missing fidelity rejection, exact prompt/story binding, blinded packet access/redaction, reviewer independence, two-reviewer readiness and grading inactivity in disposable PostgreSQL. Its expanded final rerun passed 1/1; all identities and database writes in that test are disposable fixtures.
- Test-only role names and UNKNOWN judgments are disposable contract fixtures, not real reviewer identities or creative-quality evidence. No provider inference is used and no fixture demonstrates a real B→A improvement.
- Prior ML CPQ/Adaptive focused suite: 30 passed; the CPQ-focused suite was rerun in this task as recorded below; no ML code changed. The last broader suites were not green: backend 19 operational-view/TRUNCATE errors, two saved-story retry assertions and a prompt-lineage null-version failure; ML escalation-applicability/story-duplicate failures; frontend seven failures and eight video-detail fixture errors. No clean baseline proves these are unrelated. They remain reported and were not rerun for this acceptance-only application scope.
- No application source changed during this task; no rebuild/deploy was needed. Existing deploy.sh runtime identities were rechecked and services remain healthy. Docker volumes and historical records were preserved.

## Final statuses

- `MOBILE_STEP6_ACCEPTANCE: VERIFIED`
- `CALIBRATION_INTAKE: INCOMPLETE`
- `CPQ_GRADING: INACTIVE`
- `REAL_B_TO_A_ACCEPTANCE: NOT_VERIFIED`

CPQ-focused ML rerun: `tests/test_creative_prompt_quality_v1.py` — **5 passed** in 1.76 seconds; no real inference.
