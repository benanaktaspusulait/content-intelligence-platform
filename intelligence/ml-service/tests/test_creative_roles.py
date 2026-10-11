import json
import os
import pytest
from app.workflow.creative_roles import migrate_legacy_production_spec, perform_role, run_paid_role, role_readiness

class FixtureProvider:
    def __init__(self, result): self.result = result; self.calls = []
    def complete(self, prompt, system='', temperature=0, image=None):
        self.calls.append((json.loads(prompt), system))
        return json.dumps(self.result)


def production_fixture(source='Mimi stands by the toy cabinet. A sticky note sticks to her paw.'):
    beats = [
        ('0-3s', 'Mimi stands by the cabinet.', 'Mimi stands by the toy cabinet.'),
        ('3-6s', 'A note sticks to her face.', 'A sticky note sticks to her paw.'),
        ('6-9s', 'Mimi removes the note.', 'A sticky note sticks to her paw.'),
        ('9-12s', 'Notes return to Mimi.', 'A sticky note sticks to her paw.'),
        ('12-15s', 'Mimi is covered by notes.', 'A sticky note sticks to her paw.'),
    ]
    prompt = ('TITLE / FORMAT 15 seconds 9:16.\n\nVISUAL STYLE grounded.\n\nCHARACTER / CONTINUITY Mimi remains the same character.\n\n'
              'TIMED SHOT PLAN 0-3s close camera; 3-6s medium shot; 6-9s shot; 9-12s shot; 12-15s ending.\n\n'
              'AUDIO simple sound.\n\nNEGATIVE CONSTRAINTS no extra characters.\n\nFINAL CUT hard cut.')
    plan = {'sourceIdentity': {'title': 'Mimi Sticky Note Adventure'}, 'creativeObjective': 'Make a funny animation.',
            'characterBindings': [{'name': 'Mimi', 'status': 'active'}],
            'visualExecution': {'openingState': 'Close on Mimi.', 'mechanism': 'Notes stick to Mimi.', 'continuity': 'Keep Mimi visible.', 'endingState': 'Hard cut.',
                                'beats': [{'time': t, 'framing': 'medium', 'action': action, 'staging': 'Near the cabinet.', 'consequence': action,
                                           'sourceEvidence': quote, 'sourceRelationship': 'FAITHFUL_ADAPTATION', 'importance': 'CORE'} for t, action, quote in beats]},
            'productionConstraints': {}, 'intentClassification': {'status': 'PRESERVE'}, 'evidenceLimitations': [],
            'generatorRisks': ['Potential for animation to not capture humor.'], 'referencePlan': {}}
    return {'prompt': prompt, 'productionPlan': plan}


def test_creative_role_accepts_json_fenced_by_configured_text_endpoint():
    provider = FixtureProvider({'alternatives': ['A grounded story']})
    provider.complete = lambda prompt, system='', temperature=0, image=None: '```json\n{"alternatives":["A grounded story"]}\n```'
    response = perform_role('STORY', 'Idea', {}, provider, 'configured-model')
    assert response['result']['alternatives'] == ['A grounded story']


def test_creative_role_reports_empty_provider_response():
    provider = FixtureProvider({})
    provider.complete = lambda prompt, system='', temperature=0, image=None: ''
    with pytest.raises(ValueError, match='empty JSON response'):
        perform_role('STORY', 'Idea', {}, provider, 'configured-model')


def test_story_candidates_are_bounded_when_provider_overproduces():
    provider = FixtureProvider({'alternatives': ['one', 'two', 'three', 'four']})
    response = perform_role('STORY', 'Idea', {}, provider, 'configured-model')
    assert len(response['result']['alternatives']) == 3

