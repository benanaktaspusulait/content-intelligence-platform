# First Real Pompom Pilot Readiness

**Final status: `PILOT_BLOCKED`**

## Decision

The selected image2video candidate is **Kiko — Runaway Toothbrush**. Its actual 9:16 opening still shows Kiko reaching toward a toothbrush that has escaped across the sink. The canonical Kiko reference and this exact first frame have separate human approvals recorded in the existing registries. Do not render yet: linked production quality validation is not `RENDER_READY`.

Human approvals are now recorded separately through the existing registries: Kiko reference `APPROVED` (record `4a142386-cb1d-48d6-9f0a-73076cf0267f`) and exact first frame accepted in visual plan `0138454a-4d59-492f-8cb6-76359edd5825` (asset `72afb9e6-5aca-44a1-bedb-c097fdf0171c`). Both records bind the exact hashes listed below. The pilot remains blocked by production validation, described in the run addendum.

`FIRST_FRAME_MISSING` and `RENDER_MODE_UNSUPPORTED` are cleared: the exact still is accepted, and the selected model supports image2video under the checked local schema. `CREATIVE_VALIDATION_FAILED` remains active: linked quality validation returned `SERVICE_ERROR` and did not reach `RENDER_READY`. A separate provider-call policy incident and a first-frame summary display inconsistency are documented in the run addendum.

## Deduplicated local inventory

Scope is the configured Pompom production library at `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS`, not unrelated private directories.

- **Production prompt sources:** 215 files matching video prompt, OpenArt prompt, first-frame prompt, and first-scene prompt naming patterns; 215 unique SHA-256 contents.
- **Local scene/still images:** 393 files, 392 unique contents; 377 unique vertical images at portrait dimensions.
- **Prompt-paired vertical stills:** 339 images live beside a video prompt. 201 of those also have a separate first-scene/first-frame prompt. These are candidate opening stills, not automatically approved first frames.
- Existing mixed evidence inventory at `intelligence/docs/pilot-readiness-v1/local-prompt-inventory.json` counts 814 named files / 807 unique contents across platform evidence and the Pompom library. That broader number is not a production-prompt count.

The prompt/image counts are scoped and reproducible by path/name/hash; they do not claim a full search of all files in the parent `video` directory.

## Existing references and approvals

| Character | Canonical local file | SHA-256 | Approval evidence |
|---|---|---|---|
| Kiko | `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/kiko.png` (1402×1122) | `8b9e643660722d5c00bd0d25ebef066ea868f52d8a57aa1e4a2b0eb9b55747fc` | `APPROVED`, record `4a142386-cb1d-48d6-9f0a-73076cf0267f`, reviewer Benan Aktas, timestamp 2026-11-02T14:47:22.539959Z. |
| Mimi | `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/mimi.png` (1536×1024) | `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57` | Existing evidence says `UNREVIEWED / NOT_APPROVED`; not selected. |

The platform reference API now records the Kiko asset as `APPROVED` with the exact SHA above. The scene still was copied byte-for-byte to the prompt-bound visual-reference plan and accepted by the explicit human decision; its stored SHA is `18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a`. The mounted stored copy hash matches the original.

## Three candidate assessment

| Rank | Candidate | Local assets | First-frame and story assessment | Decision |
|---:|---|---|---|---|
| 1 | **Kiko — Runaway Toothbrush** | `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_prompt.md`; `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_image.png` | Actual frame is 941×1672 (9:16), showing Kiko, bathroom sink, one toothbrush sliding away, and her active reach. Prompt calls for exactly 15 seconds and a continuous gag. Frame and story are well matched. Prompt packs many micro-actions into 15 seconds, so generator continuity remains a risk. | **Primary**, pending human approval. |
| 2 | **Mimi — Inflating Ears** | `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Absurd_Moments/04_mimi_inflating_ears/01_video_prompt.txt`; `02_first_scene_image_prompt.txt`; existing PNG and MP4 in same directory | 941×1672 vertical. Mimi is identifiable and the impossible ear state is immediately visible. But the actual still has both ears inflated while the source prompt specifies only the left ear inflated and the right ear normal. It also includes unrelated toys. | Not selected: frame/prompt mismatch. |
| 3 | **Mimi — Missing Carrot** | `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Can You Find It?/02_mimis_missing_carrot/01_video_prompt.txt`; `02_first_scene_image_prompt.txt`; existing PNG and MP4 in same directory | 941×1672 vertical. Actual still contains Mimi and a second child, with a carrot visibly present in the scene; the “missing” problem is not immediately legible and it is not a one-character setup. | Not selected: weaker opening clarity and higher identity/continuity risk. |

