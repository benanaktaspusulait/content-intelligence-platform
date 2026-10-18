# Pompom Hills Canonical Character Identity Correction

**Correction code:** `CANONICAL_CHARACTER_CORRECTION_PIP_TO_MIMI`  
**Disposition:** `NOT_CLAIMED` — local prospective source revision only; not approved, persisted to production, or activated.  
**Historical source:** V6.3 Pip sticky-note source SHA-256 `ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d`.  
**New local revision ID:** `LOCAL-CANONICAL-CHARACTER-CORRECTION-PIP-TO-MIMI-V1`  
**New prompt-body SHA-256 (excluding terminal newline):** `6e51187223efc4c5f8e6b067fa3ab627aba583d6db4e1b33d0d1bf4665d18c3a`  
**Revision artifact file SHA-256 (including terminal newline):** `1e19d2abcb1ee7c6c82f3c1920ddf58fb5c7b025a0280869c0a817fd57dc2354`

## Finding

The frozen V6.3 source names Pip. The active character registry contains Mimi (`00000000-0000-0000-0000-000000000003`) as the canonical character; the owner identifies Mimi as the light-blue rabbit. The historical source and V6.3 review response remain unchanged and are still evidence about that original Pip text. The changed source is a separate, unapproved local revision.

## Corrected source revision

See [source-revision-mimi-sticky-note-v1.txt](canonical-character-correction/source-revision-mimi-sticky-note-v1.txt). The only narrative change is replacing Pip's identity with Mimi and using the owner-supplied descriptor “light-blue rabbit.” The events, order, cabinet, sticky-note counts (1→2→4→8), transfer/multiplication rule, overwhelmed state, mirror reaction, sneeze release, relief, and messy cabinet are preserved. No new event, object, action, rule, timing, or ending was added.

## Root cause and guardrail

The previous workflow allowed a story to be imported without a required canonical character selection. Provider generation passed a display name without an authoritative registry ID, and source review evaluated fidelity to the submitted text without separately checking that the protagonist was registered. That made source fidelity insufficient to establish canonical identity.

The local correction adds these separate checks:

- New story requests require an active registry ID and matching name before provider dispatch. The selected character ID, registry record, and active registry are sent to the story generator.
- The model response must bind each candidate to the selected protagonist ID and use its registered name. Unregistered named-character declarations are rejected. The result reports `REGISTRY_PASS` separately from story/source-fidelity assessment.
- Detailed-story import, explicit approval, operator revisions, autonomous evolution start/approval, and prompt handoff revalidate identity against the active registry. Missing identity fails closed for new operations; it does not rewrite any existing record.
- The Creative Studio requires a registered character selection before generation.

This registry check confirms name/ID binding only. It does not prove approved visual likeness, source fidelity, creative quality, render safety, or audience performance. Those remain independent checks.

## Files changed

- `intelligence/backend/src/main/java/com/pompomhills/intelligence/character/CanonicalCharacterIdentity.java` — active registry lookup and story identity validation.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/IdeaDraftService.java` — canonical identity on detailed-story import.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/WorkflowService.java` — identity binding before dispatch and checks for approval/revision/evolution.
- `intelligence/backend/src/main/java/com/pompomhills/intelligence/workflow/StoryEvolutionService.java` — identity propagated through story evolution and prompt handoff.
- `intelligence/ml-service/app/workflow/creative_roles.py` — model contract and deterministic registry validation.
- `intelligence/frontend/src/app/pages/creative-studio.page.ts` — required registered character selection.
- `intelligence/backend/src/test/java/com/pompomhills/intelligence/workflow/IdeaDraftPostgresTest.java`, `intelligence/ml-service/tests/test_creative_roles.py`, and `intelligence/frontend/src/app/pages/creative-studio.page.spec.ts` — focused deterministic tests.
- [POST_V6_3_NEW_CONCEPT_RESEARCH.md](../POST_V6_3_NEW_CONCEPT_RESEARCH.md) — the new concepts use canonical registry IDs for Mimi, Kiko, and Luca; unknown visual references remain marked `UNKNOWN`. The concept structures are unchanged.
- [source-revision-mimi-sticky-note-v1.txt](canonical-character-correction/source-revision-mimi-sticky-note-v1.txt) — separate local, unapproved source revision.

## Verification

- ML story contract and creative-role tests: **42 passed**; no real provider dispatch.
- Backend `IdeaDraftPostgresTest`: **10 passed** against a disposable Testcontainers PostgreSQL instance (including rejection of the noncanonical Pip import and acceptance of a Mimi-bound story).
- Backend Maven compile: **passed**.
- Creative Studio focused unit test: **28 passed**.
- Concept document structure: **3 concepts**, each with 5 timed beats and the required character, object, rule, frame-zero, production-risk, and differentiation sections.
- `git diff --check`: **passed**.

No deployment, production database write, provider call, image/video generation, approval, or publication was performed. Current application deployment has therefore **not** been updated by these local changes.

## Historical integrity and remaining gates

V6.1–V6.3 files, provider evidence, receipts, token/cost records, source/candidate hashes, assessment, and `OWNER_DECISION: PENDING` were not modified. This correction does not approve the Mimi text or either new concept. Before production use, the local changes must be deployed through the normal owner workflow, and an authorized operator must separately create/approve the source revision and bind verified character reference evidence. Canonical identity validation is not a visual-reference pass or render authorization.
