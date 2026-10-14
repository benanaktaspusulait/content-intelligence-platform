"""Motion semantics are versioned; text motion estimates are not render evidence."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.parser.prompt_parser import ParserConfig, PromptParser
from app.workflow.review import _run_canonical_evaluation

ROOT = Path(__file__).resolve().parents[3] / 'output/verification/attempt-extraction-1.9'
NEW = ParserConfig(attempt_evidence_policy='ACTOR_SOURCE_BOUND_V2', motion_evidence_policy='TOKEN_MOTION_V2')


@pytest.mark.parametrize('text,expected', [
    ('The note flies.', 'moderate'), ('The notes scatter.', 'moderate'),
    ('The cards scatter.', 'moderate'), ('Zed notices a knot.', 'moderate'),
    ('No dialogue. The notes fly.', 'moderate'), ('No pause: Zed pulls.', 'moderate'),
    ('Zed is still pulling.', 'moderate'), ('Zed stands still.', 'none'),
    ('No movement.', 'none'), ('The subject is motionless.', 'none'),
    ('[static close-up; keep the cabinet visible] Zed pulls.', 'moderate'),
    ('The camera remains still; Zed pulls.', 'moderate'),
    ('[static camera] Zed stands still.', 'none'),
    ('The notes move rapidly.', 'high'), ('The notes move slowly.', 'minimal'),
    ('The stillness is ominous.', 'moderate'),
])
def test_motion_tokens_and_camera_scope(text, expected):
    assert PromptParser(NEW)._estimate_motion_amount(text) == expected


def evaluations(result):
    groups = ['passedRules', 'failedRules', 'unknownRules', 'notApplicableRules']
    return {r['ruleId']: r for group in groups for r in result[group]}


def saved_cases():
    original = json.loads((ROOT / 'official-analysis.json').read_text())
    comparison = json.loads((ROOT / 'official-comparison.json').read_text())
    return [('Original', original)] + [(c['candidateId'], c['review']) for c in comparison['candidates']]


@pytest.mark.parametrize('name,saved', saved_cases())
def test_saved_workflow_and_frozen_history(name, saved):
    request = {**saved['boundRequest'], 'prompt': saved['originalPrompt']}
    with patch('app.llm.semantic_checks.get_provider', side_effect=AssertionError('No paid provider')):
        historical = _run_canonical_evaluation({**request, 'canonicalRulesetVersion': '1.9'})
        current = _run_canonical_evaluation({**request, 'canonicalRulesetVersion': '1.10'})
    assert json.loads(json.dumps(historical)) == saved['canonicalRuleEvaluation']
    assert current['status'] == 'EVALUATED' and current['rulesEvaluated'] == 46
    assert current['score'] == pytest.approx(84.20833333333334)
    old, new = evaluations(historical), evaluations(current)
    assert [k for k in old if old[k]['outcome'] != new[k]['outcome']] == ['MOTION_001']
    assert new['ATTEMPT_001']['outcome'] == 'FAIL'
    assert 'Only 2 active attempt(s)' in new['ATTEMPT_001']['message']
    assert new['CONTINUOUS_ACTION_MOMENTUM']['outcome'] == 'FAIL'
    assert new['CONTINUOUS_ACTION_MOMENTUM']['details']['passiveSeconds'] == 0
    assert new['CONTINUOUS_ACTION_MOMENTUM']['details']['finalAftermathSeconds'] == 3
    assert all(b['motionAmount'] == 'moderate' for b in current['videoPlanIR']['beats'])
