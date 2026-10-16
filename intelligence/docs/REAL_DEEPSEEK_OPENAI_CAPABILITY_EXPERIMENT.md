EXPERIMENT: REAL_MODEL_A_CAPABILITY_RESEARCH_V1
OWNER_AUTHORIZATION: YES
AUTHORIZED_MANIFEST_REUSED: YES
SCOPE_FINGERPRINTS_MATCHED: YES

REAL_DEEPSEEK_GENERATION: YES
REAL_OPENAI_GENERATION: YES
REAL_OPENAI_REVIEWS: NO — no accepted DeepSeek candidate existed
REAL_DEEPSEEK_REVIEWS: NO — no accepted OpenAI candidate existed

REAL_PROVIDER_REQUESTS_ATTEMPTED: 2
REAL_PROVIDER_RESPONSES_RECEIVED: 2
ACCEPTED_CANDIDATES: 0
ACTUAL_PROVIDER_SPEND_USD: 0.05801854
MAX_AUTHORIZED_USD: 0.675625
UNRESOLVED_BILLING: NO
AUTOMATIC_RETRIES: 0
FALLBACKS_OR_MODEL_SUBSTITUTIONS: 0

DEEPSEEK_CANONICAL_SCORE: NOT_EVALUATED
DEEPSEEK_CANONICAL_GRADE: NOT_EVALUATED
DEEPSEEK_CREATIVE_VALIDITY: STORY_FIDELITY_FAILED

OPENAI_CANONICAL_SCORE: NOT_EVALUATED
OPENAI_CANONICAL_GRADE: NOT_EVALUATED
OPENAI_CREATIVE_VALIDITY: COMPILER_CONTRACT_FAILURE

BASELINE_CANONICAL_SCORE: 93.42708333333334
BASELINE_CANONICAL_GRADE: A
BASELINE_CREATIVE_VALIDITY: CREATIVE_RISK_DETECTED / PROVISIONAL
FINAL_CANONICAL_A_ADMITTED: NO
OFFICIAL_CREATIVE_A_PLUS: INACTIVE

EXPERIMENT_STATUS: EXECUTED_STOPPED_NO_ACCEPTED_CANDIDATE
CAPABILITY_COMPARISON: INCONCLUSIVE

# Real DeepSeek vs OpenAI capability experiment

## Scope and safety result

The exact prepared disposable snapshot and its existing manifest were reused. Before dispatch, the worker matched all five authorized fingerprints:

| Binding | Authorized and executed SHA-256 |
|---|---|
| Source scope | `962dd2d754dfed207f8f5d5fdee7fdf48fded3b34d08fe7f848a1649614ac613` |
| Instruction context | `a16599a2f0a0be747185490dd15d7eced8e1d08c6cf0c091f512a0fca06a1a67` |
| Approved story | `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d` |
| Baseline prompt | `1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5` |
| Production settings | `e6aedfab391d7ee0a7e753b3dc8f4e8d57c31d8b2ada4b9f8b130b95b2689937` |

The network policy allowed only `api.deepseek.com` and `api.openai.com`; it recorded no blocked attempt and exposed no fixture fallback. All database writes were confined to the restored disposable PostgreSQL snapshot. No production database write, global configuration change, deployment, prompt approval, story evolution, image generation, video render, publication, commit or push occurred.

The baseline remained Ruleset 1.11 `93.42708333333334/A`, but its creative result remains provisional: frame-zero evidence, visual silhouette evidence and real render behavior are unresolved. That baseline score is not attributed to either provider.

## Execution accounting

| Run | Durable request | Provider/model | Ledger state | Prompt | Completion | Total | Verified cost | Result |
|---|---|---|---|---:|---:|---:|---:|---|
| A | `6fc1bcbd-1425-4440-9569-7a2ee34ba39e` | DeepSeek / `deepseek-v4-pro` | `COMPLETED` | 13548 | 608 | 14156 | USD 0.02029104 | Response accepted by transport; plan rejected by source-fidelity validator |
| B | `21dddc65-7a77-48b0-9bff-33bbd55d8766` | OpenAI / `gpt-6.1-sol` | `FAILED_OR_AMBIGUOUS` | 12399 | 673 | 13072 | USD 0.0377275 | Response received and billed; deterministic compilation failed locally |

