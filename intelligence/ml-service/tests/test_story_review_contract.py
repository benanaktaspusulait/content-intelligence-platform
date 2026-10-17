"""Provider-free contract fixtures for the optional STORY_REVIEW role."""
from app.workflow.creative_roles import perform_role
import json


class FakeReviewProvider:
    last_usage = {'input_tokens': 12, 'output_tokens': 20}

    def complete(self, prompt, system, temperature=0):
        return '{"reviewId":"review-1","sourceRequestId":"story-1","sourceFingerprint":"src-1","reviewModel":"fixture","reviewModelVersion":"fixture-v1","reviewPolicyVersion":"story-review-v1","reviewTimestamp":"2026-10-09T00:00:00Z","reviewStatus":"COMPLETED","diversityAssessment":{"classification":"NEAR_DUPLICATES","summary":"Shared structure"},"comparativeFindings":["Shared ending"],"candidateReviews":[{"candidateId":"candidate-1","overallStatus":"STRONG_CANDIDATE","strengths":["Clear opening"],"concerns":[],"materialFindings":[],"suggestedMinimalImprovements":[],"editorialRecommendation":"RECOMMENDED","confidenceOrEvidenceStatus":"SUPPORTED"},{"candidateId":"candidate-2","overallStatus":"NEEDS_REVISION","strengths":[],"concerns":["Ambiguous rule"],"materialFindings":["Clarify the rule"],"suggestedMinimalImprovements":["Explain the note movement"],"editorialRecommendation":"NEEDS_REVISION","confidenceOrEvidenceStatus":"POTENTIAL_RISK"},{"candidateId":"candidate-3","overallStatus":"STRONG_CANDIDATE","strengths":["Useful reveal"],"concerns":[],"materialFindings":[],"suggestedMinimalImprovements":[],"editorialRecommendation":"STRONG_CANDIDATE","confidenceOrEvidenceStatus":"SUPPORTED"}],"recommendedCandidateId":null,"recommendationReason":"None clearly preferred","overallConcerns":["Shared plot structure"],"usageAndCost":{"provider":"LOCAL_MOCK","costUpperBoundUsd":0},"evidenceLimitations":["Text-only fixture"],"revisionComparison":{"resolved":[],"remaining":[],"newFindings":[]}}'


def test_story_review_uses_one_collection_contract() -> None:
    result = perform_role('STORY_REVIEW', 'Mimi and sticky notes', {
        'sourceRequestId': 'story-1', 'sourceFingerprint': 'src-1',
        'candidates': [
            {'candidateId': 'candidate-1', 'text': 'Opening story'},
            {'candidateId': 'candidate-2', 'text': 'Changed story'},
            {'candidateId': 'candidate-3', 'text': 'Ending story'},
        ],
    }, FakeReviewProvider(), 'fixture')
    assert result['result']['recommendedCandidateId'] is None
    assert len(result['result']['candidateReviews']) == 3


def test_story_review_rejects_unknown_recommendation() -> None:
    class Invalid(FakeReviewProvider):
        def complete(self, prompt, system, temperature=0):
            return '{"reviewId":"r","sourceRequestId":"s","sourceFingerprint":"f","reviewModel":"m","reviewModelVersion":"v","reviewPolicyVersion":"p","reviewTimestamp":"t","reviewStatus":"COMPLETED","diversityAssessment":{},"comparativeFindings":[],"candidateReviews":[],"recommendedCandidateId":"missing","recommendationReason":"x","overallConcerns":[],"usageAndCost":{},"evidenceLimitations":[],"revisionComparison":{"resolved":[],"remaining":[],"newFindings":[]}}'
    try:
        perform_role('STORY_REVIEW', 'story', {'candidates': [{'candidateId': 'c1', 'text': 'x'}]}, Invalid(), 'fixture')
    except ValueError as error:
        assert 'candidate IDs' in str(error) or 'recommendation' in str(error)
    else:
        raise AssertionError('malformed recommendation should fail closed')


