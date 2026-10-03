# Part 01 Completion Roadmap — Prompt Quality Engine + Render Authorization

**Status file. Read this first in any new session before touching Part 01 code.**

Source task: complete `AUDIT_PART_01_PROMPT_QUALITY_ENGINE.md` (repo root) per the
19-phase specification given by the user on 2026-10-03. Do not redesign the platform;
fix and complete the existing architecture.

**Branch policy: work directly on `master`. No worktrees, no feature branches — single
user, single active session at a time. Always `git pull`/continue from current `master`
HEAD at the start of a session.**

---

## 0. Phase 0 audit verification (done)

Verified against actual code, not just the audit doc. All P0/P1 findings in
`AUDIT_PART_01_PROMPT_QUALITY_ENGINE.md` confirmed true by direct inspection:

- `IntelligenceQualityValidationService.java` never populates semanticProvider/
  semanticModelVersion/producibilityValidatorVersion/independentRevalidationId (confirmed,
  code comment admits it's deferred to a "later slice").
- `V6__quality_validations.sql`'s status CHECK constraint is still
  `RENDER_READY/NEEDS_REVISION/BLOCKED` only — no `SERVICE_ERROR`. `V30` migration added
  evidence columns but did not touch this constraint.
- All 4 LLM providers (`openai_provider.py`, `claude_provider.py`, confirmed same pattern
  expected in gemini/ollama) do `del image` in `complete()` — vision input is silently
  discarded. `character_verifier.py` judges an image the model never saw.
- `api/quality.py`'s `QualityReportResponse` only exposes `failed_rules`; no
  `unknown_rules`/`not_applicable_rules`/`service_errors` fields exist on the response model.
  `RuleEvaluationResponse.result` is a bare `bool`, collapsing the 5-state `RuleOutcome` enum.
- `iteration_loop.py`'s retry loop `continue`s past a failed fix but never removes it from
  `current_enhanced.priority_fixes`, so the same unfixable top fix is retried every iteration.
- Angular `app.routes.ts` has no `quality` route. `QualityValidatorComponent` files exist
  under `pages/quality-validator/` but are orphaned (not imported/routed anywhere).

**Positive finding (reduces scope):** `ValidationEvidenceService.java` (Spring) and
`ValidationEvidencePolicy.java` (creative-render-service) are already well-built —
fail-closed, recompute status from field completeness on every read (never trust stored
status column), and `independent_revalidation_id` has a DB-level unique constraint
preventing self-certification. **These two files should need little to no change.** The
gap is almost entirely in what populates the evidence fields (Spring validation service),
not in how the evidence is consumed/enforced (render policy).

No contradiction found between the spec and the actual schema/classes.

---

## 1. Decomposition into sub-plans

Per `writing-plans` skill's scope-check rule (a spec touching multiple independent
subsystems must be split before planning), this work is split into sub-plans, each
independently plannable/testable/committable. **Work them in order — later plans assume
earlier plans' deliverables exist.** (Originally 8 sub-plans A–H; Plan C was further split
into C0–C3 mid-session once investigation showed the single "Plan C" would have been
either incomplete or quietly dishonest — see the note below the dependency list.)

| # | Plan name | Spec phases covered | Codebase(s) | Status |
|---|---|---|---|---|
| A | Python outcome model + API contract completion | 1, 5, 6, 13 | ml-service, backend | ✅ Done (commit `5a9ffd0`, see §4 for details) |
| B | Vision QA fix (image passthrough + character verifier) | 7 | ml-service | ⬜ Not started |
| C0 | Semantic evaluation provenance threading | 3 (prerequisite) | ml-service | 🟨 Partial (flat per-report field landed via a parallel session, commit `c2dd149`; per-rule granularity + zero-semantic-checks correctness still missing — see `plans/PLAN_C0_SEMANTIC_PROVENANCE.md` §5-6) |
| C1 | Evidence contract cleanup (remove `producibilityValidatorVersion`) | 3 (prerequisite) | backend | ✅ Done (commit `ab29da1`) |
| C2 | Independent revalidation + SERVICE_ERROR persistence | 3, 4 | backend | ✅ Substantially done (landed via a parallel session, commits `943e067`/`c2dd149`; see `plans/PLAN_C0_SEMANTIC_PROVENANCE.md` §5 "Bonus finding") |
| C3 | End-to-end RENDER_READY authorization tests | 3, 4, 18 (partial) | backend, ml-service | ⬜ Not started — now the highest-value next step per the reconciliation above |
| D | Render authorization stage model + evidence invalidation | 2, 15 | ml-service, backend, creative-render-service | ⬜ Not started |
| E | Auto-fix repair + rule metadata single-source + recommendations | 8, 9, 10, 11 | ml-service | ⬜ Not started |
| F | Angular quality screen reconnection | 14 | frontend | ⬜ Not started |
| G | Two creative rule gaps (over-constraint, portfolio duplication) | 12 | ml-service (new RULESET_1.4 only if needed) | ⬜ Not started |
| H | End-to-end integration tests + final completion report | 18, 19 | all | ⬜ Not started |