## Selected prompt and exact frame

- **Selected production prompt:** `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_prompt.md`
- **Prompt SHA-256:** `d623dd1f1bbbb1207090c7caff4db5f4b8b806cb55d26cb6aa14ceb8f356b610`
- **Exact first-frame image:** `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_image.png`
- **Image SHA-256:** `18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a`
- **Dimensions:** 941×1672; portrait 9:16.
- **Character reference to compare during review:** `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/kiko.png` (SHA above).
- **Source prompt:** copied verbatim below from the selected file; no story or prompt edits were made.

### Human visual checklist

The actual still was opened and compared side-by-side with the official Kiko sheet.

| Check | Result |
|---|---|
| Correct recognizable Kiko | Visual match: yes; human approval: pending. Coral-pink top, white shorts, brown double buns, face and proportions broadly align. |
| Location and primary object | Pass: bathroom sink and one toothbrush are visible. |
| Everyday goal | Pass: Kiko is reaching to catch the toothbrush. |
| Impossible problem active at frame zero | Pass: toothbrush is already escaping. |
| 9:16 composition | Pass: 941×1672 portrait. |
| No unrelated character or text dependency | Pass: no other character or text is needed to understand the frame. |
| Human asset approval | **APPROVED** for both exact images; registry records are listed above and in the addendum. |

Human review has now explicitly approved each exact asset. Canonical character lifecycle remains unchanged; only the existing character-reference approval record and visual-reference first-frame binding were updated.

## Existing image2video compatibility and dry run

Installed CLI: `openart 0.1.1`, commit `85fa0ad`, built 2026-08-31. Its actual `openart generate video --help` says `--image` uploads a local file as the start frame and switches the request to `image2video`. `openart model list` reports `grok-imagine-1-5` with `text2video` and `image2video`. No element2video mode or new client is needed for this pilot.

A local CLI dry run completed with exit code 0 and no provider request. The sanitized request preview was:

```json
{
  "model": "grok-imagine-1-5",
  "media": "video",
  "mode": "image2video",
  "params": {
    "duration": 15,
    "aspectRatio": "9:16",
    "resolution": "720p",
    "startFrame": {
      "label": "01_runaway_toothbrush_image.png",
      "type": "image",
      "url": "(uploaded from /Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_image.png)"
    }
  },
  "endpoint": "POST /api/cli/v1/generate",
  "plannedOutputPath": "/tmp/pompom-runaway-toothbrush-pilot.mp4"
}
```

The exact selected prompt above was passed to the dry run. The CLI binds the image as the outgoing start frame, and did not fall back to text2video. The `--output /tmp/pompom-runaway-toothbrush-pilot.mp4` argument was present in the dry-run invocation; no output file was created. The CLI rewrites ASCII `->` sequences into a Unicode arrow in its printed request; the saved source prompt itself is unchanged.

**Duration contract:** source requests exactly 15 seconds. The CLI accepts an integer `--duration`; model metadata lists image2video. CLI help explicitly says duration, aspect ratio, and resolution are model-specific. The dry run does not query or validate model schema, so support for 15 seconds, 9:16 and 720p remains **unverified**. No 14-second request is substituted without a schema confirming it. A future encoded video must be checked with `ffprobe`; the requested duration is not a guarantee of final stream duration.

**Current platform preflight:** content/prompt IDs 18/29 and visual plan `0138454a-4d59-492f-8cb6-76359edd5825` are now present. The scene asset is accepted with exact path, prompt hash, image hash and model contract. The queue still cannot admit a render because linked production quality returned `SERVICE_ERROR` rather than `RENDER_READY`; details are in the run addendum.

## Focused tests and regression

Executed in `intelligence/creative-render-service`:

```text
mvn -q -Dtest=CliRealOpenArtAdapterTest,OpenArtReferenceResolverTest,RenderAttemptOrchestratorTest,RenderJobQueueServiceTest,VisualReferencePlanningServiceTest test
```

**44 tests passed, 0 failed, 0 errors, 0 skipped.** Coverage includes CLI image2video request construction and image binding, character-reference resolution, render orchestration, queue rejection when first-frame review is missing, and visual-reference plan validation. Tests are offline fixtures; they do not approve real assets or verify the selected model’s live duration schema.

