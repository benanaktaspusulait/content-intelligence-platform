# Kiko Offline Validation Recovery

**Final status: `PILOT_BLOCKED`**  
**Run date:** 2026-11-02 (Europe/London)

> **Superseded for current workflow coverage and regression results:** see [KIKO_PILOT_FINAL_RECOVERY.md](KIKO_PILOT_FINAL_RECOVERY.md) and its exact-set [REGRESSION_BASELINE_DIFF.md](REGRESSION_BASELINE_DIFF.md). This earlier report's `NOT_EVALUATED` workflow list and 3,483/42 test result are historical interim results.

## 1. Root cause and exact call path

Record 24 was created by the linked backend validation endpoint, `POST /api/v1/intelligence/quality/validate`, for content 18 / prompt version 29. Backend log: `IntelligenceQualityValidationService` received the request and persisted validation record 24 after the ML response.

Call graph:

```text
HTTP POST /api/v1/intelligence/quality/validate
  -> IntelligenceQualityValidationController.validate
  -> IntelligenceQualityValidationService.validateAndPersistEvidence
  -> QualityMlClient.validatePrompt
  -> POST /api/v1/quality/validate (FastAPI)
  -> app.api.quality.validate_prompt
  -> RuleVersionManager.load_latest (ruleset 1.12)
  -> RuleEngine.evaluate
  -> _evaluate_goal_001
  -> RuleEngine._semantic_check
  -> check_goal_is_natural
  -> get_provider (DEFAULT_LLM_PROVIDER defaults to openai)
  -> OpenAIProvider.complete
  -> OpenAI chat.completions.create
```

This was an intentional AI-dependent quality rule reached through an accidental offline-policy gap. `POMPOM_SEMANTIC_ENABLED=false` only gated video-image semantic analysis; it did not prohibit the ruleset's text-semantic judgments. Ruleset 1.12 declares `semanticPolicy: TARGETED_STORY_GATES`; `_semantic_check` permits `GOAL_001` (and `ATTEMPT_002`) under that policy. `OPENAI_API_KEY` was available to the ML container from its configured environment file, while `DEFAULT_LLM_PROVIDER` fell back to `openai`. Credentials therefore enabled a call but were not an appropriate safety control.

The provider returned a response, but it was unusable: required JSON field `ending_meaningfully_addresses_goal` was missing. The response was rejected as `SERVICE_ERROR`; this is not evidence that the story itself failed GOAL_001. No provider retry occurred: `OpenAIProvider` sets `max_retries=0`; the backend only performs an independent second validation when the first result is `RENDER_READY`, which this was not. Ruleset evaluation continued after the gate error; record 24 contains outcomes for the other rules. No cached semantic response was applicable or used.

## 2. Record 24 classification

Immutable historical record 24 remains unchanged: ruleset 1.12, prompt fingerprint `d623dd1f1bbbb1207090c7caff4db5f4b8b806cb55d26cb6aa14ceb8f356b610`, status `SERVICE_ERROR`, score 73.052083, 4 blocker failures, 5 critical failures, 8 warnings.

