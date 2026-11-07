# Post-render QA — Mimi and the rising dough ridge

**Classification: POST_RENDER_REVISION_REQUIRED**  
**Duration gate: POST_RENDER_FAIL_DURATION**

Exactly one authorized Seedance video generation completed. The accepted prompt and architecture were used unchanged. No retry or second render was made. The actual clip has multiple blocking execution defects, so it is not production-ready.

## 1. Render record

- Candidate: `mimi-rolling-pin-dough-wall`
- Provider/platform: OpenArt
- Model: Seedance 2.0 Mini (`byte-plus-seedance-2-mini`)
- Model version: not exposed by the CLI response
- Generation mode: text-to-video
- Render count: **1** (history ID `DCHjC7aOM4KLtVTVxrrJ`); second render: **0**
- Prompt version: `production-prompt-v1`
- Exact prompt source: `../production-prompt-v1/FINAL_PRODUCTION_PROMPT.md`; copied byte-for-byte to this folder before render
- Prompt SHA-256: `9b185670aa97e838975c2f7f717c8b5b947d6b43414dce6d707c887409f03f93`
- References: none. The current CLI exposes text-to-video and first-frame image-to-video, not Seedance `element2video` visual references; no project-approved Mimi visual reference was available in that workflow.
- Config: 15s requested (nearest supported integer to 14.5s under the 15s ceiling), 9:16, 720p, 24 fps output, seed unset/provider default, one output. Exact pre-render configuration is in `render-config-before.json`.
- Audio: the CLI path does not expose the model's `generateAudio=false` field. The returned file contains AAC audio. Treat the audio as unapproved; the visual QA below was performed without relying on audio.
- Credits: account balance was 5,063 before and 4,463 after: **600 credits observed difference**. The provider did not return an itemized cost; do not treat this as a quoted line-item price.
- Result: `rendered-video.mp4`; provider resource ID `6N0pJHCuyslBjaEgwJa5`.
- File SHA-256: `4634143f846a35cf66b1ec33596060407ca54d8fdf9c2daacdcc9650ef088fdf`.

## 2. Duration and format

`ffprobe` reports a **15.104s container**, with a 15.041667s video stream and 15.104s AAC stream. Dimensions are 720×1280 (9:16), H.264, 24 fps. The hard maximum is 15.0s; therefore the clip fails duration. It has not been trimmed or altered.

## 3. First-frame audit

**FAIL — major.** At 0.0s Mimi, the pin, flat dough, and a raised dough form are visible. However, the raised form is a small dollop sitting on top of the rolling-pin barrel, rather than the specified chest-high ridge directly beneath the barrel supporting it. The intended impossible contact and obstruction are not clearly established in the first frame.

## 4. Beat-by-beat audit (timestamps approximate, based on sampled frames and transitions)

| Accepted beat | Observed interval | Mimi strategy / contact | Ridge before → after | New state / result |
|---|---|---|---|---|
| 1. Continue opening press | 0.0–3.0s | Presses at the table; barrel appears to stay low while a small dough peak rises over it. Contact geometry is ambiguous. | Small nub → narrow peak near Mimi's face | Height increases, but the rise is not clearly beneath/supporting the barrel. **MEANINGFUL visual change; rule evidence weak.** |
| 2. Crosswise false tamp | 3.0–6.5s | Mimi lifts/repositions and presses; no legible crosswise orientation is established. A pause with the pin held occurs around 3.3–4.5s; later contact returns to the tabletop. | Tall narrow peak → low rounded mound/stub | The ridge appears shorter/reset instead of continuing higher; the distinct strategy and causal result are unclear. **ACTIVITY_ONLY / repetition risk.** |
| 3. Reverse roll from far side | 6.5–10.2s | Mimi and camera framing jump wider. The pin sits separately on the tabletop to the right while the same vertical ridge continues to lengthen; the pin later appears partway up the ridge without a visible continuous roll. | Low mound → tall column | The column grows without visible pin contact, and the pin's relocation is discontinuous. A visual height escalation occurs, but it violates the rule. **ACTIVITY_ONLY as an accepted beat; causal hard fail.** |
| 4. Final press / out of reach | 10.2–15.104s | Mimi presses at the column, releases, and reaches upward. Later the pin rests on the ridge top. | Tall column → pin held above Mimi's comfortable reach | Payoff reads clearly by about 11.3s and remains through the ending. **MEANINGFUL_PROGRESS**, though the payoff hold is long. |

## 5. Contact causality

**FAIL — major.** The frame-zero dollop is above the roller, so the specified barrel-under-ridge support is not established. The Beat 2 lift/contact/orientation is unclear. Most materially, from roughly **6.6–8.6s** the ridge grows taller while the rolling pin is visibly separate on the table. Around **9.0–9.3s** the pin appears partway up the column without a visible contact path. This reads as autonomous growth and a position jump.