**Regression status:** no source code changed. The previously recorded Phase B production-render regression remains a known historical failure (wrong character identity, weak opening, broken contact causality, duration overflow, and other QA findings); this new local candidate was not rendered, so no new render regression result exists. Existing post-render QA was not rerun. No full test suite was run.

## Calls and remaining blockers

- OpenArt/media-generation provider calls: **0**. One linked quality-validation request triggered an LLM semantic call; see the run addendum.
- Render calls: **0**.
- Docker resources cleaned: **no**.
- Human asset approval: **required** — explicit Kiko canonical reference review and exact first-frame review/acceptance.
- Platform ingestion and evidence binding: **pending** — requires the local app/DB and normal import/validation path after asset review.
- Model-specific 15s / 9:16 / 720p contract: **unverified** — verify the installed model schema before authorizing a render.
- `RENDER_MODE_UNSUPPORTED`: **not a blocker**; image2video is supported.
- `FIRST_FRAME_MISSING`: **not a blocker**; a candidate still exists.
- `CREATIVE_VALIDATION_FAILED`: **not established**; app creative validators could not be run without the local platform.
- `INTEGRATION_DEFECT`: **not established**; existing queue and visual-reference gates are present and focused tests pass.

## Exact next operator action

Review the exact Kiko canon and Runaway Toothbrush still linked above. If accepted, use the normal character-reference review and visual-reference acceptance flow to record the reviewer and hashes; then bring up the existing local app and import this exact prompt/image through its normal content workflow. Confirm the app reaches `RENDER_READY`, verify the model’s supported `image2video` duration/settings, and re-run the final request preflight. Do not submit the paid render until those records bind to the prompt and first-frame hashes.

---

## Exact selected source prompt (verbatim)

