# Mimi V2 production prompt and render readiness

Date: 2026-10-16. **The complete V2 draft is created. The single requested pulling correction is applied; real visual improvement remains NOT_YET_VERIFIED. Render readiness is BLOCKED by missing verified inputs and existing admission requirements.** A blocked render gate does not establish a creative failure of the draft.

This delivery changes no application code, saved prompt, source story, policy, historical evidence or production settings. No paid inference, image generation, render, approval, Docker build, deployment, cleanup, commit or push was performed.

## Exact prompt fingerprints and correction

| Artifact | SHA-256 of prompt body / source |
|---|---|
| Immutable Original Prompt 10/version 1 | `0fe229774deb4b31a42145bad91cf10c91634ba00da39fa3e9d288b3a2e7bd98` |
| V1 development draft, unchanged | `82a2d896798076cb3fd3cf88482c5709167d88034a8b6702149f000bc690abef` |
| **V2 development draft** | **`44779084f986b4a7b1b3a5d1eab9c617f2e6f518a9c5b771cab02bce446cd219`** |
| Approved Turkish story, unchanged | `df653dbcaf16bfdbceb87baa23688d70d739c34941d0075e30e96b181e1bf32b` |

Body extraction is identical to V1: UTF-8 text after `PROMPT BODY` plus its blank separator, removing only trailing file newline characters. Settings/header are excluded. Full V2 file SHA-256 is `7d3517ac1f906225f586a05f5bfb4a259f7f534da45c286dad008e81e1452c5d`.

Only the following phrase in the 5–10s line changed:

```diff
-do not add another attempt or another doubling beyond eight.
+stop pulling once the existing two-to-four-to-eight escalation is complete; add no further doubling beyond eight.
```

`MIMI_V1_TO_V2.diff` is the exact unified file diff, containing one removed line and one added line. Reversing this phrase replacement reconstructs the V1 file byte-for-byte. The external settings/header and every other line are unchanged. There is one V2 draft, not multiple alternatives.

## Complete V2 production prompt

**Set separately in OpenArt; these settings are not prompt-body text:**

| Setting | Value |
|---|---|
| Content profile | ABSURD_PHYSICS |
| Generator | SEEDANCE_2_0_MINI |
| Configured API model | `byte-plus-seedance-2-mini` |
| Duration | 15 seconds |
| Mode | image2video |
| Resolution | 480p |
| Aspect ratio | 9:16 |

Copyable complete English prompt body:

```text
TITLE / FORMAT
Mimi Sticky / 15s Video

VISUAL STYLE
Bright and colorful animation with a playful tone. Make Mimi, the sticky note, and the toy cabinet easy to read together at the opening. Keep staging simple and spatially consistent; reframe only when needed to keep the action clear.

CHARACTER / CONTINUITY
Mimi is the established anthropomorphic bunny. Preserve that identity and do not invent unverified appearance details. Keep the toy cabinet and mirror in the same scene.

TIMED SHOT PLAN
0-2s: Mimi reaches to place one sticky note on the toy cabinet as a cleanup reminder. In a clear view that includes Mimi, the note, and the cabinet, the note visibly sticks to one fingertip instead of the cabinet. The cleanup intention should read from the action; readable lettering is not required.
2-5s: Mimi tries once to peel the stuck note away with her other hand. The note splits into two, with one note sticking to each hand.
5-10s: Continuing the same note-pulling action, show the notes doubling clearly from two to four to eight. The notes progressively cover Mimi's arms, legs, and parts of her face, while keeping her eyes and mouth readable. Mimi becomes visibly overwhelmed; stop pulling once the existing two-to-four-to-eight escalation is complete; add no further doubling beyond eight.
10-12s: Mimi sees herself in the mirror and screams. Show the same already note-covered, overwhelmed Mimi in the reflection. Keep the existing note coverage unchanged through the mirror reaction and directly into the sneeze; add no pulling action, notes, or escalation here.
12-15s: Mimi sneezes; all the notes fly off her and stick to the toy cabinet. Mimi visibly breathes a sigh of relief. End with Mimi relieved and the cabinet still visibly messy.

AUDIO
Playful background music with simple sneeze and sticky-note sounds. No speech or captions.

NEGATIVE CONSTRAINTS
No dark themes, violence, injury, or choking imagery.

CHARACTER IDENTITY LOCK
Mimi is the established anthropomorphic bunny character. Preserve that identity; do not render a human or invent unverified visual details. No approved visual reference is currently bound, so appearance details remain unverified.
```

The corresponding standalone production file is `CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V2.txt`, including separately labelled settings and this exact body. It is DRAFT_ONLY, not an approved saved prompt version.

