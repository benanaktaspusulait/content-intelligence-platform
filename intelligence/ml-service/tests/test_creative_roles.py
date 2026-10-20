from creative_http_test_auth import post_role
import json
import os
import pytest
from optimization_test_fixture import valid_optimization_fixture
from app.workflow.creative_roles import migrate_legacy_production_spec, perform_role, run_paid_role, role_readiness


def test_canonical_story_identity_is_registry_gated_separately_from_story_fidelity():
    from app.workflow.creative_roles import _validate_canonical_story_identity

    context = {
        'characterRecord': {'id': 'mimi-id', 'name': 'Mimi'},
        'canonicalCharacterRegistry': [
            {'id': 'mimi-id', 'name': 'Mimi'},
            {'id': 'kiko-id', 'name': 'Kiko'},
        ],
    }
    valid = [{
        'candidateId': 'candidate-1',
        'protagonistCharacterId': 'mimi-id',
        'text': 'Mimi, the light-blue rabbit, finds a paper boat.',
    }]
    assert _validate_canonical_story_identity(valid, context) == [{
        'candidateId': 'candidate-1',
        'status': 'REGISTRY_PASS',
        'characterId': 'mimi-id',
        'characterName': 'Mimi',
    }]

    wrong_id = [{**valid[0], 'protagonistCharacterId': 'kiko-id'}]
    with pytest.raises(ValueError, match='canonical protagonist ID'):
        _validate_canonical_story_identity(wrong_id, context)

    unknown_character = [{**valid[0], 'text': 'Mimi meets Zuzu the rabbit.'}]
    with pytest.raises(ValueError, match='unregistered character: Zuzu'):
        _validate_canonical_story_identity(unknown_character, context)

    with pytest.raises(ValueError, match='absent from the canonical character registry'):
        _validate_canonical_story_identity(valid, {
            **context,
            'canonicalCharacterRegistry': [{'id': 'other-id', 'name': 'Mimi'}],
        })


def test_story_identity_uses_structured_protagonist_and_never_treats_titles_or_determiners_as_names():
    from app.workflow.creative_roles import _validate_canonical_story_identity
    context = {'characterRecord': {'id': 'kiko-id', 'name': 'Kiko'},
               'canonicalCharacterRegistry': [{'id': 'kiko-id', 'name': 'Kiko'}]}
    base = {'candidateId': 'kiko-shy-box-01', 'title': 'The Shy Storage Box',
            'protagonistCharacterId': 'kiko-id',
            'text': 'Kiko watches the bear slowly sink inside the storage box.'}
    assert _validate_canonical_story_identity([base], context)[0]['characterName'] == 'Kiko'
    assert _validate_canonical_story_identity([{**base, 'title': 'An Ordinary English Title'}], context)[0]['status'] == 'REGISTRY_PASS'
    assert _validate_canonical_story_identity([{**base, 'text': 'Kiko and Mimi the rabbit wave. The bear stays put.'}],
                                              {**context, 'canonicalCharacterRegistry': [{'id': 'kiko-id', 'name': 'Kiko'}, {'id': 'mimi-id', 'name': 'Mimi'}]})[0]['status'] == 'REGISTRY_PASS'
    with pytest.raises(ValueError, match='unregistered character: Zuzu'):
        _validate_canonical_story_identity([{**base, 'text': 'Kiko meets Zuzu the rabbit.'}], context)
    with pytest.raises(ValueError, match='does not bind the selected canonical protagonist ID'):
        _validate_canonical_story_identity([{**base, 'protagonistCharacterId': ''}], context)

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