```text
Create an EXACTLY 15-second vertical 9:16 Pompom Hills short engineered for MAXIMUM REWATCHABILITY, visual comedy, and loop replay.

Use the official existing Kiko character reference exactly.
Do not redesign Kiko or replace her with a generic child.
Preserve Kiko's face, double-bun brown hair, coral-pink long-sleeve top, white shorts, coral-pink shoes, proportions, colours, and established soft 3D preschool style.

SERIES:
Pompom Chaos

EPISODE:
01 - Runaway Toothbrush — REPLAY MAX VERSION

MAIN CHARACTER:
KIKO

MAIN OBJECT:
ONE NORMAL TOOTHBRUSH ONLY

CORE PHYSICAL RULE:
The toothbrush refuses to be caught.
Whenever Kiko is about to grab it, it escapes at the last possible instant.
It never talks, never has a face, never grows limbs, and never changes identity.

PRIMARY GOAL:
Make the viewer laugh immediately, then reward a second and third watch with tiny visual details, near-misses, and a loop that snaps back naturally to the opening.

GLOBAL RETENTION RULES:
- EXACTLY 15 seconds.
- 9:16 vertical throughout.
- The chaos is ALREADY happening in frame one.
- NO establishing shot.
- NO slow setup.
- NO passive looking beat longer than 0.25 seconds.
- Every 0.8-1.5 seconds must contain a clear change, reversal, near-miss, or escalation.
- One toothbrush only.
- One physical rule only: Kiko almost catches it -> toothbrush escapes.
- The toothbrush remains visually normal: no eyes, mouth, arms, legs, or character face.
- Comedy must be understandable with SOUND OFF.
- Preserve Kiko's official design exactly.
- Stable, readable camera with tiny purposeful push-ins only if needed.
- No camera rotation.
- No subtitles, captions, logos, or text inside the scene.
- No narrator.
- No extra characters.
- No duplicate toothbrushes.
- No wardrobe changes.
- Avoid clipping, deformed hands, broken fingers, face drift, duplicate limbs, or teleportation.

--------------------------------------------------
0.0-0.55 SEC — INSTANT CHAOS HOOK
--------------------------------------------------
FIRST FRAME:
Kiko is ALREADY half-stretched across the bathroom sink, one foot on a small stool, one hand centimeters from the toothbrush.

The toothbrush is ALREADY sliding away fast across the wet countertop.

A tiny splash trail shows it escaped a split-second earlier.

Kiko's eyes are wide and determined, mouth open in disbelief.

No setup.
No calm reach.
The chase has already started.

--------------------------------------------------
0.55-2.0 SEC — NEAR-MISS #1
--------------------------------------------------
Kiko lunges with both hands.

At the exact last instant the toothbrush shoots sideways around the soap dispenser.

Kiko's hands clap together where the toothbrush WAS.

Tiny beat:
Kiko looks at her empty hands for 0.15 sec.

Then immediately turns and chases.

Kiko:
"STOP!"

--------------------------------------------------
2.0-3.6 SEC — NEAR-MISS #2 / REVERSAL
--------------------------------------------------
Kiko blocks the toothbrush's path with her left hand.

It reverses direction instantly.

She quickly blocks the other side with her right hand.

It reverses AGAIN.

For one very fast comic beat, Kiko's eyes flick left-right-left while the toothbrush ping-pongs between her hands.

On the third fake-out, it slips through the tiny gap between her wrists.

Kiko spins after it.

--------------------------------------------------
3.6-5.4 SEC — ALMOST CAUGHT
--------------------------------------------------
The toothbrush slides toward the edge of the sink.

Kiko dives forward and catches the HANDLE with two fingers.

The toothbrush keeps moving and drags her hand forward.

She adds the second hand.

Now Kiko is holding it with BOTH hands.

Kiko:
"BRUSH!"

Tiny victory smile.

--------------------------------------------------
5.4-7.2 SEC — PHYSICAL STRUGGLE / BIGGER
--------------------------------------------------
The toothbrush vibrates violently in Kiko's hands.

Her arms shake side-to-side.

Her whole upper body wiggles with the motion.

Her two hair buns bounce comically but remain intact.

Kiko squeezes harder.

The toothbrush suddenly goes completely STILL.

Silence for a fraction of a second.

Kiko raises one eyebrow, suspicious.

--------------------------------------------------
7.2-8.5 SEC — FAKE VICTORY #1
--------------------------------------------------
Kiko slowly brings the toothbrush toward her mouth.

Just as she opens her mouth—

WHOOSH.

The toothbrush slips straight upward out of her hands.

Kiko's mouth is still open, now with NO toothbrush.

She blinks once in disbelief.

--------------------------------------------------
8.5-10.0 SEC — ESCALATION / HEAD FAKE
--------------------------------------------------
The toothbrush lands briefly on top of Kiko's LEFT hair bun.

Kiko reaches LEFT.

Before her hand arrives, it slides over the top of her head to the RIGHT bun.

Kiko reaches RIGHT.

It slips back LEFT again.

Her hands cross awkwardly.

This creates a fast, clean left-right-left visual fake-out.

No new magic rule:
it is still simply escaping whenever she nearly grabs it.

--------------------------------------------------
10.0-11.2 SEC — FAKE VICTORY #2
--------------------------------------------------
Kiko finally traps the toothbrush gently between both palms on top of her head.

She freezes.

Tiny proud smile.

She carefully lowers it toward her mouth.

Everything goes quiet for LESS THAN 0.5 sec.

--------------------------------------------------
11.2-13.6 SEC — BIGGEST FINAL COMEDY BEAT
--------------------------------------------------
At the last possible instant the toothbrush twists free and begins rapidly brushing THROUGH the top of Kiko's hair between the two buns.

Kiko's hair fluffs slightly bigger with each rapid pass.

NOT huge transformation.
Only enough to make the silhouette increasingly funny.

Kiko reaches up with both hands, misses once, then twice.

The toothbrush darts from one bun to the other, still brushing.

Kiko:
"GO?!"

Her expression escalates from shock -> determination -> total comic disbelief.

--------------------------------------------------
13.6-15.0 SEC — LOOP TRAP
--------------------------------------------------
The toothbrush suddenly shoots DOWN from Kiko's hair, lands on the wet sink, and immediately slides away in EXACTLY the same direction and speed as the opening shot.

Kiko instantly lunges after it in the SAME body pose as frame one.

HARD CUT while her fingertips are again centimeters away from the toothbrush.

The final composition must visually match the first frame closely enough that the loop feels seamless.

--------------------------------------------------
MANDATORY DIALOGUE
--------------------------------------------------
Use ONLY:
"STOP!"
"BRUSH!"
"GO?!"

No other dialogue.
No narrator.
Dialogue must never delay movement.

--------------------------------------------------
REWATCH ENGINEERING
--------------------------------------------------
Build in tiny details that reward repeat viewing WITHOUT adding extra plot:
- first hand clap where the toothbrush was
- left-right-left eye tracking
- suspicious eyebrow before first escape
- bun bounce during the tug
- crossed hands during the hair fake-out
- tiny hair fluff increase during final brushing
- opening and ending chase pose should nearly match

These micro-gags must be fast enough that a viewer may not notice all of them on the first watch.

--------------------------------------------------
COMEDY RHYTHM
--------------------------------------------------
0.0-2.0s: immediate chase
2.0-3.6s: quick reversal gag
3.6-5.4s: almost caught
5.4-7.2s: physical struggle
7.2-8.5s: first fake win collapses
8.5-10.0s: head fake
10.0-11.2s: second fake win
11.2-13.6s: biggest visual payoff
13.6-15.0s: instant reset into opening loop

No dead air.

--------------------------------------------------
SOUND DESIGN
--------------------------------------------------
Bright, playful preschool background music with no vocals.

Use very short, clean effects:
- tiny slide WHOOSH on escapes
- soft CLAP when Kiko's hands miss
- tiny rubbery vibration during tug
- micro silence before both fake resolutions
- rapid brushing sound in final hair beat
- stronger WHOOSH when toothbrush shoots back to the sink
- final sound should connect naturally to opening sound for looping

Do not overload the mix.

--------------------------------------------------
NEGATIVE CONSTRAINTS
--------------------------------------------------
Do NOT:
- add a face to the toothbrush
- add a second toothbrush
- add random magical sparkles
- add unrelated objects flying around
- let Kiko stand still and watch
- turn this into a teaching demonstration
- explain BRUSH / STOP / GO
- add long dialogue
- use slow zooms
- introduce a second physics rule
- make the hair transformation extreme
- make Kiko fall dangerously
- let the final beat be smaller than earlier beats

The entire short should feel like ONE escalating joke:
KIKO ALMOST CATCHES IT -> IT ESCAPES -> SHE TRIES HARDER -> IT ESCAPES HARDER -> FINAL HAIR CHAOS -> PERFECT LOOP.
```