## 6. Known risks

- **Cross-tamp/contact legibility: MAJOR_DEFECT.** No clearly visible crosswise rotation or exact contact-strip rise; the ridge also shortens after the press.
- **Reverse-roll/same-ridge continuity: MAJOR_DEFECT.** One connected column remains, but it rises without contact and the pin reappears on it discontinuously. Topology is mostly continuous; causal continuity is broken.

## 7. Character, pin, hands, and dough

- **Mimi identity: MAJOR_DEFECT.** The render shows a human child, not the project's canonical light-blue rabbit Mimi. The clip keeps this invented human design fairly consistent internally, but it does not satisfy canonical identity. No approved reference was used.
- **Rolling pin: MINOR_DEFECT.** One wooden rolling pin with two handles remains visible. Its position jumps from tabletop to mid-column around 9.0–9.3s without a visible route.
- **Hands: PASS WITH MINOR RISK.** Broad two-hand handle grips and the final release/reach are readable. No major hand fusion or duplicate limb is visible in sampled frames.
- **Dough: MAJOR_DEFECT.** No box or independent second wall appears, and the column stays attached to the table sheet. But its opening geometry is inverted relative to the intended support, it shrinks during Beat 2, and it grows independently of contact during Beat 3.

## 8. Camera, mobile legibility, pacing, ending

- **Camera:** The portrait framing keeps Mimi, dough, and pin visible. Around 6.5s there is an abrupt change to a wider framing/position; it does not hide the final transformation but departs from the single stable framing request.
- **Mobile legibility:** PASS for the main objects and final elevated-pin silhouette. The first-frame contact/ridge relationship is not legible enough.
- **Silent-view test:** PASS for broad story gist (Mimi presses dough and the pin ends high), with audio ignored. The exact causal rule is **not** communicated reliably because of autonomous ridge growth.
- **Activity vs progress:** Beats 1 and 4 visibly change height/reach; Beat 2 does not establish continued escalation; Beat 3 changes height but breaks contact causality. Not all four beats qualify as meaningful progress under the accepted rule.
- **Dead time:** A roughly 1.2s lift/reposition interval around 3.3–4.5s adds little state change. The final image is held for roughly 3s, longer than the planned 0.7s hold.
- **Payoff predictability:** **ACCEPTABLE.** The elevated-pin outcome becomes clear around 11.3s, inside the final beat; the camera does not reveal the completed payoff at the opening.
- **Payoff:** PASS visually. At the end, the pin is on the very tall connected ridge and Mimi is below, reaching/look-up focused rather than presenting to camera.

## 9. Classification and exact defects

**POST_RENDER_REVISION_REQUIRED** because this is a fixable execution/configuration failure, but it is not acceptable for production. The explicit duration gate is **POST_RENDER_FAIL_DURATION**.

1. **0.0s:** opening ridge is a small dough lump on top of the roller, not a chest-high ridge beneath it.
2. **3.0–6.5s:** cross-tamp orientation/contact is unclear; ridge shrinks rather than progressing.
3. **6.6–8.6s:** ridge grows while the pin is visibly separate; rule mutation/autonomous growth.
4. **~9.0–9.3s:** rolling pin appears partway up the ridge without a visible path.
5. **All frames:** human-child design does not match canonical light-blue rabbit Mimi.
6. **15.104s:** file exceeds hard 15.0s duration maximum.
7. **Audio track:** AAC was generated despite silent-only intent; CLI did not expose the available provider `generateAudio=false` setting. Speech content was not assessed and must not be treated as accepted.
8. **~3.3–4.5s and ~12.0–15.1s:** low-progress reposition interval and overlong final hold.

### Minimal fix recommendation (not applied)

No retry or repair render was made. For a separately authorized future attempt, the minimal fixes are: use an approved Mimi light-blue rabbit visual reference with an element-reference-capable workflow; explicitly anchor the ridge below and supporting the barrel in frame zero; keep the pin in uninterrupted contact through reverse rolling; configure audio off; and choose/export a duration that measures at or below 15.0s. Preserve the four-beat architecture. These changes are recommendations only and were not applied here.

## 10. Integrity and stop record

- Generation count: **1**; provider history contains the one new completed run ID above.
- Second render / retry / variant / repair: **0**.
- Semantic generation calls: **0**.
- Story architecture changed: **No**; the rendered prompt hash matches the accepted prompt hash.
- Original Phase B evidence: **unchanged**; the same 10-file SHA-256 manifest matches the earlier pre-render baseline. See `historical-evidence-integrity.json` and `historical-evidence-hashes-after.json`.
- Human review and PRE_RENDER_QA: preserved and not overwritten.
- Phase A: untouched.
- Raw output and QA frames are retained in this folder. No trimming or audio removal was performed.
