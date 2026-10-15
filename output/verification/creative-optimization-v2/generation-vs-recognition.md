# Additional acceptance: recognition versus reconstruction

## Acceptance boundary

**Implementation readiness is demonstrated. Real-model creative effectiveness is UNVERIFIED. Creative quality is not proven.**

The earlier `mock-response.json`, fixed `MockProvider` responses and isolated full-stack run use pre-authored plan choices. They establish evaluation/compilation/integration behavior when supplied those choices. They do **not** establish that a real optimizer invented, selected or improved that plan. The before/after example remains useful evidence of an observable textual execution change, not evidence of autonomous model creativity or actual visual improvement.

## Capability 1 — recognize and explain an intervention

**Evidence:** `test_capability_one_recognizes_an_authored_material_intervention_only` and existing cosmetic/timing/risk/story regression tests.

A controlled authored plan is supplied intentionally. The real source/canonical/comparison functions identify the contact-plane change, preserve source-event coverage, expose original/new instructions and rationale, and classify it as PLAUSIBLE_IMPROVEMENT_UNVERIFIED. Cosmetic and timestamp-only cases are rejected. The classifier keeps `provenBetter: false` and semantic fidelity UNKNOWN.

**Established:** deterministic recognition/explanation of a concrete source-bound production intervention, plus rejection behavior. **Not established:** successful imagery, actual quality superiority, or creative generation by a real model.

## Capability 2 — construct a fresh source-specific execution

**Evidence:** `test_creative_v2_generation_evidence.py`, with full runtime requests/responses/compiled prompts in `generation-vs-recognition-evidence.json`.

The new test-only `DiagnosisDrivenPlanner` receives no authored plan, candidate prompt or response fixture. It reads the real role request's current diagnosis. Given a quality-dimension objective, it selects an available diagnosed opportunity and constructs a fresh structured plan using that opportunity's ID, operation, proposed objective and source-derived expected change. The application's existing reconstructor then compiles the actual source-specific choreography and validates the full prompt. The planning policy is deterministic test code; it is not a real model or a newly shipped production planner.

Counterfactuals distinguish this from replaying a completed answer:

| Runtime input/objective | Constructed result | Canonical/comparison result |
|---|---|---|
| Saved Mimi source; visual-storytelling objective | CONTACT_PLANE using source-bound cabinet/finger relationship | 88.40625/B; PLAUSIBLE_IMPROVEMENT_UNVERIFIED |
| Same saved source; causal-progression objective | COUNTABLE_STATE_PATH with existing two → four → eight | 87.88542/B; REGRESSION; KEEP_ORIGINAL |
| Ephemeral source count path changed to three → six → twelve | Reconstructed instruction uses three → six → twelve, not the previous numbers | 87.88542/B; REGRESSION; KEEP_ORIGINAL |
| Opening strategy CURIOSITY_DISCOVERY; unsupported contact-clarity objective | No candidate; source does not support the requested opportunity | NO_JUSTIFIED_IMPROVEMENT; KEEP_ORIGINAL |

The source-state counterfactual exists only in memory. Saved Prompt 10 and the approved story were never edited. Its independent semantic story fidelity is UNKNOWN; a changed count path is not being approved as a production revision.

An additional test sends the same input-responsive planner through the actual FastAPI creative-role HTTP handler and OpenAI adapter with a patched SDK. The SDK double constructs its response **after reading the current request**, rather than returning a stored answer. There is one mocked SDK request, `max_retries=0`, bounded test budget, real source/canonical validation and comparison. No real SDK/network provider request occurs.

**Established:** the bounded reconstruction pipeline builds fresh source-specific output that responds to diagnosis, objective and source changes; it does not merely retrieve the prepared Mimi candidate. It can also return no candidate. **Not established:** whether a real model can independently choose strong interventions, produce novel choreography beyond the bounded production grammar, reliably improve prompt quality or outperform the original. The current production code still uses server-authored operation templates. This test cannot validate the quality of real-model decision-making.

## Verification and restrictions

`generation-vs-recognition-tests.log`: **20 passed** = 5 new acceptance tests plus 15 existing V2 tests rerun. This is not 20 additional independent tests. Existing full-stack mock verification remains an implementation-readiness result.

No runtime application/scoring/infrastructure changes were needed for this acceptance clarification. Changes are focused tests and evidence documentation; no redeployment was needed. No real provider call, automatic retry, provider budget increase, approval, prompt version, story edit, production evaluation, generation, render, publish or commit/push was performed.

A real-model generation test remains **NOT RUN / NO AUTHORIZATION**. It requires a separately explicit operator-authorized request with positive bounded budget and the existing source/settings/analysis binding, idempotency, persistence and approval controls. Even a successful real text-provider test would establish only observed prompt-level creative behavior; visual and audience superiority still need their own evidence.