## Approval and production-preflight run (2026-11-02)

### Explicit asset decisions and registry evidence

The user selected `APPROVE` separately for the exact Kiko reference and the exact first frame. A first approval prompt contained a mistyped frame hash; its answer was ignored. Only the later approval for the corrected frame hash below is used.

- **Kiko canonical reference:** platform character ID `00000000-0000-0000-0000-000000000002`; reference record `4a142386-cb1d-48d6-9f0a-73076cf0267f`; status `APPROVED`; SHA-256 `8b9e643660722d5c00bd0d25ebef066ea868f52d8a57aa1e4a2b0eb9b55747fc`; reviewer `Benan Aktas (explicit approval in Codex)`; approved at `2026-11-02T14:47:22.539958712Z`.
- **First-frame image:** visual-reference plan `0138454a-4d59-492f-8cb6-76359edd5825`; asset `72afb9e6-5aca-44a1-bedb-c097fdf0171c`; role `FIRST_FRAME`; `accepted=true`; SHA-256 `18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a`; 941×1672; prompt version 29 hash `d623dd1f1bbbb1207090c7caff4db5f4b8b806cb55d26cb6aa14ceb8f356b610`; contract `image2video`, `9:16`, model `byte-plus-seedance-2-mini`.
- Imported frame copy: `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/data/content/18/visual-references/18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a.png`; byte size 1,850,849; hash exactly matches source. The source image files were not modified.
- The provider-free visual-reference validation reports `INSUFFICIENT_EVIDENCE`: metadata/path/hash/prompt binding are verified, while automatic semantic identity and prompt compatibility are `UNKNOWN`. Human visual approval is recorded separately and does not change that machine evidence classification.

### Prompt import and production quality result

- Content record `18`, prompt version `29`, source alias is the selected local `.md` path; immutable prompt SHA-256 `d623dd1f1bbbb1207090c7caff4db5f4b8b806cb55d26cb6aa14ceb8f356b610`.
- Linked quality validation record `24`, ruleset `1.12`: `SERVICE_ERROR`; score 73.052083; 4 blockers, 5 criticals, 8 warnings; creative grade `F`; readiness `BLOCKED_TECHNICAL_FAILURE`.
- Failed creative/structural gates include `HOOK_002`, `ATTEMPT_001`, `CHAR_002`, `PRODUCIBILITY_002`, `ATTEMPT_002`, `INSTANT_VISUAL_ABSURDITY_GATE`, `MINI_STORY_LOCK`, `TEMPORAL_COMPLEXITY_SPLIT_GATE`, and `BEAT_DENSITY_RULE`. Reported measurements include 0 active attempts, 0% active solution behavior, 108 main props, 9 major beats for one 15-second generation, and a split recommendation of 2×15 seconds. Do not follow that split recommendation: it violates the pilot’s ≤15.000-second cap. No prompt rewrite or new concept was made.
- `GOAL_001` returned `SERVICE_ERROR`: the LLM result omitted required field `ending_meaningfully_addresses_goal`. The content remains `DRAFT`; no render queue submission was attempted.