def test_story_review_canonicalizes_ordinal_candidate_aliases() -> None:
    class AliasProvider(FakeReviewProvider):
        def complete(self, prompt, system, temperature=0):
            value = super().complete(prompt, system, temperature)
            import json
            payload = json.loads(value)
            for index, item in enumerate(payload['candidateReviews'], 1):
                item['candidateId'] = f'candidate-{index}'
            payload['recommendedCandidateId'] = 'candidate-2'
            return json.dumps(payload)

    result = perform_role('STORY_REVIEW', 'story', {
        'sourceRequestId': 'story-1', 'sourceFingerprint': 'src-1',
        'candidates': [
            {'candidateId': 'uuid-candidate-1', 'text': 'one'},
            {'candidateId': 'uuid-candidate-2', 'text': 'two'},
            {'candidateId': 'uuid-candidate-3', 'text': 'three'},
        ],
    }, AliasProvider(), 'fixture')
    review = result['result']
    assert [item['candidateId'] for item in review['candidateReviews']] == [
        'uuid-candidate-1', 'uuid-candidate-2', 'uuid-candidate-3'
    ]
    assert review['recommendedCandidateId'] == 'uuid-candidate-2'


def _canonical_context():
    return {'version': 'canonical-story-feasibility-context-v1', 'rulesetVersion': '1.11',
            'contextSha256': 'a' * 64, 'target': {'name': 'CANONICAL_A', 'minimumScore': 92}}


def _aware_review(status='STRUCTURALLY_PROMISING', rule_status='SUPPORTED', recommendation='candidate-1'):
    base = json.loads(FakeReviewProvider().complete('', '', 0))
    base['candidateReviews'] = [base['candidateReviews'][0]]
    base['recommendedCandidateId'] = recommendation
    base['creativeQualityAssessment'] = {'candidateAssessments': [{
        'candidateId': 'candidate-1', 'status': 'CREATIVELY_STRONG', 'reason': 'Causal progression',
        'strengths': ['Distinct attempts'], 'risks': ['Text-only assessment']}]}
    base['structuralFeasibilityAssessment'] = {'candidateAssessments': [{
        'candidateId': 'candidate-1', 'status': status, 'remainingBlockers': [],
        'visualEvidenceUnknowns': ['Rendered readability remains unknown'],
        'ruleAssessments': [{
            'ruleId': rule, 'storyEvidenceExcerpt': 'Pip tries to peel the note.',
            'status': rule_status, 'reason': 'Exact source-bound actor action',
            'necessaryImprovement': '', 'changesProtectedSource': True,
        } for rule in ('ATTEMPT_001', 'ATTEMPT_002', 'CHAR_002', 'REPETITION_004', 'MINI_STORY_LOCK')]}]}
    return base


def test_merit_review_rejects_label_only_and_fabricated_dimension_evidence():
    import pytest
    from app.workflow.creative_reconstruction import DIMENSIONS
    text = 'Pip tries to peel the note.'
    context = {'canonicalStoryFeasibilityContext': {**_canonical_context(), 'creativeReviewVersion': 'creative-story-merit-v1'},
               'sourceRequestId': 'story-1', 'sourceFingerprint': 'src-1',
               'candidates': [{'candidateId': 'candidate-1', 'text': text}]}
    value = _aware_review()
    class Provider:
        def complete(self, *args, **kwargs):
            return json.dumps(value)
    with pytest.raises(ValueError, match='all six CPQ'):
        perform_role('STORY_REVIEW', text, context, Provider(), 'offline')
    value['candidateReviews'][0]['materialFindings'] = [
        {'dimension': dim, 'finding': 'Text-supported hypothesis; visual result unverified.',
         'supportingTextEvidence': text, 'severity': 'ADVISORY', 'confidenceOrEvidenceStatus': 'TEXT_SUPPORTED',
         'suggestedMinimalImprovement': 'Review rendered continuity separately.'} for dim in DIMENSIONS]
    result = perform_role('STORY_REVIEW', text, context, Provider(), 'offline')
    assert result['result']['recommendedCandidateId'] == 'candidate-1'
    value['candidateReviews'][0]['materialFindings'][0]['supportingTextEvidence'] = 'Invented scene.'
    with pytest.raises(ValueError, match='exact candidate'):
        perform_role('STORY_REVIEW', text, context, Provider(), 'offline')


def test_story_preview_compiles_effective_instructions_without_a_provider():
    from app.workflow.creative_roles import preview_story_request
    preview = preview_story_request('STORY', 'Pip and a sticky note.', {
        'requestedAlternativeCount': 2,
        'canonicalStoryFeasibilityContext': _canonical_context(),
    })
    assert not preview['providerDispatched']
    assert 'natural pacing' in preview['system']
    assert preview['systemBytes'] == len(preview['system'].encode())
    assert preview['payload']['text'] == 'Pip and a sticky note.'