def _structured_long_form_candidate():
    lines = [
        'Duration: 20 seconds.',
        'Goal: Kiko wants to flatten her paper drawing so she can show it proudly.',
        'Why: She has worked carefully on it and wants to share the finished picture.',
        'Rule: Whenever Kiko smooths one crease flat, the paper makes a new crease on the opposite side.',
        '0.0-4.0 SEC: At frame zero Kiko is already smoothing the drawing, but the opposite edge buckles upward before she can flatten it.',
        '4.0-8.0 SEC: Kiko presses the buckled edge with both palms; the crease shifts across the page and traps one corner underneath.',
        '8.0-12.0 SEC: Kiko turns the page around and smooths from the other side; the new crease appears diagonally and the drawing still will not lie flat.',
        '12.0-16.0 SEC: Kiko notices the crease always appears opposite her hand, then aligns the existing folds into a neat accordion instead of chasing each one.',
        '16.0-20.0 SEC: Kiko opens the accordion into a tidy fan-shaped display of the drawing and proudly holds it up; the far edge starts to buckle again.',
    ]
    text = '\n'.join(lines)
    beats = []
    for index, (start, end) in enumerate(((0, 4), (4, 8), (8, 12), (12, 16), (16, 20))):
        beats.append({
            'startSeconds': start, 'endSeconds': end,
            'development': ['Opening obstruction', 'First consequence', 'Changed strategy', 'Discovery and reversal', 'Goal payoff and loop'][index],
            'action': ['Kiko smooths the page', 'Kiko presses the opposite edge', 'Kiko turns and smooths from the other side', 'Kiko aligns the new folds', 'Kiko opens the accordion display'][index],
            'consequence': ['A far edge buckles', 'A corner is trapped', 'A diagonal crease appears', 'The creases form an accordion', 'The drawing is displayed and the edge starts to buckle'][index],
            'stateChange': ['Flat page becomes buckled', 'Page stays folded at one corner', 'Page changes orientation but stays creased', 'Kiko stops chasing the crease', 'Kiko shows the drawing before the rule recurs'][index],
            'sourceQuote': lines[index + 4],
        })
    plan = {
        'character': 'Kiko',
        'conceptSelection': {
            'mechanism': 'An opposite-side crease replaces every fold Kiko smooths.',
            'nearestComparison': 'Upside-Down Chair spatial inversion.',
            'distinction': 'The conflict comes from changes in a paper surface rather than an object repeatedly flipping.',
        },
        'everydayGoal': {'task': 'Flatten her paper drawing to show it proudly', 'why': 'She wants to share a picture she worked on', 'sourceQuote': lines[1]},
        'frameZeroTrouble': {'description': 'The opposite edge buckles while Kiko is already smoothing the drawing', 'sourceQuote': lines[4]},
        'impossiblePhysicalRule': {'rule': 'Smoothing one crease creates a new crease on the opposite side', 'sourceQuote': lines[3], 'targetObject': 'paper drawing'},
        'causalRelationship': 'The opposite crease prevents Kiko from flattening the drawing she wants to show.',
        'attempts': [
            {'beatId': 'beat-1', 'strategy': 'smooth the page', 'action': 'Kiko smooths the drawing', 'consequence': 'The far edge buckles', 'stateChange': 'Flat page becomes buckled', 'sourceQuote': lines[4]},
            {'beatId': 'beat-2', 'strategy': 'press the other edge with both palms', 'action': 'Kiko presses the buckled edge', 'consequence': 'A corner is trapped', 'stateChange': 'Page stays folded at one corner', 'sourceQuote': lines[5]},
            {'beatId': 'beat-3', 'strategy': 'turn the page and smooth from the other side', 'action': 'Kiko turns and smooths from the other side', 'consequence': 'A diagonal crease appears', 'stateChange': 'Page changes orientation but stays creased', 'sourceQuote': lines[6]},
        ],
        'discovery': {'description': 'Kiko notices the crease appears opposite her hand', 'strategyChange': 'She aligns the folds instead of chasing them', 'sourceQuote': lines[7]},
        'payoff': {'description': 'The drawing becomes a neat fan-shaped display', 'goalOutcome': 'Kiko can proudly show the drawing', 'sourceQuote': lines[8]},
        'loopMechanism': {'description': 'The far edge begins to buckle again under the same rule', 'sourceQuote': lines[8]},
        'timecodedBeats': beats,
        'recommendedRuntimeSeconds': 20,
        'durationJustification': {'eightSecondRemovalTest': 'Removing the failed strategies or discovery loses the reason Kiko changes from flattening to arranging the creases.', 'meaningfulLossIfShortened': True, 'sourceQuotes': [lines[5], lines[6], lines[7]]},
        'productionComplexity': {'level': 'MODERATE', 'seedanceRisks': ['Paper fold continuity may be difficult to maintain'], 'segmentStrategy': 'SINGLE_GENERATION'},
    }
    return {'candidateId': 'candidate-1', 'title': 'The Crease That Moves', 'protagonistCharacterId': 'kiko-id', 'text': text, 'storyPlan': plan}


def test_long_form_story_role_maps_explicit_goal_and_runs_existing_canonical_gates(monkeypatch):
    import app.workflow.review as review

    captured = {}
    all_pass = {'status': 'EVALUATED', 'rulesEvaluated': 10, 'passedRules': [
        {'ruleId': rule, 'outcome': 'PASS'} for rule in (
            'GOAL_001', 'GOAL_VISIBLE_EARLY', 'MINI_STORY_LOCK', 'ATTEMPT_001', 'ATTEMPT_002',
            'PROGRESSION_006', 'ESCALATION_005', 'PAYOFF_001', 'CONCEPT_007', 'CONCEPT_008',
            'HOOK_002', 'INSTANT_VISUAL_ABSURDITY_GATE', 'CONTINUOUS_ACTION_MOMENTUM',
        )
    ], 'failedRules': [], 'unknownRules': [], 'notApplicableRules': []}

    def evaluate(value):
        captured.update(value)
        return all_pass

    monkeypatch.setattr(review, 'review_prompt', lambda value: {
        'canonicalRuleEvaluation': evaluate(value),
        'generalProducibility': {'status': 'SUPPORTED'},
        'family8': {'creativeQuality': {'status': 'NOT_EVALUATED'}},
    })
    provider = FixtureProvider({'alternatives': [_structured_long_form_candidate()]})
    winner_context = [{
        'title': 'Upside-Down Chair',
        'mechanismFamily': 'spatial_inversion_recurrence',
        'causalSummary': 'A chair repeatedly flips between normal and upside-down states.',
        'source': 'POMPOM_GOLDEN_V1',
    }]
    response = perform_role('STORY', 'Find one new 20-second Pompom Hills story.', {
        'targetDuration': 20, 'requestedAlternativeCount': 1,
        'establishedWinnerMechanisms': winner_context,
        'characterRecord': {'id': 'kiko-id', 'name': 'Kiko'},
        'canonicalCharacterRegistry': [{'id': 'kiko-id', 'name': 'Kiko'}],
    }, provider, 'configured-model')
    candidate = response['result']['alternatives'][0]
    assert 'LONG-FORM STORY CONTRACT' in provider.calls[0][1]
    assert 'EXACT JSON ENVELOPE' in provider.calls[0][1]
    assert 'application derives evidence from the story text' in provider.calls[0][1]
    assert 'does not require a nested storyPlan' in provider.calls[0][1]
    assert provider.calls[0][0]['context']['establishedWinnerMechanisms'] == winner_context
    assert 'Do not reuse or cosmetically rename a winner' in provider.calls[0][1]
    assert 'goalEvidence' not in captured
    assert 'storyPlanEvidence' not in captured
    assert candidate['storyPlanValidation']['status'] == 'SOURCE_TEXT_MAPPED'
    assert candidate['providerStoryPlanDiagnostics']['usedForCanonicalEvidence'] is False
    assert candidate['mandatoryStoryGate']['status'] == 'PASS'
    assert candidate['storyStageStatus'] == 'STORY_GATES_PASS_CREATIVE_REVIEW_PENDING'
    assert candidate['durationReview']['automaticCreativePass'] is False
    assert candidate['postFamilyReview']['generalProducibility']['status'] == 'SUPPORTED'
    quality_candidate = response['result']['storyQuality']['candidates'][0]['assessment']
    assert quality_candidate['goalMotivationGate']['status'] == 'PASS'
    assert next(row for row in quality_candidate['unknown'] if row['dimension'] == 'goalMotivation')['outcome'] == 'PASS'