## Offline preservation and causal checks

All lightweight deterministic checks passed. Results and live API snapshots are recorded in `MIMI_V2_READINESS_EVIDENCE.json`; this is technical/self-validation, not a new MACHINE_REVIEW or independent source PASS.

| Check | Result and practical limit |
|---|---|
| Exact delta | One phrase in one existing beat; no other byte changes from V1. |
| Five windows | Exactly 0–2, 2–5, 5–10, 10–12, 12–15 seconds; no sub-beat timestamps invented. |
| Initial action | Wrong finger attachment remains; other-hand removal still produces one note on each hand. |
| Pulling continuity | “Continuing the same note-pulling action” is unchanged. Pulling is now stopped **after**, rather than potentially before, the existing 2→4→8 escalation completes. |
| Doubling bounds | Two→four→eight retained; no additional attempt, 9/16-note stage, unlimited multiplication or new rule added. |
| State continuity | Existing coverage on arms/legs/face and readable eyes/mouth retained. No reset introduced between escalation, reflection and sneeze. |
| Mirror | Exact 10–12s line retained, including no new pulling, notes or escalation. |
| Release and ending | Same sneeze→notes onto cabinet→relief→still-messy cabinet, in the same final window. |
| Owner meanings | Cleanup intention remains sufficient without exact readable “Topla!”; no captions/speech; continuous overwhelmed state and no dangerous choking imagery retained. |
| Identity / safety / audio | All unchanged, including unverified appearance limitation. No substitute rabbit or invented reference. |
| Persisted original and story | Live original hash matches Prompt 10/version 1; persisted story approval `20b77d13-848d-46d0-ab4b-bb9b6efb0836` matches the exact approved source hash. |
| History | Workflow events remain 75 with unchanged full payload digest; Content 10 still has only saved Prompt 10/version 1. V1 full file SHA stays `716ce953d65a98fd7386d6533f7f320f064876423819b4e2a9655f1fc726ea46`. |

**The identified textual pulling ambiguity is resolved by the requested correction.** The 2–5s “tries once” scopes the initial split; 5–10s explicitly continues pulling and stops at eight. No new contradiction caused by this correction was found. This does not prove a generator will follow the instruction.

The genuine V2 comparison remains partial: one admitted DeepSeek diagnostic review, with factual/contextual issues; OpenAI FAILED_OR_AMBIGUOUS with no retained response/usage. No retry occurred. Neither its preference nor this self-check proves V1/V2 superiority, a canonical score for V2, independent source fidelity, A/A+, retention or replay. Original canonical result remains Ruleset 1.11 / **88.40625/B**. V2 has not been canonically re-evaluated.

Remaining execution risks are stable fingertip/hand contact, visible discrete counts while notes cover several body regions, face readability, matching reflection geometry and note placement, cleanup intent without lettering, and the sneeze/landing/relief/messy-cabinet sequence compressed into three seconds. These require real frames and transitions; neither prompt wording nor schema support demonstrates successful Seedance execution.

## Verified inputs and current admission

Live read-only inspection used Content 10 / saved Prompt 10 / authoritative analysis `f0d36feb-ee0f-4da8-ae21-2071a3ddea18`.

| Requirement | Actual observed state |
|---|---|
| Mimi character | Registered as `00000000-0000-0000-0000-000000000003`, active, status UNTESTED. A registry entry is not a verified visual reference. |
| Character reference | **MISSING**: zero `character_references` rows for Mimi; reference-binding GET returns MISSING for Content 10 / Prompt 10. No reference image was invented or substituted. |
| Start frame | **MISSING**: candidates GET returns an empty list; no accepted or verified candidate is available. |
| Visual preparation | GET returns 404; no persisted visual-preparation artifact for this prompt. |
| image2video execution input | Generation explicitly lists missing `startFrame`; required frame id/URL and verified asset hash are unavailable. |
| Settings support | Existing capability snapshot supports the requested 15s / 480p / 9:16 image2video configuration. Its schema provenance is dated 2026-10-08, `liveGenerationVerified=false`; no fresh provider call or current OpenArt UI verification was made. |
| F8 | **BLOCKED_PENDING_EVIDENCE**: missing/unverified authoritative reference (`REFERENCE_ASSOCIATION`) and missing startFrame (`EXECUTION_INPUTS`). |
| Governance | `renderPermission=false`; no recorded text acceptance or ATTEMPT_001 exception. Read-only response exposes additional canonical/evidence restrictions below. |
| Existing baseline | Zero Content 10/Prompt 10 render jobs and zero linked videos through the saved-prompt videos API. There is no verified paired video baseline; the exact original text exists. An external owner-held video, if any, has not been supplied or verified. |
| V2 binding | File-only draft with the fingerprint above; no saved V2 prompt version or analysis exists. Original analysis/hash must not be reused as V2 authorization. |

