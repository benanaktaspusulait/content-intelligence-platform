# Real-model failure repair — contract and creative materiality

**Implementation contract corrected. Real-model creative effectiveness remains UNVERIFIED.**

No OpenAI API call or other real provider call was performed in this task. No paid retry, new prompt approval, story edit, canonical score change, image/video generation, publication, direct production SQL update, commit or push occurred. The preceding real call remains historical evidence, not a new attempt.

## 1. Root causes

Two independent problems were confirmed.

**Contract defects:** the V1 temporal regex rejected every numeric range, including exact existing beat windows. In the actual response, A's 0–2s and B's 2–5s were source restatements, not invented sub-beat timings or changed story duration. Separately, spatial Ref fields were arbitrary strings in the provider schema while the consumer required exact source-catalog IDs. Six natural-language references therefore satisfied structural JSON but failed consumer binding. The catalog also omitted useful exact mentions such as “her other hand” and “each hand”.

**Creative weakness:** the actual response mostly repeats approved reach/peel/split actions and consequences, adds desired visibility and repeats generator metadata. It does not implement a new source-specific contact path, meaningful action/result staging or count-state arrangement. Repairing the technical contract cannot convert those paraphrases into a useful improvement.

Input incentives, inspected in the actual second request:

| Incentive/question | Evidence and diagnosis |
|---|---|
| Repeat protected events? | Full source narrative plus event references were supplied. “Describe existing actions; never add actions” lacked a clear delta-only field distinction. Actual choreography strings paraphrase those events. Causal incentive is a hypothesis; the copying itself is observed. |
| Copy timestamped beat? | temporalPresentation was required and min-length constrained, without a null unchanged option. Actual output fills it with 0–2s / 2–5s plus narrative. |
| Restate settings? | generatorConstraints required at least one string. Actual output repeats aspect ratio and model rather than intervention constraints. |
| Fill redundant fields? | Consequence, temporal and composition prose were mandatory even when unchanged. That invites safe padding; actual repeated content supports the concern. |
| Superficial visibility language? | The response asks for “clearly visible” and longer shot descriptions, with no implemented contact/placement change. |
| Avoid choreography? | Protected-story restrictions and server-written proposedImprovement hints could encourage conservative paraphrase. The output shows weak physical detail; the motivation is not proven. |
| Produce two weak plans? | V1 already preferred one and allowed 0–2; it did not require two. The model nevertheless chose two. The new request makes one the explicit preferred count without forcing success. |

## 2. Corrected contract behavior

New official generation requests use **model-authored-production-v2** inside the existing creative-reconstruction-v2 workflow. No new optimization framework, provider adapter, scoring feature or database policy was introduced.

**Temporal checks:** exact current source windows, including decimal/en-dash/worded forms, produce SOURCE_BEAT_WINDOW_REPEATED advisories with materialEvidence=false. A different existing beat window is WRONG_SOURCE_BEAT_WINDOW; a new proper subinterval is UNSUPPORTED_NEW_SUB_BEAT_TIMING; a changed source-window boundary is CHANGED_SOURCE_BEAT_WINDOW; a range or claimed total duration beyond the original is STORY_DURATION_CHANGED. Unbound quantified holds/pauses are UNSUPPORTED_TEMPORAL_CLAIM. Genuine new timing remains rejected. A valid original window no longer causes STORY_FIDELITY_FAILED in V2.

**References:** the wire schema enumerates allowed IDs by ENTITY/ACTION/CONSEQUENCE/STATE kind. The request separately supplies per-opportunity beat-local allowed IDs, the contact opportunity's required surface pair and relationship semantics. The consumer independently rejects unknown IDs, wrong kinds, cross-beat references and overlapping source mentions used as different entities. Natural-language names are never silently aliased to IDs. The catalog now generically extracts exact source-mentioned anatomy/object noun phrases, with real quote/spans; “her other hand” and “each hand” are usable mention IDs. It does not invent “Mimi's hands”, left/right identities or new actors. Identity/semantic verification stays UNKNOWN.

**No padding requirement:** unchanged consequence/temporal/camera fields may be null and generatorConstraints may be []. Null camera preserves the original production annotation instead of deleting an unchanged instruction. Exact authored fields are assembled with source substitutions/provenance; invalid authoring never silently falls back to server choreography.