Phases 16 (defer feedback/learning) and 17 (no variant-identity heuristics) are **standing
constraints carried into every plan above**, not separate implementation work. Any plan
touching code adjacent to feedback modules or variant/folder identity must explicitly
preserve the deferred/non-production marking — never quietly wire them in.

### Dependency notes
- **C0 depends on A** conceptually (same outcome-model vocabulary, same ml-service files
  Plan A already touched) but is otherwise self-contained.
- **C1 depends on nothing new** — it only removes a requirement, doesn't need C0's data.
- **C2 depends on C0 and C1 both being done** — C2's `IntelligenceQualityValidationService`
  changes need C0's real `semanticProvider`/`semanticModelVersion` data to populate, and
  C1's removal of `producibilityValidatorVersion` from the required-evidence check so C2's
  work can actually reach `RENDER_READY` without inventing data for a field C1 retired.
- **C3 depends on C0, C1, and C2 all being done** — it's the end-to-end proof that the
  whole chain works together.
- **D depends on A and C2** (needs the stage model concept from A's rule metadata and the
  evidence fields C2 populates).
- **E depends on A** (rule metadata single-source needs the outcome model finalized).
- **F depends on A** (Angular models need the finalized API contract shape).
- **H depends on A, B, C0–C3, D, E, F, G all being done.**
- **B and G are independent of everything else** — can be done in any order, even in
  parallel with A if desired, but default sequencing below does them after A/C*/D since they
  are lower architectural risk.

Suggested execution order: **A → C0 → C1 → C2 → C3 → D → E → B → F → G → H**. (B and G
moved later only because they're self-contained and lower-risk to slot in
opportunistically; reorder freely if it's more convenient to do B or G earlier.)

**Why Plan C was split into C0-C3 (decided 2026-10-03, mid-session, before any Plan C
code was written):** investigating Plan C's file list before writing its plan surfaced
two problems that would have made the original single "Plan C" either incomplete or
quietly dishonest:

1. `semanticProvider`/`semanticModelVersion` — the evidence fields `ValidationEvidenceService`
   already requires for `RENDER_READY` — have no data path at all today. Each LLM provider
   object (`OpenAIProvider`, `ClaudeProvider`, `GeminiProvider`, `OllamaProvider`) carries a
   `self.model` attribute, but nothing between the 8 semantic-check call sites in
   `rule_engine.py` and the API response ever captures or forwards it. Building the
   independent-revalidation chain (original "Plan C") without this would leave every
   validation permanently stuck at `NEEDS_REVISION` regardless of how correct the
   revalidation logic is — `ValidationEvidenceService.resolveStatus` requires
   `semanticProvider`/`semanticModelVersion` non-null for `RENDER_READY`, and nothing would
   ever populate them. This is now **Plan C0**, done first, in `ml-service` (not `backend`).
2. `producibilityValidatorVersion` assumes a separate "producibility validator" runtime
   exists. It does not: `ai_producibility` is a family of ordinary deterministic rules in
   `RULESET_1.3.yaml` (`PRODUCIBILITY_001/002/003`), already fully described by
   `deterministicRulesetVersion`. Populating `producibilityValidatorVersion` with anything
   (including copying `deterministicRulesetVersion` into it) would fabricate a second
   version axis for something that is not architecturally separate. **Plan C1** removes
   this field from the required-evidence contract (deprecate the column, stop requiring it
   for `RENDER_READY`) rather than inventing data to satisfy it.

**C0's target data model** (decided with the user, not to be redesigned without
re-confirming): a `SemanticEvaluationProvenance` record per semantic-check-backed rule
evaluation — `provider`, `model`, `semantic_check_version`, and which `rule_id`s it backed
— not a single flat `semanticProvider`/`semanticModelVersion` pair hardcoded at the report
level. Different rules may use different providers/models in the future (e.g. `GOAL_001`
on one model, `PERFORMANCE_001` on another) and the data model must not foreclose that.
`QualityReportResponse`/`QualityReportDto` expose the full `semantic_evaluations` list; a
convenience single `semanticProvider`/`semanticModelVersion` pair is derived at the Spring
evidence-service layer only when every entry in the list agrees (same provider, same
model) — never fabricated when they don't.

