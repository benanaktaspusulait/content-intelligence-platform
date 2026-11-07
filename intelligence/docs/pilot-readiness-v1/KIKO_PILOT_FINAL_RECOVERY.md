# Kiko Pilot Final Recovery

**Final status: `PILOT_BLOCKED`**  
**Candidate:** Kiko — Runaway Toothbrush  
**Source prompt SHA-256:** `d623dd1f1bbbb1207090c7caff4db5f4b8b806cb55d26cb6aa14ceb8f356b610`

## 1. Executive result

The accepted Kiko and first-frame approvals remain intact, the offline safety repair is active, the existing image2video dry-run succeeds, and the final test failure set exactly matches the historical accepted 36 failures. The candidate is still blocked by the existing record-25 quality result, missing mandatory offline semantic evidence for `GOAL_001`, meaningful local creative-screen findings, and an inconsistency in the existing first-frame summary field. No render was run.

## 2. Regression baseline

See [REGRESSION_BASELINE_DIFF.md](REGRESSION_BASELINE_DIFF.md) for all 36 exact identifiers. Final ML suite: **3,491 passed, 36 failed, 2 skipped**. The failure set compares exactly with the immutable accepted baseline: **0 added, 0 removed**. A transient intermediate run exposed 17 unchained integrity-hash failures; exact approval transitions were added through the existing registry and focused policy/integrity verification then passed **24/24**. No historical baseline or frozen evidence was edited.

Final command from `intelligence/ml-service`:

```sh
PYTHONPATH=. POMPOM_OFFLINE_MODE=true POMPOM_EXTERNAL_AI_AUTHORIZED=false .venv/bin/pytest -q --tb=no
```

The accepted baseline artifact does not preserve its Python version or exact shell command. The final run used Python 3.14.2 and the checked-in `.venv`.

## 3. Record-25 quality gates: all ten FAIL results

Record 25 is ruleset `1.12`, prompt fingerprint above, `BLOCKED`, 10 FAIL, 19 PASS, 13 UNKNOWN, 4 NOT_APPLICABLE, and zero service errors. The quality record is the exact record-25 evidence; authored source evidence is the immutable local prompt. The classifications below preserve the difference between malformed mapping and real story risk.

| Rule | Required behavior / recorded observation | Source evidence and assessment | Classification |
|---|---|---|---|
| `HOOK_002` | Opening should begin in an active, legible moment; record reports `startsMidAction=false`. | The 0.0–0.55s first-frame text says Kiko is already stretched over the sink, fingertips near the brush, while the brush is already sliding away. Record IR contradicts the prompt. | `EVIDENCE_MAPPING_DEFECT` |
| `ATTEMPT_001` | At least three active attempts; record reports 0. | Timed sections 0.55–13.6 describe lunging, blocking/reversing, catching, restraining, trapping and reaching. Zero is not supported by the authored prompt. | `EVIDENCE_MAPPING_DEFECT` |
| `CHAR_002` | Active solution behavior at or above the ruleset minimum (50%); record reports 0%. | Its denominator depends on the record’s zero-attempt mapping; this percentage is not independently supported. | `EVIDENCE_MAPPING_DEFECT` |
| `PRODUCIBILITY_002` | Main-prop count no greater than 2; record reports 108. | Prompt explicitly says one normal toothbrush. The opening also describes sink/counter, stool and soap dispenser. 108 is parser contamination, though the physical scene has several staging elements. | `EVIDENCE_MAPPING_DEFECT` |
| `ATTEMPT_002` | At least three distinct attempt strategies; record reports zero from zero attempts. | Source contains several distinct tactics, but record has no bound attempt evidence. | `EVIDENCE_MAPPING_DEFECT` |
| `PRODUCIBILITY_003` | Avoid fragile video-generation interactions; record returns risk tags including `FACE_CONTACT`, `HAIR_CONTACT`, `MULTI_OBJECT`, and `WATCH_CLASP`. | Fine two-finger handle capture, cross-hand blocking, a brush moving over Kiko’s hair near her face, and repeated palm/head contact are real risks. `WATCH_CLASP` has no source support and is a mapping error. | `EVIDENCE_MAPPING_DEFECT` with genuine production risks |
| `INSTANT_VISUAL_ABSURDITY_GATE` | Required opening witness fields include `staticWrongness`, `noHistoryRequired`, `noMicroComparison`, `largeVisualSignal`, and `characterAlreadyEngaged`; record says `EVIDENCE_INCOMPLETE`. | The approved still visually shows an engaged Kiko reaching toward a runaway toothbrush in a vertical bathroom composition. The record did not bind the image’s required gate evidence, and human asset approval is not a machine gate verdict. | `SOURCE_DATA_INCOMPLETE` |
| `MINI_STORY_LOCK` | Source-bound protagonist goal, obstruction and attempted responses should form a compact story; record reports attempts missing. | Attempts are present in source, so this report’s failure input is defective. The prompt names its PRIMARY GOAL as viewer laughter/rewatch; Kiko’s ordinary goal is implied by reaching for a toothbrush but is not explicitly declared. | `EVIDENCE_MAPPING_DEFECT` plus `SOURCE_DATA_INCOMPLETE` |
| `TEMPORAL_COMPLEXITY_SPLIT_GATE` | Fit one generation within the accepted time cap; record marks overload and suggests 2×15s. | Prompt has 10 timed sections across 15s and many precisely staged reversals/contact beats. The split suggestion violates the pilot’s ≤15s cap. The original count is parser-contaminated, but the dense staging risk remains real. | `GENUINE_CREATIVE_FAILURE` (timing/production density) with mapping caveat |
| `BEAT_DENSITY_RULE` | Existing ruleset safe range is 4–6 major beats; record reports 9. | Source explicitly authors many separate chase beats; record’s first parsed span also absorbs retention-rule text and the timeline is repeated later as a summary. Count needs corrected mapping, but the 15-second sequence remains crowded. | `EVIDENCE_MAPPING_DEFECT` with genuine density concern |

