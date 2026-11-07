# New Pilot Offline Validation Report

Date: 2026-11-02  
Outcome: **NEW_PILOT_BLOCKED**. Three real local concepts were used for diagnostic offline checks; none qualifies as a genuinely unused pilot.

## Runs and results

Existing local pipeline components were run in offline mode (`POMPOM_OFFLINE_MODE=true`, `POMPOM_EXTERNAL_AI_AUTHORIZED=false`). Provider call count was 0; render call count was 0. The three exact source files are under the configured production library:

- `not-generated/KIKO_AND_THE_UPSIDE_DOWN_UMBRELLA/kiko-upside-down-umbrella-production.md`
- `not-generated/MIMI_AND_THE_RAINBOW_ON_HER_HAND/mimi-rainbow-hand-production.md`
- `not-generated/LUCAS_SHADOW_TAKES_A_SHORTCUT/lucas-shadow-shortcut-production.md`

| Existing component | Kiko umbrella | Mimi rainbow | Luca shadow |
|---|---|---|---|
| Source/timing inspection | 15s; 5 authored timed beats; 9:16 | 15s; 5 authored timed beats; 9:16 | 15s; 5 authored timed beats; 9:16 |
| Existing normalizer + ranking | No eligible ranked candidate; missing canonical goal/object/rule mappings; `firstRenderCandidate=null`, render unauthorized | Same; `firstRenderCandidate=null`, render unauthorized | Same; `firstRenderCandidate=null`, render unauthorized |
| Existing `SHORT_FORM_ENGINE` | `REJECT`: opening not in trouble, everyday goal unclear, core rule unsupported by canonical fields, too few *supported* causal beats (0); high activity/low supported progress; weak payoff | Same plus `IDENTICAL_ATTEMPTS` on beat 3 | Same as umbrella |
| Existing Premise Naturalness V1 | `BROKEN`, `GENERIC_ENGINE_APPLICATION`, `CAUSE_NOT_VISIBLE_AT_FRAME_ZERO`; empty goal | Same | Same |
| Canonical Evidence | `INSUFFICIENT_EVIDENCE`: production continuity table not mapped into complete canonical structured fields; no values inferred | Same | Same |
| Opening Evaluation | `INSUFFICIENT_EVIDENCE`: no candidate-specific first-frame asset to evaluate | Same | Same |
| Premise Admission | `INSUFFICIENT_EVIDENCE`: required complete structured evidence/goal absent | Same | Same |
| Beat Grammar | `INSUFFICIENT_EVIDENCE`: authored rows exist, but they were not represented as canonical typed state transitions; no PASS inferred | Same | Same |
| Creative Shape / Historical Territory | `INSUFFICIENT_EVIDENCE`: incomplete canonical candidate and comparison records | Same | Same |
| Pre-Render QA | `BLOCKED`: no approved first-frame image bound to the candidate; lifecycle and character approval unresolved | Same | Same |

`Premise Naturalness` output is a deterministic, generic-object screen, not a full human creative judgment. The source plans visibly contain five beats, so the SFE report of zero *supported* beats reflects normalization support failure; it must not be paraphrased as zero authored beats. All three plans are within the 15-second timing ceiling, but timing alone does not pass creative gates.

## Asset evidence

- **Kiko:** canonical reference was approved in the earlier Kiko review. No approved candidate-specific frame-zero image is present. A published umbrella comparison blocks this as a new pilot.
- **Mimi:** `/01-CHARACTERS/drawings/mimi.png` exists, but approval provenance for this candidate was not verified. No approved candidate-specific first frame exists.
- **Luca:** canonical character file is referenced by the plan, but candidate-linked approval provenance was not verified. No approved candidate-specific first frame exists.

No image was generated, edited, replaced or approved. Existing model CLI image2video dry-run cannot be truthfully executed without a candidate-approved image; substituting a fixture or falling back to text-to-video would not verify the requested workflow.

## Selection

No exact pilot is selected. Mimi rainbow is the closest apparent distinct idea among these diagnostics, but its lifecycle is still `UNKNOWN`, its everyday goal is unclear, its required structure does not pass, and its frame/approval are missing. Calling it a pilot or unused would overstate the evidence. No creative rewrite was made; substantive story repair remains subject to human review.

## Full offline ML regression

Command: `POMPOM_OFFLINE_MODE=true POMPOM_EXTERNAL_AI_AUTHORIZED=false PYTHONPATH=. .venv/bin/pytest -q`  
Result: **3,493 passed, 36 failed, 2 skipped** in 225.26s. This matches the accepted aggregate baseline of 36 failures and 2 skips; the current suite has six more passing tests than the previously recorded 3,487. A follow-up `--lf` replay selected exactly the same 36 failures (27 deselected), so there were **no additional failures** in this run. The baseline report did not retain test identities, so identity-for-identity comparison to its 36 failures cannot be claimed.

Failed test identities in this run:

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
