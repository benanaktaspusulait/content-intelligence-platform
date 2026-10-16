# CPQ V1 source-fidelity closure

Delivery date: 2026-10-16. No new inference, prompt approval, story edit, scoring change, rendering, publishing, commit or push is authorized by this delivery.

## Immutable real evidence

- Pilot: `770e8477-f352-499e-aabd-b7418435e70b`.
- Historical request: `6f078994-3385-4910-8423-47a46ad9999a`, permanently `FAILED_OR_AMBIGUOUS`.
- Real provider response: `chatcmpl-EZYRV5i8EXPUfeq0yBX2PRYE6EM5R`; finish reason `stop`.
- Raw response SHA-256: `1a25709c8bd53d2f093fcb93d630081f12542591e3f74f460410154c12c75d23`.
- Original real model verdict: **FAIL**, never rewritten. Production admission was explicitly authorized by the owner and completed as a separate append-only record; the semantic FAIL remains unchanged.
- Original input, approved story, production settings and Prompt 10/version 1 are bound by their persisted SHA-256 fingerprints. Authoritative analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`: Ruleset 1.11, **88.40625/B**, unchanged.

The old rejection was a citation-contract incompatibility: mapping 11 identifies event_07 but quotes the exact complete consecutive event_06–event_08 source passage. `CONTIGUOUS_EVENT_ORDER_V1` permits this only for EVENT_ORDER, only two or three complete consecutive sentences, containing the named anchor event. Separate exact single-event coverage of all nine source spans and all six anchors remains mandatory. It does not establish semantic PASS.

## Minimal append-only recovery

Existing immutable `cpq_pilot_evidence` is reused. No migration, new optimizer, dashboard or identity system is needed.

- Owner-authenticated read-only GET `.../cpq/owner-pilot/{pilot}/requests/{request}/source-recovery` checks current source scope and invokes signed **offline** ML validation. Returns exact expected authorization bindings and derived response; writes no evidence.
- Owner-authenticated POST `.../{pilot}/requests/{request}/recover-source-evidence` requires explicit `authorizeOfflineRevalidation=true`, `confirmNoInferenceNoApproval=true`, exact proof returned by preflight, current source freshness, authenticated pilot owner and existing CSRF/origin safeguards.
- Internal HMAC-signed ML route `cpq-pilot/revalidate-source` is pure validation. It has no provider construction or inference path and works with real dispatch disabled.
- Both ML and backend independently validate retained output, original completion/accounting/provenance, unchanged raw response, source/event/anchor coverage and the demonstrated corrected citation defect. Backend also compares every raw model result field with the admitted result, allowing only validator annotations.
- Policy: `SOURCE_CITATION_RECOVERY_V1`. Typed payload provenance: `RECOVERED_MACHINE_EVIDENCE`; execution status: `OFFLINE_REVALIDATED`; new inference false; new inference cost zero. Original cost is preserved as historical accounting, not charged again.
- Owner authorization, original response digest, input/raw hashes, provider response ID, exact source binding and corrected citation version are appended with a separate evidence UUID. A per-pilot transaction lock plus existing unique request/evidence relation makes repeat recovery idempotent.
- Old request is never updated. Empty/truncated outputs, reasoning exhaustion, ambiguous completion, wrong identities/hashes, noncontiguous citations, missing anchors/spans and unrelated failures remain ineligible.
- Aggregation recognizes only the specifically governed recovered provenance after checking it against the durable failed row. A retained FAIL becomes Q04 REVIEW_REQUIRED, never PASS. Three candidate reviews remain NOT_EXECUTED. Coverage after authorized admission: 1/4; critics blocked; human reviews zero; grading inactive; render unauthorized.

## Owner handoff: two separate creative decisions

Owner decisions were explicitly received and recorded separately through the existing `REQUEST_REVISION` owner-decision operation, scoped to source findings. This operation requests a bounded text clarification; it does not create a prompt version or accept a candidate. Owner interpretation is not independent human calibration, machine verdict replacement, source/story revision or render permission.

- Recovery evidence ID: `91dd2c4d-fea0-4a0d-99f0-a0f2685ff67a`.
- OWNER_DECISION evidence ID: `d1f2a276-8e70-411f-9083-eb5d44b69c22`.
- Finding A: **equivalent visual cleanup intention is sufficient; exact readable “Topla!” lettering is not mandatory**. Approved source text stays exact.
- Finding B: **preserve the same overwhelmed, note-covered state continuously through the mirror reaction until the sneeze**. Only clarify continuity; no new pull, escalation event or timing.
- The immutable decision payload includes exact source binding, original request/response/input hashes, recovered evidence reference and the owner's instructions. The model's original omissions, additions, uncertainty, risks and FAIL remain visible. No semantic PASS or overall source-gate override is granted.

The following alternatives document the review packet presented before adjudication. The actual choices above govern the bounded proposal below.

### Finding A: “Topla!”

Approved source:

> Mimi, oyuncak dolabına 'Topla!' yazan bir yapışkan not yapıştırmak ister.

Exact affected production wording:

> 0-2s: Mimi reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to her finger [close-up on Mimi's hand] Mimi is in front of a toy cabinet, looking determined -> the note sticks to Mimi, not the cabinet

The literal lettering is absent. Whether readable glyphs are essential or cleanup intent is sufficient requires the owner decision. Choices: **exact lettering essential / equivalent visual cleanup intent acceptable / targeted clarification required / insufficient evidence**.

Conditional repair, only if exact lettering is confirmed essential: replace “with a sticky note” with “with a sticky note bearing ‘Topla!’”. Everything else in the beat stays unchanged. This is a fidelity repair, not proven creative improvement. Readable small text at 480p is unverified and requires visual evidence; no guarantee of generator typography or automatic speech addition is made.

If equivalent cleanup intent is accepted: conditionally replace “looking determined” with “intent on tidying the toy cabinet”. This makes intention explicit without adding an action or changing the gag. Owner equivalence must remain separately documented; the original real model FAIL remains intact. If evidence is insufficient, retain the original pending interpretation; do not silently add lettering.

### Finding B: mirror → overwhelming coverage → sneeze

Approved source:

> Mimi aynada kendini görünce çığlık atar. Notlar o kadar çoğalır ki Mimi boğulacak gibi olur. Sonunda hapşırır ve tüm notlar uçuşarak dolabın üzerine yapışır.

Exact affected production wording:

> 5-10s: Mimi continues to pull; each pull doubles the number of sticky notes [wide shot showing Mimi covered in notes] notes multiply from two to four to eight as she pulls, progressively covering her arms, legs and face -> Mimi is overwhelmed by notes

> 10-12s: Mimi sees herself in a mirror and screams [close-up on Mimi's shocked face] Mimi is startled by her reflection completely covered in notes -> Mimi is startled

> 12-15s: Mimi sneezes and the sticky notes fly off [medium shot of notes flying] notes scatter and stick to the cabinet -> Mimi breathes a sigh of relief but the cabinet remains messy

The overwhelming state is explicit before the mirror. Continued coverage after the mirror is plausible but not restated; this is a continuity/order ambiguity, not proof of a missing additional action. Choices: **distinct post-mirror escalation required / existing continued coverage adequate / small continuity clarification needed / insufficient evidence**.

If the owner selects continuity clarification, proposed replacement for the final consequence of 10–12s only:

> -> Mimi remains overwhelmed by the same covering notes after her mirror scream, carrying that state directly into the sneeze

No other beat, attempt, timing window or event is added. The 5–10s doubling and existing 12–15s sneeze, scatter, cabinet landing, relief and messy ending remain exact. This is source-fidelity/continuity clarification, not A/A+ evidence. Face coverage, mirror identity/geometry and the existing three-second ending remain unverified execution risks. If a distinct post-mirror intensification is required, its exact visible meaning must first be clarified with the owner; this report does not invent more pulling, notes, injury or choreography. If continued coverage is adequate, no wording change is necessary, and the owner/machine disagreement remains visible.

## Scope of proposal

The selected bounded proposal is the existing 10–12s continuity consequence replacement above. Finding A requires no readable-text addition; its accepted cleanup-intent interpretation is documented separately. The optional “intent on tidying” wording is available for owner review, not a mandatory correction. These are review wording proposals, not a saved revised prompt or automatic new version. They preserve Mimi, the five beats, physical doubling 2→4→8, mirror/scream/sneeze/cabinet/relief/messy ending and authoritative ABSURD_PHYSICS / SEEDANCE_2_0_MINI / 15s / image2video / 480p / 9:16. The old literal `Content profile: AUTO` in immutable prompt text is historical metadata, not the production authority. No proposed text has been canonically evaluated or visually tested; no score, retention or creative-quality improvement is asserted.

The owner has chosen both meanings and both are separately recorded as OWNER_DECISION. The minimal continuity proposal is ready for later owner review against the exact original; no text has been applied. Ordinary prompt acceptance does not replace adjudication or reverse the machine verdict. At the owner’s latest instruction, execution stops after deployment, recovery and separate decision recording. Candidate source assessments and critics still need their own separately authorized execution. Official A/A+ grading remains inactive.

## Verification and release

**Deployment completed through `intelligence/scripts/deploy.sh`, sequential ML then backend.** Frontend was restarted for nginx resolution by the official backend deploy helper; its image was unchanged and no frontend build occurred. No migration: Flyway remains V66, with all existing applied migrations untouched.

**60 ML tests passed; 37 backend tests passed (6 citation, 26 disposable-PostgreSQL integration, 5 owner-access), zero failures/errors/skips.** Recovery tests cover exact retained real output, append-only history, explicit authorization, wrong proof/source/prompt/settings bindings, missing output, truncated output, reasoning exhaustion, specific corrected-defect eligibility, preserved semantic fields, idempotency, source 1/4, missing candidates, gate blocking and no prompt/grading/render changes. The internal offline route was tested with paid dispatch false and rejects unsigned requests. Existing citation tests exercise noncontiguous, reordered, whole-story, missing-span/anchor and coverage-bypass rejections. No provider SDK was called.

Live verification used the owner-authenticated deployed API, not mocked transport: read-only preflight passed both running validators against the exact real response before admission; unauthenticated preflight was rejected. After the explicit owner reply, the application recovery POST appended one MACHINE_REVIEW record and the existing owner decision POST appended one separate OWNER_DECISION. Production recovery was not repeated; repeat idempotency was verified in disposable PostgreSQL. All three historical request rows remain byte-equivalent by ordered full-row digest `9fc8542ec7114168e49ba427908982ac5bedb1d6f592b71ee3b0b029cd2ce281`. Raw response SHA remains exact. Prompt 10/version 1 and all 75 workflow events are unchanged. Inventory is three pilots, three historical requests, one recovered MACHINE_REVIEW and one OWNER_DECISION; zero critic requests. Canonical Ruleset 1.11 / 88.40625/B is unchanged (serialized floating value 88.40625000000001).

Final services: backend, ML, PostgreSQL and creative-render-service running/healthy; frontend running, HTTP checks passed. Both real-dispatch flags remain false. Disk before first build: 2,303,348,736 bytes; before backend build: 1,589,776,384 bytes; final approximately 1.30 GiB free. Builds were guarded by 1.5 GiB minimum pre-build headroom, sequential, with no cleanup or deletion.

Focused logs, immutable offline validation output, release image hashes and pre/post-deployment and post-recovery integrity diagnostics are stored in `cpq-source-fidelity-closure-evidence/`. `live-final-verification.json` is the pre-recovery checkpoint; `authorized-recovery-verification.json` is the authoritative final production result. The offline response copy is revalidation/test evidence, never a new provider execution or human review. No frontend regression suite was rerun because no frontend code changed. No broad architecture or optimizer work was added.

Files: ML `app/workflow/owner_machine_pilot.py`, `app/workflow/api.py`; backend `CpqOwnerPilotService.java`, `CpqOwnerPilotController.java`, `QualityMlClient.java`; focused tests `test_source_evidence_recovery.py` and `OriginalCpqFidelityIntegrationTest.java`; this report and diagnostic evidence. Existing citation regression tests were reused.

The source-evidence delivery is complete. The next creative step, if later requested, is reviewing the one bounded continuity clarification and cleanup-intent wording proposal; it is not an inference, prompt approval or A/A+ certification. Candidate source checks remain unexecuted and critics remain blocked; any paid continuation requires fresh explicit authorization.

## Required statuses

- CITATION_FIX_DEPLOYED: YES
- SAVED_REAL_RESPONSE_VALID: YES (strict structure and both validators; semantic FAIL)
- RECOVERY_AUTHORIZED: YES
- RECOVERED_MACHINE_EVIDENCE: RECORDED
- ORIGINAL_SEMANTIC_VERDICT: FAIL (retained real response, separately admitted without changing the judgment)
- SOURCE_COVERAGE: 1/4
- OWNER_FINDINGS: ADJUDICATED
- TARGETED_REPAIR: READY_FOR_OWNER_REVIEW (wording proposal only; Prompt 10 unchanged)
- CRITIC_GATE: BLOCKED
- CPQ_GRADING: INACTIVE
- REAL_PROVIDER_CALLS_THIS_TASK: 0
- REAL_DISPATCH: DISABLED