`GOAL_001` is not one of the ten FAILs in record 25. It is `UNKNOWN` offline. The rule implementation explicitly describes its requirement as semantic judgment over an everyday goal, direct obstruction, aligned attempts, and ending. A deterministic keyword shortcut would not satisfy that contract. With offline mode enabled and external authorization false, no provider dispatch is permitted; no source-verified structured evidence establishes a substitute verdict. It remains unknown, not pass/fail. Record 24’s malformed provider response remains `SERVICE_ERROR` and is not used as a creative verdict.

## 4. Existing workflow coverage

| Workflow | Existing entrypoint / input fit | Result |
|---|---|---|
| Opening Evaluation | Existing ruleset 1.12 opening gates in record 25, notably `HOOK_002` and `INSTANT_VISUAL_ABSURDITY_GATE`; input was prompt/IR, not the approved image’s full gate evidence. | Evaluated in record 25; the first-frame gate is `EVIDENCE_INCOMPLETE`, and `HOOK_002` conflicts with the source. The image was visually inspected: Kiko’s double buns, coral top, white shorts, coral shoes, toothbrush and immediate reach are visible in a 9:16 scene. This human visual check does not rewrite the record outcome. |
| Premise Admission | Existing `premise_admission_evidence.assess(candidate, model, canonical)` and `/api/v1/workflow/story-premise/evaluate`; admission evidence requires the structured canonical context. | The existing timed-text acquisition cannot provide structured canonical fields. In particular, do not infer a character goal or fabricate source state/response classifications. Admission remains `NOT_EVALUATED`; required source contract is unavailable. |
| Beat Grammar | Existing `beat_grammar.assess(plan, composition=...)`; requires source-bound beat rows with strategy, trigger, rule, object response, character consequence, before/after states, spatial change and goal progress. | `NOT_EVALUATED`. The prose timeline does not encode all required state fields; legacy annotation would fill defaults and would not be faithful evidence. Do not synthesize them. |
| `SHORT_FORM_ENGINE` | Existing `/api/v1/workflow/short-form/evaluate`, offline, timed text accepted. | Executed against the unchanged local prompt. It extracted 10 actual timed blocks from 0.0–15.0s after ignoring the duplicated timing summary reset. Result `REVISION_REQUIRED`; hook 10, goal 0, progress density 40, escalation 89, payoff 15, rewatch 60. Findings: `OPENING_NOT_IN_TROUBLE`, `EVERYDAY_GOAL_UNCLEAR`, `HIGH_ACTIVITY_LOW_PROGRESS` (10 blocks / 4 supported causal developments), `IDENTICAL_ATTEMPTS` (B7), `ESCALATION_PLATEAU` (warning; 4.6s gap), `WEAK_VISUAL_PAYOFF`. The explicit ordinary Kiko goal is missing; scoring is not a readiness approval. |
| Candidate Ranking | Existing `/api/v1/workflow/concepts/rank`, offline, accepts source text and 1–30 candidates. | Executed with the unmodified prompt. Candidate ID `concept-f863671cac97154b` is `INELIGIBLE`, no ranking score and no first-render selection. Missing required fields include `protagonistGoal`; source normalizer preserves it as missing. It extracted episode title, Kiko, main object, rule, exact first/last timed excerpts and 15s duration. `providerCalls=0`, `renderAuthorized=false`. |

