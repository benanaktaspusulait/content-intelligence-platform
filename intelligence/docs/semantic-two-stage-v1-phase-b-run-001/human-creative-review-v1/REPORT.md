# Flat-Pack Dough: offline human creative review

**Decision: REVISION_REQUIRED**

This review is based on the exact stored Phase B response and its deterministic pipeline record. It is a story and production-feasibility judgment, not observed audience retention or rendered-video evidence. No provider, render, prompt, validator, score, or production-candidate update was used.

## 1. Original story summary

Mimi starts with the rolling pin already pressing a chest-high wall in a flat sheet of dough. Each time she relocates or turns the pin and presses, the contacted dough rises into another wall. Three placements make an L, then a three-sided enclosure, and the fourth closes an open-topped dough box around the flat center. The final image is Mimi peeking over the back wall while the rolling pin rests on the front wall. Declared duration is 16 seconds.

The rule and opening are strong. The decision is driven by the story's 16-second declaration, repeated `move pin → press → wall rises` progression, early box predictability, and the persistent geometry burden.

## 2. Production policy applied

The requested final is **15 seconds or less**, designed at storyboard stage. The stored expansion prompt also targets about 15 seconds, allows at most 20, calls for four or five major causal beats, and asks for varied strategies, broad poses, stable identities, and few moving elements. The stricter ≤15-second brief governs this review. The existing 16-second story is out of spec as written; it should not be treated as a 16-second source to trim later.

## 3. First-frame review

**Classification: STRONG (text-plan assessment; not render-verified).**

- **Scroll-stop:** Strong. A chest-high dough wall already stands directly under the rolling-pin barrel.
- **Protagonist:** Mimi's braced arms and forward lean are described clearly.
- **Goal:** The broad flat sheet on the table makes the flattening goal readable.
- **Object and anomaly:** Rolling pin and dough are named and physically connected in the same frame.
- **Causality:** The wall rises exactly at the barrel contact strip; no explanation is needed in the description.
- **Scale and silhouette:** The wall is the central silhouette against a plain background. Its narrow contact thickness is the main legibility risk; preserve visible width along the barrel.
- **Mobile 9:16:** The vertical wall is naturally suited to portrait framing. A storyboard must keep the barrel-to-wall contact visible and leave enough width to read the sheet as flat on both sides.

Keep this opening. Do not redesign it.

## 4. Beat-density review

| Beat | New strategy | New physical state | New information | Escalation | Silhouette change | Retention value |
|---|---|---|---|---|---|---|
| 1 | No; continues the opening press | Wall grows from chest to nose height; pin and hands lift | Confirms the opening rule on the next press | Moderate height increase | Moderate | Medium; clear confirmation |
| 2 | Yes; quarter-turn and move to the left strip | Single wall gains a perpendicular wall: L shape | A changed rolling direction creates a corner | Moderate | Strong | Medium; first meaningful tactic change |
| 3 | Weak; same orientation, moved to the right strip | L becomes a three-sided enclosure | Only the viewer-facing strip remains open | Low to moderate | Moderate | Low; spatial relocation repeats Beat 2 |
| 4 | Weak; move/reorient to the final strip and press | Three sides become an open-topped box | The remaining gap closes | High terminal state change | Strong | Medium; clear shape completion, low surprise |

Beats 2–4 largely follow **move pin → press → wall rises**. They accumulate real geometry, so they are not empty actions, but Beat 3 adds little strategy or rule understanding. Beat 4 changes the silhouette by closing the last side; the result is a literal completion of the enclosure.

## 5. Adjacent-beat repetition matrix

Similarity labels are qualitative comparisons of the stored text plan, not model measurements.

| Pair | Strategy similarity | Trigger similarity | Response similarity | Camera/silhouette similarity | New information | Classification |
|---|---|---|---|---|---|---|
| 1 → 2 | Low–medium | High: same downward pin pressure | High: contacted dough rises | Medium: wall turns into an L | Direction change makes a corner | BORDERLINE_REPETITION |
| 2 → 3 | High: reposition and press | High | High | Medium–high: add the opposite side | Only one open strip remains | REPETITIVE |
| 3 → 4 | High: press the remaining strip | High | High | High: enclosure closes | Confirms box completion | BORDERLINE_REPETITION |

The distinction between activity and progress matters here: the enclosure grows, but the viewer learns the same trigger-response after Beat 1. The repeated spatial placements carry most of the remaining progression.

## 6. Payoff predictability and strength

**EARLY_PAYOFF_PREDICTABILITY begins after Beat 2.** The L-shaped dough makes an enclosure a natural next shape. After Beat 3's three-sided form, the fourth side is nearly certain.

- **Surprise:** Low after Beat 2; very low after Beat 3.
- **Visual transformation:** Strong: flat sheet to open box.
- **Rule linkage:** Strong and deterministic; every wall follows the same upward-growth rule.
- **State change:** Strong.
- **Emotional reaction potential:** Moderate; Mimi peeking over the wall is readable, but the story does not give her a distinct decision or reversal.
- **Rewatch motivation:** Low–moderate; the shape accumulates clearly but has little hidden detail.
- **Loop:** No natural loop. Do not force one; the unresolved wall and perched pin make a stable ending.