@pytest.mark.parametrize('role,result,provider_name', [
    ('STORY', {'alternatives': ['A grounded story']}, 'deepseek'),
    ('BUILD_PROMPT', {'prompt': 'TITLE / FORMAT 15 seconds 9:16.\n\nVISUAL STYLE grounded.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera close shot; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO and sound.\n\nNEGATIVE CONSTRAINTS.\n\nFINAL CUT hard cut.', 'productionPlan': {'sourceIdentity': {'storyRevisionId': 'fixture'}, 'creativeObjective': 'Make the note movement readable.', 'characterBindings': [{'name': 'Mimi', 'status': 'supplied'}], 'visualExecution': {'openingState': 'Mimi is visible.', 'beats': [{'time': '0-3s', 'framing': 'close shot', 'action': 'Mimi holds a note.', 'staging': 'cabinet behind her.', 'consequence': 'setup visible.'}, {'time': '3-6s', 'framing': 'medium shot', 'action': 'note flips.', 'staging': 'in front of cabinet.', 'consequence': 'note reaches face.'}, {'time': '6-10s', 'framing': 'medium shot', 'action': 'Mimi reacts.', 'staging': 'center frame.', 'consequence': 'escalation.'}, {'time': '10-13s', 'framing': 'wide shot', 'action': 'notes multiply.', 'staging': 'around Mimi.', 'consequence': 'coverage grows.'}, {'time': '13-15s', 'framing': 'wide shot', 'action': 'Mimi is covered.', 'staging': 'cabinet behind her.', 'consequence': 'hard cut.'}], 'mechanism': 'Notes move visibly.', 'continuity': 'Mimi remains visible.', 'endingState': 'Hard cut.'}, 'productionConstraints': {'duration': 15, 'aspectRatio': '9:16'}, 'intentClassification': {'status': 'PRESERVE'}, 'evidenceLimitations': [], 'generatorRisks': [], 'referencePlan': {'status': 'NO_REFERENCE_SUPPLIED'}}}, 'openai'),
    ('MINIMAL_REPAIR', {'patches': [{'start': 0, 'end': 3, 'sourceQuote': 'CUT', 'replacement': 'Hold'}]}, 'openai'),
])
def test_roles_route_explicitly_and_never_self_validate(role, result, provider_name):
    provider = FixtureProvider(result)
    response = perform_role(role, 'CUT at end', {'retrievedLessons': [{'recordId': 'verified'}]}, provider, 'configured-model')
    assert response['provider'] == provider_name
    assert response['validationStatus'] == 'NOT_VALIDATED'
    assert response['visualInspected'] is False
    assert len(provider.calls) == 1
    assert provider.calls[0][0]['context']['retrievedLessons'][0]['recordId'] == 'verified'


def test_build_prompt_canonicalizes_provider_prompt_alias():
    result = {
        'productionPrompt': 'TITLE / FORMAT 15 seconds 9:16.\n\nVISUAL STYLE bright.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera close shot; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO playful sound.\n\nNEGATIVE CONSTRAINTS no extra characters.\n\nFINAL CUT hard cut.',
        'productionPlan': {
            'sourceIdentity': {}, 'creativeObjective': 'Make the action readable.',
            'characterBindings': [], 'visualExecution': {
                'openingState': 'Mimi is visible.', 'mechanism': 'Notes move visibly.',
                'continuity': 'Mimi remains visible.', 'endingState': 'Hard cut.',
                'beats': [{'time': time, 'framing': 'medium shot', 'action': 'Action.', 'staging': 'Center frame.', 'consequence': 'The beat advances.'}
                          for time in ('0-3s', '3-6s', '6-10s', '10-13s', '13-15s')]
            },
            'productionConstraints': {}, 'intentClassification': {}, 'evidenceLimitations': ['No visual reference supplied'],
            'generatorRisks': ['Keep the notes readable.'], 'referencePlan': {}
        }
    }
    response = perform_role('BUILD_PROMPT', 'Mimi opens a box.', {}, FixtureProvider(result), 'configured-model')
    assert response['result']['prompt'].startswith('TITLE / FORMAT')

def test_build_prompt_canonicalizes_nested_provider_response():
    prompt = 'TITLE / FORMAT 15 seconds 9:16.\n\nVISUAL STYLE bright.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera close shot; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO playful sound.\n\nNEGATIVE CONSTRAINTS no extra characters.\n\nFINAL CUT hard cut.'
    plan = {'sourceIdentity': {}, 'creativeObjective': 'Make the action readable.', 'characterBindings': [], 'visualExecution': {'openingState': 'Mimi is visible.', 'mechanism': 'Notes move visibly.', 'continuity': 'Mimi remains visible.', 'endingState': 'Hard cut.', 'beats': [{'time': time, 'framing': 'medium shot', 'action': 'Action.', 'staging': 'Center frame.', 'consequence': 'The beat advances.'} for time in ('0-3s', '3-6s', '6-10s', '10-13s', '13-15s')]}, 'productionConstraints': {}, 'intentClassification': {}, 'evidenceLimitations': ['No visual reference supplied'], 'generatorRisks': ['Keep the notes readable.'], 'referencePlan': {}}
    response = perform_role('BUILD_PROMPT', 'Mimi opens a box.', {}, FixtureProvider({'result': {'production_prompt': prompt, 'production_plan': plan}}), 'configured')
    assert response['result']['prompt'] == prompt
    enriched = response['result']['productionPlan']
    assert enriched['sourceIdentity']['projectTitle'] == 'UNKNOWN'
    assert enriched['fieldProvenance']['visualExecution'] == 'AI_DERIVED'
    assert enriched['visualExecution']['beats'][0]['sourceRelationship'] == 'UNKNOWN'


