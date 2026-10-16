# SOURCE_FIDELITY — final citation repair and owner evidence packet

Date: 2026-10-16. **Citation contract corrected in local source; saved real output passes OFFLINE_REVALIDATION_ONLY with its original FAIL intact. Not deployed. Production review remains NOT_EVALUATED. No provider calls.**

## 1. Exact reproduced root cause

Saved request: `6f078994-3385-4910-8423-47a46ad9999a`; pilot: `770e8477-f352-499e-aabd-b7418435e70b`; provider response: `chatcmpl-EZYRV5i8EXPUfeq0yBX2PRYE6EM5R`. The actual deployed validator reproduced `ValueError: Exact required source-event citation required` from the exact immutable input/raw response, without any provider transport.

Mapping index **11** (zero-based) is **EVENT_ORDER**, declared eventId **event_07**. Its verbatim sourceQuote is:

> Mimi aynada kendini görünce çığlık atar. Notlar o kadar çoğalır ki Mimi boğulacak gibi olur. Sonunda hapşırır ve tüm notlar uçuşarak dolabın üzerine yapışır.

This is the exact contiguous source text for **event_06 through event_08**. The existing validator interpreted every eventId as an exclusive single-sentence citation boundary, so it looked only within:

> Notlar o kadar çoğalır ki Mimi boğulacak gibi olur.

The quote was not fabricated and was not a reordered paraphrase. The interoperability defect was applying single-event containment to evidence whose purpose is establishing an ordering relationship across adjacent events. Model output violated the previously advertised per-span instruction, but rejecting every such exact local ordering quotation is unnecessarily restrictive for EVENT_ORDER.

Historical facts remain: input 1,883 tokens, completion 1,673, provider-reported reasoning 0, finish_reason stop, visible JSON 6,581 characters / 6,690 UTF-8 bytes, calculated cost $0.02143750. Those are the previous execution's usage, not new usage for this task.

## 2. Minimal implemented correction

Changed only the ML source validator/instructions and its matching backend admission validator, plus focused tests.

**CONTIGUOUS_EVENT_ORDER_V1** semantics:

- Existing single-event quotations remain exact substrings of their declared event span.
- Only **EVENT_ORDER** additionally supports a unique, explicitly bounded range of **2 or 3 consecutive complete source sentences**.
- The declared eventId remains the anchor event and must belong to the quoted range.
- No new model JSON field is needed: the exact complete-sentence sourceQuote explicitly defines the endpoints, which are resolved uniquely against the already bound source spans. The existing eventId declares the anchor. The offline diagnostic exposes the resolved IDs; the provider response itself is not rewritten.
- Compare with the exact source substring, including whitespace, punctuation and sentence order. No normalization, concatenation of noncontiguous sentences, omitted middle events, paraphrases or fabricated text are accepted.
- Ambiguous range matches, partial endpoints, more than three events and whole-story range quotations are rejected. This is a local ordering window, not permission for arbitrary narrative citations.
- A multi-event ordering quote earns **no substitute credit** for mandatory individual event coverage. All nine exact source sentence spans still require their separate complete single-event mappings; all six anchors and saved changed-beat requirements remain mandatory.
- Source/prompt/settings hashes, literal prompt quotations, uncertainty, omissions/additions, unsupported-PASS rejection and changed-execution quotation checks are unchanged. FAIL/UNKNOWN remain valid non-PASS judgments when the complete contract is met.

The 2–3-event bound permits a local before/current/after relationship; longer order arguments must use multiple local mappings plus the existing individual coverage. The rule is generic and has no Mimi names, sentence text, hashes, request IDs or story-specific exception in production logic.

Files changed:

- `intelligence/ml-service/app/workflow/owner_machine_pilot.py`: range resolver, narrow EVENT_ORDER admission, provider instructions describing the same boundaries.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/CpqOwnerPilotService.java`: identical range semantics, Unicode code-point offsets, existing single-event coverage checks retained.
- `intelligence/ml-service/tests/test_source_citation_repair.py`: exact persisted real output, range/coverage/semantic and legacy tests.
- `intelligence/backend/src/test/java/com/pompomhills/intelligence/workflow/CpqSourceCitationTest.java`: matching pure Java admission tests.
- `intelligence/backend/src/test/java/com/pompomhills/intelligence/OriginalCpqFidelityIntegrationTest.java`: disposable PostgreSQL proof that offline validation does not promote the historical request or open gates.

No JSON schema shape, database schema/migration, frontend, optimizer, canonical rule, ruleset or score changed. Existing batch source contracts retain their interpretation.

## 3. Exact saved output offline revalidation

| Check | Result |
| --- | --- |
| Original deployed validator | REJECTED: Exact required source-event citation required |
| Revised source validator | **PASS — OFFLINE_REVALIDATION_ONLY** |
| Pure Java backend admission | PASS in focused tests |
| Raw JSON / strict JSON Schema | PASS, unchanged |
| Original provider raw decision | **FAIL**, retained |
| Structurally admissible decision | **FAIL**; not converted to PASS/UNKNOWN |
| Mapping count | 14 |
| Protected anchors | All six |
| Required individual source coverage | All nine spans, event_01 through event_09 |
| Changed-beat coverage | Not applicable: original request has no changed beats |
| EVENT_ORDER range | event_06, event_07, event_08; anchor event_07 belongs |
| Additional rejected citations | **None** |
| Source/prompt quotations | Literal; one empty prompt quote explicitly marks the FAIL claim for event_07 |
| Missing uncertainty/omissions/additions/conflict fields | None |
| Production machine evidence appended | **0** |
| Production durable request | Still FAILED_OR_AMBIGUOUS |
| Production semantic result | Still NOT_EVALUATED |

The saved response has empty beatId strings. The current original-only contract permits these while identifying source events explicitly by eventId; there are no changed beats requiring named beat coverage. This is a visible traceability limitation, **not an additional current validation failure**. No beat IDs or sub-beat timings were invented to fill it.

The original response bytes were never altered. Raw-response SHA-256 remains `1a25709c8bd53d2f093fcb93d630081f12542591e3f74f460410154c12c75d23`; the archived durable-result file hash remains `b48c5c7135caadede8ce69ca88666a92d2321eac98527932b534e5f253f5aad2`. Normalized diagnostic output carries the existing REVIEW_REQUIRED notice due to the model's conflict/omission/addition findings; that is an in-memory/offline diagnostic, not a production acceptance record.

Passing the structural contract does not independently establish that every model interpretation is correct. In particular, benign production additions and operationalizing doubling as 2→4→8 are not automatically unauthorized story deviations merely because the model listed them under additions.

## 4. Actual finding A — “Topla!” note lettering

Exact approved source:

> Mimi, oyuncak dolabına 'Topla!' yazan bir yapışkan not yapıştırmak ister.

Relevant exact original prompt:

> 0-2s: Mimi reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to her finger

**Direct textual finding:** the full original prompt contains no `Topla!` lettering instruction. This absence is demonstrable. **Semantic classification:** whether literal readable glyphs are essential to the approved story is an owner interpretation; the word communicates the cleanup intention and reinforces the irony of the cabinet remaining messy, but does not cause the sticky-note doubling mechanism.

The source explicitly mentions a written note, so it should not be dismissed as irrelevant by default. Conversely, requiring every source word literally on screen would overstate fidelity requirements. This is prop text, not obligatory spoken dialogue. An equivalent visible cleanup intention could be acceptable only if the owner explicitly judges it equivalent; no such decision has been made.

**Visible-story impact:** possibly weakens the cleanup setup/ending irony; no text-only evidence proves the joke or central event is lost. **Seedance concern:** actual legibility of small prop lettering at the authoritative 480p setting is unverified. Simply adding “readable text” creates an additional visual-execution requirement; no generated frame proves or disproves it, and this review makes no model-capability claim.

**Appropriate targeted clarification, if authorized:** establish whether exact lettering or equivalent cleanup intent is required. If exact lettering is essential, specify the prop content and plan how to verify it in the accepted visual input/output. If intent is sufficient, explicitly document that interpretation. Do not silently edit the source or Prompt 10, add dialogue or mandate readable typography as an automatic correction.

## 5. Actual finding B — escalation after the mirror

Exact approved source ordering:

> Mimi aynada kendini görünce çığlık atar. Notlar o kadar çoğalır ki Mimi boğulacak gibi olur. Sonunda hapşırır ve tüm notlar uçuşarak dolabın üzerine yapışır.

Relevant exact original prompt:

> 5-10s: Mimi continues to pull; each pull doubles the number of sticky notes [wide shot showing Mimi covered in notes] notes multiply from two to four to eight as she pulls, progressively covering her arms, legs and face -> Mimi is overwhelmed by notes

> 10-12s: Mimi sees herself in a mirror and screams [close-up on Mimi's shocked face] Mimi is startled by her reflection completely covered in notes -> Mimi is startled

> 12-15s: Mimi sneezes and the sticky notes fly off [medium shot of notes flying] notes scatter and stick to the cabinet -> Mimi breathes a sigh of relief but the cabinet remains messy

**Direct textual finding:** the prompt explicitly stages the overwhelming coverage before the mirror, then moves from mirror/scream to sneeze. It contains no explicit post-mirror instruction for an additional near-suffocation presentation. **Semantic interpretation needed:** the already-covered, overwhelmed state may continue across the mirror scene. “Boğulacak gibi” may be an intensification of that continuous state rather than a new discrete physical action. Literal text placement alone does not prove the visible source event was omitted.

**Evidence strength:** a defensible ambiguity/order-risk finding; **not an established missing new action**. The raw model's categorical omission claim is stronger than what literal inspection alone proves. The need for post-mirror escalation/visible strain must be adjudicated without inventing another pull, another attempt or new timestamps.

**Visible-story impact:** an explicit escalation-to-sneeze transition may make the source's pressure/release sequence clearer. Existing overwhelming coverage may already communicate it; no rendered evidence resolves that. **Seedance concern:** face coverage, mirror readability, state continuity and the existing three-second sneeze/scatter/cabinet/relief window are text-supported production risks. Additional choreography could increase complexity. None is a confirmed rendered defect.

**Appropriate targeted clarification, if authorized:** clarify the continuation/intensification of the existing covered state between mirror and sneeze while preserving the approved event sequence and playful tone. Do not add a separate event, real injury, fabricated sub-beat timing or a third attempt. No actual prompt repair was performed.

## 6. Short owner adjudication packet — proposed choices only

No owner finding decision is recorded by this report. The owner remains one authenticated person, never two independent human reviewers.

| Choice | Finding A: note lettering | Finding B: mirror/escalation |
| --- | --- | --- |
| Accept as genuine missing source event/detail | Exact written prop content is essential; its absence requires a bounded correction | Distinct visible post-mirror escalation is essential and not represented adequately |
| Treat as equivalent visual implementation | Cleanup intention is sufficient without requiring readable glyphs; equivalence must be explicitly justified | Existing continuous coverage/overwhelmed reaction represents the same state across the mirror |
| Request targeted prompt clarification | Clarify exact lettering versus cleanup intent and how visual evidence will verify it | Clarify the continuing/intensifying state before sneeze without adding events/timings |
| Mark evidence insufficient | Text alone cannot determine whether the cleanup intention is visually evident | Text alone cannot determine whether the persistent covered state communicates the source intensity/order |

**Suggested review focus, not an approval:** targeted clarification is proportionate for both ambiguities; decide the required visual meaning before writing any prompt revision. The raw FAIL remains available and is not overruled by this recommendation. Neither finding automatically changes the canonical score or establishes render readiness.

## 7. Focused tests and production integrity

**ML: 112 passed**, no failures/skips; one unrelated file-regenerating request-size diagnostic test was deselected to avoid rewriting earlier fixture evidence. All single-subject behavior tests, prior budget/provider failure tests, owner-machine pilot tests and 37 new citation cases ran. Optional tokenizer check ran using the existing temporary diagnostic tokenizer; no dependency installation was performed.

**Backend: 36 passed**, zero skips/errors/failures: six pure citation test methods (including loops across rejection cases), 25 real-input/disposable PostgreSQL integration tests and five owner-auth tests. No production database writes or provider transports occurred. In particular, the saved failed request was copied into disposable PostgreSQL, validated only in memory, and compared before/after: its row remained identical, no MACHINE_REVIEW row appeared, source coverage remained zero, critic gate stayed false, humanReviewCount=0, grading inactive and render authorization false.

Cases cover exact saved real output, valid single citations, local two/three-event ranges, anchor containment, noncontiguous/reordered/fabricated/partial/whitespace-normalized/overlong/whole-story quotes, ordinary-anchor strictness, unknown/wrong event IDs, missing anchors/spans, range-only coverage refusal, unsupported PASS, complete FAIL/UNKNOWN, legacy batch behavior and no evidence promotion/gate bypass.

`git diff --check` passed. Frontend and canonical code were not changed; no full-stack rebuild or frontend suite was run for this focused validator task. Earlier broader frontend failures remain disclosed in the prior report and are not claimed resolved.

Read-only production checks show:

- All three historical durable request rows unchanged; ordered full-request digest remains `9fc8542ec7114168e49ba427908982ac5bedb1d6f592b71ee3b0b029cd2ce281`.
- Three requests, zero pilot machine-evidence rows, zero critic requests.
- Prompt 10/version 1 SHA unchanged; source/story/settings and 75 historical workflow events/digest unchanged.
- Official production review remains NOT_EVALUATED; canonical Ruleset 1.11 / 88.40625/B unchanged.
- Both real-dispatch flags false; CPQ grading inactive. Deployed backend and ML images remain unchanged.

No deployment, Docker rebuild/cleanup, model call, replay, direct production SQL mutation, owner approval, story/prompt change, grade activation, rendering, publication, commit or push occurred. Host headroom stayed approximately 1.2 GiB; tests used existing dependencies and disposable PostgreSQL only.

## 8. Deployment requirement and shortest controlled acceptance path

**Affected services: ML and backend only. No migration; V66 remains sufficient. No frontend rebuild.** Deploy both corrected validators together after separate deployment authorization, with dispatch disabled. The official backend deployment helper may restart frontend for nginx address resolution; that does not require a new frontend image. The JSON response shape and existing batch records remain compatible, but mixed old/new validators would still reject the multi-event quote at one layer.

Offline revalidation does not change the old execution to COMPLETED. The current owner-pilot API has no command for accepting a saved failed provider response through a separate append-only offline revalidation record; normal source completeness requires a COMPLETED request plus matching immutable evidence. Do not pretend that an existing recovery/import endpoint exists, use direct SQL, rerun execute, or backfill a false successful execution.

**Shortest no-new-inference route to formal acceptance:** after deployment, explicit owner review/authorization could admit a **new, separately identified append-only revalidation decision/evidence record** referencing the existing real provider request, exact raw-response/input/prompt/story/settings hashes and corrected validator version. It must state that provider output was reused and no new inference occurred, preserve the old FAILED_OR_AMBIGUOUS row, retain semantic FAIL/UNKNOWN/uncertainty, and use an explicitly governed acceptance/gate rule. That narrow acceptance operation is not implemented or authorized by this citation-only task. An ordinary OWNER_DECISION can record the owner's interpretation, but is not automatically completed machine source evidence.

No paid inference is technically needed to re-examine this stored JSON. No paid retry is proposed here. Until an authorized controlled acceptance path exists, the proper production state is NOT_EVALUATED. Even if original-only revalidation is later formally accepted, the other three subjects remain missing and critics stay blocked. Owner adjudication of the two findings is the next evidence decision, not automatic candidate/prompt approval.

## 9. Required statuses

- CITATION_CONTRACT: **CORRECTED** (local code; not deployed)
- SAVED_OUTPUT_OFFLINE_VALIDATION: **PASS — OFFLINE_REVALIDATION_ONLY**
- Structurally admissible original model judgment: **FAIL**, unchanged
- REAL_PROVIDER_CALLS_THIS_TASK: **0**
- PRODUCTION_REVIEW_STATUS: **NOT_EVALUATED**
- HISTORICAL_REQUESTS: **UNCHANGED**
- CRITIC_REQUESTS: **0**
- CPQ_GRADING: **INACTIVE**
- REAL_DISPATCH: **DISABLED**

Evidence directory: `cpq-source-citation-final-repair-evidence/` contains deployed-validator reproduction, immutable hashes, revised-validator diagnostics with every resolved citation, focused test logs and final production integrity/test counts. Full raw response stays in its original delivery evidence directory. No copied provider response is relabelled as a new execution or human assessment.