Premise Naturalness was also run through its existing deterministic function with the source-explicit protagonist, toothbrush, rule and opening while leaving the everyday goal empty. It found `ARBITRARY_MAGIC_RELATIONSHIP`, `GENERIC_ENGINE_APPLICATION`, and `CAUSE_NOT_VISIBLE_AT_FRAME_ZERO`; because the naturalness response classifier can mistake negated “never grows limbs” language for `SCALE_UP`, this output is diagnostic and not treated as an authoritative verdict. No automatic repair or fabricated admission was applied.

There is no existing single operator command that runs the quality record, premise admission, beat grammar, short-form engine and concept ranking and writes one combined status report. Creating such a wrapper would be a new orchestrator, prohibited by this task. The local results are consolidated here; repeat the existing local service endpoints individually. This integration gap does not change any gate to PASS.

## 5. Creative and production review

- **Everyday goal:** not explicit as Kiko’s goal. The prompt’s labeled PRIMARY GOAL is audience laughter/rewatch. Brushing teeth is suggested by the toothbrush and mouth action, but must remain an inference until the source is revised.
- **Opening problem:** immediately legible in the approved still and source prose: Kiko is reaching while the toothbrush slides away. No history is needed to understand the immediate chase.
- **Attempts and rule:** authored attempts exist and mostly reuse “almost catch → escape.” Blocking, reversals, hand capture, palm trap and head fake differ visually, while the single rule remains recognizable.
- **Progress and payoff:** the prompt declares escalation, a hair-brushing visual payoff, and a loop reset. The existing local evaluator finds only four supported causal developments and a weak rule-linked payoff; its detailed mapping should be corrected before treating this as final quality evidence.
- **Silent comprehension:** core chase and reversals are visual; dialogue is not necessary to understand the opening problem.
- **Duration:** ten timed blocks and multiple hand/face/hair interactions are densely packed into exactly 15 seconds. A 2×15s split is not allowed. Final encoded duration cannot be guaranteed until a render is measured.
- **Approved appearance:** first frame shows Kiko with the approved double-bun brown hair, coral-pink top, white shorts and coral footwear; the toothbrush and reach are visible. Human approval and the SHA binding remain valid.
- **Generation risk:** precise finger capture, repeated hand crossings, moving brush contact near face/hair, hair deformation, multiple reversals and tight loop-pose matching are plausible Seedance consistency risks. The unsupported `WATCH_CLASP` tag should be removed by repairing mapping, not used as evidence.

One minimal proposed source edit, **not applied and not approved**, is to add this line under `MAIN OBJECT`:

```text
KIKO'S EVERYDAY GOAL: Kiko wants to brush her teeth.
```

This makes explicit the goal already suggested by the toothbrush and the later attempt to bring it to her mouth. It is a proposal for the source owner to review, not a fact added to current validation evidence. It does not resolve the separate density and contact-precision concerns; the approved prompt remains unchanged.

## 6. Offline safety and exact approvals

