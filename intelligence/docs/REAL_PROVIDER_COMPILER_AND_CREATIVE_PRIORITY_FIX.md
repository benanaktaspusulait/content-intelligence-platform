ACTUAL_ORIGINAL_PROVIDER_CALLS: 2
ACTUAL_ORIGINAL_PROVIDER_SPEND_USD: 0.05801854

NEW_PROVIDER_CALLS: 0
NEW_PROVIDER_SPEND_USD: 0

OPENAI_PROFILE_NORMALIZATION_DEFECT: CONFIRMED
OPENAI_COMPILER_FIX: VERIFIED
OPENAI_SAVED_RESPONSE_REPLAY: ACCEPTED
OPENAI_REPLAY_CANONICAL_SCORE: 92.48958333333336
OPENAI_REPLAY_CANONICAL_GRADE: A
OPENAI_REPLAY_CREATIVE_VALIDITY: CREATIVE_RISK_DETECTED / PROVISIONAL_CREATIVE_VALIDITY_REQUIRED

DEEPSEEK_BOUND_REFERENCE_ROOT_CAUSE: GENUINE_SOURCE_REFERENCE_VIOLATION_IN_spatialRelationships.1
DEEPSEEK_ORIGINAL_RESPONSE_REPLAY: REJECTED
DEEPSEEK_VALIDATOR_WEAKENED: NO

CREATIVE_OPPORTUNITY_COVERAGE_AUDITED: YES
FRAME_ZERO_RISK_VISIBLE_TO_GENERATOR: YES
REPETITION_RISK_VISIBLE_TO_GENERATOR: YES
ENDING_OVERLOAD_VISIBLE_TO_GENERATOR: YES

SOURCE_STORY_CHANGED: NO
BASELINE_PROMPT_CHANGED: NO
RULESET_1_11_CHANGED: NO

REAL_PROVIDER_A_INDEPENDENTLY_VERIFIED: NO
OFFICIAL_CREATIVE_A_PLUS: INACTIVE

REGRESSION_TESTS: 127 focused passed; full ML 1319 passed/2 skipped/2 unrelated failures; offline replay passed; backend 211 passed/1 skipped/2 unrelated failures
OFFLINE_REPLAY_EXIT_CODE: 0

# Real provider compiler and creative priority fix

## Evidence and immutable inputs

The decisive replay read the exact persisted responses from `backend/target/disposable-owner-http/run-oT9HS7/real-execution-runtime`; it did not replace them with fixtures or repaired JSON.

- Baseline prompt SHA-256: `1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5`.
- Immutable run A file SHA-256: `612e723f33ec37364af1c808421a7c883a2125c9b1bc35722c7675549ae3e994`.
- Immutable run B file SHA-256: `be4055bd3e4bb049a652fe6be065afb642e4999c675b00f744c317cef75328fa`.
- DeepSeek raw response SHA-256: `ed50f5430d266ff3bda5fcbd2429d302d76ef1f156fe13443f2250fcd09a8344`.
- OpenAI raw response SHA-256: `72432a0e56eb49c43c581230de07e437ae298e209f3ae99ff9e49cfc869e0588`.
- Reconstructed OpenAI research candidate SHA-256: `657cd1caf9f892bd986bfd2f2a92a757ee5cd4ad90d570a62dc8138463d50984`.
- Original provider usage remains two requests and USD 0.05801854. Replay recorded zero external dispatches and zero additional cost.

The original evidence files and historical ledger records were not changed. Replay results are separate append-only research artifacts:

- `offline-real-response-replay.json`
- `openai-offline-accepted-research-candidate.txt`

## OpenAI defect and correction

The defect was deterministic and confirmed. The compiler assembled a source-valid beat-2 intervention, then `normalize_candidate_profiles` used the prompt body as a metadata sink and appended `Content profile: ABSURD_PHYSICS.`. `validate_compiled_source` correctly compared protected text outside timed beats and rejected the compiler's own addition.

