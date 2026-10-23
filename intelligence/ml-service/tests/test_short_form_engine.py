"""Deterministic source-plan checks, never footage or performance evaluations."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from app.workflow.short_form_engine import assess
from app.workflow.story_premise_engine import assess as assess_long

ROOT = Path(__file__).parents[2]
GOLDEN = ROOT / 'data/golden/pompom-golden-v1'
CASES = json.loads((Path(__file__).parent / 'fixtures/short_form_cases.json').read_text())['cases']
WINNER = (GOLDEN / 'prompts/upside-chair-01.md').read_text()
OLD_CASES = json.loads((Path(__file__).parent / 'fixtures/story_premise_cases.json').read_text())
OPT_IN = {'shortFormEvaluation': True}


def evaluate(text, **context):
    return assess(text, {**OPT_IN, **context})


def codes(result):
    return {f['code'] for f in result['findings']}


@pytest.mark.parametrize('context', [None, {}, {'desiredDuration': 15}, {'shortFormEvaluation': False}, {'shortFormEvaluation': 'true'}])
def test_explicit_boolean_opt_in_only(context):
    assert assess(WINNER, context) is None


def test_real_historical_source_is_bound_to_frozen_manifest_not_a_synthetic_winner():
    import yaml
    asset = next(a for a in yaml.safe_load((GOLDEN / 'manifest.yaml').read_text())['assets'] if a['goldenId'] == 'upside-chair-01')
    result = evaluate(WINNER)
    assert asset['corpusRole'] == 'WINNER'
    assert result['sourceSha256'] == asset['promptHash']
    assert result['status'] == 'PASS_WITH_WARNINGS'
    assert result['hookScore'] == 100 and result['payoffScore'] == 100
    assert result['majorCausalBeatCount'] == 6
    assert not result['duplicateEngineRisk']['matches']
    assert result['providerCalls'] == 0 and not result['renderAuthorized']
    assert 'ESCALATION_PLATEAU' in codes(result)  # Historical success does not suppress diagnostics.


@pytest.mark.parametrize('name', ['structurally_different', 'garden_guardian_short'])
def test_distinct_strong_shorts_need_no_moral_arc(name):
    result = evaluate(CASES[name])
    assert result['status'] == 'PASS'
    assert result['majorCausalBeatCount'] == 5
    assert result['goalScore'] == result['progressDensityScore'] == result['payoffScore'] == 100
    assert result['earlyRuleUnderstandingPenalized'] is False


@pytest.mark.parametrize('name,flag', [
    ('activity_without_progress', 'HIGH_ACTIVITY_LOW_PROGRESS'),
    ('beautiful_unclear', 'OPENING_NOT_IN_TROUBLE'),
    ('identical_attempts', 'IDENTICAL_ATTEMPTS'),
    ('unrelated_rules', 'MULTIPLE_UNRELATED_RULES'),
    ('boogeyman_compressed', 'AUDIO_DEPENDENT_CAUSALITY'),
])
def test_weak_concepts_do_not_pass(name, flag):
    result = evaluate(CASES[name])
    assert result['status'] in {'REJECT', 'REVISION_REQUIRED'}
    assert flag in codes(result)


def test_activity_and_described_blocks_are_not_causal_progress():
    busy = evaluate(CASES['activity_without_progress'])
    strong = evaluate(CASES['structurally_different'])
    assert busy['describedBlockCount'] == strong['describedBlockCount'] == 5
    assert busy['majorCausalBeatCount'] == 1
    assert busy['progressDensityScore'] < strong['progressDensityScore']
    assert busy['beatDensityScore'] < strong['beatDensityScore']
    assert busy['shortFormScore'] < strong['shortFormScore']


def test_payoff_is_material_not_a_smile_or_moral():
    text = CASES['structurally_different']
    weak_ending = text[:text.index('12-15s:')] + '12-15s: Mimi closes the lid successfully, smiles and celebrates.'
    assert evaluate(weak_ending)['payoffScore'] < evaluate(text)['payoffScore']
    assert 'WEAK_VISUAL_PAYOFF' in codes(evaluate(weak_ending))


def test_long_form_and_short_form_are_independent_in_both_directions():
    assert assess_long(OLD_CASES['strong']['boogeymans_exam'])['score'] == 91
    assert evaluate(CASES['boogeyman_compressed'])['status'] == 'REJECT'
    assert assess_long(OLD_CASES['weak']['garden_guardian'])['status'] == 'STORY_REVISION_REQUIRED'
    # Explicit adaptation: not claiming that the historical 60s source itself passes.
    assert evaluate(CASES['garden_guardian_short'])['status'] == 'PASS'


def test_compressing_metadata_alone_does_not_rewrite_a_60_second_plan():
    result = evaluate(OLD_CASES['strong']['boogeymans_exam'], desiredDuration=15)
    assert 'TIMING_UNVERIFIED' in codes(result)
    assert result['status'] in {'REJECT', 'REVISION_REQUIRED'}


@pytest.mark.parametrize('object_name', ['stool', 'bench', 'brush'])
def test_engine_duplicate_is_structural_and_ignores_object_names(object_name):
    text = WINNER.replace('chair', object_name).replace('CHAIR', object_name.upper())
    result = evaluate(text)
    assert 'ENGINE_DUPLICATE_RISK' in codes(result)
    assert result['duplicateEngineRisk']['status'] == 'HIGH'
    assert result['duplicateEngineRisk']['matches'][0]['matchingAxes'] == ['opening', 'progression', 'ending']
    assert result['status'] == 'REVISION_REQUIRED'


def test_familiar_rule_with_distinct_execution_is_not_globally_rejected():
    text = CASES['structurally_different'].replace('it pops open', 'it flips upside down').replace('springs open', 'flips upside down')
    result = evaluate(text)
    assert result['duplicateEngineRisk']['status'] != 'HIGH'


def test_optional_loop_absence_is_not_a_failure():
    text = CASES['structurally_different'].replace('Loop back to the first frame.', '')
    result = evaluate(text)
    assert result['status'] == 'PASS'
    assert result['rewatchType'] == 'OPTIONAL_NOT_ESTABLISHED'
    assert result['rewatchScore'] == 60


def test_confusion_is_not_intentional_rewatch():
    result = evaluate(CASES['structurally_different'] + ' The ending is confusing and unexplained.')
    assert result['rewatchType'] == 'CONFUSION_REWATCH'
    assert result['rewatchScore'] == 10
    assert 'CONFUSION_REWATCH' in codes(result)


def test_short_useful_dialogue_does_not_reduce_visual_score():
    text = CASES['structurally_different']
    short = evaluate(text + ' Mimi says “Again?”')
    original = evaluate(text)
    assert 'DIALOGUE_LOAD' not in codes(short)
    assert short['shortFormScore'] == original['shortFormScore']
    assert short['dialogue']['words'] == 1


@pytest.mark.parametrize('extra,flag', [
    ('Mimi addresses the viewer in front-facing presenter blocking.', 'PRESENTER_BLOCKING'),
    ('Many characters perform fine finger interaction with tiny text in another room.', 'MANY_CHARACTERS'),
    ('A complex costume transformation and identity swap occur.', 'IDENTITY_CONTINUITY'),
])
def test_execution_and_production_risk_do_not_veto_strong_premise(extra, flag):
    text = CASES['structurally_different'] + ' ' + extra
    result = evaluate(text)
    assert flag in codes(result)
    assert result['status'] == 'PASS_WITH_WARNINGS'
    assert result['shortFormScore'] == evaluate(CASES['structurally_different'])['shortFormScore']


@pytest.mark.parametrize('text', ['Kiko wants to have fun. Kiko smiles.', 'Kiko hopes to be brave. Kiko runs.', 'Kiko learns something. She celebrates.'])
def test_vague_goals_are_not_everyday_goals(text):
    result = evaluate(text)
    assert result['goalScore'] == 0
    assert 'EVERYDAY_GOAL_UNCLEAR' in codes(result)


def test_negated_instructions_and_quoted_claims_do_not_establish_visual_causality():
    text = '0-3s: Kiko says “I want to sit on a giant upside-down chair.” No chair flips.\n3-15s: Kiko smiles.'
    result = evaluate(text)
    assert result['hookScore'] < 70
    assert result['goalScore'] == 0
    assert result['ruleClarityScore'] == 0


def test_eyes_huge_is_not_an_object_growth_rule():
    assert evaluate(WINNER)['rules'] == ['INVERSION']


def test_same_action_can_advance_when_its_visible_magnitude_or_consequence_changes():
    text = ('0-3s: Luca tries to retrieve the ball, but it is stuck to the wall. His eyes widen.\n'
            '3-6s: Luca pulls with both hands; the ball stays stuck.\n'
            '6-9s: Luca pulls harder; the ball stays stuck.\n'
            '9-12s: Luca pulls; the wall flexes and the ball stretches.\n'
            '12-15s: The ball drops onto his cheek and sticks there.')
    result = evaluate(text)
    assert result['majorCausalBeatCount'] == 5
    assert result['beats'][2]['materialProgress']
    assert not result['beats'][2]['newStrategy']
    assert result['status'] in {'PASS', 'PASS_WITH_WARNINGS'}
    assert 'IDENTICAL_ATTEMPTS' not in codes(result)


def test_unrelated_ordinary_reveal_is_not_a_rule_linked_payoff():
    text = CASES['structurally_different'].split('12-15s:')[0] + '12-15s: A new cat reveals a toy actually inside a basket.'
    result = evaluate(text)
    assert result['payoffScore'] == 15
    assert 'WEAK_VISUAL_PAYOFF' in codes(result)


def test_seven_causal_beats_trigger_overload_warning():
    text = ('0-2s: Mimi tries to close the lid, but it pops open.\n'
            '2-4s: Mimi pushes harder with both hands; it springs open and spills crumbs.\n'
            '4-6s: Mimi clamps the lid; it pops open and traps her arm.\n'
            '6-8s: Mimi wedges it behind her back; it pops open.\n'
            '8-10s: Mimi shakes the box; the lid pops open.\n'
            '10-12s: Mimi holds the lid; it pops open.\n'
            '12-15s: Mimi finally closes the lid and relaxes. The lid pops open again, recreating the opening.')
    result = evaluate(text)
    assert result['majorCausalBeatCount'] == 7
    assert 'TEMPORAL_OVERLOAD' in codes(result)
    assert result['status'] == 'PASS_WITH_WARNINGS'


def test_counting_and_prior_context_are_not_an_instant_visual_hook():
    text = CASES['structurally_different'].replace('Her eyes widen.', 'The problem requires counting objects and prior context.')
    result = evaluate(text)
    assert result['hookScore'] <= 20
    assert not result['alreadyInTrouble']


def test_repeated_action_with_explicit_growth_is_material_progress():
    text = ('0-3s: Kiko tries to eat a snack, but her spoon is huge. Her eyes widen.\n'
            '3-6s: Kiko lifts the spoon; it grows even bigger.\n'
            '6-9s: Kiko lifts the spoon; it grows even bigger.\n'
            '9-12s: Kiko lifts the spoon; it grows even bigger.\n'
            '12-15s: The giant spoon fills the frame and blocks Kiko from reaching her snack.')
    result = evaluate(text)
    assert result['majorCausalBeatCount'] == 5
    assert result['status'] == 'PASS'
    assert 'IDENTICAL_ATTEMPTS' not in codes(result)


def test_again_is_not_a_payoff_without_a_broken_resolution():
    result = evaluate(CASES['identical_attempts'].replace('12-15s: Kiko pushes the lid; it pops open.',
                                                        '12-15s: Kiko pushes the lid; it pops open again.'))
    assert result['payoffScore'] == 15


def test_explicit_two_second_normal_intro_is_not_frame_zero_trouble():
    text = CASES['structurally_different'].replace('0-3s:', '0-3s: After two seconds in a normal situation,')
    assert evaluate(text)['hookScore'] <= 20


def test_ordinary_negative_statement_is_not_a_visual_anomaly():
    text = '0-3s: Kiko tries to sit. The chair is not upside down.\n3-15s: Kiko smiles.'
    assert evaluate(text)['rules'] == []


@pytest.mark.parametrize('text', [
    '0-3s: Kiko sits.\n4-15s: Kiko smiles.',
    '0-5s: Kiko sits.\n3-15s: Kiko smiles.',
    '0-3s: Kiko sits.\n3-9s: Kiko smiles.',
    'Kiko sits.\nKiko smiles.',
])
def test_missing_or_overlapping_timing_cannot_pass_or_invent_a_curve(text):
    result = evaluate(text, desiredDuration=15)
    assert not result['timingVerifiedFromPlan']
    assert result['escalationCurve']['longestPlateauSeconds'] is None
    assert 'TIMING_UNVERIFIED' in codes(result)


@pytest.mark.parametrize('duration', [5, 30, 60])
def test_out_of_scope_duration_does_not_inherit_long_form_quality(duration):
    assert 'SHORT_DURATION_MISMATCH' in codes(evaluate(CASES['structurally_different'], desiredDuration=duration))


@pytest.mark.parametrize('name', list(CASES))
def test_every_beat_quote_is_exact_source_evidence_and_inputs_are_immutable(name):
    context = deepcopy(OPT_IN)
    text = CASES[name]
    first = assess(text, context)
    assert assess(text, context) == first
    assert context == OPT_IN
    for b in first['beats']:
        start, end = b['sourceSpan']
        assert text[start:end] == b['quote']


def test_reference_catalog_provenance_and_structure_are_reproducible():
    from app.workflow.short_form_engine import _features, _signature, _timeline
    refs = json.loads((ROOT / 'ml-service/app/workflow/short_form_references.json').read_text())
    for ref in refs:
        source = Path(__file__).parents[3] / ref['sourcePath']
        text = source.read_text()
        assert hashlib.sha256(text.encode()).hexdigest() == ref['sourceSha256']
        assert _signature([{**b, **_features(b['quote'])} for b in _timeline(text)]) == ref['signature']