- **PASS (19):** BEAT_004, BEAT_005, CONCEPT_006, ESCALATION_004, ESCALATION_005, GENERATION_EXECUTABLE_ATTEMPTS, GOAL_VISIBLE_EARLY, MOTION_001, NOVELTY_001, PAYOFF_001, PAYOFF_002, PAYOFF_004, PAYOFF_006, PRODUCIBILITY_001, PROGRESSION_005, PROGRESSION_006, REPETITION_002, REPETITION_003, REPETITION_004.
- **FAIL (10; deterministic/source-derived outcomes preserved):** HOOK_002 (opening not mid-action), ATTEMPT_001 (0 active attempts; minimum 3), CHAR_002 (0% active solution behavior; minimum 50%), PRODUCIBILITY_002 (108 main props; maximum 2), ATTEMPT_002 (0 strategies from 0 active attempts; minimum 3), PRODUCIBILITY_003 (fragile interaction risk tags), INSTANT_VISUAL_ABSURDITY_GATE (insufficient first-frame absurdity evidence), MINI_STORY_LOCK (attempts missing), TEMPORAL_COMPLEXITY_SPLIT_GATE (overload; existing rule suggests 2×15s, disallowed by the ≤15s pilot cap), BEAT_DENSITY_RULE (9 major beats; safe range 4–6).
- **SERVICE_ERROR (1):** GOAL_001 only; malformed/incomplete provider result, not a trustworthy creative verdict.
- **UNKNOWN / insufficient evidence (12):** CONCEPT_007, CONCEPT_008, CONSISTENCY_001, CONTINUOUS_ACTION_MOMENTUM, ENGINE_SILHOUETTE_DUPLICATE, HOOK_003, HOOK_004, PAYOFF_003, PERFORMANCE_001, STUBBORN_RETURN_HOOK, STUBBORN_RETURN_LOOP, STUBBORN_RETURN_PAYOFF. GOAL_001 is separately `SERVICE_ERROR` in record 24 and becomes `UNKNOWN` on offline replay.
- **NOT_APPLICABLE (4):** CONCEPT_009, CONSISTENCY_002, CONTINUATION_LOCK, PAYOFF_005.

No status above turns unavailable evidence into PASS. Existing real failures remain blockers independently of the provider incident.

## 3. Offline safety changes

- `POMPOM_OFFLINE_MODE` defaults to `true`; Compose allows an operator to set it explicitly, and sets `POMPOM_EXTERNAL_AI_AUTHORIZED` to `false` by default.
- The rule engine short-circuits AI-dependent semantic judgments in offline mode to its existing evidence-unavailable/UNKNOWN path. It does not call validators, invent a passing response, retry, or fall back.
- The shared LLM provider factory and provider adapter constructors deny initialization unless offline mode is explicitly disabled **and** `POMPOM_EXTERNAL_AI_AUTHORIZED=true`. Missing credentials are not relied on for enforcement.
- Nested semantic checks flow through this boundary; direct OpenAI/Claude/Gemini/Ollama adapter construction is also guarded.
- OpenArt `--dry-run` remains request preparation only; it does not authorize media generation. Render authorization remains a separate production gate.

Provider-enabled operation is possible only by explicitly setting `POMPOM_OFFLINE_MODE=false` and `POMPOM_EXTERNAL_AI_AUTHORIZED=true`. Neither is set for this pilot.

## 4. Offline replay through the real application path

After rebuilding/restarting the existing ML service with offline mode active, the existing linked endpoint was invoked once for content 18 / prompt version 29. This created record 25 and exercised the real backend → ML service → ruleset orchestrator path. Container configuration was verified as `offline=true`, `auth=false`.

Record 25 uses the same ruleset and prompt fingerprint as record 24. It completed with `BLOCKED`, score 73.052083, 4 blocker failures, 5 critical failures, 8 warnings, and **zero service errors**. AI-dependent GOAL_001 became `UNKNOWN` with provider dispatch disabled; no synthetic result was inserted. Outcomes: 19 PASS, 10 FAIL, 13 UNKNOWN, 4 NOT_APPLICABLE. Thus record 24's SERVICE_ERROR no longer masquerades as a quality verdict, while deterministic failures are preserved.

This real replay is evidence that this execution path made zero provider calls after the repair. The ML service returned the report directly; its log recorded the local validation request only. No outbound provider request was attempted. The pre-existing earlier unauthorized invocation remains part of the historical incident count.

## 5. Requested component coverage

