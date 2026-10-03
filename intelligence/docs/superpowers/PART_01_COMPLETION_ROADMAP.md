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
subsystems must be split before planning), this work is split into 8 sub-plans, each
independently plannable/testable/committable. **Work them in order — later plans assume
earlier plans' deliverables exist.**

| # | Plan name | Spec phases covered | Codebase(s) | Status |
|---|---|---|---|---|
| A | Python outcome model + API contract completion | 1, 5, 6, 13 | ml-service | 🟨 Plan written (`docs/superpowers/plans/2026-10-03-plan-a-outcome-model-api-contract.md`, commit `880e607`), not yet executed |
| B | Vision QA fix (image passthrough + character verifier) | 7 | ml-service | ⬜ Not started |
| C | Spring evidence chain + independent revalidation + DB migration | 3, 4 | backend | ⬜ Not started |
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
- **C depends on A** conceptually (same outcome-model vocabulary) but is a separate codebase
  (Spring) and separate migration — can start once A's contracts are stable, doesn't need to
  wait for A's full merge.
- **D depends on A and C** (needs the stage model concept from A's rule metadata and the
  evidence fields C populates).
- **E depends on A** (rule metadata single-source needs the outcome model finalized).
- **F depends on A** (Angular models need the finalized API contract shape).
- **H depends on A–G all being done.**
- **B and G are independent of everything else** — can be done in any order, even in
  parallel with A if desired, but default sequencing below does them after A/C/D since they
  are lower architectural risk.

Suggested execution order: **A → C → D → E → B → F → G → H**. (B and G moved later only
because they're self-contained and lower-risk to slot in opportunistically; reorder freely
if it's more convenient to do B or G earlier.)

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

### Plan C — Spring evidence chain + independent revalidation + DB migration
**Phases:** 3, 4
**Files:**
- New migration `V31__...sql` (never edit V1-V30; status CHECK constraint fix for
  `SERVICE_ERROR`, any new provenance columns: semanticCheckVersion, parserVersion,
  evaluator/rule-engine version, validationStage)
- `IntelligenceQualityValidationService.java` (populate all evidence fields from actual ML
  response; implement real independent revalidation as a *second* fresh validation call,
  not a copy of the first validation's ID)
- `ValidationEvidenceService.java` (should need minimal change — already recomputes status
  correctly; verify it reads any new columns)
- `ValidationDecisionStatus.java`, `QualityReportDto.java` (SERVICE_ERROR persistence path)
**Goal:** a render-authorizing validation can actually reach RENDER_READY with real
evidence, and independent revalidation is a genuine second execution (same content/prompt/
ruleset/stage, fresh semantic calls, separate DB row, recorded relationship to the
original) — not the original validation's ID copied into its own evidence field.

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

## 3. Session handoff protocol

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
