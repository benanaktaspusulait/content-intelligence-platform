"""Offline contract examples, NEVER real independent reviewer evidence."""
from copy import deepcopy
import json
from pathlib import Path
from story_experiment_fixture import assessment_review, assessment_failed_check

DOCS=Path(__file__).resolve().parents[2]/'docs'
HISTORICAL=DOCS/'authentic-story-independent-review-result-evidence/raw-openai-review.txt'


def material_comparison():
    return {'outcome':'MATERIAL_IMPROVEMENT',
        'baselineQuote':'turns the still note-covered face toward the mirror',
        'candidateQuote':'slowly sits down on the floor, arms folded, refusing to touch anything',
        'change':'Pip sits with arms folded rather than turning toward the mirror.',
        'visibleConsequence':'Arms folded while Pip sits makes the refusal observable.',
        'addressedWeakness':'The mirror turn competes with the deliberate stopping decision.',
        'newRisk':'Sitting plus sneeze may crowd the 15-second sequence.',
        'materialityReason':'An explicit refusal posture externalizes the stopping decision; this is a test hypothesis, not observed viewer benefit.'}


def case_response(payload,mode):
    if mode=='historical':return HISTORICAL.read_text()
    v=assessment_review(payload);row=v['candidateAssessments']['A']
    if mode=='missing-check':row['semanticChecks'].pop('trigger_conditions')
    if mode=='fake-quote':row['semanticChecks']['identity']['candidateQuote']='An invented passage'
    if mode=='invalid-enum':v['researchPreference']='A | B | NO_CREATIVE_WINNER'
    if mode=='aggregation':assessment_failed_check(v,payload);row['semanticOutcome']='SEMANTIC_SOURCE_PASS'
    if mode=='malformed':return '{bad'
    if mode=='incomplete':return '{"schemaVersion":'
    return json.dumps(v,ensure_ascii=False,separators=(',',':'))