Run A reserved USD `0.088727` and stopped after one request with `ROUND_LIMIT`. Run B reserved USD `0.178043` and stopped after one request with `UNCERTAIN_PROVIDER_DISPATCH_OR_CONTRACT`. Total reservation was USD `0.2667700000`; verified incurred cost was USD `0.05801854`, 8.59% of the USD `0.675625` experiment ceiling. Both provider responses reported `finishReason=stop`, the configured model identities, complete usage accounting, and fewer than 4,000 completion tokens.

The OpenAI request's `FAILED_OR_AMBIGUOUS` ledger state concerns end-to-end request completion, not billing. The provider returned a response and complete token usage, so the recorded USD `0.0377275` is treated as incurred. The no-retry policy was honored.

## Run A — actual DeepSeek result

DeepSeek independently chose the diagnosed `SEPARATE_ACTION_RESULT:beat_02` opportunity and proposed a locked lateral hand-separation treatment. The deterministic materiality check found new physical features (`apart`, `gap`, `left`, `right`) and classified the textual change as material but visually unverified.

The proposal was rejected before prompt compilation:

- Classification: `STORY_FIDELITY_FAILED`
- Exact reason: `STORY_FIDELITY_FAILED: BOUND_PARTICIPANTS_NOT_ADDRESSED`
- Exact field: `spatialRelationships.1`
- Source grounding: `SOURCE_REFERENCES_BOUND`
- Semantic story fidelity: `UNKNOWN`
- Visual benefit: `UNKNOWN`
- Audience benefit: `UNMEASURED`

The second spatial relationship bound `beat_02.entity.0` and `beat_02.hand`, but its instruction described “the two notes” and left/right hands instead of addressing the exact bound subject/object pair. The validator correctly refused to turn this into a source-faithful prompt. No OpenAI source-fidelity or creative-critic request was therefore eligible.

### Complete DeepSeek structured model response