def test_long_form_story_without_provider_plan_maps_only_text_evidence_and_reaches_canonical(monkeypatch):
    import app.workflow.review as review
    candidate_source = _structured_long_form_candidate()
    candidate_source.pop('storyPlan')
    captured = {}
    monkeypatch.setattr(review, 'review_prompt', lambda value: captured.update(value) or {
        'canonicalRuleEvaluation': {'status': 'EVALUATED', 'rulesEvaluated': 1, 'passedRules': [],
            'failedRules': [], 'unknownRules': [{'ruleId': 'GOAL_001', 'outcome': 'UNKNOWN'}], 'notApplicableRules': []},
        'generalProducibility': {'status': 'UNKNOWN'},
        'family8': {'creativeQuality': {'status': 'NOT_EVALUATED'}},
    })
    provider = FixtureProvider({'alternatives': [candidate_source]})
    response = perform_role('STORY', 'Generate a 20-second story.', {'targetDuration': 20}, provider, 'configured-model')
    candidate = response['result']['alternatives'][0]
    assert captured['prompt'] == candidate_source['text']
    assert 'goalEvidence' not in captured and 'storyPlanEvidence' not in captured
    assert candidate['storyPlanValidation']['canonicalEvaluationEligible'] is True
    assert candidate['storyPlanValidation']['sourceBoundGoal']['sourceQuote'].startswith('Goal: Kiko wants')
    assert candidate['canonicalStoryEvaluation']['status'] == 'EVALUATED'
    assert candidate['mandatoryStoryGate']['rules']['GOAL_001'] == 'UNKNOWN'
    assert candidate['mandatoryStoryGate']['status'] == 'UNKNOWN'


def test_long_form_generation_prompt_routes_curiosity_and_absurd_physics_separately():
    from app.workflow.creative_roles import preview_story_request

    base = {
        'targetDuration': 22,
        'targetConfiguration': {'duration': 22, 'contentProfile': 'CURIOSITY_ADVENTURE'},
        'requestedAlternativeCount': 1,
    }
    curiosity = preview_story_request('STORY', 'Create one story.', base)
    curiosity_system = curiosity['system']
    assert curiosity['providerDispatched'] is False
    assert 'EFFECTIVE CREATIVE PROFILE: CURIOSITY_ADVENTURE' in curiosity_system
    assert 'viewer-facing question' in curiosity_system
    assert 'visible clue or contradiction' in curiosity_system
    assert 'genuinely new consequence or development' in curiosity_system
    assert 'does not require impossible physics' in curiosity_system
    assert 'blocked at frame zero by one impossible physical rule' not in curiosity_system

    absurd = preview_story_request('STORY', 'Create one story.', {
        **base,
        'profile': 'ABSURD_PHYSICS',
        'targetConfiguration': {'duration': 22, 'contentProfile': 'ABSURD_PHYSICS'},
    })
    assert 'EFFECTIVE CREATIVE PROFILE: ABSURD_PHYSICS' in absurd['system']
    assert 'ABSURD_PHYSICS requires one coherent impossible physical rule' in absurd['system']