def test_build_prompt_rejects_conflicting_confirmed_aspect_ratio():
    result = {
        'prompt': 'TITLE / FORMAT 15 seconds 16:9.\n\nVISUAL STYLE bright.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO playful sound.\n\nNEGATIVE CONSTRAINTS no extra characters.\n\nFINAL CUT hard cut.',
        'productionPlan': {'sourceIdentity': {}, 'creativeObjective': 'x', 'characterBindings': [], 'visualExecution': {'openingState': 'x', 'mechanism': 'x', 'continuity': 'x', 'endingState': 'x', 'beats': [{'time': t, 'framing': 'x', 'action': 'x', 'staging': 'x', 'consequence': 'x'} for t in ('0-3s','3-6s','6-10s','10-13s','13-15s')]}, 'productionConstraints': {'aspectRatio': '16:9'}, 'intentClassification': {}, 'evidenceLimitations': ['x'], 'generatorRisks': ['x'], 'referencePlan': {}}
    }
    with pytest.raises(ValueError, match='confirmed settings'):
        perform_role('BUILD_PROMPT', 'Mimi story', {'targetConfiguration': {'aspectRatio': '9:16'}}, FixtureProvider(result), 'configured')

def test_build_prompt_completes_missing_confirmed_aspect_ratio():
    result = {
        'prompt': 'TITLE / FORMAT 15 seconds.\n\nVISUAL STYLE bright.\n\nCHARACTER / CONTINUITY Mimi remains visible.\n\nTIMED SHOT PLAN: 0-3s opening camera; 3-6s action; 6-10s escalation; 10-13s reveal; 13-15s ending.\n\nAUDIO playful sound.\n\nNEGATIVE CONSTRAINTS no extra characters.\n\nFINAL CUT hard cut.',
        'productionPlan': {'sourceIdentity': {}, 'creativeObjective': 'x', 'characterBindings': [], 'visualExecution': {'openingState': 'x', 'mechanism': 'x', 'continuity': 'x', 'endingState': 'x', 'beats': [{'time': t, 'framing': 'x', 'action': 'x', 'staging': 'x', 'consequence': 'x'} for t in ('0-3s','3-6s','6-10s','10-13s','13-15s')]}, 'productionConstraints': {}, 'intentClassification': {}, 'evidenceLimitations': ['x'], 'generatorRisks': ['x'], 'referencePlan': {}}
    }
    response = perform_role('BUILD_PROMPT', 'Mimi story', {'targetConfiguration': {'aspectRatio': '9:16'}}, FixtureProvider(result), 'configured')
    assert 'Aspect ratio: 9:16.' in response['result']['prompt']
    assert response['result']['productionPlan']['productionConstraints']['aspectRatio'] == '9:16'


def test_mimi_identity_title_provenance_and_missing_reference_are_explicit():
    source = 'A sticky note sticks to Mimi, then other notes multiply, fly back and follow her.'
    result = production_fixture(source)
    context = {'sourceStoryRecordId': 'story-1', 'storyRevisionId': 'candidate-1-revision-a', 'storyTitle': "Mimi's Sticky Note Mystery",
               'mainCharacter': 'Mimi', 'promptBuilderContractVersion': 'openart-production-prompt-v2', 'characterRecord': {'id': 'mimi-id', 'name': 'Mimi', 'status': 'UNTESTED'},
               'targetConfiguration': {'duration': 15, 'aspectRatio': '9:16', 'selectedGenerator': 'SEEDANCE_2_0_MINI', 'contentProfile': 'ABSURD_PHYSICS', 'mainCharacter': 'Mimi'}}
    response = perform_role('BUILD_PROMPT', source, context, FixtureProvider(result), 'fixture')
    plan = response['result']['productionPlan']
    binding = plan['characterBindings'][0]
    assert binding['identityRequirement'].startswith('Anthropomorphic bunny')
    assert binding['referenceStatus'] == 'MISSING_VERIFIED_REFERENCE'
    assert 'anthropomorphic bunny' in response['result']['prompt']
    assert plan['sourceIdentity']['projectTitle'] == "Mimi's Sticky Note Mystery"
    assert plan['sourceIdentity']['narrativeTitle'] == 'Mimi Sticky Note Adventure'
    assert plan['builderContractVersion'] == 'openart-production-prompt-v2'
    assert plan['fieldProvenance']['visualExecution'] == 'AI_DERIVED'
    assert plan['fieldProvenance']['sourceIdentity'] == 'SYSTEM_VERIFIED'
    assert plan['visualExecution']['timelineIntegrity']['status'] == 'COMPLETE'
    assert plan['mechanismAssessment']['causalStatus'] == 'MULTIPLE_EFFECTS_CAUSAL_LINK_UNCLEAR'
    assert 'not mandatory' in plan['creativeObjective']