**Versioning/history:** future backend requests/cache checks use V2, changing the request fingerprint and preventing stale V1 result reuse. The V1 reader/system/schema retain their original interpretation for historical replay. Offline V2 revalidation is a separate derived report; it does not rewrite the actual V1 role/comparison or their prior diagnostics. Ruleset 1.11 semantics are untouched.

## 3. Offline results for the exact actual A/B output

Fixture bytes were copied directly from the actual provider response, without repairing timestamps, references or prose. SHA-256: `0783b28b78e18bcdfa3c2ac14aec5266e91a15e89b65aaedea489c09c7ab95e0`. The fixture is `intelligence/ml-service/tests/fixtures/real-model-authored-failure-2026-10-15.json`; its hash is asserted by tests.

| Dimension | Actual A | Actual B |
|---|---|---|
| Structural response | Parses | Parses |
| Original time range | 0–2s: valid redundant source window | 2–5s: valid redundant source window |
| Technical validity | INVALID: 2 spatial reference IDs | INVALID: 4 spatial reference IDs |
| Source fidelity | UNKNOWN; not a confirmed story change | UNKNOWN; not a confirmed story change |
| Source grounding | UNVERIFIABLE due to bad references | UNVERIFIABLE due to bad references |
| Independent creative materiality | **VALID_BUT_EQUIVALENT** | **VALID_BUT_EQUIVALENT** |
| Actual improvement evidence | None established | None established |
| Operator recommendation | **KEEP_ORIGINAL** | **KEEP_ORIGINAL** |
| Candidate score/critic | Not run: no valid complete candidate | Not run: no valid complete candidate |

“VALID_BUT_EQUIVALENT” here labels the creative dimension. It does not turn the technically invalid raw response into a valid admitted candidate. Overall proposal admission stays blocked as AUTHORING_CONTRACT_INVALID; known reference errors are not relabeled story mutations. Correcting only the false-positive timing gate does not cure the remaining errors or manufacture a successful candidate.

Exact per-field diagnostics, allowed IDs, timing advisories and separate materiality results are in `actual-real-response-offline-evaluation.json`. No alias resolution or repaired derivative of the real response was used to obtain acceptance.

## 4. Why materiality still fails, independently

A asks for the existing close hand shot with the cabinet visible behind it; its actual spatial instruction merely restates the reach/attachment. It does not implement the claimed cabinet/finger contact arrangement. B restates peel→split→one note per hand and a medium shot; it does not specify separated screen positions or continuous physical paths. Neither addresses 2→4→8 staging, although changing every beat was never required.

The independent materiality evaluator excludes reference validity, field count/text length, expanded camera labels, repeated source consequences, settings and source timecodes as evidence. It requires source-grounded physical relationship/choreography differences or differentiated state arrangements. The actual A/B content lacks these. A separate negative control uses valid source IDs with paraphrased actions and a long camera description; it is technically valid but still rejected as equivalent. This controlled negative is not a repair of the saved response.

A positive control uses a genuinely different structured contact/count arrangement and is accepted as MATERIAL_TEXTUAL_CHANGE_UNVERIFIED. It supplies structured delta instructions, not a prewritten full winning prompt. Its output is assembled without template substitution and has exact provenance. This is a controlled mock demonstrating contract/evaluation readiness, not autonomous model creativity or proven prompt quality. The positive control's canonical score remains 88.40625000000001/B under 1.11, with 0 outcome/severity changes; critic and F8 gates remain independent. Its critic status is REWRITE; render authorization is BLOCKED_PENDING_EVIDENCE.

## 5. Generation instruction changes

The new system explicitly asks for preferably ONE strong physical intervention. objective identifies one cited execution weakness; rationale contrasts baseline execution with the proposed change and explains the observable cause/result difference. Production fields contain how the existing action is staged/performed differently, not a retelling of what the character does. Camera prose cannot supply materiality alone.

The request states exact Ref encoding, allowed IDs, beat scope, contact participants and missing-grounding behavior. An unsupported relation is omitted or the model abstains; missing evidence never becomes PASS. State progression uses only supported states in source order. Relative continuity may be described; invented schedules remain blocked.