Actual F8 missing-input reasons do **not** exhaust render admission. The current governance evaluator also returns these findings with `blocksRender=true` for the saved original:

| Rule | Outcome | Severity | Required resolution category |
| ATTEMPT_001 | FAIL | BLOCKER | POLICY_EXCEPTION_REQUIRED |
| PRODUCIBILITY_003 | FAIL | CRITICAL | PRODUCTION_RISK_REVIEW |
| INSTANT_VISUAL_ABSURDITY_GATE | FAIL | BLOCKER | EVIDENCE_REQUIRED |
| ENGINE_SILHOUETTE_DUPLICATE | FAIL | BLOCKER | EVIDENCE_REQUIRED |
| BEAT_004 | UNKNOWN | CRITICAL | EVIDENCE_REQUIRED |
| CONSISTENCY_001 | UNKNOWN | WARNING | EVIDENCE_REQUIRED |
| HOOK_003 | UNKNOWN | CRITICAL | EVIDENCE_REQUIRED |
| ATTEMPT_002 | UNKNOWN | CRITICAL | EVIDENCE_REQUIRED |
| PAYOFF_003 | UNKNOWN | CRITICAL | EVIDENCE_REQUIRED |
| CONCEPT_007 | UNKNOWN | BLOCKER | EVIDENCE_REQUIRED |
| GOAL_001 | UNKNOWN | BLOCKER | EVIDENCE_REQUIRED |
| CONCEPT_008 | UNKNOWN | CRITICAL | EVIDENCE_REQUIRED |
| HOOK_004 | UNKNOWN | CRITICAL | EVIDENCE_REQUIRED |
| PERFORMANCE_001 | UNKNOWN | WARNING | EVIDENCE_REQUIRED |
| GENERATION_EXECUTABLE_ATTEMPTS | UNKNOWN | BLOCKER | EVIDENCE_REQUIRED |

These are the saved original's findings, not a new evaluation of V2. Missing/UNKNOWN evidence is not converted to a confirmed creative defect or PASS. ATTEMPT_001 remains FAIL; any admission exception requires the existing scoped architecture policy, authenticated authority, independent story/progression/payoff support and explicit justification. No third attempt or exception was fabricated. Fragile face/thin-object risk needs separate acknowledgement; missing visual/semantic evidence cannot be waived by text acceptance. The uncredentialed governance GET also reports authenticated role requirements; CPQ owner access is not assumed to confer those roles. No authentication redesign is proposed.

Source status is unchanged: the original real source verdict remains FAIL, separate owner meanings remain intact, and V2 has no independent source verdict. The diagnostic machine review cannot authorize source or production gates. Official CPQ grading remains inactive.

### Existing way to bind a future test safely

Reuse the existing versioned-prompt, production-reference binding, visual preparation, accepted-start-frame and review/handoff workflow. Source inspection of `WorkflowService.admission` / `requireAuthorized` confirms it checks saved content/prompt identities, saved and freshly evaluated review authorization, matching binding hash, generator/mode/duration/settings and the reviewed frame path/hash. Unsaved/editorial candidates are not render-admission evidence. This read-only task did not call admission, because admission performs a fresh evaluation.

After explicit future text/version approval, the saved V2 prompt must reproduce body SHA-256 `44779084f986b4a7b1b3a5d1eab9c617f2e6f518a9c5b771cab02bce446cd219` exactly and receive its own analysis and evidence binding. Preserve the original version and all historical source results. Bind the actual Mimi reference and accepted first frame to that exact new version and settings; then re-evaluate existing permissions. No new system is needed and no manual OpenArt submission should bypass those gates. Existing manual handoff/export permission explicitly does not authorize spending or rendering.

## Bounded real-video handoff — plan only