def test_incomplete_timeline_and_missing_beat_quotes_remain_unknown():
    result = production_fixture('A character opens a drawer. A ball rolls out.')
    result['productionPlan']['visualExecution']['beats'] = result['productionPlan']['visualExecution']['beats'][:3]
    result['productionPlan']['visualExecution']['beats'][0]['sourceEvidence'] = 'invented quote'
    source = 'A character opens a drawer. A ball rolls out.'
    response = perform_role('BUILD_PROMPT', source, {'targetConfiguration': {'duration': 15}}, FixtureProvider(result), 'fixture')
    plan = response['result']['productionPlan']
    assert plan['visualExecution']['timelineIntegrity']['status'] == 'INCOMPLETE'
    assert plan['visualExecution']['beats'][0]['evidenceStatus'] == 'UNKNOWN'
    assert any(item['code'] == 'TIMED_PLAN_INCOMPLETE' for item in response['result']['qualityFindings'])


def test_build_prompt_rejects_overlapping_timing_and_material_story_deviation():
    result = production_fixture()
    result['productionPlan']['visualExecution']['beats'][1]['time'] = '2-6s'
    with pytest.raises(ValueError, match='overlapping'):
        perform_role('BUILD_PROMPT', 'Mimi stands by a toy cabinet.', {}, FixtureProvider(result), 'fixture')
    result = production_fixture()
    result['productionPlan']['visualExecution']['beats'][0]['sourceRelationship'] = 'MATERIAL_CREATIVE_DEVIATION'
    with pytest.raises(ValueError, match='material creative deviation'):
        perform_role('BUILD_PROMPT', 'Mimi stands by a toy cabinet.', {}, FixtureProvider(result), 'fixture')


def test_generator_capability_contract_is_read_from_configured_metadata(tmp_path, monkeypatch):
    catalog = {'version': 'fixture-contract', 'models': {'SEEDANCE_2_0_MINI': {'apiModelId': 'mini', 'version': 'snapshot',
               'modes': {'image2video': {'properties': {'duration': {'minimum': 4, 'maximum': 15},
               'aspectRatio': {'enum': ['9:16']}, 'startFrame': {}}}}}}}
    (tmp_path / 'workflow').mkdir()
    (tmp_path / 'workflow' / 'provider-capabilities.json').write_text(json.dumps(catalog))
    monkeypatch.setenv('POMPOM_DATA_ROOT', str(tmp_path))
    result = production_fixture()
    context = {'targetConfiguration': {'duration': 15, 'aspectRatio': '9:16', 'selectedGenerator': 'SEEDANCE_2_0_MINI'}}
    provider = FixtureProvider(result)
    response = perform_role('BUILD_PROMPT', 'Mimi sticks a note on a toy cabinet.', context, provider, 'fixture')
    capability = response['result']['productionPlan']['generatorCapabilityAssessment']
    assert capability['duration']['supported'] is True
    assert capability['aspectRatio']['status'] == 'SUPPORTED'
    assert capability['source'] == 'snapshot'
    assert provider.calls[0][0]['context']['generatorCapabilities']['duration'] == {'minimum': 4, 'maximum': 15}

def test_invalid_patch_quote_is_rejected():
    provider = FixtureProvider({'patches': [{'start': 0, 'end': 3, 'sourceQuote': 'wrong', 'replacement': 'Hold'}]})
    with pytest.raises(ValueError): perform_role('MINIMAL_REPAIR', 'CUT', {}, provider, 'configured')

def test_paid_roles_require_explicit_server_enablement(monkeypatch):
    monkeypatch.delenv('WORKFLOW_CREATIVE_ROLES_ENABLED', raising=False)
    assert role_readiness()['enabled'] is False
    with pytest.raises(ValueError, match='disabled'): run_paid_role('STORY', 'Idea', {}, 1)