Before correction, the ending became:

```text
PRODUCTION SETTINGS
ABSURD_PHYSICS. SEEDANCE_2_0_MINI. 15 seconds. image2video. 480p. 9:16.
Content profile: ABSURD_PHYSICS.
```

After correction, the approved ending is preserved byte-for-byte:

```text
PRODUCTION SETTINGS
ABSURD_PHYSICS. SEEDANCE_2_0_MINI. 15 seconds. image2video. 480p. 9:16.
```

The effective profile is stored in structured candidate metadata as `targetContentProfile=ABSURD_PHYSICS`. Existing canonical tokens and legacy source-owned `Content profile: AUTO` representations are preserved without text mutation. Missing profile text is derived out of band. A newly introduced conflicting production profile or creative profile directive still raises `MATERIAL_CREATIVE_PROFILE_CONFLICT`. Repeated normalization is idempotent.

Relevant implementation points:

- `optimization_profile_contract.py:15-34` recognizes labeled and unlabeled canonical settings representations.
- `optimization_profile_contract.py:75-149` compares source and candidate representations, preserves protected text, maps the effective server-owned profile out of band, and rejects genuine mutations.
- `optimization_distinctness.py` validates the effective structured profile while retaining strict non-beat source equality.
- `creative_reconstruction.py:311-342` keeps the outbound contract bounded without deleting exact quote/span/identity grounding.

The saved OpenAI response now passes structured-plan validation, reconstruction, profile normalization and source validation without modifying any provider-authored decision.

## Actual OpenAI evaluation

The production Ruleset 1.11 evaluator ran on the complete reconstructed prompt.

| Metric | Original | OpenAI replay candidate | Difference |
|---|---:|---:|---:|
| Canonical score | 93.42708333333334 | 92.48958333333336 | -0.9375 |
| Grade | A | A | unchanged |
| Ruleset | 1.11 | 1.11 | unchanged |

Only `HOOK_002` changed: the baseline passed because it explicitly established textual first-frame intent; the candidate became `UNKNOWN/CRITICAL` because “already mid-action” did not explicitly state the visible frame-zero state. The beat-2 spatial intervention therefore did not improve the canonical score. The numerical A proves structural evaluability under the unchanged canonical ruleset; it does not prove creative strength.

`creative-validity-v1` returned:

- `creativeQualityStatus=CREATIVE_RISK_DETECTED`
- `structuralQualification=STRUCTURALLY_COMPLIANT`
- `finalQualification=PROVISIONAL_CREATIVE_VALIDITY_REQUIRED`
- `creativelyStrongVerified=false`
- `realProviderCapabilityClaimAllowed=false`
- `renderAuthorized=false`
- `officialAPlus=INACTIVE`

Open risks remain:

1. `FRAME_ZERO_STATE_UNVERIFIED` — “already mid-action” does not define the actual first visible state.
2. `REPETITIVE_VIEWER_VISIBLE_CONSEQUENCE` — changed verbs may still collapse to the same visible multiplication result.
3. `ENDING_TIMING_OVERLOAD` — the 11–15 second window contains too many state/action transitions.
4. `CRITICAL_PRODUCIBILITY_RISK` — thin-object contact and multi-object continuity remain unverified.

There is no independent source-fidelity review, independent creative review, rendered first-frame evidence, audience evidence or official A+ calibration. The candidate is a structurally evaluable research result only.

## Full reconstructed OpenAI candidate