1. **Next owner action now:** provide the actual approved Mimi reference image (or identify its existing project asset and approve its use as Mimi). An unrelated rabbit is not acceptable. If you already have a suitable Mimi opening image, supply it as a separate start-frame candidate; it still needs provenance/identity verification and explicit acceptance. Otherwise start-frame creation needs its own separate authorization and cost limit. No generation is initiated here.
2. Review this V2 text and explicitly authorize its use/version approval before any production version is created. This delivery alone is not that approval. Use the existing workflow to resolve required source, canonical/evidence, risk and role-specific conditions for the exact V2 binding. Do not presume reference approval alone clears all gates.
3. Verify a start image consistent with the existing 0–2s wrong-attachment setup: Mimi, fingertip note and cabinet must be visually legible, without relying on tiny lettering; no extra character, count, action or story event. Check its suitability against the actual first-frame gate. If the available image cannot satisfy both the approved sequence and that gate, report the conflict for owner resolution instead of altering the story or inventing evidence. Accept it through the existing frame operation and bind its hash.
4. Once independent requirements pass, obtain separate explicit paid-render authorization specifying the exact prompt hash, reference/frame hashes, model, settings, one output, credit/cost ceiling and **no automatic retry**. Obtain a fresh provider credit estimate at that future point; no current price is invented. Stop on ambiguous dispatch; a failed/poor output is not permission to spend again.
5. First run: **one V2 feasibility render**, not a paired-improvement experiment. Fixed settings: Seedance 2.0 Mini, 15 seconds, image2video, 480p, 9:16, videoCount 1; record actual model/version, all input asset hashes, full prompt hash, settings, actual seed if exposed, request/job ID, credit cost and resulting video fingerprint. Do not promise deterministic output or seed support beyond the configured contract. Record actual selected audio settings with the prompt's existing music/SFX intention; do not invent speech/captions.
6. Inspect the real output with the checklist below. No output exists for this task, so no frames or transition results can be marked PASS yet. If a later original-versus-V2 comparison is authorized, generate/verify the original with matched verified Mimi/start-frame context, same actual model version, duration, resolution, ratio, mode and audio settings. Match seed where actually supported and record it; same seed does not prove determinism. Starting-image suitability must be comparable for both prompts. With no existing verified baseline, one V2 output supports feasibility only; a fair paired claim needs a separately authorized matching baseline. No second render is authorized by this plan.

| Actual-video check | Inspect in future output | Failure versus minor imperfection |
|---|---|---|
| Opening / first frame | Wrong fingertip attachment and Mimi–note–cabinet relationship readable in opening frames; cleanup intention does not depend on text. | Invisible/reversed relationship undermines the gag; tiny lettering differences are not automatic failure. |
| Peel / split | Other-hand removal visibly causes one note to become two, one on each hand. | Unrelated spontaneous duplication or missing split is serious; minor hand jitter may be tolerable if causality is clear. |
| Doubling | Visible 2→4→8 progression during the existing pulls; stopping at eight before mirror. | Missing/reversed/extra multiplication undermines the central mechanic; brief motion blur is not by itself failure if states remain clear. |
| Identity / objects | Same verified Mimi, cabinet and sticky notes across frames. | Identity replacement or object teleportation that breaks the story is serious; slight texture drift may be minor. |
| Mirror | Reflection matches Mimi and existing coverage at the scream. | Wrong character/contradictory note state is serious; small surface artifacts may be tolerable. |
| Overwhelmed continuity | Coverage/expression continues from doubling through mirror until sneeze. | Coverage reset or new pulling/escalation is serious; subtle pose variation is not a new event. |
| Release | Sneeze causes notes to leave Mimi and adhere to cabinet. | Disappearance without consequence or wrong destination breaks payoff; minor trajectory variation can be tolerable. |
| Final state | Relief is readable while cabinet remains visibly messy. | Missing/reversed final state is serious; imperfect note spacing is not automatic failure. |
| Timing / transitions | Inspect the complete clip and transitions around 2, 5, 10, 12 and 15s, plus intermediate count changes. | Do not infer correct progression from isolated selected stills. |
| Comparative appeal | Assess visible clarity/compelling progression against a verified matched baseline, if later available. | Without that baseline, report feasibility and uncertainty only. No measured retention/replay claim. |

Preserve defects and tolerable imperfections separately. Strong execution of the protected identity, mechanic, cause/effect and ending matters more than eliminating every cosmetic artifact. A single successful or failed stochastic sample does not prove general model superiority.

## Delivery and statuses

Created: `CPQ_V1_MIMI_CREATIVE_IMPROVEMENT_V2.txt`, `MIMI_V1_TO_V2.diff`, `MIMI_V2_READINESS_EVIDENCE.json`, and this report. No existing V1/report/source/prompt artifact was edited by this delivery.

```text
MIMI_V2_DRAFT: CREATED
TARGETED_CAUSAL_FIX: APPLIED
APPROVED_STORY_UNCHANGED: YES
V1_DRAFT_UNCHANGED: YES
REAL_CREATIVE_IMPROVEMENT: NOT_YET_VERIFIED
CHARACTER_REFERENCE: MISSING
START_FRAME: MISSING
RENDER_READINESS: BLOCKED
RENDER_EXECUTED: NO
OFFICIAL_CPQ_GRADING: INACTIVE
```

The immediate missing input is the owner's real approved Mimi image. No paid request, start-frame generation, prompt approval or render permission is inferred from supplying that image.