The expected completion is a flattened sheet. The actual reveal is an enclosure around an untouched flat center. That is visually clear, but the box is built incrementally in the most predictable order. There is no moment where Mimi appears to have found a solution and the same rule redirects it. A false solution and reversal would improve continuation pressure.

## 7. Original timing audit

The source declares 16 seconds and supplies no per-beat timings. The actions could be hurried into 15 seconds, but doing so would compress the pin turns, contact changes, wall formation, and final reaction. That would be a new timing design, not an honest claim about the stored 16-second plan. The stored story therefore fails the requested ≤15-second requirement as written.

## 8. Generation-feasibility audit

| Element | Risk | Reason |
|---|---|---|
| Persistent dough geometry | HIGH | Flat sheet, one wall, L, three sides, then a box must persist and connect correctly. |
| Wall height/continuity | HIGH | Contact strip, wall width, and height must remain stable across four activations. |
| Rolling-pin orientation | HIGH | Horizontal, quarter-turn, reposition, then parallel closure must be tracked exactly. |
| Mimi's hands | HIGH | Repeated lift, rotate, regrip, place, press actions create contact and continuity demands. |
| Contact relationship | HIGH | The rule is legible only if the contacted strip is visibly beneath the barrel. |
| Identity consistency | LOW | One protagonist, one location, no costume or character changes specified. |
| Camera continuity | MEDIUM–HIGH | A single kitchen/table helps, but the viewer must read the L, three-sided layout, and final closure. |
| Portrait/mobile composition | HIGH | Showing the entire tabletop enclosure and Mimi's relationship to it may force a wide or top-down view that weakens the central contact hook. |
| Props and location | LOW | Mimi, rolling pin, dough, table, and one kitchen only. |

### Geometry-state count

The source sequence asks the model to preserve **five stated geometric states**: flat sheet, one wall, L, three-sided enclosure, and four-sided open-topped box. This is too much persistent geometry to rely on for a short generated clip without a strong storyboard and continuity controls. The final two shapes also require remembering which edges have already formed.

## 9. Human-review decision

**REVISION_REQUIRED.**

Reasons:

1. The stored 16-second duration exceeds the requested ≤15-second production limit.
2. Beats 2–4 mostly repeat a pin relocation and the same press-response.
3. The box payoff becomes predictable at the L-shaped state and nearly certain at three sides.
4. Five persistent geometric states, repeated hand placements, and rotating pin orientations raise video-generation risk.
5. A false solution or reversal could create stronger continuation pressure without adding a second rule.

This is not a rejection of the seed. The strong frame-zero contradiction, simple cast, and clear source rule are worth retaining.

## 10. One revised story architecture (specification only)

Preserve Mimi, the rolling pin, the flatten-dough goal, the exact rule and trigger, and the exact stored frame zero. Keep one connected dough wall throughout; vary height and the direction of the pin's approach instead of building an L/box.

**FRAME ZERO — unchanged:** Mimi stands behind a kitchen table, leaning forward with both palms pressing down on the handles of a horizontal rolling pin. A broad, thin sheet of dough lies on the tabletop. Directly beneath the rolling-pin barrel, that same sheet forms a smooth, chest-high vertical wall of dough, as wide as the barrel and only as thick as the barrel's contact strip. The barrel rests across the wall's narrow top, far above the flat dough on either side. Mimi's downward-braced arms and the towering dough wall form the large central silhouette against a plain kitchen background.

### Beat 1 — Continue the opening press

- **Strategy:** Mimi continues the same downward stroke on the raised strip.
- **Consequence:** The contacted section rises from chest height toward her nose, lifting the barrel and her hands.
- **New state/information:** The wall is higher; the same press confirms the rule.
- **Distinctness:** Direct causal continuation, no setup or reset.

### Beat 2 — False tamp

- **Strategy:** Mimi lifts the pin clear, turns the barrel crosswise, sets it on the top of the same wall, and presses down to tamp the ridge flat.
- **Consequence:** The dough directly beneath the barrel rises upward again and supports the pin at a higher level.
- **New state/information:** The wall becomes taller without adding a new wall; tamping with the roller does not flatten it.
- **Distinctness:** A deliberate false solution with a different contact orientation.

### Beat 3 — Reverse the rolling direction

- **Strategy:** Mimi moves to the far side and rolls backward along the same ridge while keeping the barrel pressed down, trying to push the wall back toward the table.
- **Consequence:** The contacted ridge rises continuously along the pin's path; the pin rides along the higher single wall.
- **New state/information:** Reversing the direction does not reverse the rule; the ridge extends as one connected strip.
- **Distinctness:** Changes the direction and path of the attempt while preserving trigger, target, and response.

### Beat 4 — The tool goes out of reach