def test_opening_and_momentum_failures_block_long_form_story_stage(monkeypatch):
    import app.workflow.review as review
    candidate_source = _structured_long_form_candidate()
    candidate_source.pop('storyPlan')
    failed = {'status': 'EVALUATED', 'rulesEvaluated': 3, 'passedRules': [],
        'failedRules': [
            {'ruleId': 'HOOK_002', 'outcome': 'FAIL'},
            {'ruleId': 'INSTANT_VISUAL_ABSURDITY_GATE', 'outcome': 'FAIL'},
        ], 'unknownRules': [], 'notApplicableRules': []}
    monkeypatch.setattr(review, 'review_prompt', lambda value: {
        'canonicalRuleEvaluation': failed,
        'generalProducibility': {'status': 'UNKNOWN'},
        'family8': {'creativeQuality': {'status': 'NOT_EVALUATED'}},
    })
    provider = FixtureProvider({'alternatives': [candidate_source]})
    response = perform_role('STORY', 'Generate a 20-second story.', {'targetDuration': 20}, provider, 'configured-model')
    candidate = response['result']['alternatives'][0]
    assert candidate['mandatoryStoryGate']['rules']['HOOK_002'] == 'FAIL'
    assert candidate['mandatoryStoryGate']['rules']['INSTANT_VISUAL_ABSURDITY_GATE'] == 'FAIL'
    assert candidate['mandatoryStoryGate']['status'] == 'FAIL'
    assert candidate['storyStageStatus'] == 'STORY_GATES_FAIL'


def test_long_form_story_plan_keeps_missing_selection_rationale_separate_from_story_evidence():
    from app.workflow.creative_roles import _bind_story_source_evidence, _story_plan_errors

    candidate = _structured_long_form_candidate()
    candidate['storyPlan'].pop('conceptSelection')
    _bind_story_source_evidence(candidate, {'establishedWinnerMechanisms': [{'title': 'Upside-Down Chair'}]})
    assert candidate['conceptSelectionStatus'] == 'NOT_EVALUATED_MISSING_SELECTION_RATIONALE'
    assert 'CONCEPT_SELECTION_INCOMPLETE' not in _story_plan_errors(candidate, 20)
    persisted = {'mechanism': 'paper crease migration', 'nearestComparison': 'Upside-Down Chair', 'distinction': 'surface state changes rather than object inversion'}
    _bind_story_source_evidence(candidate, {'conceptSelection': persisted})
    assert candidate['storyPlan']['conceptSelection'] == persisted
    assert candidate['conceptSelectionStatus'] == 'MAPPED_FROM_PERSISTED_WORKFLOW'


def test_long_form_story_binds_goal_and_opening_quotes_from_actual_parser_spans():
    from app.workflow.creative_roles import _bind_story_source_evidence, _story_plan_errors

    candidate = _structured_long_form_candidate()
    candidate['storyPlan']['everydayGoal']['sourceQuote'] = 'provider paraphrase of the goal'
    candidate['storyPlan']['frameZeroTrouble']['sourceQuote'] = 'provider paraphrase of the opening'
    _bind_story_source_evidence(candidate)
    assert candidate['storyPlan']['everydayGoal']['sourceQuote'].startswith('Goal: Kiko wants')
    assert candidate['storyPlan']['frameZeroTrouble']['sourceQuote'] == candidate['storyPlan']['timecodedBeats'][0]['sourceQuote']
    assert _story_plan_errors(candidate, 20) == []


def test_long_form_source_mapping_does_not_invent_missing_goal_or_opening_trouble():
    from app.workflow.creative_roles import _bind_story_source_evidence, _story_plan_errors

    candidate = _structured_long_form_candidate()
    candidate['text'] = candidate['text'].replace('Goal: Kiko wants to flatten her paper drawing so she can show it proudly.', 'Kiko stands beside the paper drawing.')
    candidate['text'] = candidate['text'].replace('Why: She has worked carefully on it and wants to share the finished picture.\n', '')
    candidate['text'] = candidate['text'].replace('At frame zero Kiko is already smoothing the drawing, but the opposite edge buckles upward before she can flatten it', 'Kiko looks at the drawing')
    _bind_story_source_evidence(candidate)
    errors = _story_plan_errors(candidate, 20)
    assert candidate['storySourceEvidenceStatus']['goal'] == 'MISSING'
    assert candidate['storySourceEvidenceStatus']['frameZero'] == 'MISSING'
    assert 'EVERYDAY_GOAL_QUOTE_NOT_IN_STORY' in errors
    assert 'FRAME_ZERO_TROUBLE_QUOTE_NOT_IN_STORY' in errors


def test_unverified_duration_claim_is_not_evaluated_and_does_not_block_story_content_review(monkeypatch):
    import app.workflow.review as review

    provider = FixtureProvider({'alternatives': [_structured_long_form_candidate()]})
    provider.result['alternatives'][0]['storyPlan']['durationJustification']['meaningfulLossIfShortened'] = 'removing eight seconds loses the discovery'
    called = {}
    def review_prompt(value):
        called.update(value)
        return {'canonicalRuleEvaluation': {'status': 'EVALUATED', 'rulesEvaluated': 1, 'passedRules': [],
                'failedRules': [{'ruleId': 'GOAL_001', 'outcome': 'FAIL'}], 'unknownRules': [], 'notApplicableRules': []},
                'generalProducibility': {'status': 'UNKNOWN'}, 'family8': {'creativeQuality': {'status': 'NOT_EVALUATED'}}}
    monkeypatch.setattr(review, 'review_prompt', review_prompt)
    result = perform_role('STORY', 'Find one new 20-second story.', {
        'targetDuration': 20, 'requestedAlternativeCount': 1,
        'characterRecord': {'id': 'kiko-id', 'name': 'Kiko'},
        'canonicalCharacterRegistry': [{'id': 'kiko-id', 'name': 'Kiko'}],
    }, provider, 'configured-model')
    candidate = result['result']['alternatives'][0]
    assert called['prompt'] == candidate['text']
    assert candidate['storyPlanValidation']['status'] == 'SOURCE_TEXT_MAPPED'
    assert candidate['providerStoryPlanDiagnostics']['status'] == 'FAIL'
    assert candidate['storyPlanValidation']['canonicalEvaluationEligible'] is True
    assert candidate['durationReview']['status'] == 'NOT_EVALUATED'
    assert candidate['durationReview']['assessment']['status'] == 'NOT_EVALUATED'
    assert candidate['mandatoryStoryGate']['status'] == 'FAIL'


