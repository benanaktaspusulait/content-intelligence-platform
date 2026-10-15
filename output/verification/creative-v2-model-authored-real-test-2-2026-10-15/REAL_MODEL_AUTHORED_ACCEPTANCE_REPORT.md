# REAL_MODEL_AUTHORED_ACCEPTANCE_REPORT

**Primary result: REAL_MODEL_AUTHORING_CONTRACT_FAILURE**

**Operator recommendation: KEEP_ORIGINAL.**

One real inference completed. It returned two structured proposals and neither passed the authoring contract. No complete revised prompt was compiled, no candidate canonical evaluation or execution critic ran, and no selection/approval was made. This run did not demonstrate a useful independent creative reconstruction. Its failure is not an OpenAI connectivity failure or evidence that the approved story actually changed.

## 1. Provider, model and dispatch proof

| Item | Actual evidence |
|---|---|
| Provider | OpenAI direct, no custom API base |
| Requested model | `gpt-4o-mini-2024-07-18` |
| Completed provider response | `chatcmpl-EZEiQxunvxhZjZUCRJBwxSIecaZK1` |
| Finish reason | `stop` |
| Official application command | `POST /api/v1/intelligence/workflow/records/f0d36feb-ee0f-4da8-ae21-2071a3ddea18/creative-optimization` |
| Official HTTP outcome | 200, approximately 11.38 seconds; this is not candidate acceptance |
| Instructions version | `model-authored-production-v1` |
| Real inference requests | **1** |
| Automatic retries / fallback | **0 / none** |
| Request output limit | **4,000 tokens** |
| Authorization ID | `567d41d3-fda4-422c-98b3-206ddb0bd3a3` |
| Attempt ID | `2fa80bfc-aedb-4750-9f5c-96e3bd66c0f2` |
| Durable reservation record | `bf864696-f668-4a9f-a46d-a5da720db875` |
| Completed role record | `d7b98b52-034f-4c7f-b2d5-238e428d5439` |
| Normal immutable comparison record | `2e2adcea-31de-4817-8fc8-8e301396fa50` |
| Request fingerprint | `f4b20f02d6b36af6c44044100ebd6fb1248b5b2f677e37b9475905cffa7a9d5a` |


A separate fresh user authorization was bound to the supplied attachment and an exclusive local send marker. Before sending, there were zero existing model-authored-production-v1 attempts. The application used its normal advisory-lock/fingerprint and REQUIRES_NEW durable reservation. Exactly one official POST and one ML creative-role access-log entry occurred; the provider adapter has max_retries=0 and one completion call. The saved completed role reports calls=1 and a single completion ID with usage. No raw external network packet trace was captured; request-count evidence is the bounded code path, access log and durable provider completion, not an invented transport trace.

The two new CREATIVE_ROLE rows are an append-only reservation and its completed result, linked by the same attempt ID and fingerprint. They are not two inferences. The third new row is the normal CREATIVE_OPTIMIZATION comparison. The reservation’s original OUTCOME_UNKNOWN label remains historical audit evidence; its matching completed record resolves this operation.

Evidence: [explicit-authorization.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/explicit-authorization.json), [preflight-result.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/preflight-result.json), [official-request.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/official-request.json), [official-transport-result.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/official-transport-result.json), [provider-dispatch-log.txt](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/provider-dispatch-log.txt), [new-durable-workflow-records.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/new-durable-workflow-records.json), [authorization-consumption.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/authorization-consumption.json).

## 2. Actual usage, cost and preflight bindings

- Input tokens: **6,432**; cached input tokens: **0**.
- Output tokens: **722**; total: **7,154**.
- Calculated cost: `(6432 × $0.15 + 722 × $0.60) / 1,000,000` = **USD $0.001398**.
- Authorized total ceiling: **USD $0.20**. Unused allowance does not authorize another request.
- Application pre-dispatch estimate: **USD $0.00645225**, using 18,908 payload bytes + 4,019 schema bytes + 4,088 system bytes and maximum 4,000 output tokens. The payload remained under the existing 24,000-byte input gate.


