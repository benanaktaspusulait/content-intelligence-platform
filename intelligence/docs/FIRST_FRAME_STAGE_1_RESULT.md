# First Frame Stage 1 — Result

**Status:** `KIKO_FIRST_FRAME_SELECTED` for concept-level first-frame testing; **actual image production is blocked** because there is no approved Kiko visual reference. This selection is not a character-identity pass, image approval, canonical grade, or render authorization.

## 1. Character reference discovery and binding

The live local application was inspected using read-only `GET` requests on 2026-10-18. The canonical registry contains active records for Kiko (`00000000-0000-0000-0000-000000000002`) and Mimi (`00000000-0000-0000-0000-000000000003`), both currently marked `UNTESTED`. This proves registry membership only.

The approved-reference endpoints returned an empty list for both IDs. The workspace-reference discovery endpoint returned these existing local candidates:

| Character | Candidate path in application data root | Status | SHA-256 | Binding decision |
|---|---|---|---|---|
| Kiko | `library/01-CHARACTERS/drawings/kiko.png` | `UNREVIEWED` | `8b9e643660722d5c00bd0d25ebef066ea868f52d8a57aa1e4a2b0eb9b55747fc` | Not approved or bound |
| Mimi | `library/01-CHARACTERS/drawings/mimi.png` | `UNREVIEWED` | `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57` | Not approved or bound |

The two files were inspected as pixels. The Kiko sheet depicts a human child; the Mimi sheet depicts a light-blue rabbit. They are only candidate reference sheets and have not been visually authenticated or approved by an owner. No character appearance has been inferred from registry IDs. No reference was imported, approved, or written to the production database.

**Exact missing approved assets:** an approved Kiko reference image for `00000000-0000-0000-0000-000000000002` and an approved Mimi reference image for `00000000-0000-0000-0000-000000000003`. The named workspace candidates above can be reviewed by the owner in the existing character-reference workflow. Until then, neither is an authoritative visual binding.

## 2. First-frame comparison

Both concepts were checked against the same gates using their current text drafts, the searchable golden prompt archive, and the available local visual-reference records. No image for either new concept exists, so pixel-dependent gates remain untested.

| Gate | Kiko — One-Beat-Late Shadow | Mimi — Uphill Ball |
|---|---|---|
| Instant causal legibility in a still | **Conceptually strong.** Kiko is visibly holding one arm up while the one attached floor shadow keeps that arm down. The contradiction is simultaneous and needs no earlier shot. It shows a pose mismatch, but cannot prove the exact one-beat delay. | **Weak in a still.** A single ball on an inclined ramp can be stationary. Motion blur may suggest a trajectory but does not prove uphill travel without motion history. The ramp could also be misread if its slope is foreshortened. |
| Character readability | Full-body character and shadow can share the frame. **Actual identity: NOT_EVALUATED** because Kiko has no approved visual binding. | Mimi and ramp can share the frame, but the full slope and ball compete for vertical space. **Actual identity: NOT_EVALUATED** because Mimi has no approved visual binding. |
| Historical engine/silhouette | No exact delayed-shadow engine was found in the searchable golden prompt set. Nearest overlap is the historical sticky-note story’s mirror reaction and a golden lamp prompt using a mirror to observe indirectly. The new frame has no mirror, reflected room, or second character; the floor-attached delayed silhouette is a distinct engine. **Duplicate risk: MEDIUM**, pending visual archive comparison. | The golden archive includes Luca’s ball-multiplying crocodile and a sticky-ball-on-wall gag. This concept uses one ball climbing one ramp, with no multiplication, mouth, burst, or pile. The engine differs, but the central ball motif overlaps. **Duplicate risk: MEDIUM.** |
| Seedance 2.0 Mini feasibility | A locked camera, one broad limb gesture, one attached shadow, and explicit holds are bounded, but the model must preserve an independently delayed shadow, attachment, and one light direction. **Text-based risk: HIGH; animation not tested.** | One continuous roll and one soft catch are relatively simple, but the generator may normalize gravity, imply an unseen push, or lose paw-ball contact. **Text-based risk: MEDIUM; animation not tested.** |
| Story promise and payoff | The opening promises that the shadow is wrong; the current ending catches up and confirms the same rule. It is coherent, but risks feeling like a repeat of the opening mechanic rather than a strong payoff. | The opening promises unexplained uphill motion; the catch completes the climb. The researched draft has a position-continuity contradiction at the ending; a correction is recorded separately below. |

### Static causal-legibility decision

Kiko is the stronger static first-frame candidate: the still itself can show two simultaneous, incompatible poses on one connected shadow. It does not prove temporal delay or that Seedance can sustain the rule. Mimi’s still cannot establish that the ball is moving uphill; that requires actual motion evidence.

### Historical archive evidence