def test_canonical_story_evaluation_binds_only_source_quoted_story_plan_attempts(monkeypatch):
    from types import SimpleNamespace
    import app.parser.prompt_parser as parser
    import app.rules.rule_engine as rules
    from app.config import settings
    from app.rules.rule_engine import RuleEngine as CanonicalRuleEngine
    from app.workflow.review import _run_canonical_evaluation

    candidate = _structured_long_form_candidate()
    parsed = parser.parse_prompt(candidate['text'], parser.ParserConfig(
        attempt_evidence_policy='ACTOR_SOURCE_BOUND_V2'
    ))
    captured = {}

    class CapturingEngine:
        ruleset = {'rules': []}

        def __init__(self, _path):
            pass

        def evaluate(self, video_plan_ir):
            captured['ir'] = video_plan_ir
            return SimpleNamespace(evaluations=[], overall_score=100, ruleset_version='1.11')

    monkeypatch.setattr(parser, 'parse_prompt', lambda *_args, **_kwargs: parsed)
    monkeypatch.setattr(rules, 'RuleEngine', CapturingEngine)
    result = _run_canonical_evaluation({
        'prompt': candidate['text'],
        'storyPlanEvidence': candidate['storyPlan'],
        'goalEvidence': {
            'description': candidate['storyPlan']['everydayGoal']['task'],
            'sourceQuote': candidate['storyPlan']['everydayGoal']['sourceQuote'],
        },
        'canonicalRulesetVersion': '1.11',
    })
    assert result['status'] == 'EVALUATED'
    mapped = [beat for beat in captured['ir']['beats'] if beat.get('isAttempt')]
    assert len(mapped) == 3
    assert all(beat['attemptSource'] == 'STRUCTURED_PLAN_ROLE' for beat in mapped)
    assert all(beat['sourceAttemptQuote'] in candidate['text'] for beat in mapped)
    captured['ir']['metadata']['duration'] = 24
    attempt_count = CanonicalRuleEngine(
        str(settings.rules_dir / 'RULESET_1.11.yaml')
    )._evaluate_attempt_001(captured['ir'], {})
    assert attempt_count.outcome.value == 'FAIL'
    assert attempt_count.actual_value == 3
    assert attempt_count.required_value == 7

    broken_plan = dict(candidate['storyPlan'])
    broken_plan['attempts'] = [dict(candidate['storyPlan']['attempts'][0], sourceQuote='not in source')]
    rejected = _run_canonical_evaluation({
        'prompt': candidate['text'], 'storyPlanEvidence': broken_plan,
        'canonicalRulesetVersion': '1.11',
    })
    assert rejected['status'] == 'ERROR'
    assert 'not source-bound' in rejected['reason']


def test_story_review_receives_known_winner_mechanisms_for_originality_comparison():
    winner_context = [{'title': 'Upside-Down Chair', 'mechanismFamily': 'spatial_inversion_recurrence'}]
    review = {
        'reviewId': 'review-1', 'sourceRequestId': None, 'sourceFingerprint': None,
        'reviewModel': 'fixture', 'reviewModelVersion': 'fixture', 'reviewPolicyVersion': 'v1',
        'reviewTimestamp': 'fixture', 'reviewStatus': 'PARTIAL', 'diversityAssessment': {},
        'comparativeFindings': [], 'candidateReviews': [{'candidateId': 'candidate-1'}],
        'recommendedCandidateId': None, 'recommendationReason': 'Insufficient evidence',
        'overallConcerns': [], 'usageAndCost': {}, 'evidenceLimitations': [], 'revisionComparison': {},
    }
    provider = FixtureProvider(review)
    perform_role('STORY_REVIEW', 'Review the candidate.', {
        'establishedWinnerMechanisms': winner_context,
        'candidates': [{'candidateId': 'candidate-1', 'title': 'A distinct story', 'text': 'Kiko acts.'}],
    }, provider, 'configured-model')
    assert provider.calls[0][0]['context']['establishedWinnerMechanisms'] == winner_context
    assert 'originality against siblings and context.establishedWinnerMechanisms' in provider.calls[0][1]


