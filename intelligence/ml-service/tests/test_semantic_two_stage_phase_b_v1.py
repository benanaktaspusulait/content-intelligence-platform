"""Mocked one-request checks for expanding the previously stored accepted seed."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
SERVICE = ROOT / 'intelligence/ml-service'
sys.path.insert(0, str(SERVICE))
sys.path.insert(0, str(ROOT / 'intelligence/scripts'))
MODULE_PATH = ROOT / 'intelligence/scripts/run-semantic-two-stage-phase-b-v1.py'
SPEC = importlib.util.spec_from_file_location('phase_b_once', MODULE_PATH)
phase_b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(phase_b)


def matching_story(context):
    mocks = json.loads((SERVICE / 'tests/fixtures/semantic_two_stage_v1_mocks.json').read_text())
    story = deepcopy(mocks['consistentExpansion'])
    from app.workflow.semantic_two_stage_v1 import FROZEN_FIELDS
    for field in FROZEN_FIELDS:
        story[field] = getattr(context['seed'], field)
    for beat in story['beats']:
        for field, value in beat.items():
            beat[field] = value.replace('Kiko', 'Mimi').replace('hammer', 'rolling pin').replace('Hammer', 'Rolling pin').replace('nail', 'dough').replace('wall', 'dough wall')
    story['finalPayoff'] = story['beats'][-1]['visibleConsequence']
    story['providerRationale'] = 'The rolling pin pressure lifts dough into a wall as it moves.'
    return story


def test_loads_exact_stored_seed_and_builds_one_low_phase_b_request():
    context = phase_b.build_context()
    assert context['seed'].seedId == 'mimi-rolling-pin-dough-wall'
    assert context['sourceSeedSha256'] == phase_b.sha256_bytes(phase_b.SOURCE_SEED_PATH.read_bytes())
    assert context['savedGate']['seedSha256'] == context['sourceSeedCanonicalSha256']
    assert context['currentGate']['acceptedForExpansion'] is True
    assert context['currentGate']['openingScore'] == 90
    spec = context['spec']
    assert spec['phase'] == 'B'
    assert spec['arguments']['model'] == 'gpt-6.1-sol'
    assert spec['arguments']['reasoning_effort'] == 'low'
    assert spec['arguments']['max_completion_tokens'] == 8192
    assert spec['arguments']['response_format']['type'] == 'json_schema'
    payload = json.loads(spec['prompt']['prompt'])
    assert payload['frozenOpeningSeed'] == context['seed'].model_dump()
    assert payload['frozenFields']


def test_exactly_one_mocked_expansion_request_and_no_second_attempt(tmp_path):
    context = phase_b.build_context()
    story = matching_story(context)
    raw = json.dumps({'ideas': [story]})
    calls = []

    def runner(path, profile, spec):
        calls.append((profile['provider'], spec['phase']))
        (path / 'response.txt').write_text(raw)
        return dict(status='COMPLETED', httpStatus=200, SDKRequestsForwarded=1,
            HTTPRequestsObserved=1, finishReason='stop', usage=dict(prompt_tokens=12, completion_tokens=42, total_tokens=54))

    directory = tmp_path / 'single-phase-b'
    result = phase_b.execute_once(context, runner, directory)
    assert calls == [('openai', 'B')]
    assert result['requestCount'] == result['execution']['SDKRequestsForwarded'] == 1
    assert result['execution']['HTTPRequestsObserved'] == 1
    assert result['execution']['retries'] == result['execution']['fallbacks'] == result['execution']['DeepSeekCalls'] == result['execution']['renders'] == 0
    assert result['analysis']['drift']['status'] == 'PRESERVED'
    audit = result['storyAudit']
    assert audit['pipelineRecordPresent'] and len(audit['ruleConsistency']) == 4
    assert all(row['consistency'] in {'CONSISTENT', 'AMBIGUOUS', 'INCONSISTENT'} for row in audit['ruleConsistency'])
    assert set(audit['payoffOrientation']) >= {'beforeState', 'trigger', 'afterState', 'classification'}
    with pytest.raises(FileExistsError):
        phase_b.execute_once(context, runner, directory)
    assert calls == [('openai', 'B')]


def test_one_failed_mock_request_is_terminal_with_no_retry_or_fallback(tmp_path):
    context = phase_b.build_context();calls=[]
    def fail_once(path, profile, spec):
        calls.append(spec['phase'])
        raise TimeoutError('mock timeout')
    result = phase_b.execute_once(context, fail_once, tmp_path / 'failed-phase-b')
    assert calls == ['B']
    assert result['execution']['status'] == 'FAILED'
    assert result['requestCount'] == 1
    assert result['execution']['retries'] == result['execution']['fallbacks'] == result['execution']['DeepSeekCalls'] == result['execution']['renders'] == 0
    assert result['analysis'] is None
    assert json.loads((tmp_path / 'failed-phase-b/analysis.json').read_text())['status'] == 'NO_COMPLETED_RESPONSE'


def test_every_frozen_field_is_preserved_or_classified_as_seed_drift():
    from app.workflow import semantic_two_stage_v1 as stage
    context = phase_b.build_context()
    mocks = json.loads((SERVICE / 'tests/fixtures/semantic_two_stage_v1_mocks.json').read_text())
    story = deepcopy(mocks['consistentExpansion'])
    for field in stage.FROZEN_FIELDS:
        story[field] = getattr(context['seed'], field)
    assert stage.expansion_drift(context['frozen'], story)['status'] == 'PRESERVED'
    for field in stage.FROZEN_FIELDS:
        changed = deepcopy(story); changed[field] = 'Changed frozen seed field.'
        result = stage.expansion_drift(context['frozen'], changed)
        assert result['status'] == 'EXPANSION_SEED_DRIFT'
        assert any(item['field'] == field for item in result['differences'])
        assert result['repairPerformed'] is False


def test_existing_full_story_schema_enforces_beats_duration_and_payoff_contract():
    from app.workflow.semantic_native_schema_integrity_v1 import native_response_format
    schema = native_response_format(1)['json_schema']['schema']
    validator = Draft202012Validator(schema)
    mocks = json.loads((SERVICE / 'tests/fixtures/semantic_two_stage_v1_mocks.json').read_text())
    story = deepcopy(mocks['consistentExpansion'])
    assert len(story['beats']) == 4 and story['durationSeconds'] == 15
    for count, valid in ((3, False), (4, True), (5, True), (6, False)):
        candidate = deepcopy(story); candidate['beats'] = (candidate['beats'] * 2)[:count]
        assert validator.is_valid({'ideas': [candidate]}) is valid
    for seconds, valid in ((9, False), (10, True), (15, True), (20, True), (21, False)):
        candidate = deepcopy(story); candidate['durationSeconds'] = seconds
        assert validator.is_valid({'ideas': [candidate]}) is valid
    candidate = deepcopy(story); candidate['beats'][-1]['visibleConsequence'] = 'A mirror appears.'
    candidate['finalPayoff'] = candidate['beats'][-1]['visibleConsequence']
    assert validator.is_valid({'ideas': [candidate]})
    assert candidate['finalPayoff'] == candidate['beats'][-1]['visibleConsequence']


def test_payoff_rule_mutation_is_detected_without_repair():
    from app.workflow import semantic_two_stage_v1 as stage
    context = phase_b.build_context(); story = matching_story(context)
    prompt = context['spec']['prompt']
    story['beats'][-1]['visibleConsequence'] = 'The rolling pin becomes a mirror and reveals a second magical rule.'
    story['finalPayoff'] = story['beats'][-1]['visibleConsequence']
    result = stage.analyze_expansion(json.dumps({'ideas': [story]}), context['frozen'], context['config'], prompt)
    assert result['status'] == 'EXPANSION_RULE_INCONSISTENT'
    assert not result['pipelineRan']