The local golden prompt archive contains `ball-crocodile-01.txt` (ball multiplication), `sticky-ball-01.txt` (ball adheres to a wall), and `lamp-01.md` (mirror used as an indirect observation surface). The existing Mimi prompt drafts also contain a mirror reaction. The Kiko shadow concept avoids those objects and story engines, though its body/silhouette mismatch may still evoke a reflection gag at a glance. The searchable archive did not provide a verified Kiko shadow frame for direct pixel-to-pixel silhouette comparison; that check remains `NOT_EVALUATED`.

### Selection

`KIKO_FIRST_FRAME_SELECTED` means selected as the better **concept for a future static-frame test**, not ready for generation. The identity gate is blocked on owner review of the actual Kiko asset. If the candidate `kiko.png` is not approved as Kiko’s canonical visual, the correct next outcome is `NEITHER_CONCEPT_READY` until an approved reference is supplied.

## 3. Final first-frame creative brief

- **Canonical identity:** Kiko, registry ID `00000000-0000-0000-0000-000000000002`; attach only an owner-approved Kiko reference. The currently discoverable `kiko.png` is `UNREVIEWED` and cannot be treated as authoritative.
- **Pose:** Full body in a stable standing pose; one clearly separated arm held overhead. The one attached floor shadow has the corresponding arm down at Kiko’s side. Keep the remaining body pose and feet consistent.
- **Camera:** Locked, vertical 9:16, near-frontal three-quarter view, camera around character chest height with a modest downward tilt so face, raised arm, foot contact, and floor shadow are visible together. No cut or lens change.
- **Framing:** Keep the whole character inside the central 60% of frame height; allocate the lower half to clean floor and the shadow. Do not crop the raised hand, feet, or shadow tip. Preserve margins for a 480p phone display.
- **Shadow geometry:** Exactly one dark, attached floor shadow. Its feet meet Kiko’s foot contact point. It falls diagonally down-right from one broad upper-left light source. The shadow’s torso and legs match the planted pose; only the raised arm differs, remaining down. Make that mismatch large enough to read at thumbnail size.
- **Lighting/background:** One diffuse key from upper-left; plain warm-neutral wall and slightly darker matte floor, with clean value contrast around the shadow. No environmental shadow shapes.
- **Foreground/background:** Kiko and the entire shadow occupy the same unobstructed plane; no furniture or props overlap either silhouette.
- **Static impossibility:** Simultaneously show Kiko’s arm raised and the corresponding part of the single attached shadow still lowered. The frame communicates a pose mismatch only; it makes no claim about delay duration.
- **Exclusions:** No mirror, reflection, second character, second shadow, visible lamp, window, text, arrows, symbols, props, or explanatory graphics.
- **Phone readability:** Use broad silhouettes and simple background values; no fine fur/cloth detail may carry the gag. At a 480px-tall preview, both arm positions and the point where the shadow meets the feet must remain distinguishable.

## 4. Reference-ready English image prompt

**Use only after an owner-approved Kiko reference image has been attached in the existing first-frame workflow.** The available `kiko.png` is unreviewed. If the approved reference slot is empty, stop; do not substitute that candidate or invent Kiko’s appearance.

> Create one polished, family-friendly 3D Pompom Hills still in a vertical 9:16 composition for a 15-second image-to-video starting frame. Use the attached, owner-approved canonical Kiko reference image as the sole authority for the character’s exact design, proportions, materials, colors, face, and limbs. Preserve that design exactly; do not reinterpret it. Show Kiko full-body, standing steadily in a simple room, with one clearly separated arm raised overhead. At the same moment, show exactly one dark floor shadow physically attached at Kiko’s feet. The shadow’s body and legs match Kiko’s planted stance, but the corresponding arm remains lowered at Kiko’s side. Make this single arm-pose mismatch immediately obvious in the still while keeping the shadow coherent with one broad light source from upper-left. Use a locked near-frontal three-quarter camera around Kiko’s chest height with a modest downward angle, enough to show Kiko’s face, raised arm, feet, and the complete shadow together. Keep the entire character and shadow inside a clean central vertical composition; leave generous clear floor around the shadow. Use a plain warm-neutral wall and matte floor with strong, simple value contrast that remains readable when reduced to a 480-pixel-tall phone preview. Soft even family-friendly lighting, crisp silhouettes, no motion blur, no lettering, no captions, no watermark.
>
> **Negative constraints:** no mirror, no reflection, no second character, no duplicate Kiko, no second shadow, no detached shadow, no visible lamp, no window, no furniture, no props, no text, no arrows, no labels, no extra limbs, no altered character design, no cropped feet or raised arm, no dramatic camera angle, no split screen, and no prior-action inset.

This prompt is complete as a reference-bound brief, but it is **not dispatch-ready** until the approved Kiko asset is bound. It must not be sent to an external image service under this task.

## 5. Offline visual layout and validation

The existing render-service visual-reference planner supports provider-free inspection and first-frame asset binding, while actual image proposals use the render workflow. No approved Kiko image exists and no existing local compositing workflow can create a faithful frame without the character asset. Therefore **no image was generated or composited**. There is no offline draft image path.

