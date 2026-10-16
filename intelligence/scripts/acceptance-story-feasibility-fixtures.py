#!/usr/bin/env python3
"""Deterministic P2 story-feasibility transport fixtures; never real-model evidence."""
import json
from pathlib import Path
import sys

folder = Path(sys.argv[1])

negative_a = (
    "Pip tries to pull a sticky note from one finger. Pip pulls harder and more notes appear. "
    "Pip pulls again until the notes cover Pip, then sees the mirror and sneezes them onto the cabinet."
)
negative_b = (
    "Pip finds a sticky note stuck to one finger. Repeated pulling doubles the notes until Pip is covered. "
    "The mirror reveals the mess and a sneeze sends the notes onto the cabinet."
)
positive_r1 = (
    "Already mid-action, Pip the rabbit tries to place one sticky note on the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched. "
    "Pip tries to peel the note away with the free hand, but it splits into two notes, one on each hand. "
    "Pip tries to press both notes onto the cabinet, but they spring back and double into four notes. "
    "Pip tries to push the four notes off against the cabinet door edge, but they split into eight and cover Pip's arms and face. "
    "Pip realizes that every removal or transfer attempt multiplies the notes, freezes, and sees the note-covered reflection in the mirror. "
    "Pip remains covered until a sneeze scatters the notes onto the cabinet. Pip is relieved, but the cabinet remains messy."
)
positive_r2 = positive_r1.replace(
    "Pip realizes that every removal or transfer attempt multiplies the notes, freezes, and sees the note-covered reflection in the mirror.",
    "Pip sees the four-to-eight change finish, realizes that every removal or transfer attempt multiplies the notes, deliberately stops struggling, and turns the still note-covered face toward the mirror."
)
positive_alt = positive_r1.replace("cabinet door edge", "cabinet's straight door edge")

def candidate(cid, title, text):
    return {'candidateId': cid, 'title': title, 'text': text}

(folder / 'story.json').write_text(json.dumps({'scenarios': {
    'default': {'alternatives': [candidate('candidate-1', 'Probe A', negative_a), candidate('candidate-2', 'Probe B', negative_b)]},
    'P2_NEGATIVE_STRUCTURAL_CASE': {'rounds': {'1': {'alternatives': [
        candidate('negative-repeat-pull', 'Repeated pulling', negative_a),
        candidate('negative-consequence-only', 'Consequence description', negative_b),
    ]}}},
    'P2_POSITIVE_STRUCTURAL_CASE': {'rounds': {
        '1': {'alternatives': [candidate('positive-round-1', 'Distinct physical strategies', positive_r1), candidate('positive-alt', 'Door-edge staging', positive_alt)]},
        '2': {'alternatives': [candidate('positive-equivalent', 'Retained candidate replay', positive_r1), candidate('positive-round-2', 'Realization after visible state change', positive_r2)]},
    }},
}}, indent=2), encoding='utf-8')

rules = ('ATTEMPT_001', 'ATTEMPT_002', 'CHAR_002', 'REPETITION_004', 'MINI_STORY_LOCK',
         'HOOK_002', 'HOOK_004', 'CONSISTENCY_001', 'GENERATION_EXECUTABLE_ATTEMPTS',
         'INSTANT_VISUAL_ABSURDITY_GATE', 'ENGINE_SILHOUETTE_DUPLICATE')