- `POMPOM_OFFLINE_MODE` defaults to `true`; `POMPOM_EXTERNAL_AI_AUTHORIZED` defaults to `false` in Compose.
- Provider factory and adapter constructors require explicit operator authorization. Nested semantic checks take the existing unknown/unavailable route when offline or unauthorized. No hidden fallback or retry is enabled.
- Exact-hash approval transitions for `short_form_engine.py` and `concept_ranking.py` were added to the existing `offlineSafetyApproval` registry. Prior approved hashes remain represented in the approval chain; frozen historical manifests were not rewritten.
- Focused active-integrity/policy tests after that change: **24 passed**.
- Provider test transport is mocked and constrained to a local unavailable proxy; the Kiko deterministic evaluations made **0 provider calls**.

## 7. Asset and image2video preflight

| Asset | Current SHA-256 | Approval evidence |
|---|---|---|
| Canonical Kiko reference `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/kiko.png` | `8b9e643660722d5c00bd0d25ebef066ea868f52d8a57aa1e4a2b0eb9b55747fc` | `APPROVED`, exact user approval recorded in [FIRST_REAL_PILOT_READINESS.md](FIRST_REAL_PILOT_READINESS.md) |
| First frame `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_image.png` | `18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a` | Accepted `FIRST_FRAME`, 941×1672, prompt version 29 binding; exact user approval recorded in the readiness report |

The imported PNG at `intelligence/data/content/18/visual-references/18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a.png` also hashes to the exact approved first-frame value. Source image bytes were not changed.

Rechecked dry-run command:

```sh
PROMPT_FILE='/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_prompt.md'
FRAME_FILE='/Users/benanaktas/project/video/content-intelligence-platform/intelligence/data/content/18/visual-references/18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a.png'
openart --dry-run generate video "$(cat "$PROMPT_FILE")" --model byte-plus-seedance-2-mini --image "$FRAME_FILE" --duration 15 --aspect-ratio 9:16 --resolution 480p
```

It exited 0 and emitted an `image2video` request with `startFrame` bound to the imported approved PNG, model `byte-plus-seedance-2-mini`, 9:16, 480p, requested duration 15. Local schema supports 4–15 seconds. A 14-second request is supported by schema but would not match the authored 15-second timeline without an approved retiming. A 15-second request does not guarantee a final encoded duration ≤15.000 seconds. `--dry-run` made no generation request and created no video.

The readiness API still reports `firstFrameStatus=MISSING` in its summary while listing the accepted first-frame binding. This contradictory status projection remains an integration defect; it must be reconciled before production readiness.

## 8. Calls, blockers, and operator action

- Provider calls during this recovery’s local workflow runs: **0**.
- OpenArt generation calls: **0**.
- Render calls: **0**.
- Automatic retries/fallbacks: **0**.
- Approved asset byte changes: **0**.

Remaining blockers:

1. **Genuine creative/production blocker:** dense 15-second staging with fine finger, hand-crossing, hair and near-face interactions; current short-form evaluator remains `REVISION_REQUIRED`.
2. **Missing mandatory AI evaluation:** `GOAL_001=UNKNOWN` under the enforced offline policy; no external provider authorization was given.
3. **Source-data/validator mapping blockers:** record-25 attempt/prop/opening measurements conflict with the actual prompt, while required structured goal/beat evidence is missing. Do not treat those measurements as valid creative failures or as passes.
4. **Engineering integration blocker:** no existing single operator command aggregates the separately exposed applicable endpoints into a unified generated report without adding a prohibited orchestrator; readiness view still says `firstFrameStatus=MISSING` despite the accepted binding.
5. **Render-duration blocker:** the dry-run request is 15 seconds, but final encoded duration cannot be assured ≤15.000 before a render and measurement.
6. **Regression blocker:** none beyond the accepted historical baseline; current failure identifiers match exactly.

Existing safe offline production-quality recheck command:

```sh
curl -fsS -X POST http://127.0.0.1:8080/api/v1/intelligence/quality/validate \
  -H 'Content-Type: application/json' \
  -d '{"contentId":18,"promptVersionId":29,"rulesetVersion":"latest"}'
```

This invokes the existing linked quality workflow for the immutable prompt under the offline container policy. It does not run Premise Admission or Beat Grammar, which lack the required source-bound structured input, and it does not run Candidate Ranking; those existing endpoints remain separate. No render command is provided because gates do not pass. No render was performed.
