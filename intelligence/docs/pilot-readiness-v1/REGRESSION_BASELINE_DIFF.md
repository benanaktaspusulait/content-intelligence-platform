# Regression Baseline Diff — Kiko Pilot Recovery

**Disposition: exact failure-set match; no new regression remains.**

## Comparison

| Evidence | Accepted historical run | Final recovery run |
|---|---:|---:|
| Command | Historical artifact records a pytest full-suite run; exact shell invocation and Python version were not preserved | `PYTHONPATH=. POMPOM_OFFLINE_MODE=true POMPOM_EXTERNAL_AI_AUTHORIZED=false .venv/bin/pytest -q --tb=no` from `intelligence/ml-service` |
| Result | 3,487 passed, 36 failed, 2 skipped | 3,491 passed, 36 failed, 2 skipped |
| Failure identifiers | 36 | 36 |
| New failures vs baseline | — | 0 |
| Baseline failures no longer failing | — | 0 |

The immutable baseline source is [full-regression.log](../semantic-two-stage-v1/full-regression.log). Its exact failure set is independently recorded as matching two accepted historical runs in `intelligence/docs/opening-evaluator-calibration-v1/regression-comparison.json`. The final failure IDs were extracted from the final full-suite log and compared as complete strings; the difference is empty in both directions.

The accepted log does not preserve Python version, dependency lock digest, or full command line. The current run used the checked-in `.venv`, Python 3.14.2, `PYTHONPATH=.`, and explicit offline/provider-denied flags. Current pass count is four higher; test collection/configuration is therefore not assumed byte-identical. Despite that limitation, the exact 36 failure IDs match, and there are no added or removed failures.

## Final accepted historical failures

Each identifier below is classified `ACCEPTED_HISTORICAL_FAILURE` because it appears in the immutable accepted baseline and in the final run. This classification does not claim that an individual test's underlying behavior is correct.

```text
tests/test_actor_source_attempts.py::test_inline_character_only_constraint_is_not_an_actor_declaration
tests/test_authoring_contract_repair_v2.py::test_nullable_unchanged_fields_and_no_settings_padding_still_compile_authored_delta
tests/test_creative_reconstruction_v2.py::test_actual_saved_mimi_full_role_source_canonical_comparison_pipeline
tests/test_creative_roles.py::test_long_form_story_role_maps_explicit_goal_and_runs_existing_canonical_gates
tests/test_creative_roles.py::test_canonical_story_evaluation_binds_only_source_quoted_story_plan_attempts
tests/test_creative_v2_generation_evidence.py::test_reconstruction_changes_with_objective_without_a_prepared_answer
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[sticky-ball-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[ball-crocodile-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[upside-chair-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[lamp-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[snack-box-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[box-cat-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[spot-cat-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[sneaky-door-01]
tests/test_family10_golden_review.py::test_reviewed_requirements_are_source_grounded_and_lossless_across_assessment_api[island-journal-01]
tests/test_family2_escalation.py::test_island_journal_escalation_is_not_applicable
tests/test_hook_002_metamorphic_stability.py::test_saved_real_candidate_keeps_identical_opening_inputs_and_hook_result
tests/test_hook_002_metamorphic_stability.py::test_later_beat_and_metadata_edits_cannot_change_hook_002[ [starting side visible]]
tests/test_hook_002_metamorphic_stability.py::test_later_beat_and_metadata_edits_cannot_change_hook_002[ [  starting   side   visible  ]]
tests/test_hook_002_metamorphic_stability.py::test_later_beat_and_metadata_edits_cannot_change_hook_002[ [locked lateral composition]]
tests/test_hook_002_metamorphic_stability.py::test_later_beat_and_metadata_edits_cannot_change_hook_002[ [static camera with the result held beside the action]]
tests/test_hook_002_metamorphic_stability.py::test_later_beat_and_metadata_edits_cannot_change_hook_002[\nPRODUCTION NOTE: Keep later contact readable.]
tests/test_hook_002_metamorphic_stability.py::test_missing_opening_evidence_never_becomes_pass_from_later_start_tokens
tests/test_hook_002_metamorphic_stability.py::test_actual_p2_stops_prompt_only_generation_but_preserves_score_and_evidence
tests/test_hook_002_metamorphic_stability.py::test_formatting_only_preserves_all_rule_outcomes_and_score
tests/test_model_authored_execution.py::test_complete_mock_provider_source_canonical_critic_and_comparison_gates
tests/test_motion_token_policy.py::test_saved_workflow_and_frozen_history[Original-saved0]
tests/test_motion_token_policy.py::test_saved_workflow_and_frozen_history[candidate-a-saved1]
tests/test_motion_token_policy.py::test_saved_workflow_and_frozen_history[candidate-b-saved2]
tests/test_post_family_workflow.py::test_curiosity_canonical_review_skips_only_physics_gates_and_keeps_shared_quality_gates
tests/test_ruleset_1_11_measurements.py::test_saved_inputs_preserve_1_10_and_correct_only_measurements[Original-saved0]
tests/test_ruleset_1_11_measurements.py::test_saved_inputs_preserve_1_10_and_correct_only_measurements[candidate-a-saved1]
tests/test_ruleset_1_11_measurements.py::test_saved_inputs_preserve_1_10_and_correct_only_measurements[candidate-b-saved2]
tests/test_ruleset_1_3_new_rules.py::TestGoal001GoalObstructionClarity::test_flawed_juice_mechanic_demo_fails_as_missing_motivation
tests/test_ruleset_1_4_new_rules.py::test_engine_silhouette_duplicate_blocks_missing_comparison
tests/test_studio_self_service.py::test_one_idea_is_not_a_timecoded_story_and_retains_paid_receipt
```

