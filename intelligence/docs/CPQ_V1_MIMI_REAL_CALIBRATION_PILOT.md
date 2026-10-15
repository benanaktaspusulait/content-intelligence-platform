# Mimi real CPQ pilot — operational evidence and owner-managed continuation

Date: 2026-10-15. Latest operator direction supersedes the initial assumption that four separate people will be appointed. Roles are logical permissions. No external IdP or reviewer appointments exist, as explicitly confirmed by the owner. No new governance policy has been activated.

## Actual preparation

Four exact saved prompts and approved source have been verified against persisted records. New preparation directory: `cpq-v1-mimi-pilot-2026-10-15/`. Original prompt hash is `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`; approved story hash is `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`. Approval ID is `20b77d13-848d-46d0-ab4b-bb9b6efb0836`, source story ID `bc1cf798-d20b-4b98-8b73-56e1581c3afc`, actual text revision `candidate-2-revision-7c63cc86`. The approval-record UUID and text revision are distinct identifiers.

Analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18` remains Ruleset 1.11, 88.40625/B. Effective persisted analysis/candidate settings are ABSURD_PHYSICS, SEEDANCE_2_0_MINI, 15s, image2video, 480p, 9:16. Historical AUTO prompt footer is preserved exactly and does not override effective production context.

Each `fidelity-review/*.json` includes complete exact story/prompt, hashes/IDs, effective settings, five source-event mappings, changed-beat comparison, claimed benefit explicitly marked hypothesis, potential source conflict, execution implications and empty decision/submission template. These are evidence preparation, not completed reviews. Exact quotations have been checked, but semantic interpretation is UNKNOWN.

| Real subject | Fingerprint | Changed instruction | Independent result |
|---|---|---|---|
| Original Prompt 10/version1 | 0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98 | Baseline five beats | UNKNOWN |
| e651eb75-b894-477d-ae77-0fe6e05236da / candidate-a | 90bdda1e9cea8e2e46662821b52a01dc94359df87b7753f2c77a645c77905495 | beat_01 adds left/right cabinet/finger staging, continuous unobstructed attachment, gap/contact-edge instructions | UNKNOWN; INSUFFICIENT_EVIDENCE |
| 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-a | 218a9b367d6484d2a12bc8f6e02150f8812cdf8874c73b0171c254035a6be749 | beat_01 static close-up keeps cabinet and finger together | UNKNOWN; INSUFFICIENT_EVIDENCE |
| 9275c94b-fc35-4207-8648-dfd8d166e502 / candidate-b | 2151ed0e2d4b8afa42ea80bad8238a9a639a1be40eea6576390e04704774c746 | beat_02 tracking continuous pull/split; beat_03 static two/four/eight holds | UNKNOWN; INSUFFICIENT_EVIDENCE |

Candidate 1 has concrete staging additions to examine, but precise edge/gap control in two seconds may add execution risk. Candidate 2 changes framing with no new action or consequence; material benefit is unproven. Candidate 3 makes continuous presentation and quantity states explicit, but tracking fine hand contact and three holds inside five seconds may increase complexity. Holds and shot labels alone do not establish new progression. All retain mirror/scream/sneeze/cabinet/relief text unchanged; a real fidelity reviewer still must assess story intent, including the literal “Topla!” omission and the interpretation of nearly suffocating versus overwhelmed. Mimi's established identity is textually stated; verified visual character adherence remains unavailable.

## Blind preparation

`blind-preparation/Q01–Q04.txt` preserve exact full source bytes. JSON counterparts add only neutral ID, production settings and review instructions. Automated inspection found no original/candidate/provider/score/outcome metadata in these packets, and no provider/candidate-label or canonical-score strings in the raw prompts. No supervisor manifest is distributed to blind reviewers. Fidelity packages are a separate non-blind source review stage.

Assignment is reproducible: sort SHA-256(seed + `|` + prompt hash), with seed and true identity map exclusively in `supervisor-only/randomization-and-provenance.json`. New neutral assignments intentionally differ from the previous intake drafts. Reviewer-slot orders are Q04,Q01,Q02,Q03 and Q02,Q03,Q01,Q04; slots are not appointed identities. These reduce one fixed presentation order but do not prove statistically balanced sampling. All variants share `mimi-sticky-note` and one provisional CALIBRATION partition. No split is frozen or imported.

Official API packets issued: **0**. Completed real fidelity reviews: **0**. Completed real human or machine quality assessments: **0**. Reviewer disagreement: **not measurable yet**. Quality anchors: **none**. Real corpus/examples: **0/0**. No independent evidence supports superiority, equivalence or regression; all three material comparisons remain INSUFFICIENT_EVIDENCE. Existing model rationales and the preparer's hypotheses do not substitute for independent assessment. NO_REAL_IMPROVEMENT_PAIR_AVAILABLE remains.

## Authentication and actual blockers

Existing CPQ endpoints use trusted servlet principal and `isUserInRole`; no CPQ login/principal adapter was found in the inspected backend/nginx. There are no user/identity/reviewer/account-named tables in the local intelligence public schema. The owner confirms there is no external IdP or appointed reviewer group. This conclusion is not inferred solely from an anonymous browser.

A reusable bounded authorization pattern already exists: `RuleGovernanceController` validates `X-Rule-Governance-Token` against server configuration with constant-time comparison and fails closed when unset. The current backend has RULE_GOVERNANCE_TOKEN **unconfigured**. It protects rule-governance routes only; it does not create a named CPQ owner principal, provide browser login, or establish reviewer independence. Provider/social OAuth credentials are unrelated to owner authentication. No secret was printed or used to impersonate anyone.

Live GET capabilities confirms anonymous/all capabilities false. Existing CPQ routes, importer, blind packet, judgments and readiness are available; authenticated positive production actions cannot currently be invoked. EVIDENCE_REVIEWER gates fidelity; CREATIVE_QUALITY_REVIEWER gates blind packets/judgments; CREATIVE_QUALITY_ARCHITECTURE_APPROVER gates original binding, corpus/import and preview; PRODUCTION_OPERATOR gates persisted CPQ text assessment. These are permissions, not headcount.

**Not blocked solely by headcount:** real-input disposable testing found two additional V64 contract mismatches:

1. Saved `PRODUCTION_SETTINGS` event `2d90c69b-bcec-4871-9c4e-7e029906c974` has authoritative top-level aspectRatio/profile/generator/duration but no nested execution `settings`. `originalContext` passes this directly to `normalizedSettings`, which requires settings.aspectRatio; real Mimi preflight returns PRODUCTION_SETTINGS_BINDING_REQUIRED. The saved analysis/candidate boundRequest does contain mode/resolution/aspectRatio. Safe repair must join validated current persisted sources and reject conflicts, never invent execution defaults.
2. Actual studio session uses `storyRecordId`. Original resolution supports that field; candidate review/import still check `sourceStoryRecordId` then role-context `storyId`, neither present for these historical candidates. All three are COMPATIBLE on GET yet actual candidate review rejects “Approved story ID and revision binding are required.” A shared verified source-ID resolution should reuse the existing original/approval resolver and exact revision checks. No historical record should be patched.

The earlier V64 report established generic contract readiness, but did not prove the real Mimi positive write path. This pilot narrows that claim with actual inputs. These bugs and missing owner authentication remain even if human reviewer count changes.

**Policy blockers:** current importer requires qualified independent fidelity PASS; current quality-judgment API is human-only and the current calibration policy requires two distinct qualified reviewers plus justified anchors/thresholds. AI-generated output cannot be inserted as those human reviews. Owner sharing all logical permissions does not make self-certification independent. There is no literal four-employee policy; four separate functions and independence rules currently prevent a single actor from supplying every evidence role.

## Smallest owner-managed proposal — not applied

1. **Local owner authentication.** Reuse the existing server-side token verification pattern with a separate CPQ owner credential and fixed configured owner ID. Establish a named server-side principal with explicit owner permissions. Use a small login/session adapter with HttpOnly/SameSite cookies, CSRF protection for writes, no token storage in localStorage, no client-claimed roles, fail-closed unset configuration and no credential logging. Bind to localhost for the local setup; require TLS for remote access. No external IdP, accounts dashboard or employee directory is needed. Do not silently reuse a rule-editing secret across scopes.
2. **Two independent machine critics.** Extend the current CPQ review contract/ledger with typed MACHINE_REVIEW evidence and model/provider/version, role/purpose, exact input/output hashes, request identity, prompt/settings/rubric/policy binding, timestamps, usage/cost and evidence citations. Use independently dispatched reviews with no access to each other's answers or optimizer rationale; preferably distinct model families. Shared-model bias remains a declared limitation. Reuse current blind packets, six dimensions and comparison flow. Do not put model results into current human judgments or report simulated runs as real model results.
3. **Independent fidelity stage.** A separate source-fidelity check reads approved story and exact prompt and returns cited PASS/FAIL/UNKNOWN, including every protected anchor/event and changed beat. It must not be the generating model's self-review. Record deterministic hash/ordering checks separately from semantic machine judgment; owner confirms source authority and resolves conflicts without relabelling own approval as independent verification. Missing evidence remains UNKNOWN.
4. **Owner decision.** Present both critics, source result, disagreement, observable changes and risks; owner explicitly chooses keep original, request correction, or accept text for preparation. Human approval, machine opinion, source evidence and canonical outcome remain separate records. No candidate approval, prompt-version creation or F8/render authorization follows automatically.
5. **Ungraded pilot and later calibration.** With explicitly approved owner-machine evidence policy, permit exact-scope pilot collection/import under a versioned ungraded policy. Current human-calibrated A/A+ eligibility stays untouched and inactive. Machine agreement alone cannot qualify A/A+. No real review inference runs until separately authorized with models, per-call/total budget and retry/idempotency limits.

Minimum implementation scope: the two existing real-data mapping repairs; one narrow owner-auth adapter; typed machine provenance added to existing review persistence/API through a new migration if needed; readout in the existing CPQ area; policy-gated ungraded pilot import. No new grading engine, general identity platform or dashboard. These changes were **not implemented or deployed in this operational/proposal turn**.

## Exact decisions requiring owner approval

- Approve a named single-owner authentication and permission model, using local credentials configured by the owner; no invented account, identity or secret.
- Approve MACHINE_REVIEW as a separate evidence type, two independently executed critics and a separate source check, including eligible models and conflict/adjudication policy. Permission to use AI reviews does not authorize paid dispatch.
- Approve a versioned owner-machine **ungraded pilot** intake policy and its relationship to independent fidelity. Do not silently count machine records toward existing human-review quotas or bypass current self-certification rules.
- Separately approve any future change to A/A+ calibration/activation requirements after seeing evidence. That decision is not requested or inferred now; grading stays inactive.
- Provide a separate explicit model/cost/request authorization before any paid real test. Existing historic one-call authorizations are spent and do not carry forward.

## Evidence needed for defensible A/A+

A four-variant single-story pilot proves workflow use and helps inspect changes; it is not a calibration population. Need source-approved, settings-bound, independently judged strong/weak/equivalent/regression examples across multiple unrelated stories, profiles and generators; grouped held-out cases; reviewed anchors; critic repeatability, prompt-order sensitivity and model-family bias measurements; explicit disagreements/adjudication; false-positive/false-negative estimates and uncertainty; justified dimension/aggregate thresholds; a genuinely accepted full-pipeline B→A improvement case; and formal policy activation. Owner-reviewed anchor cases can inform a proposed revised policy but cannot be presented as multiple independent human reviewers. If a machine-assisted standard replaces the current human-calibrated standard, it must be versioned and labelled explicitly. Rendering is not necessary to evaluate textual production quality; visual fidelity and audience impact remain unverified/unmeasured until suitable evidence exists.

## Prioritized golden continuation and handoff

Existing packages were reused, not rebuilt. All nine frozen source hashes still match. All six retain SOURCE_APPROVAL_REQUIRED, PRODUCTION_SETTINGS_BINDING_REQUIRED, REVIEW_AUTHORIZATION_REQUIRED. No example is currently eligible for production import.

| Priority | Existing package | Smallest specific settings/provenance action |
|---|---|---|
| 1 | P03 Lamp | Explicit 15s source declaration; owner identifies separate story/revision and confirms generator/profile/settings |
| 2 | P01 Sticky Ball | 15s timeline; preserve sticky-deformation story and bind exact execution settings |
| 3 | P05 Missing Carrot | Source ends at 17s; confirm exact supported target without silent truncation |
| 4 | P02 Upside-Down Chair | Resolve 15–18s range to exact production target and approved source |
| 5 | P04 Missing Shoe | Resolve 15–18s range, preserve reveal and establish actual settings |
| 6 | P06 Island Journal | Preserve 25.5s long-form context; confirm generator support, story scope and settings |

Detailed source hashes, exact existing package paths, responsible logical permissions and next actions are in `golden-prioritized-intake-queue.json`. Priority reflects apparent intake effort, not quality or popularity.

| Operation | Responsible permission / person | Evidence and action | Next step |
|---|---|---|---|
| Establish owner identity | Actual owner | Approve small auth model; configure own credential privately; verify capability endpoint | Authenticated operations possible |
| Bind Mimi original | Owner with architecture permission, after technical repairs | Exact original hash + actual story/approval + joined current settings; POST `/cpq/original-prompts/preflight`, then `/bindings` with concrete rationale | Real immutable subject, no PASS implied |
| Source fidelity | Current authorized independent human, or approved future distinct machine source checker | Review `fidelity-review/*.json`; fill evidence/rationale/expiry and protected mappings; original `/cpq/original-prompts/{subjectId}/fidelity-review`; candidates `/records/{analysis}/comparisons/{comparison}/candidates/{candidate}/fidelity-review` | Qualified evidence only under applicable evidence policy |
| Blind review | Two genuine qualified humans under current policy, or two separately authorized critics under new machine policy | Only `blind-preparation/` and effective settings; no supervisor/previous-review access; six dimension citations, strengths, weaknesses, opportunities, constraints, uncertainty | Two transparent independent assessments, conflicts visible |
| Import pilot | Authenticated owner with architecture permission + explicit import authorization + policy-qualified fidelity | Existing `/cpq/calibration/corpora/{version}` then `/examples`; exact story/revision/settings/fingerprints and one split | Ungraded qualified pilot examples |
| Human judgment submission today | Actual authenticated human quality reviewer only | GET `/cpq/calibration/examples/{exampleId}/blind-review`; POST `/judgments` with cpq-human-blind-review-v2 | Never submit AI answers here |
| Material decision | Owner after independent comparison evidence | Actual beat changes and critic/fidelity/risk results, including disagreement | KEEP_ORIGINAL or explicit bounded next action; no automatic prompt or render approval |
| Golden authority | Owner/source approver | Existing `/creative-role/{id}/approve-story` with real source/candidate/revision/fingerprint, not copied prompt; separately confirm settings | Original fidelity preflight becomes meaningful |

All paths use `/api/v1/intelligence/workflow` prefix. Readiness and preview are diagnostic and cannot activate grading.

## Engineering verification and production integrity

Added an isolated real-saved-input diagnostic to the existing OriginalCpqFidelityIntegrationTest, using exact persisted field projections for 10 prerequisite events plus exact prompt. It verifies story/prompt/candidate fingerprints, actual three COMPATIBLE bindings, the real original settings blocker and all three candidate story-binding rejections, unchanged 88.40625 canonical scores, no created review/original subject, inactive grading, no ML transport calls and unchanged disposable historical event digest. The initial positive-flow attempt failed at real settings resolution; that result is preserved, not presented as successful real pilot execution. A transient test edit compilation error was corrected before final verification.

Final focused run: **18 tests passed, 0 failures/errors/skips** (existing 17 plus the real-saved-input blocker diagnostic). No application code changed; frontend/ML suites were not rerun because this turn changes offline preparation and one backend test only. The previous broader suite failures remain unresolved as recorded in the prior intake report; this focused result does not establish a clean full-suite baseline.

Prior generic tests still cover successful original→fidelity→import→two-human-fixture-review→disagreement→preview and candidate import, expiry/conflict/auth/scope/leakage failures. Those are implementation fixtures, not real human reviews. Full real four-subject positive import, human/machine review, material equivalence/regression conclusions and actual rendering remain **not executed** because the demonstrated data/auth/policy prerequisites are unresolved. No mocked judgment establishes quality.

Current runtime unchanged: V64, backend image `sha256:dd73b57f02097fe7382cd9293b257afe53d487c5ce2507c96657e4f9d358b74c`. No application logic changed and no rebuild/deploy was performed. Read-only integrity recheck matches the prior V64 snapshot: Prompt10 hash unchanged, 75 workflow events, eight comparisons, ordered payload digest `e7e55725c68f7c27d61183b854b4b1b7799b410814acde27ca2db69fa3190275`, all CPQ write counts zero, activation false. API snapshots and hashes are under `evidence/`. No paid inference, generated candidate, production review/import/corpus, identity grant, story/prompt/canonical mutation, render/publication, database write, commit/push or Docker cleanup occurred.

## Independent statuses

| Status | Result | Basis |
|---|---|---|
| MIMI_SOURCE_FIDELITY | BLOCKED | Complete evidence prepared; actual original settings/candidate source-ID mapping and authentication unresolved; no real reviews |
| MIMI_BLIND_CREATIVE_REVIEW | INCOMPLETE | Four exact reproducibly ordered drafts ready, no official imported examples or actual reviewers; machine policy not yet approved |
| MIMI_MATERIAL_IMPROVEMENT | INSUFFICIENT_EVIDENCE | Concrete changed instructions documented; no independent comparative judgments |
| CALIBRATION_PILOT | PREPARATION_ONLY | No corpus/import/review evidence created |
| GOLDEN_CALIBRATION_EXPANSION | PARTIALLY_READY | Existing six packages intact; exact prioritized owner actions prepared |
| CPQ_GRADING | INACTIVE | Existing policy preserved |
| REAL_B_TO_A_ACCEPTANCE | NOT_VERIFIED | No independent accepted improvement pair |
