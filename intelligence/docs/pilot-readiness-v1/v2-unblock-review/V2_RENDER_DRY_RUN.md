# V2 Render Dry-Run

Status: **BLOCKED BEFORE PROVIDER REQUEST CONSTRUCTION**

This dry-run used the exact accepted local V2 prompt and preserved local model/CLI capability evidence. It did not execute `openart generate`, `upload`, `model form`, an API request, or a render. Provider calls: **0**. Render calls: **0**.

## Candidate

- Prompt: `/Users/benanaktas/project/video/content-intelligence-platform/intelligence/docs/semantic-two-stage-v1-phase-b-run-001/human-creative-review-v1/production-render-v2/V2_PRODUCTION_PROMPT.md`
- Prompt SHA-256: `fcc442d53a2ca9d823a924fa4582fc3a3363af14aa9fee39cde1df0092ad5d56`
- Model: `byte-plus-seedance-2-mini`
- Intended API mode: `element2video` (stored model form says `visualReferences` exists)
- Desired duration: 14 seconds; hard measured video stream maximum: 15 seconds
- Aspect: 9:16; resolution target: 720p; audio: disabled in prompt intent

## Reference bindings

| Binding | Intended source | Status | Request inclusion |
|---|---|---|---|
| Mimi identity reference | `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/mimi.png`, SHA-256 `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57` | UNREVIEWED / NOT_APPROVED | Not sent; approval gate blocks |
| V2 exact scene first frame | No approved asset found | MISSING | Not sent; no substitution made |

## Sanitized request plan

```json
{
  "model": "byte-plus-seedance-2-mini",
  "mode": "element2video",
  "promptPath": "intelligence/docs/semantic-two-stage-v1-phase-b-run-001/human-creative-review-v1/production-render-v2/V2_PRODUCTION_PROMPT.md",
  "promptSha256": "fcc442d53a2ca9d823a924fa4582fc3a3363af14aa9fee39cde1df0092ad5d56",
  "durationSeconds": 14,
  "aspectRatio": "9:16",
  "resolution": "720p",
  "generateAudio": false,
  "visualReferences": "BLOCKED: candidate unapproved; exact item payload shape not preserved in local form evidence",
  "firstFrame": "BLOCKED: no approved V2 scene frame; element2video frame semantics unverified",
  "wouldUseCurrentCli": false,
  "providerCall": false,
  "renderCall": false
}
```

This is a sanitized **blocked plan**, not a claim that a complete executable provider payload was constructed. The current CLI only supports text2video and image2video; substituting `--image` would make the chosen image the start frame and cannot serve as a separate identity reference. Thus the required proof that Mimi is present in a constructed outgoing request is intentionally **not met**; no image was silently omitted from an otherwise executable request.

Dry-run result: `BLOCKED_CHARACTER_REFERENCE`, `BLOCKED_FIRST_FRAME`, `BLOCKED_ELEMENT2VIDEO_CLI_CONTRACT`, `BLOCKED_DURATION_GUARANTEE`, `BLOCKED_AUDIO_CONTROL`.

## Verification results

- Creative-render-service adapter, resolver and orchestrator tests: **25 passed, 0 failed**. These used the existing local fake CLI and do not contact OpenArt. The adapter tests prove image references enter image generation and the start frame enters video image2video separately.
- OpenArt Python wrapper unit tests: **12 passed, 0 failed** under the repository ML-service virtual environment. A first attempt with system Python failed collection because Pydantic was absent; no project or dependency files were changed.
- Docker site config check: `docker compose config --quiet` passed and listed service `app`; no container or image was built or started.
- New code changed: **none**. There is no published CLI flag for the required element2video request, so an implementation here would require guessing a provider argument or adding a second client.