The real, applicable local quality ruleset replay above is the evidence source for the gate results. The following separately named workflows were **NOT_EVALUATED** in this run: Opening Evaluation, Premise Naturalness, Premise Admission, Beat Grammar, SHORT_FORM_ENGINE, Creative Shape, Historical Territory, Candidate Ranking, and Production Preselection. Record 24/25 does not contain versioned, source-bound outputs for those separate workflows, and no applicable frozen result with matching prompt provenance was identified during this recovery. They are not represented as PASS. The pre-render checks present in the quality ruleset are included in the PASS/FAIL/UNKNOWN lists above.

## 6. Tests and execution safety

- Focused provider / semantic / ruleset tests on the final code: **126 passed**, including offline and unauthorized nested-call denial before dispatch, adapter factory/constructor checks, and the existing semantic rule tests. Provider adapter calls in the provider test module use mocked SDK clients.
- Full ML regression: `POMPOM_OFFLINE_MODE=true POMPOM_EXTERNAL_AI_AUTHORIZED=false .venv/bin/python -m pytest -q` from `intelligence/ml-service`, with the test-only policy in `tests/conftest.py` explicitly authorizing mocked adapter tests and redirecting non-loopback HTTP(S) through an unavailable local proxy. Result: **3,483 passed, 42 failed, 2 skipped** (222.12s). The full run preceded the final small nested-call authorization check; the affected focused tests were then rerun on final code and all passed. Provider access remained fail-closed at external transport; no successful external provider request occurred. The first run before test-only authorization had 139 failures, many caused by tests depending on mocked provider construction; adding the guarded test policy reduced that to 42.
- Real execution test: linked backend endpoint completed offline as record 25; no SERVICE_ERROR; `GOAL_001=UNKNOWN`; no provider fallback or retry. The common factory and adapter constructors deny provider setup before network transport. No real AI call was made for this safety test.
- Asset hash verification during this run matched both approval records exactly (see section 7).

## 7. Approved assets preserved

- Canonical Kiko reference: `/Users/benanaktas/project/video/yuvarlak-dunya/01-CHARACTERS/drawings/kiko.png` — SHA-256 `8b9e643660722d5c00bd0d25ebef066ea868f52d8a57aa1e4a2b0eb9b55747fc`; still `APPROVED`.
- Runaway Toothbrush first frame: `/Users/benanaktas/project/video/yuvarlak-dunya/POMPOM_HILLS_PRODUCTION/09_SOCIAL_REELS/new14092026/Chaos/01_runaway_toothbrush/01_runaway_toothbrush_image.png` — SHA-256 `18c12f79825b2e88309db0ab00a6fe985acee790d5383353ae4cd9ec1960ad0a`; still accepted as `FIRST_FRAME`.
- Both source image byte streams remain unchanged. Creative quality blockers did not change asset approvals.

## 8. image2video preflight and duration

Existing preflight evidence remains the OpenArt CLI dry-run for model `byte-plus-seedance-2-mini`, image2video mode, the approved first-frame path, exact prompt version 29, ratio 9:16, resolution 480p, and duration 15 seconds. It exited 0 and did not produce a video. Local capability snapshot allows 4–15 seconds, includes 9:16/480p, and requires `startFrame`. No text-to-video fallback was selected. This recovery made no new OpenArt generation call and no render call.

Although the capability snapshot allows a 14-second request, the accepted source prompt's event timing runs through 15 seconds. Changing the requested value to 14 without a source-approved timing change would truncate or retime the selected story; it is not used as a workaround. A 15-second request is not a guarantee that provider output duration will be ≤15.000 seconds. No render is authorized, and explicit render authorization remains required.

## 9. Files changed and preserved records

- `intelligence/ml-service/app/llm/provider.py`
- `intelligence/ml-service/app/llm/openai_provider.py`
- `intelligence/ml-service/app/llm/claude_provider.py`
- `intelligence/ml-service/app/llm/gemini_provider.py`
- `intelligence/ml-service/app/llm/ollama_provider.py`
- `intelligence/ml-service/app/rules/rule_engine.py`
- `intelligence/docker-compose.yml`
- `intelligence/ml-service/tests/test_llm_providers.py`
- `intelligence/ml-service/tests/conftest.py`
- This recovery report.

