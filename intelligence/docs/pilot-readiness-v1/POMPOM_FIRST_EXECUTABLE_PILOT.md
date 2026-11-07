# Pompom First Executable Pilot

**Decision: `PILOT_BLOCKED_CREATIVE`**  
**Selected package:** Kiko — Runaway Toothbrush (best supported existing candidate; not render-ready)

## Candidate and immutable evidence

- **Source prompt:** `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_prompt.md` — SHA-256 `d623dd1f1bbbb1207090c7caff4db5f4b8b806cb55d26cb6aa14ceb8f356b610`.
- **Approved canonical Kiko reference:** `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/kiko.png` — SHA-256 `8b9e643660722d5c00bd0d25ebef066ea868f52d8a57aa1e4a2b0eb9b55747fc`.
- **Approved first frame:** `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_image.png` — SHA-256 `18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a`, 941×1672. Imported copy at `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/data/content/18/visual-references/18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a.png` has the same hash. Registry acceptance remains bound to content 18 / prompt 29. Image and reference bytes and approval records were not changed.
- **Source identity and premise:** Kiko; one ordinary toothbrush; toothbrush escapes whenever she is about to catch it. The source explicitly shows her reaching for it, saying “BRUSH!”, bringing it to her mouth, and retrying. `PRIMARY GOAL` is explicitly the audience’s laughter/rewatch, not the character’s goal.

## Canonical field reconciliation

Classification describes source-to-contract evidence, not a quality pass. Canonical story fields are `everydayGoal`, opening problem/state, primary object/interaction, impossible rule, escalation/attempts, payoff/end state, and duration.

| Contract field | Evidence in original prompt | Classification |
|---|---|---|
| Character | `MAIN CHARACTER: KIKO` | `PRESENT_MAPPED` |
| Character everyday goal | Attempts to use the toothbrush; “BRUSH!” and bringing it to her mouth. No explicit statement that she is brushing her teeth or why. | `AMBIGUOUS` — source evidence is present, but “Kiko wants to brush her teeth” interprets the scene and is not an authored goal field. |
| Opening problem | Frame one says the chase is already underway: brush slides away while Kiko reaches. | `PRESENT_NOT_MAPPED` in the stale record-25 opening boolean (`startsMidAction=false`); mapped correctly by the timed-text input adapter. |
| Main object | `ONE NORMAL TOOTHBRUSH ONLY` | `PRESENT_MAPPED` |
| Impossible rule | Explicit last-moment escape whenever Kiko is about to grab the brush. | `PRESENT_MAPPED` in source; record-level attempted rule fields remain incompletely mapped. |
| Attempts/escalation | Timed sections 0.55–13.6 give several reaches, blocks/reversals, capture, escape, head fake and retry. | `PRESENT_NOT_MAPPED` in record-25 attempt count/strategy evidence (record says zero); mapped as timed text by the existing Short Form adapter. |
| End/payoff/loop | Hair-brushing gag and 13.6–15.0 return to the opening chase pose. | `PRESENT_MAPPED` in source; insufficiently represented in record-25 payoff evidence. |
| Duration | Exactly 15 seconds; contiguous authored sections end at 15.0. | `PRESENT_MAPPED` |
| Structured before/after body, object, control and spatial states per beat | Some prose describes actions, but required typed state transitions are not consistently supplied. | `SOURCE_ABSENT` as a complete structured evidence set; do not manufacture it from prose. |

The proposed sentence `Kiko wants to brush her teeth` is **not literally stated**. It is strongly suggested by “BRUSH!”, bringing the toothbrush to her mouth, and the repeated attempts, but the validated source contract requires an explicit everyday goal. A single candidate addition is prepared for human review in section “One proposed revision”; it has not been added to the source or any validation input.

## Existing validators and quality evidence