---

## 2. Per-plan detail

### Plan A — Python outcome model + API contract completion
**Phases:** 1, 5, 6, 13
**Files (expected, confirm against current code before editing):**
- `intelligence/ml-service/app/quality/contracts.py` (already mostly correct — 5-state
  `RuleOutcome` exists; verify nothing downstream collapses it)
- `intelligence/ml-service/app/api/quality.py` (add `unknown_rules`/`not_applicable_rules`/
  `service_errors` to `QualityReportResponse`; stop collapsing outcome to `bool` in
  `RuleEvaluationResponse`; expose `parserConfidence`/`parserWarnings`/`parserAssumptions`/
  `topStrengths`/`topWeaknesses`/`provenance`/`authorizationEligible`/
  `authorizationFailureReasons` per Phase 13's required field list)
- `intelligence/ml-service/app/parser/prompt_parser.py` (remove optimistic defaults listed
  in Phase 5: `hook.startsAt=0`, `hook.visualStrength=4`, `hook.soundOffClear=true`,
  `coreMechanic.consistency=consistent`, `coreMechanic.mechanicCount=1`; stop requiring
  `[ATTEMPT: VERB]` markers for attempt recognition; emit confidence/assumptions/warnings/
  evidence-missing explicitly; do not silently return an empty plan on timeline parse failure)
- `intelligence/ml-service/app/llm/semantic_checks.py` (Phase 6: wrap timeout/HTTP/SDK/
  network/malformed-response/credential errors into `SemanticCheckServiceError` consistently
  — today only the provider-construction `ValueError` is converted)
- All 4 LLM provider files for the error-wrapping part of Phase 6 (not the vision part —
  that's Plan B)
- Backend DTOs mirroring the new response fields: `QualityReportDto.java` and friends
**Goal:** one outcome vocabulary (PASS/FAIL/UNKNOWN/NOT_APPLICABLE/SERVICE_ERROR) visible
end-to-end from rule engine through HTTP response, with no field silently dropped, no
optimistic parser default manufacturing false evidence, and no raw provider exception
reaching callers as an unstructured error.

### Plan B — Vision QA fix
**Phases:** 7
**Files:**
- `intelligence/ml-service/app/llm/provider.py` (interface already documents `image` param —
  verify signature supports multiple images if needed for reference + sampled frames)
- `intelligence/ml-service/app/llm/openai_provider.py`, `claude_provider.py`,
  `gemini_provider.py`, `ollama_provider.py` (stop `del image`; forward as actual vision
  content parts per each SDK's multimodal API; Ollama/other non-vision-capable configs must
  return explicit SERVICE_ERROR/UNKNOWN, never silently ignore)
- `intelligence/ml-service/app/qa/character_verifier.py` (attach canonical reference image
  to the comparison call, not just validate its existence; persist per-frame + aggregate
  result, frame timestamps, provider/model/check version)
**Goal:** character continuity QA actually sees both the canonical reference and sampled
rendered frames (early/middle/late, skipping failed extractions) when judging consistency.

### Plan C0 — Semantic evaluation provenance threading
**Phases:** 3 (prerequisite — makes semantic evidence fields real before C2 needs them)
**Files:**
- `intelligence/ml-service/app/llm/semantic_checks.py` (every semantic-check function
  returns which provider/model backed its judgment, not just the judgment itself)
- `intelligence/ml-service/app/rules/rule_engine.py` (all 8 semantic-check-calling
  evaluators: `_evaluate_attempt_002`, `_evaluate_payoff_003`, `_evaluate_concept_007`,
  `_evaluate_goal_001`, `_evaluate_concept_008`, `_evaluate_hook_004`,
  `_evaluate_performance_001`, `_evaluate_generation_executable_attempts` — thread
  provenance into each evaluation)
- `intelligence/ml-service/app/quality/contracts.py` (new `SemanticEvaluationProvenance`
  frozen dataclass: `provider`, `model`, `semantic_check_version`, `rule_ids`; new
  `semantic_evaluations: tuple[SemanticEvaluationProvenance, ...]` field on
  `EnhancedQualityReport`)
- `intelligence/ml-service/app/api/quality.py` (expose `semantic_evaluations` on
  `QualityReportResponse`)
- Mirror onto `intelligence/backend/.../quality/DtoModels.java` /
  `QualityReportDto.java` (new `SemanticEvaluationProvenanceDto` + `semanticEvaluations`
  list field, same pattern as Plan A's Task 8)
**Goal:** every semantic-check-backed rule evaluation records which LLM provider and model
version actually produced its judgment, with no flat/fabricated single
`semanticProvider`/`semanticModelVersion` pair invented at the report level — the data
model stays honest even once different rules use different providers.

### Plan C1 — Evidence contract cleanup
**Phases:** 3 (prerequisite — stops requiring evidence that cannot exist)
**Files:**
- `ValidationEvidenceService.java` (`resolveStatus`/`requireCompleteBaseEvidence`: drop
  `producibilityValidatorVersion` from the required-evidence checks entirely)
- `ValidationEvidencePolicy.java` (drop the same field from its `EVIDENCE_VERSIONS_INCOMPLETE`
  check)
- `QualityValidationEntity.java` (mark `producibilityValidatorVersion` field `@Deprecated`,
  keep the column — nullable, unused, not dropped; a schema-removal migration is a separate,
  later, non-urgent cleanup, not part of this plan)
- Doc note added to `ValidationEvidenceService`'s Javadoc explaining why: AI producibility
  validation is part of the deterministic versioned ruleset; its version is
  `deterministicRulesetVersion`; there is no independent producibility validator runtime.
**Goal:** stop requiring evidence for a system that does not exist. Never write
`producibilityValidatorVersion = deterministicRulesetVersion` just to satisfy the gate —
that would make the data model lie.

### Plan C2 — Independent revalidation + SERVICE_ERROR persistence
**Phases:** 3, 4
**Files:**
- New migration `V31__...sql` (never edit V1-V30; status CHECK constraint fix to allow
  `SERVICE_ERROR`)
- `IntelligenceQualityValidationService.java` (now that C0 makes `semanticProvider`/
  `semanticModelVersion` real: populate them from the ML response; implement real
  independent revalidation as a *second* fresh validation call, not a copy of the first
  validation's ID — new `independentlyRevalidate(long originalValidationRecordId)` method
  and a new `POST /api/v1/intelligence/quality/{id}/revalidate` endpoint; return 409 if the
  original record already has a non-null `independentRevalidationId`, since a validation's
  independent-revalidation link is set once and locked, not replaceable)
- `ValidationEvidenceService.java` (verify it reads the now-real semantic provenance fields
  correctly; no change expected beyond what C1 already did)
- `ValidationDecisionStatus.java`, `QualityReportDto.java` (SERVICE_ERROR persistence path)
**Goal:** a render-authorizing validation can actually reach RENDER_READY with real
evidence (depends on C0 and C1 both being done first), and independent revalidation is a
genuine second execution (same content/prompt/ruleset/stage, fresh semantic calls, separate
DB row, recorded relationship to the original) — not the original validation's ID copied
into its own evidence field.

### Plan C3 — End-to-end RENDER_READY authorization tests
**Phases:** 3, 4, 18 (partial — the render-authorization-specific scenarios only; the full
Phase 18 suite is Plan H)
**Files:**
- New integration test(s) spanning: valid prompt → validation #1 → semantic provenance
  persisted (C0) → independent validation #2 → complete evidence → `RENDER_READY` → render
  gate accepts the exact prompt/hash/version; same record + changed prompt hash → denied;
  semantic provider timeout → `SERVICE_ERROR` persisted → render denied.
**Goal:** automated proof that the full chain (C0 + C1 + C2) actually reaches
`RENDER_READY` under real evidence, not just that each piece's unit tests pass in
isolation. Do not mark Plan C done, or claim render authorization "works," until these
pass.

### Plan D — Render authorization stage model + evidence invalidation
**Phases:** 2, 15
**Files:**
- Rule catalog (`RULESET_1.3.yaml` schema — add `evaluationStage` metadata: PRE_RENDER /
  POST_RENDER / BOTH, single canonical source, not hardcoded per-call-site)
- `rule_engine.py` (stage-aware evaluation: POST_RENDER-only rules → NOT_APPLICABLE during
  PRE_RENDER, never UNKNOWN)
- `ValidationEvidencePolicy.java` (should need minimal change — confirm it only considers
  PRE_RENDER/BOTH rules for queueing; add evidence invalidation checks: prompt hash/version/
  ruleset version/semantic model version/producibility validator version/reference asset
  revision/TTL expiry — several of these already enforced, confirm full coverage)
**Goal:** CONSISTENCY_002 and other POST_RENDER-only rules never block PRE_RENDER
authorization by appearing UNKNOWN; a previously valid authorization is correctly
invalidated the instant any required identity changes.

### Plan E — Auto-fix repair + rule metadata single-source + recommendations
**Phases:** 8, 9, 10, 11
**Files:**
- `intelligence/ml-service/app/autofix/iteration_loop.py` (track attempted-and-failed fixes
  per run; skip NON_FIXABLE/REPLACE_CONCEPT/unsupported fixes instead of re-selecting them;
  never let the fixer itself mark RENDER_READY — only the normal validator path can)
- `intelligence/ml-service/app/autofix/prompt_fixer.py` (fixability registry completeness)
- `intelligence/ml-service/app/scoring/quality_scorer.py` (13-family weights consistent with
  `rule_engine.py`'s `_calculate_overall_score`; recommendation text for all 34 active 1.3
  rules — meaningful guidance or explicit NON_FIXABLE, never empty `Fix:` text; guidance
  describes the violated principle, not mechanical over-choreography)
- Correlation/root-cause handling for ATTEMPT_002/REPETITION_002/003/004 (Phase 11) — the
  `correlation_group` tagging added in a previous session exists in `rule_engine.py`;
  this plan should use it in scoring to avoid multiplying one root defect's score penalty,
  without weakening BLOCKER/CRITICAL gate semantics
**Goal:** auto-fix never loops on an unfixable top rule; every active rule has honest
guidance; family scoring is consistent everywhere it's computed or displayed; one repeated
defect isn't penalized N times in the aggregate score.

### Plan F — Angular quality screen reconnection
**Phases:** 14
**Files:**
- `intelligence/frontend/src/app/app.routes.ts` (add `quality` route)
- `intelligence/frontend/src/app/pages/quality-validator/*` (reconnect or cleanly replace;
  must display all outcome states, parser confidence/warnings, provenance, and whether the
  result is render-authorizing — ad-hoc vs render-authorizing endpoints clearly labeled)
**Goal:** the quality engine is reachable from the actual running product, not just from
curl/Postman.

### Plan G — Two creative rule gaps
**Phases:** 12
**Files:** TBD after investigation — likely a new `RULESET_1.4.yaml` (never mutate 1.3) if
Prompt Over-Constraint Risk is genuinely absent; Portfolio Mechanic Family Duplication is
explicitly expected to be **deferred, documented, not implemented** per the spec (it needs
Part 02's broken variant/folder identity to do properly — do not build a folder-based
detector as a workaround).
**Goal:** confirm whether these two gaps already have equivalents in RULESET 1.3 before
writing any code; implement only the one that's genuinely missing and genuinely
implementable without Part 02's broken identity model.

### Plan H — End-to-end integration tests + final completion report
**Phases:** 18, 19
**Files:**
- Integration tests spanning Spring → ML quality validation → persistence → evidence →
  render authorization (mocked LLM providers for determinism)
- All 18 test scenarios listed in the spec's Phase 18 (valid prompt → RENDER_READY, render
  gate accepts complete evidence, missing independent revalidation blocks authorization,
  changed prompt hash invalidates authorization, expired evidence rejected, SERVICE_ERROR
  persists, provider timeout → structured SERVICE_ERROR not 500, parser missing evidence →
  UNKNOWN not PASS, marker-less prompt still parses, POST_RENDER-only rule → NOT_APPLICABLE
  pre-render, vision provider actually receives image bytes, reference image participates,
  all active rules have recommendation/NON_FIXABLE, auto-fix skips unfixable + doesn't
  repeat, family weights consistent, API preserves all states, Angular renders all states)
- `docs/PART_01_QUALITY_GATE_COMPLETION.md` (final report per spec's required contents)
**Goal:** automated proof, not a claim. Do not write "production ready" unless these tests
actually pass.

---

## 4. Plan A completion record

**Status: ✅ Done.** Executed via `subagent-driven-development`, 8 tasks, each with an
implementer → review → fix-round cycle. Plan doc:
`docs/superpowers/plans/2026-10-03-plan-a-outcome-model-api-contract.md`.

Final state: Python test suite 312/312 passing, `ruff`/`mypy --strict` clean. Java test
suite 62/62 passing, `BUILD SUCCESS`. Full-plan diff reviewed holistically (not just
per-task) and Approved — no cross-task field mirroring gaps, no global-constraint
violations, no scope creep.

Commit range: `b2afd01..5a9ffd0` (10 commits: 8 task commits + 2 fix-round commits from
task review feedback on Tasks 3 and 4).

Delivered:
- `RuleOutcome`'s 5 states (PASS/FAIL/UNKNOWN/NOT_APPLICABLE/SERVICE_ERROR) are now visible
  end-to-end: rule engine → `QualityReportResponse` (`unknown_rules`/`not_applicable_rules`/
  `service_errors` fields) → Spring `QualityReportDto` (`unknownRules`/`notApplicableRules`/
  `serviceErrors`). `RuleEvaluationDto.result: boolean` → `outcome: String` on the Java side.
- Parser confidence/warnings/assumptions and top strengths/weaknesses now exposed on the API
  response (`parser_confidence`, `parser_warnings`, `parser_assumptions`, `top_strengths`,
  `top_weaknesses`) and mirrored on `QualityReportDto`.
- Parser no longer fabricates hook/consistency evidence: HOOK_002, HOOK_003, and
  CONSISTENCY_001 report UNKNOWN instead of a manufactured PASS/FAIL when the underlying
  evidence genuinely isn't extractable from the prompt text.
- `[ATTEMPT: VERB]` markers are no longer required — attempts are inferred from leading verbs
  in beat descriptions, closing the Phase 5 "optimistic default" gap for this specific case.
- Timeline parse failure (`_fallback_beat_parsing` returning zero beats) now surfaces
  explicitly via a new `evidence_missing: tuple[str, ...]` field on `ParserMetadata`, mirrored
  through to the API response and (implicitly, since Task 8 added the parser-metadata fields)
  available to Spring consumers.
- All LLM provider runtime failures (timeout, HTTP, SDK, network — not just the
  provider-construction `ValueError`) are now normalized into `SemanticCheckServiceError` via
  a new `_call_llm_safely` helper in `semantic_checks.py`, used at all 8 call sites.
- Proved (via a new integration test, no production code change needed — the architecture
  was already correct) that `/validate` returns a structured 200 + `SERVICE_ERROR` response,
  never an unstructured 500, when an LLM provider fails mid-request.

**Not delivered by Plan A, by design (deferred to later plans per the dependency graph in
§1):** `provenance`, `authorizationEligible`, `authorizationFailureReasons` fields mentioned
in Phase 13's full field list were deliberately NOT added in Plan A — populating them
correctly needs Plan C's evidence model first; adding them now would mean either fabricating
placeholder values (violating this plan's own anti-fabrication goal) or adding dead fields.
Revisit when Plan C lands.

**Follow-up required before relying on Plan A's Spring-side changes in production (found and
documented during Task 8, independently verified by the controller, NOT fixed as part of
Plan A since it's a pre-existing gap unrelated to this plan's scope):**

`intelligence/backend`'s `QualityMlClient` has **no Jackson snake_case naming configuration
anywhere** — no `spring.jackson.property-naming-strategy`, no `@JsonNaming`, no custom
`ObjectMapper`/`RestClientCustomizer`. It builds its `RestClient` from the plain
autoconfigured `RestClient.Builder`. This means the production path deserializing the Python
ML service's snake_case JSON (`overall_score`, `blocker_count`, `unknown_rules`, etc.) into
`QualityReportDto` may be silently dropping every field value today — Jackson's default
behavior ignores unrecognized JSON properties rather than erroring, so this would fail
silently, not loudly. This predates Plan A entirely (the original `overallScore`/
`rulesetVersion` fields have the same problem) and was never previously caught because no
test exercised `QualityMlClient`'s real deserialization path before this session.
**Recommend a dedicated task** (not clearly owned by any of Plans B–H as currently scoped):
add a global `spring.jackson.property-naming-strategy: SNAKE_CASE` (or a `RestClient`
`ObjectMapper` customizer bean) plus a real `QualityMlClient` integration test proving the
full HTTP round-trip, not just the DTO's own isolated Jackson deserialization (which
`QualityReportDtoTest`, added in Task 8, already proves — but only when given an explicitly
SNAKE_CASE-configured mapper, not the production default).

---

## 4a. Parallel-session reconciliation record (2026-10-03)

A second Kiro session worked in this same repo concurrently with this one and stopped
mid-stream with substantial uncommitted work. This controller session reconciled it rather
than discarding or re-doing it:

1. **`943e067`** (the parallel session's own commit): generated `RULESET_1.3.yaml` with 7
   new rules (`GOAL_001`, `CONCEPT_008`, `PROGRESSION_006`, `ESCALATION_005`, `HOOK_004`,
   `PERFORMANCE_001`, `PRODUCIBILITY_003`) via the proper `RuleVersionManager` path, plus
   (bundled into the same commit despite the message only mentioning RULESET_1.3) the `V31`
   migration and `QualityValidationEntity`/`QualityValidationRepository` changes
   independent revalidation needed.
2. **`c2dd149`**: this controller session's reconciliation of everything the parallel
   session left uncommitted — closing the silent-image-ignore half of Plan B (all 4
   providers), switching `CharacterVerifier` to local OpenCV comparison, a shared
   `CANONICAL_FAMILY_WEIGHTS` source (Plan E), the 7 new rule evaluators, a `provenance`
   block on the API response, real independent-revalidation orchestration in
   `IntelligenceQualityValidationService`, cross-referenced verification in
   `ValidationEvidenceService`, and the Angular `/quality` route (Plan F) — **plus fixes**
   for what was left broken: one `mypy --strict` error, 4 unformatted files, a Spring
   compile failure (DTO grew 20→23 fields, two `src/test` helpers not updated — the exact
   near-miss Plan A Task 8 had warned about), and 3 Java test failures from behavior changes
   the parallel session's own tests hadn't been updated for.
3. **`ab29da1`**: a dedicated Plan C1 fix — the parallel work had populated
   `producibilityValidatorVersion` end-to-end from a hardcoded config string, exactly the
   fabrication Plan C1 was created to prevent. Removed the requirement from both
   `ValidationEvidenceService` and `ValidationEvidencePolicy`, stopped populating it, and
   marked the entity field `@Deprecated` (column kept, nullable, unused).

Full before/after classification against a pre-written design checklist:
`intelligence/docs/superpowers/plans/PLAN_C0_SEMANTIC_PROVENANCE.md` §5-6. That doc also
records what's genuinely still missing (C0's per-rule semantic-provenance granularity, and
a real correctness bug where the flat provenance field claims a provider was used even on
reports where zero semantic checks actually ran) versus what turned out to already be
handled by the parallel work (C1, C2).

Verified after all three commits: ml-service 307/307 passed, ruff + format + mypy --strict
clean; backend 62/62 passed, BUILD SUCCESS; creative-render-service 286/286 passed, BUILD
SUCCESS.

---

## 5. Session handoff protocol

- Before starting work in a new session: read this file, run `git log --oneline -10` on
  `master` to see what's actually landed, check the status table in §1 against reality
  (a plan may be "done" in this doc but verify the commits are actually on master).
- After finishing a plan (or a meaningful chunk of one): update this file's status table
  and commit it together with the code changes, or as its own small commit if the code
  commit already happened.
- Never start Plan N+1 if Plan N's status is not ✅ — dependencies are real, not advisory.
- Each plan gets its own `docs/superpowers/plans/YYYY-MM-DD-<plan-name>.md` written via the
  `writing-plans` skill before implementation starts on that plan.

Status legend: ⬜ Not started · 🟨 In progress · ✅ Done · ⛔ Blocked