def test_visual_input_is_rejected_before_any_provider_call():
    provider = FixtureProvider({'prompt': 'text'})
    with pytest.raises(ValueError, match='text-only'): perform_role('BUILD_PROMPT', 'Story', {'video': 'clip'}, provider, 'configured')
    assert not provider.calls


def test_cost_ceiling_is_checked_before_constructing_paid_provider(monkeypatch):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_INPUT_USD_PER_MILLION', '1000')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_OUTPUT_USD_PER_MILLION', '1000')
    with pytest.raises(ValueError, match='cost ceiling'):
        run_paid_role('BUILD_PROMPT', 'Story', {}, 0.001)


def test_paid_repair_enforces_json_at_provider_boundary(monkeypatch):
    from unittest.mock import MagicMock, patch
    monkeypatch.setenv('OPENAI_API_KEY', 'fixture-key')
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_MINIMAL_REPAIR_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_MINIMAL_REPAIR_INPUT_USD_PER_MILLION', '0.15')
    monkeypatch.setenv('WORKFLOW_MINIMAL_REPAIR_OUTPUT_USD_PER_MILLION', '0.6')
    content = json.dumps({'patches': [{'start': 0, 'end': 3, 'sourceQuote': 'CUT', 'replacement': 'Hold'}]})
    with patch('app.llm.openai_provider.OpenAI') as sdk:
        client = sdk.return_value
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=content))], usage=None)
        result = run_paid_role('MINIMAL_REPAIR', 'CUT at end', {}, 0.01)
        request = client.chat.completions.create.call_args.kwargs
        assert request['response_format'] == {'type': 'json_object'}
        assert request['max_tokens'] == 2000
        client.chat.completions.create.assert_called_once()
        assert result['result']['patches'][0]['sourceQuote'] == 'CUT'
        assert result['validationStatus'] == 'NOT_VALIDATED'