### Provider-call policy incident

The user prohibited provider calls. I made one linked local quality-validation request to complete the requested preflight. The existing validator dispatches `GOAL_001` to the configured OpenAI LLM even though the semantic-video flags are false. The returned missing-field error confirms that the LLM-backed evaluation ran. **At least one OpenAI provider call occurred**; the exact provider usage/request ID is not available from the persisted record. No OpenArt generation call or media render occurred. I stopped further quality/LLM validations after identifying this path. This was an execution error; no claim of zero provider calls is made for this run.

### Confirmed integration fixes and verification

- Fixed JSONB mapping annotations on `VisualReferencePlan` JSON strings and `VisualReferenceAsset.validationEvidenceJson`, which had blocked plan persistence with PostgreSQL SQLState `42804`.
- Set multipart upload limits to 20 MB/file and 21 MB/request to match the existing 20 MB image import method; the selected 1.85 MB original PNG is now copied unchanged through the normal upload/accept endpoints.
- **Focused creative-render tests:** 44 passed, 0 failures/errors/skips across `CliRealOpenArtAdapterTest`, `OpenArtReferenceResolverTest`, `RenderAttemptOrchestratorTest`, `RenderJobQueueServiceTest`, and `VisualReferencePlanningServiceTest`.
- **OpenArt dry-run:** exact selected prompt hash above; model `byte-plus-seedance-2-mini`; mode `image2video`; duration 15; aspect `9:16`; resolution `480p`; outgoing `startFrame` points to the selected local PNG; output path `/tmp/pompom-runaway-toothbrush-final-pilot.mp4`; `--dry-run` exit 0. No generation or file output occurred.
- Local capability schema `openart-cli-schema-2026-10-08`, schema SHA-256 `e5458973228db9a1a6fd2185322e98e4f33595496e8c12cf9f22d69206ea1b94`, records duration 4–15 seconds, ratio `9:16`, resolution `480p`/`720p`, and required `startFrame` for this model. Fifteen seconds is supported by that local schema snapshot. The CLI dry-run confirms the prepared request shape, not provider acceptance or encoded duration.
- Current `/prompts/18/29` view returns `firstFrameStatus=MISSING` while listing an accepted `FIRST_FRAME` reference binding. The accepted binding is present and render admission also checks it directly; the contradictory summary field remains a preflight display inconsistency.

### Final status and blockers

**Final status: `PILOT_BLOCKED`**

- `HUMAN_ASSET_APPROVAL_REQUIRED`: cleared; exact approvals are recorded.
- `FIRST_FRAME_MISSING`: the image exists and is accepted in the plan. The read-only summary’s `firstFrameStatus=MISSING` inconsistency is recorded above.
- `RENDER_MODE_UNSUPPORTED`: cleared; model schema and local CLI support single-start-frame image2video.
- `CREATIVE_VALIDATION_FAILED`: **active**; record 25 is `BLOCKED` with 10 deterministic/source-derived failed gates. Record 24's GOAL_001 `SERVICE_ERROR` was an invalid creative verdict; offline replay now reports GOAL_001 as `UNKNOWN` without provider dispatch.
- `INTEGRATION_DEFECT`: **partly repaired** (JSONB persistence and image upload limit); plan summary still reports `MISSING` despite its accepted binding.
- Provider-call policy: the historical record 24 run made at least one OpenAI semantic validation call. Offline safety was then repaired and real linked replay record 25 completed with zero provider requests. Details and test results: [KIKO_OFFLINE_VALIDATION_RECOVERY.md](KIKO_OFFLINE_VALIDATION_RECOVERY.md).
- Render calls: **0**. No controlled render command is issued because the production preflight did not pass.

The existing Compose services were started to use the platform registries and remain running. No Docker resources were cleaned up.