def test_story_paid_path_uses_mocked_usage_and_disabled_path_never_constructs_provider(monkeypatch):
    import pytest
    from unittest.mock import patch
    from app.workflow.creative_roles import run_paid_role
    for key, value in {'WORKFLOW_CREATIVE_ROLES_ENABLED':'true','WORKFLOW_STORY_MODEL':'mock-story',
                       'WORKFLOW_STORY_INPUT_USD_PER_MILLION':'0.3','WORKFLOW_STORY_OUTPUT_USD_PER_MILLION':'1.2'}.items():
        monkeypatch.setenv(key, value)
    class Provider:
        last_usage = {'prompt_tokens':100,'completion_tokens':200}
        def complete(self, *args, **kwargs):
            return json.dumps({'alternatives':[{'candidateId':'candidate-1','title':'Proposal only','text':'Pip follows the moving note.'}]})
    with patch('app.workflow.creative_roles.DeepSeekTextProvider', return_value=Provider()) as factory:
        result = run_paid_role('STORY', 'Pip and a note.', {'requestedAlternativeCount':1}, .02)
        factory.assert_called_once()
        assert result['providerDispatched'] is True
        assert result['actualCostUsd'] == pytest.approx(.00027)
        assert result['rawProviderResponse']
    monkeypatch.setenv('WORKFLOW_CREATIVE_ROLES_ENABLED','false')
    with patch('app.workflow.creative_roles.DeepSeekTextProvider', side_effect=AssertionError('No dispatch')):
        with pytest.raises(ValueError, match='disabled'):
            run_paid_role('STORY', 'Pip and a note.', {}, .02)


def test_canonical_aware_story_review_accepts_separate_creative_and_structural_evidence() -> None:
    class Provider(FakeReviewProvider):
        def complete(self, prompt, system, temperature=0):
            assert 'canonical' in prompt and 'STRUCTURALLY_PROMISING' in system
            return json.dumps(_aware_review())
    result = perform_role('STORY_REVIEW', 'source', {
        'sourceRequestId': 'story-1', 'sourceFingerprint': 'src-1',
        'canonicalStoryFeasibilityContext': _canonical_context(),
        'candidates': [{'candidateId': 'candidate-1', 'text': 'Pip tries to peel the note.'}],
    }, Provider(), 'fixture')
    assert result['result']['structuralFeasibilityAssessment']['candidateAssessments'][0]['status'] == 'STRUCTURALLY_PROMISING'


def test_canonical_aware_story_review_rejects_false_feasibility_recommendation() -> None:
    class Provider(FakeReviewProvider):
        def complete(self, prompt, system, temperature=0):
            return json.dumps(_aware_review('STRUCTURALLY_BLOCKED', 'NOT_SUPPORTED'))
    try:
        perform_role('STORY_REVIEW', 'source', {
            'sourceRequestId': 'story-1', 'sourceFingerprint': 'src-1',
            'canonicalStoryFeasibilityContext': _canonical_context(),
            'candidates': [{'candidateId': 'candidate-1', 'text': 'Pip tries to peel the note.'}],
        }, Provider(), 'fixture')
    except ValueError as error:
        assert 'structurally ineligible' in str(error)
    else:
        raise AssertionError('least-bad structurally blocked recommendation must fail closed')


def test_canonical_aware_story_review_rejects_invented_quote() -> None:
    invalid = _aware_review()
    invalid['structuralFeasibilityAssessment']['candidateAssessments'][0]['ruleAssessments'][0]['storyEvidenceExcerpt'] = 'Invented third attempt'
    class Provider(FakeReviewProvider):
        def complete(self, prompt, system, temperature=0): return json.dumps(invalid)
    try:
        perform_role('STORY_REVIEW', 'source', {
            'sourceRequestId': 'story-1', 'sourceFingerprint': 'src-1',
            'canonicalStoryFeasibilityContext': _canonical_context(),
            'candidates': [{'candidateId': 'candidate-1', 'text': 'Pip tries to peel the note.'}],
        }, Provider(), 'fixture')
    except ValueError as error:
        assert 'exact candidate story' in str(error)
    else:
        raise AssertionError('invented story evidence must fail closed')
