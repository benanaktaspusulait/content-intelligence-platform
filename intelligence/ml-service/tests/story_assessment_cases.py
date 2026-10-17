"""Offline contract examples, NEVER real independent reviewer evidence."""
from copy import deepcopy
import json
from pathlib import Path
from story_experiment_fixture import assessment_review, assessment_failed_check, evidence_ids

DOCS=Path(__file__).resolve().parents[2]/'docs'
HISTORICAL=DOCS/'real-strict-story-review-execution-evidence/raw-openai-review.txt'


def material_comparison(payload):
    return {'outcome':'MATERIAL_IMPROVEMENT',
        'baselineEvidenceIds':evidence_ids(payload,'SOURCE','toward the mirror'),
        'candidateEvidenceIds':evidence_ids(payload,'CANDIDATE_A','slowly sits down'),
        'change':'Pip sits with arms folded rather than turning toward the mirror.',
        'visibleConsequence':'Arms folded while Pip sits makes the refusal observable.',
        'addressedWeakness':'The mirror turn competes with the deliberate stopping decision.',
        'newRisk':'Sitting plus sneeze may crowd the 15-second sequence.',
        'materialityReason':'An explicit refusal posture externalizes the stopping decision; this is a test hypothesis, not observed viewer benefit.'}


def case_response(payload,mode):
    if mode=='historical':return HISTORICAL.read_text()
    if mode=='historical-v1':return (DOCS/'authentic-story-independent-review-result-evidence/raw-openai-review.txt').read_text()
    v=assessment_review(payload);row=v['candidateAssessments']['A']
    if mode=='positive':
        for ref,item in v['candidateAssessments'].items():
            item['semanticChecks']['identity'].update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=evidence_ids(payload,'SOURCE','Pip the rabbit')[:1],candidateEvidenceIds=evidence_ids(payload,'CANDIDATE_'+ref)[:1],reason='The same named rabbit is explicit; mocked opinion, not a real review.')
            records=[r for r in payload['evidenceCatalog']['records'] if r['documentRole']=='CANDIDATE_'+ref]
            start=next(i for i,r in enumerate(records) if ('wrapping' if ref=='A' else 'plastering') in r['exactOriginalText'])
            end=next(i for i,r in enumerate(records) if 'scatters' in r['exactOriginalText'])
            item['semanticChecks']['continuity'].update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=evidence_ids(payload,'SOURCE','Pip remains covered'),candidateEvidenceIds=[r['evidenceId'] for r in records[start:end+1]],reason='The covered-state, held-stop and sneeze-release sequence supports continuity without identical wording; synthetic interpretation only.')
            item['sourceUnknowns']='Trigger meaning and creative/production effectiveness remain unverified by this mocked review.'
    if mode=='missing-check':row['semanticChecks'].pop('trigger_conditions')
    if mode in ('fake-quote','fabricated-id'):row['semanticChecks']['identity']['candidateEvidenceIds']=['invented-id']
    if mode=='cross-candidate':row['creativeDimensions']['PRODUCTION_EXECUTABILITY']['candidateEvidenceIds']=evidence_ids(payload,'CANDIDATE_B')[:1]
    if mode=='stale-id':row['creativeDimensions']['PRODUCTION_EXECUTABILITY']['candidateEvidenceIds']=['A01-old-revision']
    if mode=='missing-evidence':
        row['semanticChecks']['identity'].update(outcome='PASS',basis='SEMANTIC_SUPPORT');row['semanticOutcome']='SEMANTIC_SOURCE_UNKNOWN'
    if mode=='unsupported-materiality':row['creativeConclusion']['outcome']='MATERIAL_IMPROVEMENT'
    if mode=='invalid-enum':v['researchPreference']='A | B | NO_CREATIVE_WINNER'
    if mode=='aggregation':assessment_failed_check(v,payload);row['semanticOutcome']='SEMANTIC_SOURCE_PASS'
    if mode=='malformed':return '{bad'
    if mode=='incomplete':return '{"schemaVersion":'
    return json.dumps(v,ensure_ascii=False,separators=(',',':'))