The model uses null/[] for unchanged support fields and does not repeat generator/aspect ratio/profile metadata. Server-written proposedImprovement/expectedVisualChange text was removed from new-generation diagnosis to avoid providing choreography for the model to echo. Source evidence, exact source text, weakness/risk and protected constraints remain available. NO_JUSTIFIED_IMPROVEMENT is allowed; there is no forced creativity or second weak plan. Safe bounded operations and explicit server-template fallback are retained with precise authorship attribution.

See `v2-system-instructions.txt`, `v2-request-payload.json` and `v2-response-schema.json` for exact deployed-intended contracts. Current saved-input payload size: 23116 bytes, under the unchanged 24,000-byte gate. Output cap, budget/idempotency/persistence, no automatic retry and no model fallback are preserved.

## 6. Validation and regression evidence

- **244 ML tests passed**, including **23 new repair tests** and the existing 25 authored-execution tests, source/canonical/critic/F8, optimization, recovery and budget regression suites.
- **47 backend tests passed; 3 explicitly conditional tests skipped**, zero failures/errors. Database cases use disposable PostgreSQL Testcontainers.
- **70 frontend tests passed**. No comparison redesign or operator auto-approval was introduced.
- Exact original windows pass; invented sub-beat schedules, unsupported holds, wrong beat windows and changed duration remain blocked.
- Invalid IDs have field/kind/beat/allowed-ID diagnostics; genuine exact source mentions are usable. Spurious aliases and fake entities are not accepted.
- Both untouched real paraphrases remain creatively equivalent. A valid-ID/verbose-camera negative fails materiality. Distinct source-faithful physical choreography passes as material but unverified.
- Known story changes, unsupported note counts, changed state order, identity deviations, audience claims and camera/contact risk regressions remain blocked. Equivalent numeral forms of existing count states are accepted without changing the physical rule.
- No silent template replacement. Null unchanged camera preserves its protected source annotation and provenance.
- First real legacy response still recompiles byte-for-byte; V1's actual failed response retains its historical interpretation. Historical production records are checked separately after deployment.

Warnings from the existing parser's datetime.utcnow deprecation remain. Angular tests are DOM regressions, not a new browser viewport acceptance test. No real-model inference was run.

## 7. Remaining creative limitations and model capability

Technical/reference compliance is not creativity. Spatial/state validation is conservative deterministic evidence, not a semantic oracle or audience predictor; identity, story interpretation, actual count/contact continuity, Seedance adherence and viewer benefits remain UNKNOWN without independent evidence. Geometry wording alone cannot establish complete creative quality. The safe operation grammar and locked contact/count policy remain bounded.

The real model demonstrated structured JSON and some valid action/consequence references, but did not demonstrate useful independent choreography in the observed run. Its reasoning adequacy for this task is **not established**. One test had a template-only schema; the second was confounded by reference-contract mismatch, mandatory padding fields and a timing false positive. Those observations do not prove a model-capability ceiling. A stronger reasoning model might help, but that is an untested hypothesis, not an excuse to overlook the contract defects.

The [official model description](https://developers.openai.com/api/docs/models/gpt-4o-mini) describes GPT-4o Mini as a small model for focused tasks and supports Structured Outputs; it does not establish spatial creative performance for this application. [Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs) supports machine schema constraints, not proof of material creative quality.

## 8. Recommended next single real experiment

**A — retest the same model once with the corrected V2 instructions, after separate fresh authorization.**

This isolates the input-contract change rather than changing model and contract simultaneously. Contract simplification (C) has been implemented offline; the current evidence does not yet justify concluding that the task exceeds the model's capability (B). Prefer one source-cited physical intervention; allow abstention. Use the same immutable Mimi source, current analysis/ruleset/settings bindings, dynamic ID schema and no prepared choreography. Evaluate the exact raw model decisions separately from compiler/source contributions; require a defensible physical before/after difference, not a higher score. A valid but equivalent result must remain KEEP_ORIGINAL.

No experiment was run or authorized by this recommendation. Both previous one-call authorizations were consumed. A fresh authorization must set the provider/model, single-request cap, output and budget limits. Check exact model availability at that time; do not silently replace the snapshot or retry if unavailable/ambiguous. No automatic prompt acceptance, new version or rendering follows from a candidate's technical or materiality pass.

Deployment/read-only history verification is recorded alongside this report. This task fixes implementation opportunities and diagnostics; it does **not** declare creative optimization successful.
