TASK: STORY_REVIEW_DERIVED_VERDICT_AND_ANCHOR_SCOPE_FIX

HISTORICAL_REAL_REVIEW_ATTEMPTS: 4
HISTORICAL_ACCEPTED_REVIEWS: 0
V4_SCHEMA_VALIDATION: PASS
V4_EVIDENCE_REFERENCE_VALIDATION: PASS
V4_AGGREGATION_VALIDATION: FAIL
V4_HISTORICAL_STATE: STOPPED
V4_HISTORICAL_RECEIPT_UNCHANGED: YES
MODEL_AUTHORED_SEMANTIC_AGGREGATE_REMOVED: YES
APPLICATION_DERIVED_SEMANTIC_AGGREGATE: VERIFIED
APPLICATION_DERIVED_UNKNOWN_DETAILS: VERIFIED
APPLICATION_DERIVED_OWNER_ELIGIBILITY: VERIFIED
SOURCE_CHECK_SEMANTICS_CLARIFIED: YES
TRIGGER_CONDITIONS_MEANING: VERIFIED
SINGLE_MECHANIC_MEANING: VERIFIED
PROTECTED_FACT_ANCHOR_MAPPING: VERIFIED
IRRELEVANT_SOURCE_ANCHOR_HANDLING: VERIFIED
A_B_EVIDENCE_ISOLATION: VERIFIED
CREATIVE_COMPARISON_CONTRACT: VERIFIED
NO_MATERIAL_IMPROVEMENT: SUPPORTED
NO_CREATIVE_WINNER: SUPPORTED
ML_REGRESSION_TESTS: 387 PASSED; EXIT 0
JAVA_REGRESSION_TESTS: 50 PASSED; EXIT 0
DISPOSABLE_HTTP_E2E: 12 SCENARIOS + 1 FINAL SOURCE-SPECIFIC UNKNOWN SCENARIO PASSED; EXIT 0
HISTORICAL_RECEIPTS_UNCHANGED: YES
HISTORICAL_PROVIDER_CSVS_UNCHANGED: YES
NEW_REAL_PROVIDER_CALLS: 0
NEW_PROVIDER_SPEND_USD: 0
STORY_APPROVALS: 0
BUILD_PROMPT_CALLS: 0
VIDEO_RENDERS: 0
PRODUCTION_DB_WRITES: 0
NEXT_MAX_PROVIDER_REQUESTS: 1
NEXT_MAX_RESERVED_USD: 0.006127
NEXT_OWNER_PAID_AUTHORIZATION: NOT_GRANTED
READY_FOR_NEXT_REAL_REVIEW: YES

“VERIFIED” denotes application contract, mechanical provenance checks and offline integration. It does not certify the next real model's interpretation or creative quality. No real provider request was made.

## A. Exact V4 failure and root causes

The unchanged genuine V4 run `a9f02bcf-7371-4f5a-bb2b-8fddd70712ab` remains STOPPED. Its actual model `gpt-4o-mini-2024-07-18` returned seven PASS and two UNKNOWN findings per candidate, but also claimed `SEMANTIC_SOURCE_PASS` and empty `sourceUnknowns`. The old contract correctly rejected `Uncertain/failed semantics cannot become PASS`. Historical cost remains $0.0023658 calculated from 8,461 tokens; invoice verification remains UNVERIFIED.

Three separate issues are addressed prospectively:

1. Redundant deterministic calculations were assigned to the model and could contradict its own findings.
2. Check names lacked explicit purpose: the model treated `trigger_conditions` as sneeze initiation and `single_mechanic` as whether sneezing was the only mechanism. Those questions concern the protected impossible rule, not every release/ordinary event.
3. Authentic IDs established provenance but not relevance. V4 cited source S06, a covered-state/sneeze-release span, for multiplication-rule claims. Its ENDING_REPLAY citations were A05/B05, middle-story spans. The local resolver did not previously check these mechanically available scopes.

V4's six creative descriptions were identical across A/B. Its raw NO_MATERIAL_IMPROVEMENT / NO_CREATIVE_WINNER opinions remain historically unvalidated. Nothing converts this rejected response into successful evidence.

## B. Model versus application ownership

| Information | Before | Prospective contract |
|---|---|---|
| Nine semantic opinions, reasons and evidence IDs | Model | Model, unchanged responsibilities |
| Overall source result | Model, checked locally | Application derives FAIL > UNKNOWN > PASS |
| Unknown questions | Separate model summary | Application copies each UNKNOWN check and its exact reason |
| Owner-proposal eligibility | Model boolean, locally checked | Application derives from valid complete assessment, source PASS, supported materiality and approved research policy |
| Six creative findings and baseline-relative conclusion | Model | Model, with clearer comparative grounding |
| Qualitative research preference | Rejected if preferred candidate ineligible | Preserved as machine opinion; ineligibility reasons separately recorded |
| Source document/offset integrity and anchor coverage | Application provenance | Application provenance plus mechanically derived anchor/boundary coverage |
| Story/source/BUILD_PROMPT/render approval | Owner and existing gates | Unchanged; research cannot approve production |