No actual candidate-frame pixels exist. These checks are therefore all `NOT_EVALUATED`:

| Visual check | Result | Evidence required |
|---|---|---|
| Character identity | `NOT_EVALUATED` | Owner-approved Kiko image binding and visual match review |
| Static impossible relationship | `NOT_EVALUATED` | Actual still showing one raised arm and the matching shadow arm lowered |
| Sound-off comprehension | `NOT_EVALUATED` | Independent thumbnail inspection without explanation |
| Exactly one attached shadow | `NOT_EVALUATED` | Actual pixels; verify one shadow and foot contact |
| Silhouette clarity at phone size | `NOT_EVALUATED` | Inspect actual image downscaled to 480px height |
| Lighting consistency | `NOT_EVALUATED` | Inspect shadow direction and softness against the depicted key light |
| 9:16 composition at 480p | `NOT_EVALUATED` | Actual 9:16 image inspected at target preview size |
| Duplicate-engine risk | `NOT_EVALUATED` | Compare actual composition and silhouette with nearest archive frames |
| Video start-state feasibility | `NOT_EVALUATED` | A separately authorized motion test; stills cannot prove temporal shadow behavior |

## 6. Five-beat motion handoff (not executed)

Target: OpenArt first-frame image as input to Seedance 2.0 Mini, image-to-video, 15 seconds, 480p, 9:16. One impossible rule only: the attached shadow reproduces Kiko’s pose and movement one clear beat later. Use one locked continuous shot.

| Time | Beat |
|---|---|
| 0–2s | Begin on the specified mismatch: Kiko’s arm is raised while the attached shadow’s matching arm is down. Hold long enough to read both together; Kiko glances down. This establishes the wrong state, not proof of the exact delay. |
| 2–5s | Kiko slowly lowers that arm and holds. The shadow follows Kiko’s pose path one beat late, visibly completing the prior raised-arm pose before returning to the lowered pose. Keep the feet and shadow attachment fixed. |
| 5–8s | Kiko performs one deliberate side-step and stops. The shadow completes the previous arm pose first, then shifts its ground contact and body silhouette after the same one-beat delay. Preserve one light direction. |
| 8–11s | Kiko freezes with arms at sides. The shadow finishes the delayed side-step and settles into the same still pose one beat later. No independent shadow action. |
| 11–15s | Kiko makes one broad, slow overhead arm raise and holds still. The shadow completes that same raise one beat later. End with both in the same clear V-like silhouette and Kiko watching the shadow. This is a proposed stronger final silhouette, not evidence that the draft is approved or that the motion will render. |

**First-to-second beat transition:** preserve the frame-zero raised-arm/down-shadow mismatch; Kiko lowers the arm slowly, holds, and the shadow reproduces the prior raised pose after one beat before matching the lowered pose. Do not add a cut, a second light, or an independent shadow gesture.

**Likely Seedance failures:** (1) shadow tracks immediately or with inconsistent delay; (2) shadow detaches, duplicates, or changes light direction; (3) arm silhouette/limb correspondence warps or becomes unreadable at 480p.

**Motion-test acceptance:** one continuous 15-second 9:16 clip; exactly one shadow remains attached at the feet; one consistent light direction; the opening mismatch is visible before movement; at least two large body movements are copied after a consistent one-beat delay; no independent shadow motion; the final arm silhouette visibly catches up. Any missed timing, extra shadow, detachment, or identity drift is a failure, not a partial pass.

### Payoff assessment and alternative

The researched ending (shadow catches up after a repeated single-arm raise/lower) is understandable but may only restate the opening mismatch. One material, still-unapproved alternative is the broader two-arm overhead V in the final beat shown above: the delayed copy gives a distinct final silhouette while staying within the same shadow-copy rule. No extra character or second shadow is introduced. This alternative remains a creative proposal, not an owner-approved story change.

## 7. Mimi ramp continuity correction — separate draft

The research text says Mimi reaches the upper end before the ball, then says she remains bent at the lower end while catching it at the upper lip. Those positions cannot both be true. The historical research document was not modified. A separate unapproved correction draft is at [MIMI_UPHILL_BALL_CONTINUITY_DRAFT.md](first-frame-stage-1/MIMI_UPHILL_BALL_CONTINUITY_DRAFT.md).

## 8. Exact next action for real first-frame evidence

An owner must review and approve the existing Kiko workspace candidate, or supply an approved canonical Kiko reference. Bind that exact approved asset to the Kiko concept. Then create one disposable first-frame proposal using the existing visual-reference workflow and inspect the actual pixels at 9:16 and 480px phone scale. Only after that inspection can any visual checklist item become PASS or FAIL. A future Seedance motion test requires separate authorization.

## 9. Scope and integrity

Only this report and the separate Mimi continuity draft were added. The V6.3 Pip experiment, historical source hashes, previous reviews, concept research, character records, and production database were not modified. No owner approval was invented. No provider, image-generation, OpenArt, video-render, paid model, or deployment call occurred.
