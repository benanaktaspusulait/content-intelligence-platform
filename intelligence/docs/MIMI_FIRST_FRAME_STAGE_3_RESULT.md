# Mimi First Frame Stage 3 — Result

**Outcome: `ONE_IMAGE_GENERATED`; visual gate: `FIRST_FRAME_VISUAL_FAIL`**

| Item | Current status |
|---|---|
| Mimi identity | Registry ID `00000000-0000-0000-0000-000000000003`; active, registry status `UNTESTED` |
| Original reference | `library/01-CHARACTERS/drawings/mimi.png`, SHA-256 `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57`, `UNREVIEWED` |
| Clean crop | [Owner-approved-for-this-test crop](mimi-sticky-first-frame/mimi-reference-clean-crop-owner-review.png), SHA-256 `80e0579ac5979be010da5c7250debbe9e74e84b37661d7a2213f24e055e49f14`; not registered as a canonical app reference |
| Character approval | Owner approved this exact derivative for this one image test; no application-level reference record or canonical binding was created |
| Opening-change approval | Owner approved starting mid-peel at the visible 1→2 multiplication |
| One-image authorization | Owner authorized exactly one OpenAI image-edit call, no retry/fallback, maximum USD $0.20; no video authorization |
| OpenAI model / settings | `gpt-image-2`, medium, 9:16 (`1024x1792`), `n=1`, 120-second timeout, retries disabled |
| Provider dispatch count | **1**; request `req_256b9383de494fa8ad863a32d20b8c18` |
| Generated image / preview | [Generated first frame](mimi-sticky-first-frame/mimi-first-frame-openai-gpt-image-2.png), SHA-256 `3bac6884e4783c847dd47963a1266ddeb98cf70a73fcd4c85ec4a551b6cd0194` · [480px preview](mimi-sticky-first-frame/mimi-first-frame-openai-gpt-image-2-480px.jpg) |
| Usage / estimated charge | 500 text input + 400 image input + 1,243 image output tokens; calculated USD **$0.021495** at published GPT Image 2 token rates. Below the authorized $0.20 cap. |
| Pixel findings | `FIRST_FRAME_VISUAL_FAIL` at native size and 480px phone preview |

The exact reference candidate remains a local derivative approved for this single test, not an application-level canonical reference. No production reference record or prompt binding was created. The first frame was generated through OpenAI GPT Image 2 `images.edit`, using the complete Stage 2 prompt and exact crop. OpenArt was not used; it remains reserved for later image-to-video animation.

The deployed helper currently builds a shortened image prompt from the saved first beat and requests a URL response, while GPT Image models return image bytes by default and do not support URL output. For this authorized one-off, the existing OpenAI SDK client used a 120-second timeout and zero retries; the full Stage 2 prompt was sent directly to `images.edit` and the returned PNG bytes were saved locally. The helper itself was not changed and must not be used for another image call until its prompt and response handling match this flow.

## Owner decisions and one-image result

The owner approved the exact reference derivative for this single test, approved the proposed 1→2 opening, and authorized one `gpt-image-2` image-edit call with a USD $0.20 ceiling. No prompt version was approved, no canonical reference record was created, and no video generation was authorized.

The generated frame preserves a recognizable blue-rabbit likeness and shows Mimi, two yellow notes, and the cabinet. At native size and 480px, however, it reads as two ordinary adjacent/overlapping notes near Mimi's paw. It does not clearly show one intact source note producing a second from a visible shared peel contact; part of the left note is obscured by the paw. The static causal relationship is not established: `FIRST_FRAME_VISUAL_FAIL`. No second image was generated; the authorized one-call limit is exhausted. Do not proceed to video with this frame.

The calculated charge uses 500 text input tokens at $2.50/M, 400 image input tokens at $4/M, and 1,243 image output tokens at $15/M, totaling $0.021495. See [OpenAI API pricing](https://platform.openai.com/pricing) and the [image-generation cost guide](https://developers.openai.com/api/docs/guides/image-generation/index.html?gallery=open&galleryItem=neon).

No source story, historical V6.3 evidence, production database, prompt version, deployment, or grading state was modified. Exactly one image was generated; no video was generated.