```json
{
  "proposals": [
    {
      "initial": {
        "candidateId": "candidate-a",
        "title": "Staged hand separation for beat 2",
        "objective": "The baseline beat 2 presents the action and result in the same center-frame cluster, making it hard to distinguish the single-note peel from the two-note split.",
        "interventions": [
          {
            "opportunityId": "SEPARATE_ACTION_RESULT:beat_02",
            "operation": "SEPARATE_ACTION_RESULT",
            "layout": "LATERAL",
            "camera": "LOCKED",
            "rationale": "The source beat already has two distinct hand positions. I propose staging the free hand slightly to the left as it reaches for the note on the right fingertip. When the note splits, the two resulting notes occupy clearly separated left and right hand zones, making the one-to-two transition visually distinct instead of a cluttered center motion.",
            "authorship": "MODEL_AUTHORED",
            "production": {
              "spatialRelationships": [
                {
                  "subjectRef": "beat_02.hand",
                  "relation": "LEFT_OF",
                  "objectRef": "beat_02.entity.0",
                  "instruction": "Position the free hand slightly left of the note-bearing hand at the start of the peel so the two hands are laterally separated before the split."
                },
                {
                  "subjectRef": "beat_02.entity.0",
                  "relation": "RIGHT_OF",
                  "objectRef": "beat_02.hand",
                  "instruction": "Once the split completes, the two notes settle on laterally separated hands, one left and one right, so the doubling is clearly readable."
                }
              ],
              "choreography": {
                "sourceActionRef": "beat_02.action",
                "instruction": "Pip reaches the free hand from the left toward the note stuck on the right fingertip. The peel motion happens across a visible lateral gap between the hands; when the note splits, one note remains on the right hand and the other transfers to the left, with both hands spread apart at the end of the beat.",
                "sourceConsequenceRef": "beat_02.consequence",
                "consequencePresentation": "Show one note on the right hand and one note on the left hand with a clear gap between them, emphasizing that one note has become two."
              },
              "stateProgression": [],
              "temporalPresentation": null,
              "cameraComposition": null,
              "generatorConstraints": []
            },
            "fallbackReason": null,
            "dependsOnBeatIds": [],
            "dependencyJustification": null
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

### DeepSeek candidate text

No complete DeepSeek candidate prompt exists. The server rejected the model-authored plan before compilation, so presenting a reconstructed prompt here would fabricate an experimental output.

## Run B — actual OpenAI result

OpenAI independently selected the same beat-2 separation opportunity. Its plan specified a below-face contact location, lateral non-occluding hand paths, a continuous gap-opening split, consequence spacing, locked medium composition, oblique contact plane and a hand-identity continuity constraint.

The provider response was valid structured JSON and passed the plan-level schema/critique path. The server then assembled an offline prompt candidate and normalized its profile. Final source validation raised:

```text
ValueError: Story fidelity/protected identity, physical rule, ending or production settings changed
```

An offline replay of the exact saved raw response, with no provider call, reproduced the exception. The exact conflict was:

1. The baseline already ended with `ABSURD_PHYSICS. SEEDANCE_2_0_MINI. 15 seconds. image2video. 480p. 9:16.`
2. `normalize_candidate_profiles` appended `Content profile: ABSURD_PHYSICS.`
3. `validate_compiled_source` requires text outside timed beats to be byte-semantically unchanged.
4. The appended profile line therefore caused the protected-outside-text comparison to fail.

This is a deterministic compiler/validator contract conflict, not a provider transport, JSON, token-limit or billing failure. The generated plan cannot be counted as an accepted candidate, and the authorization did not include a code fix or a second call. DeepSeek source-fidelity and creative-critic requests were therefore not executed.

### Complete OpenAI structured model response

```json
{
  "proposals": [
    {
      "initial": {
        "candidateId": "candidate-a",
        "title": "Lateral peel with diverging hand paths",
        "objective": "Address beat_02's unspecified screen positions: overlapping hands could conceal whether the single note splits or merely changes hands.",
        "interventions": [
          {
            "opportunityId": "SEPARATE_ACTION_RESULT:beat_02",
            "operation": "SEPARATE_ACTION_RESULT",
            "layout": "LATERAL",
            "camera": "LOCKED",
            "rationale": "The source specifies peeling and one note on each hand but leaves their paths unspecified. Place the existing contact below Pip's face, then execute the peel across the image rather than toward the lens: the originally occupied hand stays on one side while the free hand draws away to the other. The observable difference is a central contact becoming two laterally separated attachment sites through one continuous movement, rather than a result hidden behind overlapping hands. Self-critique: this changes physical choreography without adding an attempt, count state or cross-beat requirement; it leaves the AUTO opening unchanged. Improved legibility is an unverified hypothesis. Thin-note contact",
            "authorship": "MODEL_AUTHORED",
            "production": {
              "spatialRelationships": [
                {
                  "subjectRef": "beat_02.hand",
                  "relation": "BELOW",
                  "objectRef": "beat_02.actor",
                  "instruction": "Keep the free hand's peeling contact below Pip's head, in the open space in front of the upper torso rather than across the face."
                }
              ],
              "choreography": {
                "sourceActionRef": "beat_02.action",
                "instruction": "Bring the free hand to the exposed outer edge of the attached note with the fingertips approaching from the side, not over its visible surface. Execute the existing peel as a lateral draw across the image: keep the originally occupied hand on its starting side while the peeling hand travels toward the opposite side, with neither wrist crossing the other hand's silhouette. Let this same peel movement open a gap between the hands as the split occurs; do not add another tug or regrip.",
                "sourceConsequenceRef": "beat_02.consequence",
                "consequencePresentation": "Carry the two resulting attachments apart along those diverging hand positions, leaving open background between their silhouettes rather than stacking one note behind the other."
              },
              "stateProgression": [],
              "temporalPresentation": null,
              "cameraComposition": "Use a locked medium composition containing both lateral hand endpoints and Pip's face; view the peel plane obliquely enough that the note surface is not edge-on.",
              "generatorConstraints": [
                "Maintain the original hand-to-note attachment throughout the peel; reveal the second attachment through the same continuous separation, without hand identity swaps or an occluding cut."
              ]
            },
            "fallbackReason": null,
            "dependsOnBeatIds": [],
            "dependencyJustification": null
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

### Complete offline compiler preview — rejected, never accepted as a candidate

This text is included for diagnosis because the server assembled it from the actual response before final validation. It is not a persisted candidate, did not receive independent review, and has no canonical score.

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
Content profile: ABSURD_PHYSICS.
```

## Exact immutable baseline prompt

```text
TITLE / FORMAT
Pip sticky-note strategy escalation / 15 seconds

VISUAL STYLE
Bright playful animation with readable silhouettes.

CHARACTER / CONTINUITY
Pip is the same anthropomorphic rabbit throughout; no verified appearance reference is claimed.

TIMED SHOT PLAN
0-2s: Already mid-action, Pip the rabbit tries to place one sticky note on the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched. [locked medium shot; keep Pip, hands, notes and cabinet causally readable] -> The note attaches to Pip rather than the cabinet.
2-5s: Pip tries to peel the note away with the free hand, but it splits into two notes, one on each hand. [medium shot; keep Pip, hands, notes and cabinet causally readable] -> One note becomes two.
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

## Independent evaluations

No independent source-fidelity or creative-critic provider review was executed for either run. The workflow requires an accepted compiled candidate before spending on reviews:

| Candidate source | Source-fidelity review | Creative-critic review | Reason |
|---|---|---|---|
| DeepSeek | NOT_EXECUTED | NOT_EXECUTED | Model plan failed bound-participant source validation |
| OpenAI | NOT_EXECUTED | NOT_EXECUTED | Compiler/validator contract failed before a candidate existed |

No fixture review was substituted. Reviewer independence was therefore not established, and the experiment cannot support a model preference.

## Canonical and creative evaluation

Neither run produced a valid complete candidate. Ruleset 1.11 was consequently not run on either provider output. There are no changed rule outcomes, score deltas or defensible candidate grades to report.

| Text | Ruleset 1.11 score | Grade | Creative assessment |
|---|---:|---|---|
| Immutable baseline | 93.42708333333334 | A | `CREATIVE_RISK_DETECTED / PROVISIONAL`; final A admission remains false |
| DeepSeek candidate | NOT_EVALUATED | NOT_EVALUATED | Plan materially different in text, but source-fidelity violation |
| OpenAI candidate | NOT_EVALUATED | NOT_EVALUATED | No accepted candidate due compiler/validator conflict |

`UNKNOWN` evidence was never converted to `PASS`. Missing first-frame and silhouette evidence, thin-object producibility risk, generator adherence and audience impact remain unresolved.

## Evidence-based comparison

Both models converged on the same available diagnosis rather than proposing broad story changes: make the single-note peel and two-note result visibly separable in beat 2. Both preserved the declared event order and requested no story change at the structured-plan level.

DeepSeek supplied a concise left/right staging concept. Its second spatial instruction did not faithfully address the source-reference participants, so the source validator rejected it. This is direct evidence that the model did not fully satisfy the reference contract in this call.

OpenAI supplied more detailed contact choreography, occlusion control and continuity constraints. The saved response was structurally usable, but the server's own profile-normalization step made the compiled text fail its immutable-outside-text check. The added detail is not proof of superior creative capability because the candidate never cleared compilation, independent source review, canonical evaluation or critic review.

Both plans changed only beat 2. Neither tested whether the model could repair the weak frame-zero specification, repetitive viewer-visible consequences, or overloaded ending. Neither supplied visual or audience evidence. The experiment therefore establishes that both real adapters can produce source-specific structured production plans within budget, while establishing no valid A-grade candidate and no defensible winner.

## Creative weaknesses observed

- **DeepSeek:** exact source-reference participant discipline failed in `spatialRelationships.1`; hand identity and two-note outcome prose exceeded what the bound pair established.
- **OpenAI:** the plan was detailed but still limited to one beat; its rationale ended abruptly at “Thin-note contact,” even though the provider reported `stop`.
- **Shared:** both selected the same single opportunity and left the other known creative risks untouched.
- **Pipeline:** profile normalization and immutable outside-text validation disagree when the baseline contains the profile value but lacks the labeled `Content profile:` line.
- **Evidence:** no render, independent review, canonical candidate evaluation or audience observation exists.

## Durable evidence

The following files preserve the actual evidence without secrets:

- `real-execution-runtime/experiment-summary.json`
- `real-execution-runtime/deepseek-raw-structured-decision.json`
- `real-execution-runtime/openai-raw-structured-decision.json`
- `real-execution-runtime/openai-offline-failure-reproduction.json`
- `real-execution-runtime/openai-offline-unaccepted-compiler-preview.txt`
- `real-execution-runtime/run-a-final.json`
- `real-execution-runtime/run-b-final.json`
- `real-execution-runtime/post-experiment.dump`
- `real-execution-runtime/ml-network-audit.json`

The final database dump is a snapshot of the disposable experiment only. It preserves the two durable request ledger rows and their complete accounting.

## Conclusion

`EXPERIMENT_INCONCLUSIVE`

The exact bounded experiment was executed and stopped correctly. Two genuine generation calls cost USD `0.05801854`. DeepSeek failed source-reference fidelity; OpenAI returned a plausible model-authored plan but the local compiler/validator contract prevented a valid candidate. No independent reviews or candidate scores exist, so neither provider can be declared capable of producing a defensible canonical-A improvement from this experiment, and neither should be preferred.

No further experiment, retry or provider request was started.