- **Strategy:** Mimi makes one final two-handed downward press near the ridge's center.
- **Consequence:** That contact strip rises above her head, lifting the rolling pin and her hands. Mimi releases the handles and looks up as the pin remains supported on the wall.
- **New state/information:** The same rule has carried her tool beyond reach; another pressing attempt has made the goal harder.
- **Distinctness:** Magnitude and consequence escalate to a readable payoff; the final image is one tall wall, not a fourth boundary.

**FINAL PAYOFF:** One last press raises the single dough wall above Mimi's reach and leaves the rolling pin perched on top. The new reveal is the tool's elevation and Mimi looking up, not another wall closing a box.

**TARGET DURATION:** 14.5 seconds, authored to fit—not trimmed from a longer version.

### Revised timing blocks

| Time | Action and comprehension hold |
|---|---|
| 0.0–2.4 | Hold the unchanged opening long enough to read Mimi, flat dough, pin contact, and chest-high wall; Beat 1 raises the wall and pin. |
| 2.4–5.7 | Beat 2: lift, crosswise turn, tamp, wall rises again. Keep the whole single ridge in frame. |
| 5.7–9.2 | Beat 3: move to far side and reverse-roll along the same ridge; show continuous contact and connected growth. |
| 9.2–14.5 | Beat 4: final press raises the center above Mimi's reach; release and hold the final pin-on-wall silhouette for the last 0.7 seconds. |

### Revised rule-consistency proof

| Beat | Trigger | Expected response | Proposed actual response | Result |
|---:|---|---|---|---|
| 1 | Mimi presses both rolling-pin handles downward with the barrel in contact with dough. | Contacted dough thickens upward into a wall supporting the barrel. | The existing wall rises higher and lifts the barrel/hands. | CONSISTENT |
| 2 | Same rolling-pin pressure, now crosswise on the wall's top. | Contacted dough thickens upward into the same wall. | The wall rises and supports the pin higher. | CONSISTENT |
| 3 | Same pressure while rolling backward along the ridge. | Dough directly under the barrel thickens upward; direction does not reverse the response. | One connected ridge grows along the pin's path. | CONSISTENT |
| 4 | Same downward press near the ridge center. | Contacted dough thickens upward and supports the barrel. | The wall lifts the pin above Mimi's reach. | CONSISTENT |

This is a proposed architecture, not a regenerated or validated candidate. Any storyboard must keep the wall connected and show the barrel touching the exact strip that rises.

## 11. Production-feasibility assessment for the revision

The revised concept reduces topology memory from five states to **two primary shapes**: the broad flat sheet and one connected vertical ridge. The ridge height changes across beats, but no L, three-sided enclosure, or box must persist. Main remaining risk is exact roller-to-ridge contact during crosswise tamping and reverse rolling; keep camera locked in a portrait-friendly three-quarter view, avoid cuts, and use broad hand poses. No extra props, characters, location changes, text, or fine finger actions are required.

This reduces production risk but does not establish generation success. If Beat 3 cannot be staged as one continuous ridge without visual duplication, simplify or remove that action during a later human storyboard pass; do not add a second wall or rule.

## 12. PRE_RENDER_QA

- [ ] First frame preserves the original strong wall-under-barrel hook and is readable within the first second.
- [ ] Mimi, goal, rolling pin, dough, and contact point are all visible in 9:16.
- [ ] Exact rule remains: pressing the rolling pin makes contacted dough rise vertically instead of flattening.
- [ ] Every powered consequence uses the same trigger, target, direction, and response.
- [ ] Beat 1 continues directly from frame zero; no reset or alternate opening.
- [ ] Four beats are visibly distinct: continue, crosswise tamp, reverse-roll, final press.
- [ ] Every beat creates a new state or new rule information; no repeated press without visible progress.
- [ ] Only one connected dough wall persists; no L, enclosure, box, split wall, or independent dough motion.
- [ ] Payoff comes from the final same-rule press and changes Mimi's reach to the tool.
- [ ] Total timed plan is 14.5 seconds or less, including reaction/hold; no later trim assumption.
- [ ] No dead time; each action and wall-height change remains legible at playback speed.
- [ ] Mimi's identity, hand placement, rolling-pin shape/orientation, and wall contact continuity are stable.
- [ ] Silent viewing explains the goal, rule, failed approach, and payoff without dialogue or text.
- [ ] No extra prop, character, magic behavior, or location change appears.
- [ ] Human storyboard review confirms the wall stays connected and the contact strip is visible before any render is authorized.

## 13. Scope and evidence integrity

- Provider calls: **0**.
- Renders: **0**.
- Original Phase B response, story, seed, frozen seed, analysis, request, and prompt were only read. Their before/after SHA-256 values are in `original-evidence-hashes-before.json` and `original-evidence-hashes-after.json`; `original-evidence-immutability.json` records equality.
- No candidate, score, ranking, admission, prompt, validator, or production status was changed.
- `PHASE_A_DIVERSITY_COLLAPSE = UNRESOLVED`; untouched.