```text
TITLE / FORMAT
Pip sticky-note strategy escalation / 15 seconds

VISUAL STYLE
Bright playful animation with readable silhouettes.

CHARACTER / CONTINUITY
Pip is the same anthropomorphic rabbit throughout; no verified appearance reference is claimed.

TIMED SHOT PLAN
0-2s: Already mid-action, Pip the rabbit tries to place one sticky note on the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched. [locked medium shot; keep Pip, hands, notes and cabinet causally readable] -> The note attaches to Pip rather than the cabinet.
2-5s: Pip tries to peel the note away with the free hand, but it splits into two notes, one on each hand.  -> One note becomes two. [Keep the free hand's peeling contact below Pip's head, in the open space in front of the upper torso rather than across the face. Bring the free hand to the exposed outer edge of the attached note with the fingertips approaching from the side, not over its visible surface. Execute the existing peel as a lateral draw across the image: keep the originally occupied hand on its starting side while the peeling hand travels toward the opposite side, with neither wrist crossing the other hand's silhouette. Let this same peel movement open a gap between the hands as the split occurs; do not add another tug or regrip. Carry the two resulting attachments apart along those diverging hand positions, leaving open background between their silhouettes rather than stacking one note behind the other. Use a locked medium composition containing both lateral hand endpoints and Pip's face; view the peel plane obliquely enough that the note surface is not edge-on. Maintain the original hand-to-note attachment throughout the peel; reveal the second attachment through the same continuous separation, without hand identity swaps or an occluding cut.]
5-8s: Pip tries to press both notes onto the cabinet, but they spring back and double into four notes. [wide shot; keep Pip, hands, notes and cabinet causally readable] -> Two notes become four.
8-11s: Pip tries to push the four notes off against the cabinet door edge, but they split into eight and cover Pip's arms and face. [wide shot; keep Pip, hands, notes and cabinet causally readable] -> Four notes become eight and cover Pip.
11-15s: Pip sees the four-to-eight change finish, realizes that every removal or transfer attempt multiplies the notes, deliberately stops struggling, and turns the still note-covered face toward the mirror. Pip remains covered until a sneeze scatters the notes onto the cabinet. Pip is relieved, but the cabinet remains messy. [medium close-up; keep Pip, hands, notes and cabinet causally readable] -> Pip stops struggling, then the sneeze moves the notes to the cabinet.

AUDIO
Playful music, peel, spring, gasp and sneeze effects; no dialogue.

NEGATIVE CONSTRAINTS
No extra characters, unrelated props, invented attempts, identity changes or visual-evidence claims.

FINAL CUT
End with Pip relieved beside the messy cabinet.

PRODUCTION SETTINGS
ABSURD_PHYSICS. SEEDANCE_2_0_MINI. 15 seconds. image2video. 480p. 9:16.
```

## DeepSeek binding analysis

The original DeepSeek response remains rejected. In `spatialRelationships.1` it bound:

- subject: `beat_02.entity.0`, whose exact catalog text is the composite source mention `each hand` and whose identity resolution is `UNKNOWN_SOURCE_MENTION_ONLY`;
- object: `beat_02.hand`, the separate exact source mention `hand`.

Its instruction instead described “the two notes” settling on “one left and one right” hand. That prose did not address the exact composite subject and object references and implicitly introduced separate left/right identities that the source catalog did not establish. This is a genuine source-reference violation, not a serializer or resolution false positive.

The validator was not relaxed and the saved response was not rewritten. The outbound V2 contract now tells models to read each keyed catalog entry, use `{subjectRef}` and `{objectRef}` placeholders where wording is ambiguous, avoid treating a composite mention as proof of separate identities, and provide a grounded relationship for every independently positioned participant. Synthetic correctly bound inputs pass; the original invalid response stays rejected.

## Opportunity inventory and priority result

Previously, the actionable list contained only two `SEPARATE_ACTION_RESULT` opportunities and list order put beat 2 first. Creative-validity findings were not consistently exposed in generation context, so both models selected the easiest local intervention. The corrected diagnosis exposes all important weaknesses and ranks only source-permitted operations by severity, feasibility, generator risk and marginal visible coverage.