| Component | Result | Evidence and limitation |
|---|---|---|
| Opening Evaluation | Existing ruleset 1.12 record 25: `BLOCKED`; `HOOK_002` FAIL is a mapping conflict; `INSTANT_VISUAL_ABSURDITY_GATE` is `EVIDENCE_INCOMPLETE`. | The original text and approved image show an active reach and escaping brush at frame zero. Record-25 fields fail to bind that evidence. Asset approval is not a semantic gate verdict. |
| Premise Naturalness | Existing deterministic diagnostic ran with goal left empty; flagged `ARBITRARY_MAGIC_RELATIONSHIP`, `GENERIC_ENGINE_APPLICATION`, and `CAUSE_NOT_VISIBLE_AT_FRAME_ZERO`. | Not authoritative: its current response classifier misreads negated “never grows limbs” as `SCALE_UP`; keep the outcome unclassified rather than treating it as a reliable pass/fail. |
| Premise Admission | `INSUFFICIENT_EVIDENCE`. | Existing admission API requires structured canonical `StoryFields`; timed-text acquisition does not supply them. The absent explicit goal and structured story evidence cannot be filled by inference. |
| Beat Grammar | `INSUFFICIENT_EVIDENCE`. | Existing grammar requires source-bound beat rows with trigger, strategy, rule, object response, character consequence, before/after state, spatial change and goal progress. The authored prose does not consistently encode these fields. |
| Short Form | `REVISION_REQUIRED`; extracted 10 timed blocks from 0–15 seconds. No timing-rule violation was reported. | Existing score: hook 10, goal 0, progress density 40, escalation 89, payoff 15, rewatch 60. Findings: `OPENING_NOT_IN_TROUBLE` (mapping defect against the explicit frame-zero source), `EVERYDAY_GOAL_UNCLEAR` (goal field ambiguous), `HIGH_ACTIVITY_LOW_PROGRESS` (10 blocks / 4 supported causal developments), `IDENTICAL_ATTEMPTS` (B7), `ESCALATION_PLATEAU` warning (4.6-second gap), and `WEAK_VISUAL_PAYOFF`. The metrics are diagnostic, not a pass. |
| Creative Shape | `INSUFFICIENT_EVIDENCE` for a canonical shape judgment. | Existing annotator consumes a structured beat plan; source lacks the typed beat-state set. Do not turn a legacy annotation with defaults into canonical evidence. |
| Candidate Ranking | `INELIGIBLE`, no score or first-render selection. | Existing normalizer now maps the source’s Markdown labels and five timed beats. The goal remains ambiguous/unmapped; no goal is inferred from title or filename. `providerCalls=0`; `renderAuthorized=false`. |
| `GOAL_001` | `UNKNOWN` offline; configured severity `BLOCKER`. | Existing rule implementation calls this a semantic judgment and returns `UNKNOWN` when goal evidence is unavailable. Existing policy makes an unresolved blocker incompatible with readiness. It is not changed to PASS or FAIL. |
| Production Preflight | Image2video dry-run passes request-shape checks; overall production preflight remains blocked. | Exact results below. A dry-run is not a render or guarantee of final encoded duration. |

The record-25 `ATTEMPT_001=0`, `ATTEMPT_002=0`, `CHAR_002=0%`, `PRODUCIBILITY_002=108 props`, and `HOOK_002` do not accurately reflect the source. These are mapping defects, not evidence that the source has zero attempts, 108 main props, or a calm opening. `PRODUCIBILITY_003` mixes unsupported `WATCH_CLASP` with real fine-finger, cross-hand and near-face/hair contact risks. The separate genuine concern is the number of precision actions packed into 15 seconds. The existing 2×15-second split suggestion is out of policy and is rejected; no longer plan is proposed.

## One proposed revision — human review only

Candidate source delta (not applied):

1. Under `MAIN OBJECT`, add `KIKO'S EVERYDAY GOAL: Kiko wants to brush her teeth.` This makes explicit the supported but currently ambiguous intent. Human source-owner approval is required.
2. In the existing 8.5–13.6-second head-fake/final-payoff passage, retain one left-to-right fake-out and one clear hair-brushing payoff; remove the second repeated reach/miss cycle. Keep the 13.6–15.0 loop and all section boundaries within 15 seconds. This is a single targeted reduction of repeated micro-actions, preserving Kiko, the single toothbrush, the escape rule and the existing ending. Re-evaluate through the same Short Form and quality gates after the source owner accepts or rejects the proposed delta.

No source file was edited and no new story was generated.

## Existing package fallback comparison

The next two inventory comparison packages were checked because Kiko has unresolved creative gates:

| Package | Inventory / source evidence | Disposition |
|---|---|---|
| Kiko — Late Reflection | `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/not-generated/KIKO_AND_THE_LATE_REFLECTION/kiko-late-reflection-production.md`; inventory says 15 seconds / 5 beats, draft/not generated, declared reference path but approval not evidenced. Parsed 0–15 timeline, but no explicit everyday goal. | Not ready: no independently evidenced approved first frame; mandatory goal evidence unresolved. |
| Luca — Shadow Takes a Shortcut | `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/not-generated/LUCAS_SHADOW_TAKES_A_SHORTCUT/lucas-shadow-shortcut-production.md`; draft/not generated; inventory has no duration/beat count and reference approval unverified. Parsed source has 5 timed beats over 0–15, but no explicit everyday goal. | Not ready: no evidenced approved first frame; mandatory goal evidence unresolved. |

Neither alternative is genuinely ready. Kiko remains the strongest existing pilot package because its exact prompt, approved character reference and approved prompt-bound first frame are verified. Selecting it does not waive the quality blockers.

## Image2video preflight

The existing `openart --dry-run generate video` command exited 0 and emitted `mode: image2video`, model `byte-plus-seedance-2-mini`, the approved imported image as `startFrame`, aspect ratio `9:16`, duration `15`, resolution `480p`, and the exact source prompt. No text2video fallback was present. The local model contract supports 4–15 seconds. Automatic retries are not enabled. The requested duration is within the ≤15-second policy, but a dry-run cannot guarantee final encoded duration ≤15.000 seconds.

Reproduction (dry-run only):

```sh
PROMPT_FILE='/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_prompt.md'
FRAME_FILE='/Users/benanaktas/project/video/content-intelligence-platform/intelligence/data/content/18/visual-references/18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a.png'
openart --dry-run generate video "$(cat "$PROMPT_FILE")" --model byte-plus-seedance-2-mini --image "$FRAME_FILE" --duration 15 --aspect-ratio 9:16 --resolution 480p
```

## Regression and call accounting

- Focused source adapter, protected policy and canonical integrity tests: **25 passed**.
- Java command `mvn -q -Dtest=VisualReferencePlanningServiceTest test`: passed, including `reportsCurrentHashVerifiedBoundFirstFrameAsAvailableWithoutClaimingSemanticVerification`. The new mapping only reports `AVAILABLE_REVIEW_REQUIRED` when a current-prompt-bound `FIRST_FRAME` has a valid SHA and passes existing image verification; semantic status remains unknown and no approval is created.
- Full ML regression: **3,493 passed, 36 failed, 2 skipped**. Fresh JUnit failure-ID comparison against `REGRESSION_BASELINE_DIFF.md`: **36 expected, 36 actual, 0 added, 0 removed**. Captured at `/tmp/pompom-pilot-regression.xml`.
- Provider calls: 0 for this offline validation and dry-run. OpenArt generation/render calls: 0. Image bytes and approval records changed: 0.

## Reproducible existing operator steps

Run from `intelligence/ml-service`, with offline controls set:

```sh
export POMPOM_OFFLINE_MODE=true POMPOM_EXTERNAL_AI_AUTHORIZED=false
curl -fsS -X POST http://127.0.0.1:8080/api/v1/workflow/short-form/evaluate \
  -H 'Content-Type: application/json' \
  --data-binary "$(python -c 'import json,pathlib; print(json.dumps({"text":pathlib.Path("/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_prompt.md").read_text(),"desiredDuration":15}))'"
```

```sh
curl -fsS -X POST http://127.0.0.1:8080/api/v1/workflow/concepts/rank \
  -H 'Content-Type: application/json' \
  --data-binary "$(python -c 'import json,pathlib; print(json.dumps({"candidates":[pathlib.Path("/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_prompt.md").read_text()]}))'"
```

Use the existing quality-validation endpoint only with these offline controls. Premise Admission and Beat Grammar remain insufficient until the source supplies their structured contracts; do not synthesize those fields. No aggregate orchestrator is required or added.

## Blocker and smallest next action

**Blocking status:** `PILOT_BLOCKED_CREATIVE`. The current package has `GOAL_001=UNKNOWN` under a blocker-severity rule, Short Form is `REVISION_REQUIRED`, and the source still needs explicit human resolution of the character-goal ambiguity and the targeted repetition reduction. No readiness override or render command is issued.

**Single smallest next action:** have the source owner approve or reject the one marked source revision above. Then replay the existing offline evaluators and confirm `GOAL_001` and Short Form outcomes before any render authorization is considered.
