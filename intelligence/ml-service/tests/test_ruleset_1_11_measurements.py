"""Versioned measurement corrections: no invented substate times or passive payoff."""
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from app.config import settings
from app.parser.prompt_parser import ParserConfig, parse_prompt
from app.rules.rule_engine import RuleEngine
from app.workflow.review import _run_canonical_evaluation

ROOT = Path(__file__).resolve().parents[3] / 'output/verification/step6-exit-check'


def fixtures():
    a = json.loads((ROOT/'official-analysis.json').read_text())
    c = json.loads((ROOT/'official-comparison.json').read_text())
    return [('Original', a)] + [(x['candidateId'], x['review']) for x in c['candidates']]


@pytest.mark.parametrize('name,saved', fixtures())
def test_saved_inputs_preserve_1_10_and_correct_only_measurements(name, saved):
    q = {**saved['boundRequest'], 'prompt': saved['originalPrompt']}
    with patch('app.llm.semantic_checks.get_provider', side_effect=AssertionError('No provider')):
        old = _run_canonical_evaluation({**q, 'canonicalRulesetVersion':'1.10'})
        new = _run_canonical_evaluation({**q, 'canonicalRulesetVersion':'1.11'})
    assert json.loads(json.dumps(old)) == saved['canonicalRuleEvaluation']
    assert new['status'] == 'EVALUATED'
    assert new['score'] == pytest.approx(88.40625)
    def rows(result):
        groups = ['passedRules', 'failedRules', 'unknownRules', 'notApplicableRules']
        return {r['ruleId']: r for g in groups for r in result[g]}
    oo, nn = rows(old), rows(new)
    assert {k for k in oo if oo[k]['outcome'] != nn[k]['outcome']} == {
        'BEAT_004', 'CONTINUOUS_ACTION_MOMENTUM'
    }
    assert nn['BEAT_004']['outcome'] == 'UNKNOWN'
    assert nn['BEAT_004']['details']['substateTimes'] is None
    assert nn['CONTINUOUS_ACTION_MOMENTUM']['details']['finalAftermathSeconds'] == 0
    assert nn['ATTEMPT_001']['outcome'] == 'FAIL'


def engine():
    return RuleEngine(str(settings.rules_dir/'RULESET_1.11.yaml'))


def ir():
    saved = fixtures()[0][1]
    result = parse_prompt(saved['originalPrompt'], ParserConfig(
        attempt_evidence_policy='ACTOR_SOURCE_BOUND_V2', motion_evidence_policy='TOKEN_MOTION_V2'
    )).video_plan_ir
    result['metadata']['contentProfile'] = 'ABSURD_PHYSICS'
    return result


@pytest.mark.parametrize('text,motion,expected', [
    ('Zed sneezes and the cards fly.', 'moderate', 'PASS'),
    ('Zed stands still.', 'none', 'FAIL'),
    ('Zed does not sneeze; no cards fly.', 'none', 'FAIL'),
    ('Unspecified ending.', 'moderate', 'UNKNOWN'),
])
def test_active_payoff_passive_hold_negation_and_unknown(text, motion, expected):
    plan = ir()
    plan['beats'][-1].update(sourceAction=text, sourceQuote=text, motionAmount=motion)
    e = engine()
    rule = next(x for x in e.ruleset['rules'] if x['id']=='CONTINUOUS_ACTION_MOMENTUM')
    assert e._evaluate_continuous_action_momentum(plan, rule).outcome.value == expected


def test_real_static_state_keeps_threshold_and_failure():
    plan = deepcopy(ir())
    plan['beats'][2].update(sourceQuote='Zed stands on a mat, unchanged.', motionAmount='none')
    e = engine()
    rule = next(x for x in e.ruleset['rules'] if x['id']=='BEAT_004')
    result = e._evaluate_beat_004(plan, rule)
    assert result.outcome.value == 'FAIL'
    assert result.threshold_value == 30