def test_minimal_long_form_story_reaches_canonical_evaluation_but_missing_content_stays_blocked(monkeypatch):
    import app.workflow.review as review
    monkeypatch.setattr(review, 'review_prompt', lambda value: {
        'canonicalRuleEvaluation': {'status': 'EVALUATED', 'rulesEvaluated': 2, 'passedRules': [],
            'failedRules': [{'ruleId': 'GOAL_001', 'outcome': 'FAIL'}], 'unknownRules': [], 'notApplicableRules': []},
        'generalProducibility': {'status': 'UNKNOWN'},
        'family8': {'creativeQuality': {'status': 'NOT_EVALUATED'}},
    })
    provider = FixtureProvider({'alternatives': [{'candidateId': 'candidate-1', 'title': 'Unstructured', 'text': 'Kiko wants to do an everyday task.'}]})
    response = perform_role('STORY', 'Find one new 20-second story.', {'targetDuration': 20}, provider, 'configured-model')
    candidate = response['result']['alternatives'][0]
    assert candidate['storyPlanValidation']['canonicalEvaluationEligible'] is True
    assert 'FRAME_ZERO_TROUBLE_NOT_SOURCE_ESTABLISHED' in candidate['storyPlanValidation']['errors']
    assert candidate['canonicalStoryEvaluation']['status'] == 'EVALUATED'
    assert candidate['mandatoryStoryGate']['rules']['GOAL_001'] == 'FAIL'
    assert candidate['storyStageStatus'] == 'STORY_GATES_FAIL'


def test_creative_role_reports_empty_provider_response():
    provider = FixtureProvider({})
    provider.complete = lambda prompt, system='', temperature=0, image=None: ''
    with pytest.raises(ValueError, match='empty JSON response'):
        perform_role('STORY', 'Idea', {}, provider, 'configured-model')


def test_story_candidates_are_bounded_when_provider_overproduces():
    provider = FixtureProvider({'alternatives': ['one', 'two', 'three', 'four']})
    response = perform_role('STORY', 'Idea', {}, provider, 'configured-model')
    assert len(response['result']['alternatives']) == 3


def test_prompt_optimization_requires_two_distinct_candidates_and_preserved_source_events():
    source, context, candidates = valid_optimization_fixture()
    events=context["essentialEvents"]
    provider = FixtureProvider({'candidates': candidates})
    response = perform_role('PROMPT_OPTIMIZATION', source, {'essentialEvents': events}, provider, 'configured-model')
    assert [item['candidateId'] for item in response['result']['candidates']] == ['candidate-a', 'candidate-b']
    assert provider.calls[0][0]['context']['essentialEvents'] == events
    assert response['visualInspected'] is False


def test_paid_prompt_optimization_uses_its_explicit_role_model_and_budget(monkeypatch):
    source, context, candidates = valid_optimization_fixture()
    provider = FixtureProvider({'candidates': candidates})
    provider.last_usage = {'prompt_tokens': 100, 'completion_tokens': 100}
    selected_models = []
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_MODEL', 'gpt-4o-mini-2024-07-18')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION', '0.15')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION', '0.6')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_MODEL', 'build-only-model')
    monkeypatch.setattr(
        'app.workflow.creative_roles.OpenAIProvider',
        lambda **kwargs: selected_models.append(kwargs['model']) or provider,
    )

    result = run_paid_role(
        'PROMPT_OPTIMIZATION',
        source,
        context,
        0.20,
    )

    assert selected_models == ['gpt-4o-mini-2024-07-18']
    assert result['role'] == 'PROMPT_OPTIMIZATION'
    assert result['model'] == 'gpt-4o-mini-2024-07-18'
    assert [item['candidateId'] for item in result['result']['candidates']] == ['candidate-a', 'candidate-b']
    assert len({item['hypothesis'] for item in result['result']['candidates']}) == 2
    assert result['costUpperBoundUsd'] <= result['approvedCostCeilingUsd'] == 0.20
    assert result['actualCostUsd'] == pytest.approx((100 * 0.15 + 100 * 0.6) / 1_000_000)
    assert result['calls'] == len(provider.calls) == 1


def test_prompt_optimization_http_endpoint_uses_mock_provider_and_returns_verified_cost(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.workflow import creative_roles

    source, context, candidates = valid_optimization_fixture()
    provider = FixtureProvider({"candidates": candidates})
    provider.last_usage = {'prompt_tokens': 100, 'completion_tokens': 100}
    for key, value in {
        'WORKFLOW_CREATIVE_ROLES_ENABLED': 'true',
        'WORKFLOW_PROMPT_OPTIMIZATION_MODEL': 'fixture-optimization-model',
        'WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION': '0.15',
        'WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION': '0.6',
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(creative_roles, 'OpenAIProvider', lambda **kwargs: provider)

    response = post_role(TestClient(app), {
        'role': 'PROMPT_OPTIMIZATION',
        'text': source,
        'context': context,
        'maxCostUsd': 0.20,
    }, monkeypatch)

    assert response.status_code == 200
    assert response.json()['model'] == 'fixture-optimization-model'
    assert response.json()['actualCostUsd'] == pytest.approx((100 * 0.15 + 100 * 0.6) / 1_000_000)
    assert response.json()['approvedCostCeilingUsd'] == 0.20
    assert len(provider.calls) == 1


def test_prompt_optimization_rejects_provider_response_over_actual_cost_ceiling(monkeypatch):
    source, context, candidates = valid_optimization_fixture()
    provider = FixtureProvider({'candidates': candidates})
    provider.last_usage = {'prompt_tokens': 100, 'completion_tokens': 400_000}
    provider.last_response_metadata = {'apiStatus': 'COMPLETED'}
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION', '0.15')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION', '0.6')
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider', lambda **kwargs: provider)

    with pytest.raises(ValueError, match='Actual provider cost exceeded the authorized cost ceiling'):
        run_paid_role('PROMPT_OPTIMIZATION', source, context, 0.20)

    assert len(provider.calls) == 1


@pytest.mark.parametrize('usage', [None, {'prompt_tokens': 1}, {'prompt_tokens': -1, 'completion_tokens': 1}])
def test_prompt_optimization_rejects_unverifiable_actual_provider_cost(monkeypatch, usage):
    source, context, candidates = valid_optimization_fixture()
    provider = FixtureProvider({'candidates': candidates})
    provider.last_usage = usage
    provider.last_response_metadata = {'apiStatus': 'COMPLETED'}
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION', '0.15')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION', '0.6')
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider', lambda **kwargs: provider)

    with pytest.raises(ValueError, match='actual cost cannot be checked'):
        run_paid_role('PROMPT_OPTIMIZATION', source, context, 0.20)

    assert len(provider.calls) == 1