| Problem class | Visible | Prompt-actionable | Disposition |
|---|---|---|---|
| FRAME_ZERO_PRESENTATION | yes | no grounded opening operation | visual evidence required; do not invent opening choreography |
| VIEWER_VISIBLE_CAUSAL_VARIETY | yes | partially | staging can mitigate; new consequences require owner-approved story revision |
| TEMPORAL_LOAD_REDUCTION | yes | no | owner-approved story revision required |
| PAYOFF_PRESENTATION | yes | no | visual evidence required |
| GENERATOR_EXECUTABILITY | yes | partially | source-bound risk mitigation only; render success unknown |
| GENERIC_PRODUCTION_DIRECTIONS | yes | yes | source-bound prompt repair available |

The current actionable ranking is:

1. `SEPARATE_ACTION_RESULT:beat_04`, priority 70 — covers consequence variety, executability and generic directions at peak escalation.
2. `SEPARATE_ACTION_RESULT:beat_02`, priority 65 — covers the same classes with lower marginal coverage.

This explains the original convergence: beat 2 was formerly the first easy-to-validate eligible operation, while opening, temporal overload and payoff weaknesses either lacked grounded operations or required visual evidence/story revision. The corrected contract no longer hides these limitations or equates an easy local edit with the most consequential improvement.

Post-compilation evaluation now runs `creative-validity-v1` and carries first-frame, repetition, timing, generic-direction and producibility findings forward. It keeps numerical A separate from creative validation and makes no audience or render claim.

## Accounting semantics

New execution envelopes distinguish:

- `providerOutcome`: not dispatched, response received or dispatch ambiguous;
- `billingStatus`: no usage, known incurred, incomplete or unknown;
- `processingOutcome`: accepted result, structured-response failure, source-fidelity failure, local compiler failure or classified plan rejection.

The backend maps a received and fully accounted response that later fails locally to `LOCAL_POST_RESPONSE_VALIDATION_FAILED`, rather than implying ambiguous billing. Historical records were not overwritten. Offline replay creates no charge and no retry.

## Verification

- Focused ML regressions: **127 passed** across profile normalization, actual/synthetic authoring contracts, plan-first compilation, creative validity and optimization-loop accounting.
- Complete ML suite after correction: **1319 passed, 2 skipped, 2 failed**. The two failures are unrelated pre-existing family-2/story-similarity assertions (`island-journal` escalation applicability and paraphrase distinctness); no relevant production path failed.
- Offline decisive replay: exit code **0**; DeepSeek `REJECTED`, OpenAI `ACCEPTED`, external dispatches **0**, new spend **0**.
- Python compile check for the replay CLI: passed.
- Backend Maven suite: **211 passed, 1 skipped, 2 failed**. Both failures are unrelated existing `SavedStoryApprovalPostgresTest` record-ID stability assertions; the returned replay records had new UUIDs instead of the original IDs. No changed compiler/accounting path failed. The run was stopped after Maven emitted its final 213-test summary because test schedulers continued logging closed Testcontainers database connections.

Replay command:

```bash
./intelligence/scripts/offline-real-response-replay.py --offline-real-response-replay
```

The script verifies the exact evidence directory and baseline fingerprint, semantically matches pretty-printed evidence to the durable raw response, uses the actual reconstruction/evaluation path, prevents provider construction during evaluation, and exits nonzero unless OpenAI is accepted while the original DeepSeek response remains rejected.

## Next bounded experiment

No further provider call is authorized or needed for this repair. If a later owner authorization is granted, the smallest informative experiment is one generation request against the corrected payload, requiring the model to choose from the ranked inventory and explain why beat 4 or another grounded intervention has greater marginal value than beat 2. Any accepted candidate would still need separate source-fidelity and creative reviews. A call aimed at frame-zero or ending restructuring would first require owner-approved story revision or new visual evidence; it must not be smuggled into source-bound prompt optimization.

## Conclusion

The compiler contradiction is fixed and the authentic saved OpenAI intervention is now a complete, evaluable research candidate. It receives a real 92.48958333333336/A under unchanged Ruleset 1.11, while creative validity remains risk-detected and provisional. The authentic DeepSeek response remains correctly rejected. No real-provider capability A, independent creative A or A+ has been established, and no approval or render authorization is implied.
