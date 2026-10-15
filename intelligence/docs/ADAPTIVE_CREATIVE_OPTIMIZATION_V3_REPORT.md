# Adaptive Creative Optimization V3 — Implementation and acceptance report

Date: 2026-10-15. **Final status: ADAPTIVE_CREATIVE_OPTIMIZATION_V3_INCOMPLETE.**

The worklist was created first and implementation followed the required order. The grade audit preceded routing edits. Configurable adapters, bounded routing, durable authorization, target-aware policy and UI are implemented and deployed. Actual saved Mimi acceptance correctly stops before dispatch. However, a legitimate independently evidenced B→A candidate has **not** traversed the complete built application pipeline. Controlled policy/transport fixtures exercise the A branches; they do not close that product acceptance gap. Real-model creative effectiveness remains **UNVERIFIED**. No real inference was authorized or executed in this task.

## 1. Actual A/A+ definitions

Canonical Ruleset 1.11 uses A >=92, B >=80, C >=60, otherwise F. A+ does not exist; V3 does not emit A_PLUS_QUALIFIED. The rule engine normalizes the weighted mean over families with numeric evidence. UNKNOWN/NA/service errors/evidence-incomplete failures do not become PASS or zero. An evaluated PASS earns 100 only with configured PASS severity; other successful severities earn 85. Render admission independently requires its own gates. See [the prior-to-routing audit](ADAPTIVE_CREATIVE_OPTIMIZATION_V3_GRADE_AUDIT.md) for every loss and executable code references.

## 2. Mimi feasibility and constraints