These are provider-reported tokens multiplied by the configured rates, not an account invoice. The rates were checked against the [official GPT-4o Mini model page](https://developers.openai.com/api/docs/models/gpt-4o-mini); exact snapshot/Structured Outputs support was checked against [official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs). An authenticated model-metadata GET returned 200 before dispatch; it is not an inference and was not treated as proof of successful generation.

Content 10, Prompt ID 10/version 1, Ruleset 1.11 and analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18` matched the saved source and current settings. Prompt SHA-256: `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98`; approved-story SHA-256: `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b`. Settings record: `2d90c69b-bcec-4871-9c4e-7e029906c974`; ABSURD_PHYSICS, SEEDANCE_2_0_MINI, 15 seconds, 9:16.

The request contained the original prompt, approved story, all source event anchors, protected/editable layers, current diagnosis, generator settings and source-reference catalog. It offered multiple diagnosed opportunities without preselecting CONTACT_PLANE. It did not contain a mock response, improved full-prompt fixture or previous real candidate. Generic diagnostic improvement suggestions were present; resemblance to those suggestions is not counted as independently invented choreography.

After completion, the request was reconstructed from persisted source/context with the deployed code. Schema, system and parsed user payload match preflight. Serialized JSON key order differs following persistence; exact transport bytes were not logged. See [request-preflight-match.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/request-preflight-match.json) and [provider-request-reconstructed-from-persisted-context.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/provider-request-reconstructed-from-persisted-context.json).

## 3. Exact real structured model response

This is the genuine structured provider output, not a repaired or mocked response. JSON indentation/key order below is for readability; [raw-provider-response.txt](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/raw-provider-response.txt) preserves the returned response string.

```json
{
  "proposals": [
    {
      "initial": {
        "title": "Enhanced Visual Clarity of Attachment",
        "objective": "Improve the visibility of the intended attachment surface and the actual attachment point to enhance viewer understanding.",
        "candidateId": "candidate-a",
        "interventions": [
          {
            "camera": "LOCKED",
            "layout": "LATERAL",
            "operation": "CONTACT_PLANE",
            "rationale": "By staging the cabinet behind or beside Mimi's finger, viewers can clearly see the intended attachment surface and the actual attachment point, enhancing the comedic effect of the failed attempt.",
            "authorship": "MODEL_AUTHORED",
            "production": {
              "choreography": {
                "instruction": "Mimi reaches toward the toy cabinet with a sticky note; the note visibly clings to her finger instead of sticking to the cabinet.",
                "sourceActionRef": "beat_01.action",
                "sourceConsequenceRef": "beat_01.consequence",
                "consequencePresentation": "The note sticks to Mimi's finger, not the cabinet."
              },
              "stateProgression": [],
              "cameraComposition": "Close-up on Mimi's hand showing the sticky note clinging to her finger, with the cabinet clearly visible in the background.",
              "generatorConstraints": [
                "Aspect ratio: 9:16",
                "Target generator: SEEDANCE_2_0_MINI"
              ],
              "spatialRelationships": [
                {
                  "relation": "IN_FRONT_OF",
                  "objectRef": "the cabinet",
                  "subjectRef": "Mimi",
                  "instruction": "Mimi reaches toward the cabinet with a sticky note, her finger visibly sticking to the note."
                }
              ],
              "temporalPresentation": "0-2s: Mimi reaches toward the toy cabinet with a sticky note; the note visibly clings to her finger instead of sticking to the cabinet."
            },
            "opportunityId": "CONTACT_PLANE:beat_01",
            "fallbackReason": null
          }
        ],
        "storyChangeRequested": false
      },
      "revision": null
    },
    {
      "initial": {
        "title": "Separated Action and Result Visibility",
        "objective": "Enhance the clarity of Mimi's action and the resulting state of the sticky notes.",
        "candidateId": "candidate-b",
        "interventions": [
          {
            "camera": "LOCKED",
            "layout": "LATERAL",
            "operation": "SEPARATE_ACTION_RESULT",
            "rationale": "By separating the action of peeling the note and the result of it splitting into two, viewers can better understand the transition and the resulting chaos of the sticky notes.",
            "authorship": "MODEL_AUTHORED",
            "production": {
              "choreography": {
                "instruction": "Mimi tries to peel the stuck note away with her other hand; the note splits into two.",
                "sourceActionRef": "beat_02.action",
                "sourceConsequenceRef": "beat_02.consequence",
                "consequencePresentation": "One note sticks to each hand."
              },
              "stateProgression": [],
              "cameraComposition": "Medium shot showing Mimi struggling to peel the note, with the two resulting notes clearly visible in each hand.",
              "generatorConstraints": [
                "Aspect ratio: 9:16",
                "Target generator: SEEDANCE_2_0_MINI"
              ],
              "spatialRelationships": [
                {
                  "relation": "IN_FRONT_OF",
                  "objectRef": "the sticky note",
                  "subjectRef": "Mimi",
                  "instruction": "Mimi tries to peel the sticky note away with her other hand."
                },
                {
                  "relation": "SEPARATED_FROM",
                  "objectRef": "Mimi's hands",
                  "subjectRef": "the sticky note",
                  "instruction": "The note splits into two, with one note sticking to each hand."
                }
              ],
              "temporalPresentation": "2-5s: Mimi tries to peel the stuck note away with her other hand; the note splits into two, with one note sticking to each hand."
            },
            "opportunityId": "SEPARATE_ACTION_RESULT:beat_02",
            "fallbackReason": null
          }
        ],
        "storyChangeRequested": false
      },
      "revision": null
    }
  ],
  "noImprovementReason": null
}
```

## 4. Exact text returned in MODEL_AUTHORED fields

The provider claimed MODEL_AUTHORED for both plans. The following 15 field values genuinely occurred in its response. They were **not accepted into a compiled candidate**. “Returned by the model” does not imply original creative invention: many values copy or paraphrase the source or settings.

### candidate-a · beat_01

`production.spatialRelationships.0.instruction`

> Mimi reaches toward the cabinet with a sticky note, her finger visibly sticking to the note.

`production.choreography.instruction`

> Mimi reaches toward the toy cabinet with a sticky note; the note visibly clings to her finger instead of sticking to the cabinet.

`production.choreography.consequencePresentation`

> The note sticks to Mimi's finger, not the cabinet.

`production.temporalPresentation`

> 0-2s: Mimi reaches toward the toy cabinet with a sticky note; the note visibly clings to her finger instead of sticking to the cabinet.

`production.cameraComposition`

> Close-up on Mimi's hand showing the sticky note clinging to her finger, with the cabinet clearly visible in the background.

`production.generatorConstraints.0`

> Aspect ratio: 9:16

`production.generatorConstraints.1`

> Target generator: SEEDANCE_2_0_MINI

### candidate-b · beat_02

`production.spatialRelationships.0.instruction`

> Mimi tries to peel the sticky note away with her other hand.

`production.spatialRelationships.1.instruction`

> The note splits into two, with one note sticking to each hand.

`production.choreography.instruction`

> Mimi tries to peel the stuck note away with her other hand; the note splits into two.

`production.choreography.consequencePresentation`

> One note sticks to each hand.

`production.temporalPresentation`

> 2-5s: Mimi tries to peel the stuck note away with her other hand; the note splits into two, with one note sticking to each hand.

`production.cameraComposition`

> Medium shot showing Mimi struggling to peel the note, with the two resulting notes clearly visible in each hand.

`production.generatorConstraints.0`

> Aspect ratio: 9:16

`production.generatorConstraints.1`

> Target generator: SEEDANCE_2_0_MINI

## 5. Compiler/source contribution and provenance

| Provenance class | Actual contribution in this test |
|---|---|
| PROTECTED_SOURCE | Exact saved original prompt and approved story supplied as protected input; no replacement prompt produced |
| MODEL_AUTHORED | The 15 raw production-field strings above; unaccepted proposal text, mostly source paraphrases |
| SOURCE_BOUND_SUBSTITUTION | **0 in compiled output**; no output was compiled and the response supplied no `{referenceId}` substitutions |
| SERVER_ASSEMBLY | **0 in a revised prompt**; critique rejected both proposals before assembly |
| SERVER_TEMPLATE | **0**; no explicit fallback and no silent template replacement |
| AUTHORITATIVE_SETTINGS | Existing settings were supplied to the model; the model repeated aspect ratio/generator strings. No compiled normalization or new settings record occurred |


No final-prompt span partition is fabricated because there is no final prompt. The compiler did not write winning choreography, repair source references or replace rejected instructions. Source preservation and server-provided diagnostic suggestions are inputs, not creative model achievements.

## 6. Full original prompt (exact saved input)

```text
TITLE / FORMAT
Mimi Sticky / 15s Video

VISUAL STYLE
Bright and colorful animation with a playful tone.

CHARACTER / CONTINUITY
Mimi, an anthropomorphic bunny, interacts with sticky notes in a humorous and chaotic manner.

TIMED SHOT PLAN
0-2s: Mimi reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to her finger [close-up on Mimi's hand] Mimi is in front of a toy cabinet, looking determined -> the note sticks to Mimi, not the cabinet
2-5s: Mimi tries to peel the stuck note away with her other hand; the note splits into two [medium shot of Mimi struggling] Mimi pulls at the note -> one note sticks to each hand
5-10s: Mimi continues to pull; each pull doubles the number of sticky notes [wide shot showing Mimi covered in notes] notes multiply from two to four to eight as she pulls, progressively covering her arms, legs and face -> Mimi is overwhelmed by notes
10-12s: Mimi sees herself in a mirror and screams [close-up on Mimi's shocked face] Mimi is startled by her reflection completely covered in notes -> Mimi is startled
12-15s: Mimi sneezes and the sticky notes fly off [medium shot of notes flying] notes scatter and stick to the cabinet -> Mimi breathes a sigh of relief but the cabinet remains messy

AUDIO
Playful background music with sound effects for sneezing and notes sticking.

NEGATIVE CONSTRAINTS
No dark themes or violence.

FINAL CUT
Mimi is relieved but the cabinet remains visibly messy.

CHARACTER IDENTITY LOCK
Mimi is the established anthropomorphic bunny character. Preserve that identity; do not render a human or invent unverified visual details. No approved visual reference is currently bound, so appearance details remain unverified.

PRODUCTION SETTINGS
Aspect ratio: 9:16. Target generator: SEEDANCE_2_0_MINI. Content profile: AUTO.
```

## 7. Full reconstructed prompt

**NOT PRODUCED.** Both proposals failed validation before `compile_reconstruction` could produce a complete candidate. No manually fixed timestamp, substituted reference, merged prompt or second model response has been substituted. [reconstructed-prompt-unavailable.txt](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/reconstructed-prompt-unavailable.txt) records this absence explicitly. Full original text above remains authoritative.

## 8. Beat-by-beat execution comparison

### candidate-a · beat_01 — proposed, not compiled

**ORIGINAL — exact full beat, including its original production annotation:**

```text
0-2s: Mimi reaches toward the toy cabinet with a sticky note; instead of sticking to the cabinet, the note visibly clings to her finger [close-up on Mimi's hand] Mimi is in front of a toy cabinet, looking determined -> the note sticks to Mimi, not the cabinet
```

**MODEL-AUTHORED REVISION — exact production object returned:**

```json
{
  "choreography": {
    "instruction": "Mimi reaches toward the toy cabinet with a sticky note; the note visibly clings to her finger instead of sticking to the cabinet.",
    "sourceActionRef": "beat_01.action",
    "sourceConsequenceRef": "beat_01.consequence",
    "consequencePresentation": "The note sticks to Mimi's finger, not the cabinet."
  },
  "stateProgression": [],
  "cameraComposition": "Close-up on Mimi's hand showing the sticky note clinging to her finger, with the cabinet clearly visible in the background.",
  "generatorConstraints": [
    "Aspect ratio: 9:16",
    "Target generator: SEEDANCE_2_0_MINI"
  ],
  "spatialRelationships": [
    {
      "relation": "IN_FRONT_OF",
      "objectRef": "the cabinet",
      "subjectRef": "Mimi",
      "instruction": "Mimi reaches toward the cabinet with a sticky note, her finger visibly sticking to the note."
    }
  ],
  "temporalPresentation": "0-2s: Mimi reaches toward the toy cabinet with a sticky note; the note visibly clings to her finger instead of sticking to the cabinet."
}
```

**Observable difference:** A close-up of the hand remains, now explicitly asking for the cabinet to be clearly visible in the background. The reach and wrong-surface attachment are restated. It does not specify a new contact plane for the cabinet versus finger, an edge/gap arrangement, occlusion handling or a new continuous physical choreography. The original already places Mimi in front of a cabinet and uses close hand framing.

**Expected benefit:** The model’s rationale hypothesizes easier recognition of destination versus actual attachment. That is a plausible framing intention, not evidence of increased understanding or retention. A material production improvement is not established by the added visibility adjective.

**Execution risk:** Simultaneously keeping a small sticky note/finger contact and the cabinet readable in a close-up may create scale/composition or focus competition. No arrangement is given to resolve that tradeoff. This is an untested risk hypothesis, not an observed render defect.

**Evidence status:** Exact output text supports the above comparison. Visual legibility, successful generation, timing feasibility and viewer response remain unverified.

### candidate-b · beat_02 — proposed, not compiled

**ORIGINAL — exact full beat, including its original production annotation:**

```text
2-5s: Mimi tries to peel the stuck note away with her other hand; the note splits into two [medium shot of Mimi struggling] Mimi pulls at the note -> one note sticks to each hand
```

**MODEL-AUTHORED REVISION — exact production object returned:**

```json
{
  "choreography": {
    "instruction": "Mimi tries to peel the stuck note away with her other hand; the note splits into two.",
    "sourceActionRef": "beat_02.action",
    "sourceConsequenceRef": "beat_02.consequence",
    "consequencePresentation": "One note sticks to each hand."
  },
  "stateProgression": [],
  "cameraComposition": "Medium shot showing Mimi struggling to peel the note, with the two resulting notes clearly visible in each hand.",
  "generatorConstraints": [
    "Aspect ratio: 9:16",
    "Target generator: SEEDANCE_2_0_MINI"
  ],
  "spatialRelationships": [
    {
      "relation": "IN_FRONT_OF",
      "objectRef": "the sticky note",
      "subjectRef": "Mimi",
      "instruction": "Mimi tries to peel the sticky note away with her other hand."
    },
    {
      "relation": "SEPARATED_FROM",
      "objectRef": "Mimi's hands",
      "subjectRef": "the sticky note",
      "instruction": "The note splits into two, with one note sticking to each hand."
    }
  ],
  "temporalPresentation": "2-5s: Mimi tries to peel the stuck note away with her other hand; the note splits into two, with one note sticking to each hand."
}
```

**Observable difference:** The existing medium shot and peel→split→one-note-per-hand result are restated. “Clearly visible in each hand” adds desired visibility, but no screen positions, distinct hand paths, contact-edge continuity or action/result separation are actually specified.

**Expected benefit:** The rationale proposes separating action and result, but the production fields do not implement that separation. Merely naming the existing result does not demonstrate a new production plan.

**Execution risk:** Hand identity, contact continuity and the split transition remain unresolved. There is no demonstrated reduction of simultaneous-action complexity or object-count difficulty. These are source-supported planning concerns, not new confirmed generator failures.

**Evidence status:** Exact output text supports the above comparison. Visual legibility, successful generation, timing feasibility and viewer response remain unverified.

### Remaining source beats

The model did not select beat_03 (5–10s, 2→4→8 multiplication), beat_04 (mirror/scream) or beat_05 (sneeze/scatter/messy cabinet). Both stateProgression arrays are empty. It was allowed to choose its relevant beats; not selecting every beat is not itself a contract violation. However, this response supplies no new multiplication choreography to assess. Since compilation never happened, these source beats must not be represented as validated sections of a new complete candidate.

## 9. Actual materiality assessment

- **Meaningful new physical choreography:** not demonstrated. Both primary actions and consequences closely repeat the existing source.
- **Opening clarity on paper:** a minor background-visibility/framing emphasis is present; material causal-legibility improvement is not established.
- **2→4→8 execution:** not addressed; no state arrangement or transition authored.
- **Temporal clarity:** the model copied existing timed narrative rows rather than authoring an execution-specific temporal presentation.
- **Verbosity versus usefulness:** extra structure and instructions do not by themselves establish improvement. Generator/aspect-ratio strings merely repeat protected settings.
- **Visual causality:** no obvious intentional story substitution is visible in the raw plan, but no validated full-prompt source coverage or semantic assessment exists.
- **Candidate preferable to Original:** not established; no valid candidate is available for comparison/approval.


These are conservative textual observations of this one sample, not a claim that the model can never create useful choreography. The contract failure prevents a complete evaluation; the visible raw content also does not justify calling the product creatively successful.

## 10. Source/story fidelity and exact contract failure

**The strict JSON structure parsed successfully.** The failure was in application-level authored-plan validation. The saved pipeline rejected both plans as STORY_FIDELITY_FAILED, with the same first error:

```text
STORY_FIDELITY_FAILED: preserve source beat windows; no unbound sub-beat timestamps
```

**Timing diagnosis:** Candidate A writes `0-2s`; B writes `2-5s`. Both exactly match their source beat windows. There is no evidence of an invented sub-beat timestamp or changed duration. The broad regex rejects any numeric range, so the error message/source-fidelity inference is misleading for this input. It may enforce a timecode-free production-field format, but that is different from proving changed story timing. No guard or diagnostic was patched in this test.

**Independent real contract failures remain:** all six spatial subjectRef/objectRef values are names/phrases rather than supplied catalog IDs. Valid choreography action/consequence refs do not make invalid spatial refs acceptable.

| Candidate | Field | Actual supplied value | Result |
|---|---|---|---|
| candidate-a | `spatialRelationships.0.subjectRef` | `Mimi` | Not a catalog ID |
| candidate-a | `spatialRelationships.0.objectRef` | `the cabinet` | Not a catalog ID |
| candidate-b | `spatialRelationships.0.subjectRef` | `Mimi` | Not a catalog ID |
| candidate-b | `spatialRelationships.0.objectRef` | `the sticky note` | Not a catalog ID |
| candidate-b | `spatialRelationships.1.subjectRef` | `the sticky note` | Not a catalog ID |
| candidate-b | `spatialRelationships.1.objectRef` | `Mimi's hands` | Not a catalog ID |

The catalog actually supplied `beat_01.actor`, `beat_01.expectedSurface` and `beat_01.actualSurface` with exact source quotes/spans. Candidate A did not bind the mandatory expected/actual attachment pair. Its declared IN_FRONT_OF instruction does not express that directional geometry; Candidate B similarly states narrative events rather than concrete separation geometry. These problems would still exist if the redundant-timecode rejection were treated differently. They are not fixed or compiled in a counterfactual candidate here.

**Architecture limitation exposed:** the wire schema makes these reference fields arbitrary strings, while the consumer requires exact catalog IDs. Instructions say to use source references, but JSON-schema acceptance cannot enforce those dynamic IDs. The model could therefore satisfy the provider schema while failing the server contract. Materiality must also inspect actual staging content, not assume that a named operation/relationship establishes it.

Source/story fidelity remains **UNKNOWN**. The stored “story fidelity failure” counters are preserved as returned; this report does not reinterpret them as proof of an altered approved narrative or overwrite their historical values. See [untouched-response-contract-forensics.json](/Users/benanaktas/project/video/content-intelligence-platform/output/verification/creative-v2-model-authored-real-test-2-2026-10-15/untouched-response-contract-forensics.json).

Relevant unchanged code: [time-range guard](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/model_authored_execution.py:114), [reference resolver](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/model_authored_execution.py:158), [contact participant requirement](/Users/benanaktas/project/video/content-intelligence-platform/intelligence/ml-service/app/workflow/model_authored_execution.py:202).

## 11. Canonical score comparison

| Input/result | Ruleset | Score/grade | Canonical status |
|---|---|---|---|
| Saved Original | 1.11 | **88.40625 / B** | Existing authoritative evaluation, unchanged |
| Raw proposal A | — | **N/A** | Rejected before full prompt/canonical evaluation |
| Raw proposal B | — | **N/A** | Rejected before full prompt/canonical evaluation |

No candidate rule-by-rule delta exists. It would be incorrect to carry forward the Original’s score or the prior mock’s equal score as these candidates’ results. No rule, weight, outcome or historical score was changed.


## 12. Execution critic findings

**NOT RUN for these rejected proposals.** No complete prompt reached the local critic. There are no newly evaluated critic findings to suppress, call PASS or label false positive. The timing-regex classification above belongs to the authoring contract validator, not the execution critic. The earlier mock’s simultaneous-action warnings are not recycled as findings from this real response.

## 13. Production-risk changes and render safety

Full-pipeline production-risk regression is **NOT EVALUATED**. Manual textual risks are described per beat above. No improved contact/object continuity, count consistency or Seedance feasibility was verified. A close-up plus background visibility can compete for small-object readability; the model gives no concrete mitigation. No added attempts or invented count states are apparent in the response, but there is no complete compiled source-validation result.

The final record contains selection=null and approval=null. Original prompt text, approved story, production settings and the authoritative analysis remain identical before/after. All **72** pre-existing workflow rows have unchanged hashes; only the **three normal audit/result records** were appended. Prompt-version count remains **1**, render jobs **0**, governance events **0**. No ATTEMPT_001 exception, F8 authorization, character reference, accepted start frame, render, image, video or publication was created. F8/render readiness was not advanced.

## 14. Model-specific strengths and weaknesses observed in this run

**Observed strengths:** the requested model returned syntactically structured JSON within the cap; selected diagnosed source-supported opportunities; populated the new authoring object; kept LOCKED camera; supplied valid action/consequence IDs; used no explicit template fallback; and did not request a story change.

**Observed weaknesses:** it used natural-language entity names where catalog IDs were required; duplicated timed source rows in temporal presentation; selected relation labels without implementing their geometry; repeated existing actions/results instead of authoring substantial choreography; and left multiplication/state progression untouched. These findings describe this exact output, not a general ranking or proof of model incapability.


## 15. Evidence of improvement versus verbosity

The new technical capability was exercised: actual production fields came from a real provider response instead of a server template. That is a narrower observation than useful creative reconstruction. Here, additional structured text mostly repeats the baseline, desired visibility or protected settings. There is no demonstrated material contact arrangement, independently authored 2→4→8 staging, reduced temporal complexity or validated complete prompt. Neither successful provider dispatch nor extra prose establishes superiority. No visual, generation-adherence or audience evidence exists.

## 16. Decision and separate statuses

| Dimension | Finding |
|---|---|
| Primary classification | **REAL_MODEL_AUTHORING_CONTRACT_FAILURE** |
| Creative assessment | Material improvement not established; raw plans mostly baseline paraphrases/framing |
| Canonical score | Original 88.40625/B unchanged; candidate scores unavailable |
| Critic | NOT RUN after pre-compilation rejection |
| Production risk | Full evaluation unavailable; manual hypotheses only |
| Source fidelity | UNKNOWN; technical contract failures are not confirmed story mutations |
| Recommendation | **KEEP_ORIGINAL** |
| Approval / selection | None |
| Further paid calls under this authorization | **Not permitted; the single request is consumed** |


The saved aggregate outcome `NO_JUSTIFIED_IMPROVEMENT` means zero accepted candidates here; it is not evidence that the model abstained. Its raw `noImprovementReason` is null.

This is not REAL_MODEL_NO_JUSTIFIED_IMPROVEMENT: the model did propose two plans; the server rejected them. It is not classified as a validated equivalent or regression because no candidate reached those complete validation stages.

## 17. One next product action

**Repair the existing authoring contract offline using this untouched real response as the regression fixture.** Make the source-reference wire values unambiguous/validated against the catalog, and distinguish redundant exact beat-window text from genuinely invented sub-beat timing in the validator’s evidence classification. Retain the independent materiality rejection for source paraphrases. This targeted contract repair should precede any separately authorized real-model retest; it does not justify a new framework, a scoring change or another paid call now.

No production code, critic, ruleset or candidate was patched during this acceptance test. No response was repaired or regenerated. No second inference, automatic approval, new immutable prompt version, direct SQL update, commit or push was performed. The test ends with this evidence.