The strict provider contract is now `assessment-only-story-review-v4-derived-verdict` (future execution attempt V5, not a rewrite of historical attempt V4). Its A/B objects have only `semanticChecks`, `creativeDimensions` and `creativeConclusion`. Strict schema forbids model-authored `semanticOutcome`, `sourceUnknowns` and `eligibleForOwnerProposal`.

Raw response bytes, full SDK response, parsed model `result`, and original checkpoints remain separate and unchanged. `derivedAssessment` contains application-calculated results, exact raw-response SHA, machine-preference attribution and explicit closed production gates. The Java `researchAssessment` consumer reads this derived record; individual model findings remain in the preserved receipt's `result`.

Production code changed only:

- `intelligence/ml-service/app/workflow/story_assessment.py`: prospective response schema, concise reviewer contract, anchor relevance, deterministic derived result.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/StoryEvolutionService.java`: research result consumes `derivedAssessment`.

Test updates: `StoryExperimentContractTest.java`, `story_experiment_fixture.py`, `story_assessment_cases.py`, `test_story_assessment_strict_contract.py`, `test_story_assessment_transport.py`; added `test_story_assessment_derived.py`. No migration, scoring code, provider adapter, timeout implementation, new service, dashboard or review framework changed.

## C. Deterministic aggregation and UNKNOWN handling

`semantic_summary` derives FAIL when any individual finding fails; otherwise UNKNOWN when any finding is unknown; otherwise PASS. The schema/validator first requires all nine findings and valid outcome/basis pairs. An empty or incomplete provider assessment cannot use this path to pass.

`sourceUnknowns` is a list of `{check, reason}` derived solely from UNKNOWN findings. Reasons are preserved exactly. It is never a second model-authored summary. Valid source UNKNOWN and FAIL are completed assessment outcomes, not technical failures.

Eligibility requires a complete valid review, source PASS, validated MATERIAL_IMPROVEMENT and the existing approved assessment-only research policy. Restriction codes include `SEMANTIC_SOURCE_UNKNOWN`, `SEMANTIC_SOURCE_FAIL`, `NO_SUPPORTED_MATERIAL_IMPROVEMENT` and `RESEARCH_POLICY_NOT_AUTHORIZED`. A preferred candidate may remain ineligible; the model's preference is not rewritten or used as permission.

Even an eligible research proposal retains `ownerDecision=PENDING`, `sourceApproved=false`, `buildPromptAuthorized=false`, `renderAuthorized=false`, `officialAPlus=INACTIVE`. Existing Java approval and handoff endpoints still deny these research runs.

## D. Source semantics and protected-fact relevance

The original five locks and their offsets are unchanged. `check_scope` validates every authoritative source range against the original text, then derives evidence groups by interval intersection with the existing lossless catalog. Production code contains no Pip, sticky-note, sneeze or S05/S06-specific rule.

| Check | Meaning / authoritative anchor |
|---|---|
| identity | Same protected character identity; identity lock |
| premise | Same protected initial impossible situation; premise lock |
| rule | Same primary impossible physical rule; rule lock |
| trigger_conditions | Conditions activating that impossible rule; rule lock |
| single_mechanic | Same primary impossible mechanism; rule lock. Ordinary actions/release events need not be that mechanism. |
| causal_clarity | Understandable action-to-impossible-consequence relationship/order; rule anchor plus selected context |
| continuity | Protected held state and release transition; continuity lock |
| ending | Protected final state; ending lock |
| protected_events | Only the explicitly locked facts/events; all five lock groups for definite PASS, relevant group for FAIL/UNKNOWN |

For this exact archived source, identity/premise intersect S01, rule/trigger/mechanic/causality intersect S05, continuity intersects S06 and ending intersects S07. These IDs are calculated outputs, not production constants. A definite rule/trigger claim supported only by S06 is rejected. Selecting S05 plus additional S02/S03/S04/S06 context remains allowed. Source UNKNOWN may use empty evidence arrays with a meaningful unresolved reason; when source IDs are selected, their anchor scope is checked.

For missing direct mappings, the mapping helper reports `unmappedAnchors`; it does not guess ranges or synthesize locks. The admitted P2 scope still requires exactly the existing five trusted anchors, all of which map here. A generic second-story offset test confirms that mapping does not depend on this character or wording.

Mapping is NOT semantic proof: S05 also contains incidental mirror staging, and matching that sentence cannot prove that a model interpreted the rule correctly. Causal order, candidate action intention and actual protected-state preservation still require honest model interpretation/UNKNOWN. Candidate A's initial hand shaking is not forced to PASS or FAIL. No mirror action becomes a new protected event.

## E. Creative evaluation safeguards

The same six dimensions remain mandatory. The shorter replacement system prompt asks for concrete baseline/candidate actions and states rather than generic duplicated prose, and distinguishes source activation from ordinary release. Complete original narratives, provenance, settings, five locks and unchanged evidence catalog remain available.

MATERIAL_IMPROVEMENT retains existing baseline/candidate evidence, concrete action/state/consequence, addressed weakness, new risk and materiality requirements. Cosmetic changes, unsupported generic claims and invented measured audience/render/A+ results remain rejected. Valid conservative NO_MATERIAL_IMPROVEMENT and NO_CREATIVE_WINNER do not require inventing a gain or distinction.

For supported SCROLL_STOP_VISUAL_PROMISE and ENDING_REPLAY findings, the resolver requires the candidate's ordered opening/final catalog span respectively; additional contextual spans are allowed. Empty evidence with explicit UNKNOWN remains valid. This detects V4's middle-story-only ending citations without frame timings, seamless-loop requirements or semantic keyword heuristics. It establishes document-boundary relevance, not actual rendering quality or that every word of an interpretation is justified.

No new creative score, canonical rule, weight or audience-success metric was introduced.

## F. Historical replay and preservation

`v4-read-only-diagnostic.json` records the genuine unchanged response under its original archived validator: the same aggregation rejection. New-schema validation also rejects this historical old-contract response. A separate diagnostic derives UNKNOWN plus the two exact model reasons per candidate, records false eligibility, highlights the S06/rule-anchor mismatch and the incorrect ending evidence. This diagnostic is not an accepted machine assessment or a replacement historical verdict.

`historical-integrity.json` verifies 275 files from the current before-edit snapshot and the 164-file prior V4 integrity snapshot, including all four historical dumps, raw receipts, source archives and official provider CSVs. All four real runs remain STOPPED. V3 remains DISPATCH_UNCERTAIN with request-level billing INCONCLUSIVE; no reservation was released/reused. A's historical model mismatch and B's historical invalid continuity citation remain intact.

## G. Offline regression

- ML: 387 passed, 343 existing warnings, exit 0. Includes source/creative review contracts, provider/accounting, adaptive optimization, canonical hook stability, story evidence and F8 gates.
- Java: 50 passed, zero failures/errors/skips, exit 0: StoryExperimentContractTest 41, StoryEvolutionServiceTest 5, StoryReviewIndependenceTest 2, QualityMlAssessmentTimeoutTest 2.
- Focused assessment suite: 174 passed before the final full-suite run.
- Native installed SDK default-client timeout values and max_retries verified; actual SDK serialized body measured through mocked HTTP, not estimated.
- `git diff --check` passed.

Targeted tests cover all-PASS, UNKNOWN, FAIL and mixed precedence; no aggregate fields; exact UNKNOWN reasons; source FAIL/UNKNOWN/no-materiality/no-policy ineligibility; research eligibility without approval; preserved preference with ineligibility; generic trigger/mechanic definitions; wrong rule and creative boundary anchors; paraphrases, ambiguous triggers, real contradiction references; A/B isolation; every mandatory check/dimension; unsupported materiality; conservative/no-winner results; historical rejection and stale paid authorization.

Initial test-harness runs exposed missing local test environment values (ML data root and Java offline HMAC token), not application defects; final runs used the existing data root and test-only token. The first HTTP verifier compared JSONB object iteration order with a preserved list; its assertion was corrected to compare exact check→reason mappings. That saved positive run was inspected without redispatch. Initial logs are retained; no failure was hidden or repaired through an AI call.

## H. Disposable application HTTP E2E

Real Java backend + FastAPI + dedicated PostgreSQL restored from the original P2 snapshot + OWNER login/session/CSRF + HMAC + scheduler + V71 ledger + installed OpenAI SDK were used. Only external OpenAI HTTP was mocked, with an offline placeholder credential. ML external sockets/DNS were denied, Java could connect only to its own database/ML ports, and no production credentials were loaded.

The main 12 scenarios: positive UNKNOWN; conservative NO_MATERIAL_IMPROVEMENT; missing check; fabricated ID; wrong protected source anchor; cross-candidate reference; unsupported definite source claim; unsupported material improvement; irrelevant ending citation; forbidden model aggregate; provider refusal; timeout. Expected outcomes passed, including exact one mocked SDK call/reservation/receipt per run and no replay after terminal state.

The final extra positive scenario uses A's actual hand-shake passage and the rule's authoritative source span, with a clearly synthetic UNKNOWN about whether shaking is a removal attempt. It completes `ASSESSMENT_COMPLETE_OWNER_DECISION_PENDING`, derives UNKNOWN and false eligibility, preserves the reason and leaves production gates closed. The fixture contains no model-authored aggregate. This tests the previously broken integration, not real semantic quality.

Both runtimes rejected all four historical paid grants before dispatch. Approval and BUILD_PROMPT handoff POSTs were denied; no drafts/new story records were created. All non-ledger table counts remained unchanged. Dumps were saved with owner-only permissions, and only these test runtimes/databases were stopped. No deployment occurred.

Evidence: `http-e2e-results.json`, individual HTTP run receipts, actual SDK request traces and `final-source-specific-unknown/http-e2e-results.json`.

## I. Next single-review operation — NOT AUTHORIZED FOR SPENDING

Manifest: `intelligence/docs/STORY_REVIEW_DERIVED_VERDICT_REVIEW_MANIFEST.json`.

The new operation uses the same original source, authentic A/B narratives, pinned model, strict JSON mode, 24,000-byte input envelope, 4,000 output-token cap, 5/5/10/60-second native SDK timeouts, 90-second scoped backend timeout, 600-second workflow deadline, zero retries/fallback and existing client UUID policy.

Actual SDK body: 23,845 bytes (155 bytes larger than V4; 155 bytes below the existing cap). No input/output cap was enlarged.

```text
((23845 + 1000) × 0.15 + 4000 × 0.60) / 1,000,000
= $0.00612675
rounded up reservation = $0.006127
```

The $0.006104 V4 grant is consumed and cannot authorize this changed operation. Both paid-authorization flags in the new template remain false. No model-availability probe was made.

| Binding | Actual SHA-256 |
|---|---|
| prepared operation | `7f8a23611d6783c64e82089e934394889438baac670ca7a92cb766a475f5387b` |
| full current scope | `64f9755b9f75536c35fa30fe86d2a36bd9b6fe566d58b294d58efa884938476f` |
| original source | `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d` |
| unchanged evidence catalog | `5b15086899fc5c80f5de99a749fa3b70d47d32175a6a0ee0bcfdd8ab6f2273d7` |
| system | `1230b075d76c277847d223a1ed006eb1abcf5765a9f15d5916eedad56fd8ed5a` |
| user | `45d36b2d88f1e351d1bdf8cbe40439d44ee903d8b047c58e469e9c9be1c5c530` |
| strict response schema | `b214f3c0047417f7ed8c06986dc1bc08446b33757d1c82dc8ffb2738f8f23467` |
| response format | `ffab700b2012b430df1909cc6a00421b0f9b536ba945411153aabb5227cfa269` |
| canonical SDK request | `2ebc56ba68e3de80cea35e042fbeba98104f9d0df457384be205404b5c931519` |
| actual SDK wire body | `0c3f3d3d131ac5671feb54d873dbfbc96447fa3ff421155f4a2c85a2b7b60717` |
| protected-fact/check scope | `029d1ef976b27405adabc7372266bc31e2768c07b44dd359d397b49e4169746f` |
| ML implementation | `e51840d8b1e0c8afb2c93b3d35a715d901b178772aa66cda5e5b7a21739285dc` |
| compiled backend authority | `0b81a686ae030c42240b9364337d9215cb4fdf8723abaf6015b0176a33fcd221` |
| unchanged transport metadata | `fa89454b6228afad847fbbee39a173a329887a707191548760547e70791ea615` |

New idempotency key: `authentic-assessment-derived-v5-7f8a23611d6783c64e82089e`.

Unchanged candidate A SHA: `50bae8834df06f6092a37947d422e136c41c72ea80838057beecf2e7156bb088`.

Unchanged candidate B SHA: `4b04e664b70ea9372049231119f2ad786cf5ed0fc1a416c0941101d53167c739`.

The old manifests remain unchanged. New prompt/schema/request/implementation/scope hashes are measured, not patched into an old grant. The evidence catalog and transport policy fingerprints remain unchanged because their underlying contents did not change. The backend authority fingerprint reflects the freshly compiled consumer change.

## J. Limits and next step

The next real model may still select insufficient evidence or misinterpret a correctly anchored passage. Offset scope does not establish semantic truth; generic creative reasoning is still possible. Mocked success establishes contract readiness only. No new real independent review, winner, official A/A+, audience benefit or render readiness is claimed.

ONE next step: the owner may separately authorize the single prepared review at at most $0.006127 after inspecting this manifest. This task grants no spending permission and performs no dispatch. No story approval, BUILD_PROMPT, image/video generation, publication, production write/deploy or Git history change occurred.

The retained strict-schema subset follows [official OpenAI Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs): required object fields and additionalProperties=false are preserved. No API/model migration was introduced.

