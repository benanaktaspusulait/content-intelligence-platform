"""Provider-free contract fixtures for the optional STORY_REVIEW role."""
from app.workflow.creative_roles import perform_role


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
