# Pompom Content Intelligence V1 — Local Pilot Validation

Date: 2026-11-02
Overall result: **PILOT_BLOCKED**

## Scope and execution record

- Prompt discovery scanned the configured repository evidence directory and the configured mounted social-reels library; the bounded inventory contains 814 named source files, 807 unique contents, and 7 exact-content duplicate copies. This is not a count of every file under the video workspace.
- Primary: `mimi-rolling-pin-dough-wall`, imported from the existing structured Phase B output at `intelligence/docs/semantic-two-stage-v1-phase-b-run-001/complete-story.json`.
- The existing Phase B story output, opening gate, canonical rule audit, accepted production prompt, pre-render V2 preflight and the sole historical render/post-render QA were inspected and re-used. No source/canon file was changed. The Phase B output declares 16 seconds, so the separate V2 production prompt targets 14 seconds while preserving the story architecture.
- The already stored Phase B story is a real run and real evidence. This turn did not replay semantic generation or claim a new validator run for stored results.
- Provider calls this task: **0**. Render calls this task: **0**. Existing render fixture count: **1**.

## Candidate selection

1. **Primary — Mimi / Flat-Pack Dough** (`mimi-rolling-pin-dough-wall`). Structured concept plus four-beat story, explicit goal/object/rule/trigger/frame-zero, direct saved canonical audit, existing production prompt, and failed render QA fixture.
2. **Comparison — Kiko and the Late Reflection** (`POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/not-generated/KIKO_AND_THE_LATE_REFLECTION/kiko-late-reflection-production.md`). Five timed beats and explicit character/world references; draft status; its 15s plan is not duration-safe because the renderer has previously exceeded its requested duration.
3. **Comparison — Luca's Shadow Takes a Shortcut** (`POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/not-generated/LUCAS_SHADOW_TAKES_A_SHORTCUT/lucas-shadow-shortcut-production.md`). Existing production plan; narrative import compatibility and complete timed evidence were not demonstrated in the available local validation record.

The comparison candidates remain **LOCAL_EVIDENCE_INCOMPLETE** for end-to-end semantic evaluation. Their text is preserved and no missing fields were inferred.

## Primary validation matrix

| Component | Result | Evidence and scope |
|---|---|---|
| Local source import | PASS | Existing structured JSON loaded from the source path; exact original retained. Existing Phase B and V2 prompts remain separate derived artifacts. |
| Opening evaluation | PASS (stored gate only) | Existing accepted Phase A opening seed/gate; this is not a newly replayed opening score. |
| Premise naturalness | INSUFFICIENT_EVIDENCE | No standalone current imported-candidate result in this workflow record. |
| Premise admission | INSUFFICIENT_EVIDENCE | Phase A opening acceptance is not equivalent to the separate premise admission component. |
| Beat grammar | INSUFFICIENT_EVIDENCE | Four explicit beats exist; no exact current beat-grammar evaluator output was bound to the local-import run. |
| SHORT_FORM_ENGINE | INSUFFICIENT_EVIDENCE | No exact current SFE output bound to this local-import run; no score inferred. |
| Creative shape | INSUFFICIENT_EVIDENCE | No separately bound current shape result. |
| Historical territory | INSUFFICIENT_EVIDENCE | No comparable historical-territory result bound to this source. |
| Ranking | NOT_APPLICABLE | One pilot source is being checked, not ranked against a generated batch. |
| Production readiness | FAIL | Pre-render check stops before render on approved-character-reference provenance; first-frame asset is not approved/available for this exact story; current project CLI cannot execute the reference-capable element2video mode. |
| Canonical rule audit | PASS (stored audit) | Existing audit reports all four beats consistent with the impossible rule and clear payoff orientation. This validates text evidence only. |
| Human review status | INSUFFICIENT_EVIDENCE | Existing V1 human creative review found render defects; V2 prompt has not received fresh human approval. |

No missing evaluation was converted to PASS. The V2 prepared production prompt is at `../semantic-two-stage-v1-phase-b-run-001/human-creative-review-v1/production-render-v2/V2_PRODUCTION_PROMPT.md`.

## Existing failed-render regression evidence

The stored post-render QA consumes the actual V1 MP4 and records: container duration 15.104s; video-stream duration 15.041667s; wrong character (human child rather than Mimi); first-frame geometry failure; broken contact causality including off-contact dough growth; geometry discontinuity; weak/repeated beats and dead time; generated AAC audio not accepted. Payoff is visually present but late. This is a direct regression fixture and demonstrates post-render QA evidence is connected to a generated asset. Automated rules are combined with human visual review; the visual findings are not represented as wholly machine-verifiable.

Fixture: `../semantic-two-stage-v1-phase-b-run-001/human-creative-review-v1/production-render-v1/rendered-video.mp4`
QA record: `../semantic-two-stage-v1-phase-b-run-001/human-creative-review-v1/production-render-v1/POST_RENDER_QA.json`

## Readiness blockers

- `BLOCKED_CHARACTER_REFERENCE`: canonical Mimi sheet exists at `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/mimi.png` (1536×1024, SHA-256 `7ad3d0042965c53ae20c67c0242d49cec2d3cf43706915d715b4fadec3c59f57`), but provenance says UNREVIEWED / NOT_APPROVED. File presence does not satisfy approval.
- `BLOCKED_FIRST_FRAME`: an approved frame-zero image for this rolling-pin scene is missing. The existing V1 first frame is the failed generated result, not an approved input. The unrelated sticky-note first-frame images are not substitutes.
- `BLOCKED_RENDER_MODE`: the Seedance schema supports `visualReferences` for `element2video`, but the project OpenArt CLI integration does not support that mode. Text-to-video cannot guarantee character identity.
- `BLOCKED_DURATION_GUARANTEE`: duration request supports integer values from 4–15, but the one actual 15s request emitted a 15.041667s video stream. A 14s request has no observed output bound proving ≤15s.

No creative revision was silently accepted. Existing creative/production repair tickets and minimum owner actions are in `PILOT_FIXES.md`.

## Test and regression results

- Focused ML component/pilot regression: **261 passed** (two-stage Phase B, opening calibration, premise admission, beat grammar, SFE, creative shape, ranking and production selection).
- Full ML-service suite: **3,487 passed, 36 failed, 2 skipped** in 228.79s. This exactly matches the user-provided baseline count of 36 failures and 2 skips; no new test cases were added. The previous baseline's per-test failure list was not present as a comparable artifact, so identity-level equivalence of those failures cannot be claimed from counts alone.
- Full creative-render-service Maven suite (including publisher-contract dependency): **457 tests; 445 passed, 2 errors, 0 skipped**. Both errors are in `RenderJobIdempotencyPostgresTest` and reject requests without required source-bound post-family admission (`IllegalArgumentException`); no render was issued by these tests.
- Focused post-render QA suite: **16 passed** (`PostRenderAssessmentAggregatorTest`, `VideoQcGateTest`, `PostRenderRuleEngineTest`).
- Initial system-Python pytest attempt failed during collection because FastAPI/Pydantic dependencies were absent from system Python; rerun under the service `.venv` completed.

Tests establish software regression state only; they do not override the reference, first-frame, render-mode or duration blockers.
