# PRE_RENDER_V2_CHECK — Mimi rising dough ridge

**Status: PRE_RENDER_V2_CHECK**  
**Decision: STOP BEFORE RENDER**  
**Required stop code: `RENDER_BLOCKED_CANONICAL_REFERENCE_UNAVAILABLE`**

V2 prompt and its four minimal repairs are prepared, but no video was generated. The mandatory project-approved visual reference could not be verified: the production-library sheet exists, but its recorded provenance says `approvalStatus=UNREVIEWED` and `canonicalApproval=NOT_APPROVED`. The task explicitly requires stopping before render if an approved Mimi reference is unavailable.

## Candidate reference

- Path: `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/mimi.png`
- SHA-256: `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57`
- Dimensions: 1536×1024
- Role: Pompom Hills Mimi v2.1 character sheet with turnarounds, expressions, proportions and palette; matches `01-CHARACTERS/02-mimi.md`.
- Approval: **not verified / conflict**. `mimi-reference-clean-crop-provenance.json` records the source image as `UNREVIEWED`, the derivative as `NOT_APPROVED`, and requires owner review. Therefore this task's approval gate does not pass on current evidence.

## Reference-mode and duration checks

- Seedance 2.0 Mini model schema includes `element2video` with required `visualReferences` and `generateAudio`; the supported schema allows integer duration 4–15s and aspect ratio 9:16.
- The project's OpenArt CLI video workflow exposes text-to-video and start-frame image-to-video only; it does not expose element2video or identity references. The model form confirms provider capability, but the current project CLI does not supply the accepted character reference through it.
- 14s duration is supported and within the 15s hard maximum; audio can be disabled in the model schema.

## V2 prompt

Exact prepared prompt: [`V2_PRODUCTION_PROMPT.md`](V2_PRODUCTION_PROMPT.md)  
SHA-256: `fcc442d53a2ca9d823a924fa4582fc3a3363af14aa9fee39cde1df0092ad5d56`

It preserves the accepted four-beat architecture and adds only the four observed repairs: 14.0s target, canonical Mimi identity lock, explicit barrel-on-top/ridge-below opening geometry, and static dough during every off-contact interval.

## V1 integrity and render count

- Existing V1 prompt hash remains `9b185670aa97e838975c2f7f717c8b5b947d6b43414dce6d707c887409f03f93`.
- Existing V1 video hash remains `4634143f846a35cf66b1ec33596060407ca54d8fdf9c2daacdcc9650ef088fdf`.
- V1 evidence files checked against its saved manifest: 10; changed: 0. V1 was not overwritten.
- V2 render calls: **0**. Semantic provider calls: **0**. No credits were spent on V2.

## Local Docker cleanup authorized by the user

There were no running containers. Removed all six tagged images for `pompom-website-app`, `pompom-runtime`, and `pompom-portal-candidate`. Verification found no running site container and no matching image tag. The `intelligence_postgres-data` volume belongs to the separate `intelligence` Compose project and was preserved; anonymous volumes had no attributable project labels and were preserved.

## Required next gate

Do not render until the project supplies a reference with verified approval status and the V2 render path can submit it as Seedance `element2video.visualReferences`. No render, retry, Docker source deletion, or story change was performed.