Authoritative analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`, Content 10, Prompt 10/v1, SHA-256 `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`: **88.40625/B**. Numeric family denominator 0.96. Optimistically upgrading the two potentially addressable novelty/salience rows while keeping currently eligible evidence, protected events/windows and evaluator semantics gives **89.3125/B**. This is a conditional bound, not an achieved score or a universal bound after new independent evidence changes denominators. Even additionally removing the full fragile-interaction penalty would give 91.395833333/B; V3 does not remove it.

ATTEMPT_001 loses 4.166666667 overall points because the story has two genuine attempts versus the required three. No third event is invented. A governed exception affects admission only and cannot change FAIL or score. Several already successful rules have fixed 85-point branches. Missing visual/semantic evidence is preserved. The live official preflight returns **TARGET_BLOCKED_BY_STORY_CONSTRAINT**, with generationAllowed=false. Both hypothetical primary and escalation are suppressed.

## 3. Previous real-model failure causes

The original broad temporal guard rejected valid source beat windows. The actual second response also contains six natural-language spatial references instead of catalog IDs (2 in A, 4 in B), and largely paraphrases source actions. Its immutable raw fixture remains byte-identical, SHA-256 `0783b28b78e18bcdfa3c2ac14aec5266e91a15e89b65aaedea489c09c7ab95e0`. Correct replay reports technical INVALID, semantic fidelity UNKNOWN, creative VALID_BUT_EQUIVALENT; exact source windows are non-material advisories, not story violations. No canonical candidate evaluation is invented for rejected outputs.

## 4. Contract repairs retained and extended

Existing model-authored-production-v2 source references, per-kind/per-beat validation, temporal evidence and materiality guards are retained. Historical V1/template interpretation remains readable. V3 reuses that compiler and adds typed cross-beat dependency IDs plus justification; invented, self, duplicate or absent changed-beat dependencies fail. Dynamic schemas constrain references and opportunity IDs; schema constraint discovery now supports the adaptive intervention subtype. Full unchanged narratives/settings are assembled with exact model/compiler/source attribution. Cosmetic expansion, unsupported timing/events/claims and moving-contact execution regressions remain rejected.

## 5. Provider capability comparison

Capability configuration is data, not hardcoded generation logic: `intelligence/data/workflow/creative-provider-profiles-v3.json`. Documentation was fetched on 2026-10-15. Account-level availability remains unverified; there was no authenticated model-discovery request.

| Configured profile | Transport and structure | Documented bounds / costing |
|---|---|---|
| DeepSeek primary: deepseek-v4-pro | Chat Completions at api.deepseek.com; JSON object output; same schema sent as instructions and deterministically validated. No assumption of Chat response-format JSON Schema support. | Documented 1M context, maximum 393216 output. Peak cache-miss upper rates $1.32 input / $3.96 output per million; cached input $0.044. Thinking high; no temperature. |
| OpenAI escalation: gpt-6.1-sol | Chat Completions, strict JSON Schema, max_completion_tokens, reasoning_effort high; no temperature. | Documented 1.05M context, 128000 output. Standard short-context $2 input / $10 output, $0.10 cached and $2.50 cache-write input. Configuration conservatively reserves $2.50 input; long context and fast/ultrafast are not dispatched. |

DeepSeek publishes model-version/legacy-alias and variable peak/off-peak behavior; the profile records the documented version and conservatively avoids assuming discounts. [DeepSeek model/pricing documentation](https://api-docs.deepseek.com/quick_start/pricing/) and [Chat Completions contract](https://api-docs.deepseek.com/api/create-chat-completion/) support its profile. OpenAI's [model specification](https://developers.openai.com/api/docs/models/gpt-6.1-sol) and [parameter compatibility guidance](https://developers.openai.com/api/docs/guides/latest-model) support its profile. The inspected GPT-4.1 snapshot is labelled deprecated in its [official specification](https://developers.openai.com/api/docs/models/gpt-4.1); no silent replacement or old authorization is used. Model/profile changes invalidate the authorization binding.

## 6. DeepSeek adapter

`CreativeCapabilityProvider` extends the existing provider interface. The existing paid role selects the server-owned profile; endpoint, model, reasoning, token parameter, prices and context limits are verified before SDK construction. JSON mode receives the same source-catalog schema in its system instructions. Raw content, usage, completion ID and finish reason remain recoverable through existing durable roles. Reasoning content is not substituted for a production plan. SDK retries are zero; incomplete output fails without a retry or fallback.

## 7. OpenAI escalation

The existing WorkflowService stage performs reconstruction, source-plan production, local review, canonical evaluation and immutable comparison persistence. V3 calls that same stage conditionally. Escalation receives the complete original/story, validated material changes, canonical deficits, critic risk and rejection evidence. Rejected drafts are not preferred instructions. OpenAI is not dispatched after a qualified primary or shared contract failure, or without exact secondary authorization/budget.

## 8. Conditional routing

Modes: DEEPSEEK_ONLY, OPENAI_ONLY, ADAPTIVE. Primary generation → validation → independent policy decision. A-qualified primary stops; material B remains IMPROVED_BELOW_TARGET and may justify escalation; equivalent/regressed drafts retain failure evidence. Missing second-provider consent returns AWAITING_ESCALATION_AUTHORIZATION, never an automatic call. Both below target return TARGET_NOT_REACHED. Technical/unknown provider outcomes stop. Missing evidence/story conflicts stop before generation. State history includes generation/validation, escalation recommendation and operator review; A+ remains inactive.

A replay of an interrupted durable generation returns the recorded unresolved state and zero new calls. It does not resume dispatch. Fresh authorization must never be inferred from remaining money.

## 9. Authorization, budget and safety

The public command validates source/analysis/settings, exact profile/model/provider, one request per provider, provider count, explicit confirmation, positive combined USD ceiling, output tokens, rounds and latency. Initial ceilings: two providers, one request each, one round, 4000 output tokens, 120 seconds total, maximum allowed explicit ceiling $20. These are ceilings, not expenditure authorization. Profile/model binding, source SHA, story SHA, analysis, production-settings record and grant/limit/budget scope are bound to one authorization UUID. Rebinding it is rejected.

Advisory transaction locks serialize duplicate commands. Append-only REQUIRES_NEW run/role records reserve before dispatch. The next stage receives only remaining settled budget. Missing settled usage/cost blocks the next call and is represented as UNKNOWN, not zero. Byte-based input reservation is conservative; configured variable-pricing estimates are explicitly labelled calculated upper bounds, not exact invoices. Provider SDK timeout is at most 20 seconds and bounded by remaining total latency.

All PROMPT_OPTIMIZATION HTTP dispatches require an HMAC over the exact backend request body. The server token is configured in the ignored local environment and never returned to the browser. The provider profile is rechecked inside ML. Direct unsigned requests, client-supplied server context, unapproved models and excessive limits are rejected. Historical recovery remains provider-free. There is no automatically approved candidate, prompt version, exception or render.

## 10. Diagnosis and targeted editing

Existing V2 diagnosis, full protected source/story and reference catalog are reused. The model returns targeted production interventions; it cannot submit an arbitrary full rewritten winner. Unaffected narrative remains byte-preserved. Relevant multiple beats are allowed; declared cross-beat dependencies must identify another changed beat and explain necessity. No fixed Mimi-specific staging answer is injected into new authored requests.

## 11. Materiality and creative dimensions

Existing contact geometry/state progression and execution validators independently reject paraphrases, camera-only changes, arbitrary timestamp splits and unsupported additions. The six existing dimensions are reported separately as source-supported changes/hypotheses, unchanged, regression or missing evidence; visual/audience benefit is never inferred from instruction length. Critic/canonical/source/risk evidence remains distinct. Controlled authored contact and 2→4→8 fixtures demonstrate contract/recognition capability, not autonomous creativity.

## 12. Grade-aware qualification and remaining gap

A number alone is insufficient. V3 checks same Ruleset 1.11, actual A grade and score >=92, material evidence, approval eligibility, no canonical/production regression, applicable hard blockers/evidence, source fidelity and critic status. B is always BEST AVAILABLE DRAFT. Qualified A is TARGET-QUALIFIED FINAL CANDIDATE offered for operator review; selection/approval remain explicit.

**Unclosed producer/consumer gap:** the existing compiler intentionally emits semanticFidelity UNKNOWN. The stricter final qualifier requires independent PASS. There is currently no completed, scoped independent semantic-evidence projection through this generation path that establishes that PASS. Weakening UNKNOWN to PASS would violate the task. The offline A policy oracle supplies hypothetical independent evidence, so it proves conditional routing only. Therefore the complete built A-success path cannot yet be declared accepted. [The inactive ADR proposal](ADR_CREATIVE_V3_PRE_RENDER_QUALITY_DRAFT.md) describes the required evidence/scope decision and calibration conditions; it activates nothing.

## 13. Same-ruleset comparison evidence

Actual saved Mimi remains 88.40625/B. No new DeepSeek/OpenAI candidate was generated for it. The original and previous authored fixtures pass source/canonical integration at unchanged canonical score, with source semantics UNKNOWN and actual visual benefit unverified. New controlled policy fixtures use common Ruleset 1.11 A/B/regression assessment oracles to test primary stop, conditional escalation, same-score materiality and below-target reporting. They are not an approved, end-to-end B→A golden case and are never persisted into production.

Both provider stages are retained in run evidence; the UI can open either provider comparison without selecting or approving it. Selection remains conservative when superiority is unsupported, rather than sorting by length, score or generation order as evidence of quality.

## 14. Regression results

- ML: **269 passed** (25 new V3 tests plus existing contract, reconstruction, canonical, source/fidelity, distinctness, F8 and Ruleset 1.11 regressions).
- Backend: **56 passed, 3 conditional legacy tests skipped**, zero failures/errors. Includes nine new disposable-PostgreSQL V3 authorization/routing/durability cases. Skips require optimization.liveMock, optimization.planFirstMock or ruleset.liveMock system properties; they are not counted as passed.
- Frontend: **72 passed**, including no-call feasibility and exact-consent reset checks; production build succeeded.
- Render policy/queue: **44 passed**, zero failures.

Evidence: `output/verification/adaptive-creative-v3/*-regression.txt`; backend/render Surefire XML retains individual counts.

## 15. Actual mocked no-egress workflow and coverage

Ran `python3 intelligence/scripts/verify-creative-v2.py --adaptive-v3 --keep` using built backend/ML/frontend images and a disposable PostgreSQL clone. The repository live-target isolation guard passed before writes. Temporary DB host ingress was detached before cloning records or running commands. Backend, ML, mock and DB had only the Docker internal network; only nginx provided host ingress. Mock credentials only. Production was SELECT-only.

The official command received actual Content 10 / Prompt 10/v1 / current analysis twice. Both returned TARGET_BLOCKED_BY_STORY_CONSTRAINT with zero provider calls, no new test workflow records and unchanged prompt. Mock request log stayed empty. The actual Step 6 browser control also displayed the same block and disabled generation.

| Acceptance requirement | Evidence / honest scope |
|---|---|
| 1. Legitimate approved B→A path | **OPEN**: synthetic score feasibility fixture only; no approved full-pipeline golden A. |
| 2. DeepSeek A stops | Backend durable routing oracle and ML qualifier tests; full A-producing workflow still OPEN. |
| 3. Material B escalates | Backend mock stage/settled budget test. |
| 4. Equivalent output escalates only with consent | Backend routing and source/materiality tests. |
| 5. Regression rejected | ML independent source/canonical/risk negative cases. |
| 6. Shared technical failure stops | ML stage decision plus backend one-stage stop. |
| 7. OpenAI A final | Backend two-stage controlled oracle; full independently evidenced A pipeline OPEN. |
| 8. Both B not successful | Backend two-stage test returns TARGET_NOT_REACHED. |
| 9. Missing visual evidence | ML preflight and final qualification negative tests. |
| 10. Protected story/governance | Actual no-egress Mimi command + browser; no third attempt/exception. |
| 11. No second consent | Backend one dispatch and AWAITING_ESCALATION_AUTHORIZATION. |
| 12. Budget exhausted | Backend prevents second stage; ML refuses undersized budget before SDK creation. |
| 13. Duplicate charge | Durable backend authorization replay; actual blocked command repeated with no dispatch. |
| 14. Partial/ambiguous failure | PostgreSQL reservation survives thrown interruption; replay never calls stage. |
| 15. Reference IDs | Exact real response replay and per-kind/per-beat negative tests. |
| 16. Existing time windows | Deterministic corrected-contract tests; no materiality credit. |
| 17. Invented sub-beat times | Rejected by retained temporal/source guards. |
| 18. Historical responses | Untouched second-response fixture A/B, plus first-response compatibility regressions. |
| 19. Same score material | Recognized as draft progress, never A completion. |
| 20. Immutability | Source/story/settings/current analysis and all 75 production workflow rows unchanged. |

This matrix deliberately does not describe layered mocked tests as a fully accepted A-producing end-to-end workflow.

## 16. Deployment and actual browser

Used deploy.sh for ML/backend/frontend, then rebuilt affected images after final fixes. Health/image checks passed. Six ML source hashes match active containers; compiled backend contains V3, preflight and signed dispatch markers. Actual production Step 6 was opened, the feasibility button clicked and its result asserted in the DOM. Desktop and 390px mobile screenshots were inspected; the mobile grid was corrected to prevent long-state/model controls from forcing wide columns. Generation remains disabled. The isolated browser displayed the same built workflow; no provider/approval/render button was submitted in production.

Runtime hashes/image IDs and browser evidence: `output/verification/adaptive-creative-v3/runtime-verification.json`, `live-browser-verification.txt`, screenshots and `isolated/`.

## 17. Production integrity and downstream safety

All **75** production workflow IDs/payload hashes are unchanged. Original Prompt 10/v1 remains the only version for Content 10. Current analysis JSON, approved-story provenance and production-settings JSON are identical before/after. Historical Ruleset 1.7–1.11 analyses, provider responses and comparisons were not overwritten. No canonical rule/weight/threshold changed. No ATTEMPT_COUNT_EXCEPTION_V1 decision or text acceptance was submitted. Missing verified Mimi reference and accepted start frame continue blocking F8; a text grade cannot authorize render queue admission. Governance/F8/queue regressions passed.

## 18. Remaining architecture decisions

Close the source-fidelity evidence/qualification contract without treating UNKNOWN as PASS. Supply an existing approved golden case with independent evidence and a source-faithful, objectively repairable canonical B→A path; run it through built generation, compilation, source validation, canonical evaluation, critic, comparison and durable routing on the internal test network. Clarify whether canonical severity-derived successful-row caps are intended through governance rather than changing scores here. Consider a separately governed pre-render rubric only after calibration/approval; the draft ADR has no active effect.

Metrics contracts separate real/mock, provider/model and routing cohorts; report qualification/materiality/regression/source/contract/risk/cost/call/stop/escalation outcomes, with missing creative judgments and audience outcomes null. Operator acceptance requires explicit persisted decision evidence; unreviewed drafts are not accepted successes. No dashboard was added. A fully connected independent-evidence and operator-acceptance reporting projection remains part of the unclosed end-to-end acceptance.

## 19. Requirements for a later real test

First close the offline golden-case and evidence-binding gaps. For Mimi specifically, resolve the current canonical-target constraints with legitimate new independent evidence/approved architecture and a separately authorized official analysis; do not add prohibited story events or relabel B. Then obtain fresh operator authorization covering exact configured provider/model/profile, request count, combined budget, output tokens, rounds and latency. Adaptive consent must explicitly cover both stages to permit the second. Old one-call authorizations are consumed and are not reused. Check account model availability, current pricing/capabilities, immutable source/analysis/settings and durable prior dispatch before any call. Stop on ambiguous outcome, unavailable model or failed budget binding. Real creative effectiveness stays UNVERIFIED until that separately authorized test.

## 20. Evidence of zero real paid calls and changed files

Actual real inference requests **0**; actual provider expenditure **$0**. SDK tests use patched transports; the built no-egress acceptance has fake keys and an empty provider request log. Production workflow count/hashes and prior paid-attempt records are unchanged. Public official documentation reads were not inference calls. No image/video generation, publishing, prompt/story modification, new prompt approval, historical overwrite, direct production SQL writes, commit or push was performed.

Changed implementation files:

- ML workflow: `adaptive_optimization.py`, `creative_provider_profiles.py`, `creative_roles.py`, `creative_reconstruction.py`, `model_authored_execution.py`, `api.py`.
- Capability data: `intelligence/data/workflow/creative-provider-profiles-v3.json`.
- Backend: `WorkflowService.java`, `WorkflowController.java`, `QualityMlClient.java`.
- Frontend: `post-family-workflow.component.ts`.
- Tests: V3 ML tests and signed HTTP helper; existing three ML HTTP test callers; workflow PostgreSQL tests; frontend workflow tests.
- Harness: `intelligence/scripts/verify-creative-v2.py --adaptive-v3`.
- Documentation: worklist, grade audit, this report and inactive ADR proposal. Shared dispatch secret exists only in ignored local configuration; value omitted.

**ADAPTIVE_CREATIVE_OPTIMIZATION_V3_INCOMPLETE** — implemented safe routing and Mimi stop are verified; complete independently evidenced A-producing product acceptance remains open. No real creative-success claim is made.
