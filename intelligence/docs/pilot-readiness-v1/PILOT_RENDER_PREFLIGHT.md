# Pilot Render Preflight — Mimi / Flat-Pack Dough

Decision: **STOP BEFORE RENDER — PILOT_BLOCKED**

| Check | Evidence | Result |
|---|---|---|
| Canonical reference | `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/mimi.png`; SHA-256 `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57`; 1536×1024 | File exists, but approval provenance is UNREVIEWED / NOT_APPROVED: BLOCKED |
| First frame | Exact rolling-pin frame-zero description is in V2 prompt; no approved matching frame image found | Missing: BLOCKED |
| Model | `byte-plus-seedance-2-mini` | Previously rendered once; actual V1 failure fixture retained |
| Input mode | Provider schema previously inspected: `element2video` supports `visualReferences`; project CLI currently has no `element2video` support. Existing project text2video/image2video paths are insufficient proof of character reference | BLOCKED |
| Requested duration | V2 target 14.0s; schema accepts integer 4–15 | Request value supported; final ≤15s not guaranteed |
| Measured duration evidence | Historical requested 15s; container 15.104s; video stream 15.041667s | Hard limit failed in observed render |
| Aspect/resolution | Historical render output 720×1280 (9:16). Provider form lists 9:16 and 480p/720p | Supported in inspected form; no output guarantee beyond prior fixture |
| Audio | Prior QA observed AAC stream and did not accept audio content. V2 prompt requests silent visual and audio generation off; current supported request mode cannot carry the needed identity reference anyway | Must verify response after render; not a pre-render guarantee |
| Cost metadata | Historical render observed 600 credits; no account lookup or provider call this task | Cost evidence is historical only |
| Render count this task | 0 | Verified from task execution; no render submitted |

The existing V1 MP4 is the only rendered evidence. It is not an approved first-frame asset. Its SHA-256 is `4634143f846a35cf66b1ec33596060407ca54d8fdf9c2daacdcc9650ef088fdf`.

Next authorized render must remain disabled until reference approval, first-frame approval, reference-capable project adapter and a duration safety policy are evidenced. Do not fall back to text-to-video.