Full-suite failures after the test-policy adjustment (accepted baseline comparison unavailable; no frozen baseline result was supplied):

```text
test_actor_source_attempts::test_inline_character_only_constraint_is_not_an_actor_declaration
test_authoring_contract_repair_v2::test_nullable_unchanged_fields_and_no_settings_padding_still_compile_authored_delta
test_creative_reconstruction_v2::test_actual_saved_mimi_full_role_source_canonical_comparison_pipeline
test_creative_roles::test_long_form_story_role_maps_explicit_goal_and_runs_existing_canonical_gates
test_creative_roles::test_canonical_story_evaluation_binds_only_source_quoted_story_plan_attempts
test_creative_v2_generation_evidence::test_reconstruction_changes_with_objective_without_a_prepared_answer
test_family10_golden_review::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api (9 parameter cases)
test_family2_escalation::test_island_journal_escalation_is_not_applicable
test_hook_002_metamorphic_stability (8 named cases)
test_model_authored_execution::test_complete_mock_provider_source_canonical_critic_and_comparison_gates
test_motion_token_policy::test_saved_workflow_and_frozen_history (3 cases)
test_post_family_workflow::test_curiosity_canonical_review_skips_only_physics_gates_and_keeps_shared_quality_gates
test_ruleset_1_11_measurements::test_saved_inputs_preserve_1_10_and_correct_only_measurements (3 cases)
test_ruleset_1_3_new_rules::TestGoal001GoalObstructionClarity::test_flawed_juice_mechanic_demo_fails_as_missing_motivation
test_ruleset_1_4_new_rules::test_engine_silhouette_duplicate_blocks_missing_comparison
test_semantic_compact_capability_probe_v1::test_accepted_prompts_judges_and_all_historical_evidence_unchanged
test_semantic_low_reasoning_probe_v1::test_all_accepted_prompt_validator_and_historical_bytes_unchanged
test_semantic_prompt_v2_compact::test_all_preexisting_prompts_validators_and_evidence_byte_identical
test_semantic_prompt_v2_compact_1::test_all_prior_bytes_immutable
test_semantic_prompt_v2_compact_2::test_all_existing_prompt_judge_taxonomy_and_historical_bytes_unchanged
test_semantic_two_stage_v1::test_all_prior_prompt_validator_taxonomy_history_bytes_unchanged
test_studio_self_service::test_one_idea_is_not_a_timecoded_story_and_retains_paid_receipt
```

Quality record 24 and approvals were preserved. New linked offline replay is record 25. No prompt, scoring threshold, image, approval, render, or historical record was modified.

## 10. Counts, remaining blockers, and next operator action

- Historical record 24: at least one OpenAI provider request is confirmed by the returned response; exact provider request ID/usage count was not persisted. No retry was attempted.
- Offline replay in this recovery: **0 AI provider requests**, **0 OpenArt generation requests**, **0 render requests**.
- Remaining blockers: ten deterministic/source-derived FAILs; thirteen UNKNOWN gates; nine separately listed workflows not evaluated; unresolved output-duration guarantee; and the previously observed prompt-plan summary field that says `firstFrameStatus=MISSING` despite listing the approved accepted binding. No render command is issued.
- **Next operator command (safe offline recheck):**

```sh
curl -fsS -X POST http://127.0.0.1:8080/api/v1/intelligence/quality/validate \
  -H 'Content-Type: application/json' \
  -d '{"contentId":18,"promptVersionId":29,"rulesetVersion":"latest"}'
```

This command evaluates the immutable existing prompt under the offline policy and cannot authorize a render. Creative repairs, if desired, require a separately approved source revision and a new offline replay. Current disposition remains **`PILOT_BLOCKED`**.