## Temporary added failures during recovery

An intermediate full run had 53 failures: the 36 baseline IDs plus 17 failures in active-code integrity checks. Those 17 were `NEW_REGRESSION` at that point: the parser/ranker edits were missing a chained current-hash approval in the existing exact-source registry. They were not waived. The `offlineSafetyApproval` registry now records the two exact source transitions from their previously approved hashes to their current hashes, with before/after evidence, and `protected_integrity.py` accepts the intermediate approved revision while continuing to reject any other hash. The focused integrity suite passed 24 tests, and the final full run returned to the exact 36-ID baseline set.

## Initial 42-failure run from the task prompt

The first recovery run reported 3,483 passed, 42 failed, 2 skipped. Exact set comparison showed the baseline's 36 IDs above plus these six IDs, each classified `NEW_REGRESSION` for that intermediate run because protected active-source hashes had changed without a corresponding exact active-code approval:

```text
tests/test_semantic_compact_capability_probe_v1.py::test_accepted_prompts_judges_and_all_historical_evidence_unchanged
tests/test_semantic_low_reasoning_probe_v1.py::test_all_accepted_prompt_validator_and_historical_bytes_unchanged
tests/test_semantic_prompt_v2_compact.py::test_all_preexisting_prompts_validators_and_evidence_byte_identical
tests/test_semantic_prompt_v2_compact_1.py::test_all_prior_bytes_immutable
tests/test_semantic_prompt_v2_compact_2.py::test_all_existing_prompt_judge_taxonomy_and_historical_bytes_unchanged
tests/test_semantic_two_stage_v1.py::test_all_prior_prompt_validator_taxonomy_history_bytes_unchanged
```

Those six exact checks passed after the provider-safety implementation received its exact-hash approval. The later parser/ranker changes surfaced a separate 17-hash mismatch set during an intermediate run; those were likewise exact registry gaps, then were resolved with the documented two-source transition. Final regression equivalence is based on the complete final 36-ID run above. The immutable accepted run is 36 failures; comparison is by test ID, not by subtracting totals.