def test_prompt_optimization_checks_actual_cost_before_rejecting_an_invalid_response(monkeypatch):
    source, context, candidates = valid_optimization_fixture()
    provider = FixtureProvider({'candidates': candidates})
    provider.last_usage = {'prompt_tokens': 100, 'completion_tokens': 400_000}
    provider.last_response_metadata = {'apiStatus': 'COMPLETED'}
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_INPUT_USD_PER_MILLION', '0.15')
    monkeypatch.setenv('WORKFLOW_PROMPT_OPTIMIZATION_OUTPUT_USD_PER_MILLION', '0.6')
    monkeypatch.setattr('app.workflow.creative_roles.OpenAIProvider', lambda **kwargs: provider)

    with pytest.raises(ValueError, match='Actual provider cost exceeded the authorized cost ceiling'):
        run_paid_role('PROMPT_OPTIMIZATION', source, context, 0.20)

    assert len(provider.calls) == 1


def test_prompt_optimization_missing_role_model_fails_before_provider_creation(monkeypatch):
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.delenv('WORKFLOW_PROMPT_OPTIMIZATION_MODEL', raising=False)
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_MODEL', 'build-only-model')
    provider_factory_calls = []
    monkeypatch.setattr(
        'app.workflow.creative_roles.OpenAIProvider',
        lambda **kwargs: provider_factory_calls.append(kwargs),
    )

    with pytest.raises(ValueError, match='Explicit server model configuration required; no fallback'):
        run_paid_role(
            'PROMPT_OPTIMIZATION',
            'Approved source prompt.',
            {'essentialEvents': ['Approved source prompt.']},
            0.20,
        )

    assert provider_factory_calls == []


@pytest.mark.parametrize('candidates,message', [
    ([{'candidateId': 'candidate-a', 'title': 'A', 'hypothesis': 'A', 'prompt': 'changed'}], 'Exactly two'),
    ([{'candidateId': 'candidate-a', 'title': 'A', 'hypothesis': 'A', 'prompt': 'Mimi wants to attach a note. Each pull doubles the notes. Mimi sneezes and the notes fly off. Keep opening legible.'},
      {'candidateId': 'candidate-b', 'title': 'B', 'hypothesis': 'B', 'prompt': 'A replacement ending.'}], 'omits an essential'),
])
def test_prompt_optimization_rejects_incomplete_or_unfaithful_candidates(candidates, message):
    source,context,valid=valid_optimization_fixture()
    if len(candidates)==2: candidates[0]=valid[0]
    provider = FixtureProvider({'candidates': candidates})
    with pytest.raises(ValueError, match=message):
        perform_role('PROMPT_OPTIMIZATION',source,context,provider,'configured-model')


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


@pytest.mark.parametrize('bad_value', [None, '', {'position': 'cabinet'}])
def test_paid_build_retains_invalid_beat_response_without_accepting_or_retrying(monkeypatch, bad_value):
    from app.workflow import creative_roles
    from fastapi.testclient import TestClient
    from app.main import app
    result = production_fixture()
    result['productionPlan']['visualExecution']['beats'][1]['staging'] = bad_value
    provider = FixtureProvider(result)
    provider.last_usage = {'total_tokens': 123}
    provider.last_response_metadata = {'requestId': 'fixture-response', 'finishReason': 'stop'}
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'true')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_MODEL', 'fixture-model')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_INPUT_USD_PER_MILLION', '0.15')
    monkeypatch.setenv('WORKFLOW_BUILD_PROMPT_OUTPUT_USD_PER_MILLION', '0.6')
    monkeypatch.setattr(creative_roles, 'OpenAIProvider', lambda **kwargs: provider)
    response = post_role(TestClient(app), {
        'role': 'BUILD_PROMPT', 'text': 'Mimi stands by the toy cabinet.', 'context': {}, 'maxCostUsd': .15}, monkeypatch)
    assert response.status_code == 200
    body = response.json()
    assert body['attemptState'] == 'PROVIDER_RESULT_REJECTED'
    assert body['validationStatus'] == 'REJECTED'
    assert 'result' not in body
    assert json.loads(body['rejectedProviderResponse']) == result
    assert 'Beat 2' in body['attemptDiagnostics']['error']
    assert 'staging' in body['attemptDiagnostics']['error']
    assert body['attemptDiagnostics']['retryAutomatically'] is False
    assert body['providerResponseMetadata']['requestId'] == 'fixture-response'
    assert len(provider.calls) == 1
    assert 'REQUIRED non-empty JSON strings' in provider.calls[0][1]


