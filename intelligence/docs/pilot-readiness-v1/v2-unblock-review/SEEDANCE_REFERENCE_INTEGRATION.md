# Seedance Reference Integration Assessment

Date: 2026-11-02. No provider generation or render request was made.

## Evidence inspected

- Installed OpenArt CLI: `openart 0.1.1`, commit `85fa0ad`, built 2026-08-31.
- Current local `openart generate video --help` exposes prompt, `--model`, `--image`, `--duration`, `--aspect-ratio`, `--resolution`, `--async`, and output. Its contract says `--image` is the **start-frame image** and switches the request to `image2video`. It has no `element2video` selector or separate character-reference flag.
- Existing Java adapter `CliRealOpenArtAdapter.buildVideoGenerateCommand()` constructs `openart generate video ... --image <firstFrameImageId>` and duration/aspect/resolution. It cannot transmit a separate character reference or `visualReferences` field.
- Existing `OpenArtImageRequest` does transmit all supplied character references as repeated `--image` options to image generation. `RenderAttemptOrchestrator` uses those when it generates a first-frame image, then passes that image separately to the video request. This is two different inputs/stages; it does not prove that Seedance `element2video` accepts the V2 scene frame and Mimi identity reference simultaneously, and it does not preserve a separate character reference on every video frame.
- The stored model-form inspection in the prior V2 preflight says model `byte-plus-seedance-2-mini`, mode `element2video`, has a `visualReferences` schema field; it also records `duration`, `aspectRatio`, `resolution`, `generateAudio`, and `seed`. Its schema accepts integer duration 4–15 and 9:16. The saved preflight did not preserve the `visualReferences` value shape, item type/limits, image dimension limits, nor an explicit first-frame field for element2video. I did not make a live model-form/API request to refresh that schema because this task requires zero provider calls.
- OpenArt's current product page describes Seedance 2.0 as accepting image/video/audio references and up to 9 images. This is high-level product capability; it is not a CLI flag contract or proof that a reference image is the generated first frame. [OpenArt Seedance 2.0](https://openart.ai/ai-model/seedance-2-0/)

## Input capability matrix

| Requirement | Provider/model evidence | Current project CLI | Result |
|---|---|---|---|
| Character identity visual references | `element2video` schema has `visualReferences`; OpenArt describes image reference support. It does not establish a hard identity guarantee. | No separate reference field on video generation. Character refs can enter first-frame image generation in another step. | API-level visual reference capability; not executable by current CLI. |
| First-frame conditioning | `image2video` mode is expressly defined by CLI `--image` as the start frame. | Supported as `--image <path-or-url>`; this binds one image as the opening frame. | Supported, but V2 scene-specific approved frame is missing. |
| Identity reference and exact first frame together | Stored schema evidence does not establish whether `visualReferences` can carry the first frame, whether a separate first-frame input exists, or precedence. | No two-input video command; only the start frame is passed. | **Not proven / unsupported in current CLI.** Do not equate these modes. |
| Format and dimensions | Project's character-reference import API validates PNG/JPEG/WebP, max 15 MB and max 8192×8192. This is local import validation, not OpenArt provider limits. | CLI uploads local `--image` and probes dimensions for strict image2video models. | Mimi source passes local file bounds (PNG, 1.90 MB, 1536×1024). Provider-specific element2video image limits remain unknown. |
| Duration | Stored model form accepts integer 4–15 seconds for element2video. | CLI accepts model-specific `--duration` integer. | 14 is a supported request value; it is not an output-duration guarantee. Prior requested 15s output measured 15.041667s video stream. |
| Audio | Stored form includes `generateAudio`; V2 needs silent output. | CLI help has no audio control flag. | CLI cannot request audio off in this path. |

## Integration decision

**`BLOCKED_ELEMENT2VIDEO_CLI_CONTRACT` — no CLI extension was added.** The installed binary does not expose the mode or a separate reference-image flag. Adding invented switches would be an unverified API client; calling `--image` with the character sheet would incorrectly treat a character sheet as the V2 scene's first frame. The Java adapter has the same published CLI contract and cannot implement this through existing supported flags.

The least invasive next technical step is to obtain/upgrade to an OpenArt CLI release that documents `element2video` plus its reference payload, or an official documented CLI plug-in mechanism. Then add that exact option to the existing adapter and fixture tests. Do not handcraft a private HTTP client or silently drop references. Until the public request schema is captured and request construction is proven with a mock, V2 must stop before submission.

## Duration and frame-zero limits

14 seconds is a valid request setting under the stored schema, but a provider duration parameter cannot guarantee the final stream is ≤15 seconds. The only measured sample requested at 15 seconds yielded a 15.041667-second video stream. Enforce post-generation measured duration as a rejection gate and establish a measured request margin before calling the setup duration-compatible. No trim-after-render plan is proposed.

The V2 prompt's frame-zero state (Mimi pressing a pin against one raised dough ridge) requires an actual scene image if the chosen mode is image2video. The canonical identity sheet is not that frame. No approved scene frame exists, and none was generated here. If `element2video` references do not guarantee first-frame composition, a separately created and approved first-frame asset will still be needed.

## Relevant offline tests

The current integration fixture tests prove two distinct behaviors: supplied character reference paths are included in the mock image-generation CLI command, and a supplied start-frame path is included as `--image` on the mock video CLI command. They do not prove a single element2video request can carry both; that remains unsupported by the installed command contract. Focused results are recorded in `V2_RENDER_DRY_RUN.md`.