def test_legacy_production_spec_migration_is_provider_free_and_recovers_only_exact_text_evidence():
    source = ('Mimi stands before a messy toy cabinet, a single sticky note already stuck to her paw. '
              'She tries to stick it on the cabinet, but it twists mid-air and lands on her face. '
              'She peels it off and tries again; now notes stick to her other paw and ear. '
              'She pulls them off quickly, but they multiply and fly back, covering her arms. '
              'She hides behind the cabinet, but the notes follow and stick to her. '
              'In the final beat, a swarm covers her completely, leaving only her wide eyes visible. Hard cut.')
    prompt = ("Mimi's Sticky Note Adventure/ANIMATION (15s, 9:16), TIMED SHOT PLAN: "
              '0-3s: CLOSE-UP on Mimi in front of the cabinet, with one sticky note already stuck to her paw. '
              '3-6s: MEDIUM SHOT as Mimi throws the sticky note towards the cabinet; it twists mid-air and lands on her face. '
              '6-10s: CLOSE-UP as Mimi peels the note away and more notes stick to her other paw and ear. '
              '10-13s: MEDIUM SHOT as Mimi pulls notes off, but they multiply and fly back onto her arms. '
              '13-15s: WIDE SHOT as Mimi hides behind the cabinet and the notes cover her, leaving only her eyes visible. '
              'AUDIO playful music. NEGATIVE CONSTRAINTS no distractions. FINAL CUT hard cut.')
    context = {
        'sourceIdentity': {'storyRecordId': 'story-1', 'storyRevisionId': 'rev-1', 'approvalRecordId': 'approval-1',
                           'savedPromptRecordId': 'prompt-1', 'storyTitle': 'Sticky Note Rebellion', 'projectTitle': "Mimi's Studio"},
        'targetConfiguration': {'duration': 15, 'aspectRatio': '9:16', 'selectedGenerator': 'SEEDANCE_2_0_MINI', 'contentProfile': 'ABSURD_PHYSICS', 'mainCharacter': 'Mimi'},
        'mainCharacter': 'Mimi', 'characterRecord': {'id': 'character-1', 'catalogVerified': True},
        'generatorCapabilities': {'apiModelId': 'mini', 'version': 'fixture-v1', 'modes': {'image2video': {'properties': {
            'duration': {'minimum': 4, 'maximum': 15}, 'aspectRatio': {'enum': ['9:16']}, 'startFrame': {}}}}},
    }
    first = migrate_legacy_production_spec(prompt, source, context)
    second = migrate_legacy_production_spec(prompt, source, context)
    plan = first['productionPlan']
    beats = plan['visualExecution']['beats']
    assert first['providerCalls'] == second['providerCalls'] == 0
    assert first['prompt'] == prompt
    assert len(beats) == 5
    assert beats[0]['time'] == '0-3s' and beats[-1]['time'] == '13-15s'
    assert beats[0]['sourceEvidenceOffsets'] is not None
    assert 'stick to her other paw and ear' in beats[2]['stateChange']
    assert beats[2]['stateChangeStatus'] == 'PROMPT_SUPPORTED_ONLY'
    assert 'multiply and fly back' in beats[3]['stateChange']
    assert beats[3]['stateChangeStatus'] == 'PROMPT_SUPPORTED_ONLY'
    assert 'cover her, leaving only her eyes visible' in beats[4]['stateChange']
    assert beats[4]['stateChangeStatus'] == 'PROMPT_SUPPORTED_ONLY'
    evidence = beats[0]['sourceEvidence']
    offsets = beats[0]['sourceEvidenceOffsets']
    assert source[offsets['start']:offsets['end']] == evidence
    assert not evidence.endswith('She')
    assert beats[0]['sourceRelationship'] == 'UNKNOWN'
    assert beats[0]['evidenceStatus'] == 'SOURCE_TEXT_OVERLAP_ONLY'
    assert 'lands on her face' in beats[1]['stateChange']
    assert beats[1]['stateChangeStatus'] == 'PROMPT_SUPPORTED_ONLY'
    assert beats[1]['stateChangeEvidenceSource'] == 'SAVED_PROMPT_TEXT'
    assert plan['storyPromptFidelity']['status'] == 'NOT_EVALUATED'
    assert plan['storyPromptFidelity']['sourceSentenceCount'] is None
    assert plan['openingAssessment']['imageEvidence'] == 'UNKNOWN_NOT_GENERATED'
    assert plan['openingAssessment']['status'] == 'PLANNED_TEXT_ONLY_NOT_EVALUATED'
    assert 'Mimi in front of the cabinet' in plan['openingAssessment']['openingText']
    assert plan['characterBindings'][0]['identityStatus'] == 'CATALOG_CONFIRMED'
    assert plan['characterBindings'][0]['referenceStatus'] == 'MISSING_OR_UNVERIFIED'
    capability = plan['generatorCapabilityAssessment']
    assert capability['duration']['supported'] is True
    assert capability['aspectRatio']['status'] == 'SUPPORTED'
    assert capability['startFrameFieldSupported'] is True
    assert capability['liveVerified'] is False
    assert plan['fieldProvenance']['providerCapabilities'] == 'fixture-v1'
    assert plan['visualExecution']['timelineIntegrity']['status'] == 'PROMPT_RANGES_STRUCTURALLY_VALID'
    risk_names = {item['risk'] for item in plan['generatorRisks']}
    assert {'Repeated sticky-note contact', 'Sticky-note placement continuity', 'Simultaneous action complexity', 'Object-count continuity', 'Returning-note path', 'Cabinet occlusion', 'Final facial visibility', 'Final-state continuity'} <= risk_names
    assert all(item['severity'] == 'ADVISORY' and item['blocker'] is False for item in plan['generatorRisks'])


def test_legacy_migration_does_not_guess_missing_ancestry_or_semantics():
    migrated = migrate_legacy_production_spec('0-3s: Mimi stands by the cabinet. 3-5s: Mimi waves.', '', {
        'sourceIdentity': {}, 'targetConfiguration': {'duration': 5, 'aspectRatio': '9:16'},
        'mainCharacter': 'Mimi', 'characterRecord': {}, 'characterReferences': [],
        'generatorCapabilities': {'status': 'UNKNOWN', 'source': 'manifest unavailable'},
    })
    plan = migrated['productionPlan']
    assert plan['sourceIdentity']['storyRecordId'] == 'UNKNOWN'
    assert plan['sourceIdentity']['approvalRecordId'] == 'UNKNOWN'
    assert all(beat['sourceEvidence'] == '' for beat in plan['visualExecution']['beats'])
    assert all(beat['sourceRelationship'] == 'UNKNOWN' for beat in plan['visualExecution']['beats'])
    assert plan['storyPromptFidelity']['status'] == 'NOT_EVALUATED'
    assert plan['generatorCapabilityAssessment']['status'] == 'UNKNOWN'
    assert migrated['validationStatus'] == 'NOT_VALIDATED'