def test_paid_valid_build_still_returns_a_draft(monkeypatch):
    from app.workflow import creative_roles
    provider = FixtureProvider(production_fixture())
    for key, value in {'WORKFLOW_CREATIVE_ROLES_ENABLED': 'true', 'WORKFLOW_BUILD_PROMPT_MODEL': 'fixture',
                       'WORKFLOW_BUILD_PROMPT_INPUT_USD_PER_MILLION': '.15',
                       'WORKFLOW_BUILD_PROMPT_OUTPUT_USD_PER_MILLION': '.6'}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(creative_roles, 'OpenAIProvider', lambda **kwargs: provider)
    result = run_paid_role('BUILD_PROMPT', 'Mimi stands by the toy cabinet.', {}, .15)
    assert result['validationStatus'] == 'NOT_VALIDATED'
    assert result['result']['prompt']
    assert len(provider.calls) == 1


def test_paid_build_records_timeout_as_unknown_without_retry_or_false_zero_calls(monkeypatch, caplog):
    from app.workflow import creative_roles
    from fastapi.testclient import TestClient
    from app.main import app
    import httpx
    from openai import APITimeoutError
    class TimeoutProvider:
        invocations = 0
        def complete(self, *args, **kwargs):
            self.invocations += 1
            raise APITimeoutError(request=httpx.Request('POST', 'https://example.invalid'))
    provider = TimeoutProvider()
    for key, value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_BUILD_PROMPT_MODEL':'fixture',
                       'WORKFLOW_BUILD_PROMPT_INPUT_USD_PER_MILLION':'.15','WORKFLOW_BUILD_PROMPT_OUTPUT_USD_PER_MILLION':'.6'}.items():
        monkeypatch.setenv(key,value)
    monkeypatch.setattr(creative_roles,'OpenAIProvider',lambda **kwargs:provider)
    response=post_role(TestClient(app), {
        'role':'BUILD_PROMPT','text':'Approved story','context':{},'maxCostUsd':.15}, monkeypatch)
    assert response.status_code == 200
    body=response.json()
    assert body['attemptState'] == 'PROVIDER_OUTCOME_UNKNOWN'
    assert body['attemptDiagnostics']['exceptionType'] == 'APITimeoutError'
    assert body['attemptDiagnostics']['providerOutcome'] == 'UNKNOWN'
    assert 'calls' not in body
    assert 'result' not in body and 'rejectedProviderResponse' not in body
    assert provider.invocations == 1
    assert 'APITimeoutError' in caplog.text
    assert 'Approved story' not in caplog.text


def test_post_response_processing_exception_retains_response(monkeypatch):
    from app.workflow import creative_roles
    provider=FixtureProvider(production_fixture())
    for key,value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_BUILD_PROMPT_MODEL':'fixture',
                      'WORKFLOW_BUILD_PROMPT_INPUT_USD_PER_MILLION':'.15','WORKFLOW_BUILD_PROMPT_OUTPUT_USD_PER_MILLION':'.6'}.items():
        monkeypatch.setenv(key,value)
    monkeypatch.setattr(creative_roles,'OpenAIProvider',lambda **kwargs:provider)
    def fail(*args): raise TypeError('private payload must not be logged')
    monkeypatch.setattr(creative_roles,'_evidence_backed_production_fields',fail)
    result=run_paid_role('BUILD_PROMPT','Approved story',{},.15)
    assert result['attemptState'] == 'PROVIDER_RESULT_REJECTED'
    assert result['attemptDiagnostics']['exceptionType'] == 'TypeError'
    assert result['rejectedProviderResponse']
    assert 'private payload' not in result['attemptDiagnostics']['error']
    assert len(provider.calls) == 1

def test_optimization_system_prompt_requires_structurally_distinct_timed_shot_plans():
    """The system prompt must contain the structural-differentiation requirements
    so the model cannot produce near-identical TIMED SHOT PLANs."""
    from app.workflow.creative_roles import perform_role as _perform_role
    import inspect, ast
    src = inspect.getsource(_perform_role)
    # Must require the first beat to differ between candidates
    assert 'first timed beat' in src, \
        "System prompt does not require the first timed beat to differ between candidates"
    # Must require hypothesis to name a concrete structural change
    assert 'actually implemented in the prompt body' in src, \
        "System prompt does not require hypothesis to describe an actually implemented change"


def test_optimization_rejects_near_verbatim_baseline_paraphrase():
    source,context,candidates=valid_optimization_fixture()
    candidates[0]['prompt']=source.replace('Content profile: AUTO','Content profile: ABSURD_PHYSICS')+' Extra.'
    with pytest.raises(ValueError,match='materially unchanged execution'):
        perform_role('PROMPT_OPTIMIZATION',source,context,FixtureProvider({'candidates':candidates}),'fixture')


def test_optimization_rejects_semantically_equivalent_ab_paraphrase():
    source,context,candidates=valid_optimization_fixture()
    candidates[1]['prompt']=candidates[0]['prompt'].replace('extreme close-up','extreme close up')
    with pytest.raises(ValueError,match='same execution decisions'):
        perform_role('PROMPT_OPTIMIZATION',source,context,FixtureProvider({'candidates':candidates}),'fixture')