def review(round_number, candidates, recommended, texts, supported):
    creative_rows = []
    structural_rows = []
    candidate_reviews = []
    for cid in candidates:
        text = texts[cid]
        excerpt = ("Pip tries to peel the note away with the free hand" if supported else
                   ("Pip tries to pull a sticky note from one finger" if "tries to pull" in text else "Repeated pulling doubles the notes"))
        creative_rows.append({'candidateId': cid, 'status': 'CREATIVELY_STRONG' if supported else 'CREATIVELY_WEAK',
                              'reason': 'Meaningful causal actions.' if supported else 'The same pulling strategy is repeated.',
                              'strengths': ['Central mechanic and ending remain coherent'],
                              'risks': ['Text-only review; no visual evidence']})
        rule_rows=[]
        for rule in rules:
            visual_only=rule in {'INSTANT_VISUAL_ABSURDITY_GATE','ENGINE_SILHOUETTE_DUPLICATE'}
            semantic_risk=rule in {'ATTEMPT_002','HOOK_004','CONSISTENCY_001','GENERATION_EXECUTABLE_ATTEMPTS'}
            rule_rows.append({'ruleId': rule, 'storyEvidenceExcerpt': excerpt,
                'status': ('UNKNOWN' if supported and visual_only else 'RISK' if supported and semantic_risk else
                           'SUPPORTED' if supported else ('RISK' if rule == 'MINI_STORY_LOCK' else 'NOT_SUPPORTED')),
                'reason': ('Independent visual comparison is not present.' if supported and visual_only else
                           'The text is structurally plausible but independent semantic/generator evidence is absent.' if supported and semantic_risk else
                           'The story contains actor-bound, causally distinct attempts and an explicit realization.' if supported else
                           'Repeated pulls do not establish distinct strategies.'),
                'necessaryImprovement': ('Obtain independent evidence; do not infer PASS from story text.' if supported and (visual_only or semantic_risk) else
                                         '' if supported else 'Introduce a coherent, source-authorized different interaction rather than another pull.'),
                'changesProtectedSource': True})
        structural_rows.append({'candidateId': cid, 'status': 'STRUCTURALLY_PROMISING' if supported else 'STRUCTURALLY_BLOCKED',
                                'remainingBlockers': [] if supported else ['Distinct problem-solving strategies are absent'],
                                'visualEvidenceUnknowns': ['Opening readability and rendered feasibility remain unknown'],
                                'ruleAssessments': rule_rows})
        candidate_reviews.append({'candidateId': cid, 'overallStatus': 'STRONG_CANDIDATE' if supported else 'NEEDS_REVISION',
                                  'strengths': ['Causal sequence'] if supported else [],
                                  'concerns': [] if supported else ['Strategy repetition'], 'materialFindings': [],
                                  'suggestedMinimalImprovements': [],
                                  'editorialRecommendation': 'RECOMMENDED' if cid == recommended else 'NEEDS_REVISION',
                                  'confidenceOrEvidenceStatus': 'MOCK_TEXT_ONLY'})
    return {'reviewId': f'p2-fixture-review-{round_number}-{supported}', 'sourceRequestId': None, 'sourceFingerprint': None,
            'reviewModel': 'ISOLATED_STORY_REVIEW', 'reviewModelVersion': 'fixture-p2-v1',
            'reviewPolicyVersion': 'canonical-a-aware-story-review-v1', 'reviewTimestamp': 'TEST_FIXTURE_NOT_REAL_MODEL_TIME',
            'reviewStatus': 'COMPLETED', 'diversityAssessment': {'classification': 'MATERIAL' if supported else 'REPETITIVE'},
            'comparativeFindings': [], 'candidateReviews': candidate_reviews,
            'creativeQualityAssessment': {'candidateAssessments': creative_rows},
            'structuralFeasibilityAssessment': {'candidateAssessments': structural_rows},
            'recommendedCandidateId': recommended,
            'recommendationReason': 'Candidate has distinct actor-bound strategies and realization.' if recommended else 'No candidate is structurally promising.',
            'overallConcerns': ['No rendered or audience evidence exists.'], 'usageAndCost': {'provider': 'ISOLATED_FIXTURE', 'costUpperBoundUsd': 0},
            'evidenceLimitations': ['Deterministic mock validates contracts, not model creativity.'],
            'revisionComparison': {'resolved': [], 'remaining': ['Visual evidence remains unknown'], 'newFindings': []}}

negative_texts = {'negative-repeat-pull': negative_a, 'negative-consequence-only': negative_b}
positive_1 = {'positive-round-1': positive_r1, 'positive-alt': positive_alt}
positive_2 = {'positive-round-2': positive_r2}
(folder / 'story_review.json').write_text(json.dumps({'scenarios': {
    'P2_NEGATIVE_STRUCTURAL_CASE': {'rounds': {'1': review(1, list(negative_texts), None, negative_texts, False)}},
    'P2_POSITIVE_STRUCTURAL_CASE': {'rounds': {
        '1': review(1, list(positive_1), 'positive-round-1', positive_1, True),
        '2': review(2, list(positive_2), 'positive-round-2', positive_2, True),
    }},
}}, indent=2), encoding='utf-8')

beat_actions = [
    "Already mid-action, Pip the rabbit tries to place one sticky note on the toy cabinet's empty front panel, but it clings to Pip's fingertip while the cabinet stays untouched.",
    "Pip tries to peel the note away with the free hand, but it splits into two notes, one on each hand.",
    "Pip tries to press both notes onto the cabinet, but they spring back and double into four notes.",
    "Pip tries to push the four notes off against the cabinet door edge, but they split into eight and cover Pip's arms and face.",
    "Pip sees the four-to-eight change finish, realizes that every removal or transfer attempt multiplies the notes, deliberately stops struggling, and turns the still note-covered face toward the mirror. Pip remains covered until a sneeze scatters the notes onto the cabinet. Pip is relieved, but the cabinet remains messy.",
]
ranges = ['0-2s', '2-5s', '5-8s', '8-11s', '11-15s']
frames = ['locked medium shot', 'medium shot', 'wide shot', 'wide shot', 'medium close-up']
consequences = ['The note attaches to Pip rather than the cabinet.', 'One note becomes two.',
                'Two notes become four.', 'Four notes become eight and cover Pip.',
                'Pip stops struggling, then the sneeze moves the notes to the cabinet.']
lines = [f'{time}: {action} [{frame}; keep Pip, hands, notes and cabinet causally readable] -> {effect}'
         for time, action, frame, effect in zip(ranges, beat_actions, frames, consequences)]
prompt = ('TITLE / FORMAT\nPip sticky-note strategy escalation / 15 seconds\n\nVISUAL STYLE\nBright playful animation with readable silhouettes.\n\n'
          'CHARACTER / CONTINUITY\nPip is the same anthropomorphic rabbit throughout; no verified appearance reference is claimed.\n\n'
          'TIMED SHOT PLAN\n' + '\n'.join(lines) + '\n\nAUDIO\nPlayful music, peel, spring, gasp and sneeze effects; no dialogue.\n\n'
          'NEGATIVE CONSTRAINTS\nNo extra characters, unrelated props, invented attempts, identity changes or visual-evidence claims.\n\n'
          'FINAL CUT\nEnd with Pip relieved beside the messy cabinet.\n\nPRODUCTION SETTINGS\nABSURD_PHYSICS. SEEDANCE_2_0_MINI. 15 seconds. image2video. 480p. 9:16.')
beats = [{'time': time, 'subject': 'Pip', 'action': action, 'object': 'sticky notes and toy cabinet',
          'stateChange': effect, 'framing': frame, 'staging': 'Keep Pip, hands, notes and cabinet causally readable.',
          'consequence': effect, 'sourceEvidence': action, 'evidenceStatus': 'SOURCE_CONFIRMED',
          'sourceRelationship': 'FAITHFUL_ADAPTATION', 'importance': 'CORE'}
         for time, action, frame, effect in zip(ranges, beat_actions, frames, consequences)]
plan = {'sourceIdentity': {}, 'creativeObjective': 'Present distinct actor-bound strategies and realization without visual claims.',
        'characterBindings': [], 'visualExecution': {'openingState': beat_actions[0], 'beats': beats,
        'mechanism': 'Every attempted removal or transfer multiplies the sticky notes.',
        'continuity': 'Pip remains covered through realization and mirror reaction until the sneeze.',
        'endingState': 'Pip is relieved, but the cabinet remains messy.'}, 'productionConstraints': {},
        'intentClassification': {'status': 'TEXT_ONLY'},
        'evidenceLimitations': ['Fixture-authored prompt; no rendered or audience evidence.'],
        'generatorRisks': [{'affectedBeat': 'beat_04', 'sourceEvidence': beat_actions[3],
                           'risk': 'Exact note counts and hand interaction may be fragile at 480p.',
                           'confidence': 'POTENTIAL_RISK', 'mitigation': 'Use one stable wide view.',
                           'nextAction': 'Obtain independent visual evidence before render authorization.'}], 'referencePlan': {}}
(folder / 'build_prompt.json').write_text(json.dumps({'prompt': prompt, 'productionPlan': plan}, indent=2), encoding='utf-8')
