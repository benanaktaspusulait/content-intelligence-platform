"""Contract transport data only; never real-model creative evidence."""
from copy import deepcopy


def inputs():
    import json
    from pathlib import Path
    from app.workflow.story_experiment import sha, VERSION
    root=Path(__file__).resolve().parents[2]
    saved=json.loads((root/'docs/CREATIVE_STORY_NEXT_EXPERIMENT_MANIFEST.json').read_text())
    text=saved['originalStory'];context=deepcopy(saved['requestContextPreview'])
    clauses=[('identity','CHARACTER_IDENTITY','Pip the rabbit'),
             ('premise','CORE_PREMISE',"it clings to Pip's fingertip while the cabinet stays untouched"),
             ('rule','PHYSICAL_RULE','every removal or transfer attempt multiplies the notes'),
             ('continuity','CONTINUITY','Pip remains covered until a sneeze scatters the notes onto the cabinet'),
             ('ending','ENDING','Pip is relieved, but the cabinet remains messy.')]
    anchors=[{'id':identity,'kind':kind,'quote':quote,'start':text.index(quote),'end':text.index(quote)+len(quote)}
             for identity,kind,quote in clauses]
    context['storyExperiment']={'version':VERSION,'requestedAlternativeCount':2,'protectedAnchors':anchors,
                                'sourceStorySha256':sha(text),'sourceScopeSha256':sha({'story':text,'anchors':anchors})}
    return text,context


def alternatives(story, policy):
    quotes = {a['kind']: a['quote'] for a in policy['protectedAnchors']}
    identity = quotes['CHARACTER_IDENTITY']
    shared = ' '.join(a['quote'].rstrip('.')+'.' for a in policy['protectedAnchors'])
    scenes = [
        (f'{identity} wants to clear the cabinet, but a note blocks the intended surface. ',
         'First the hand pauses at the cabinet. Then a careful peel draws attention to the changing note count. '
         'After the contact releases, the character sees a wider patch of attached paper and stops to inspect it. '
         'The reflection reveals the coverage before the sneeze, so the final action has a clear visual cause. '),
        (f'{identity} notices a clean rectangular space surrounded by a spreading paper border. ',
         'Instead of rushing, the character tests the edge and then watches the silhouette expand. '
         'The cabinet remains a stable background while the body becomes the changing shape. '
         'After a still moment of recognition, the reflection leads into the sneeze and an imperfectly cleaned surface. '),
    ]
    result=[]
    for i,(opening,progression) in enumerate(scenes,1):
        # Protected facts are fixed source clauses; unprotected narrative is
        # distinct. This fixture demonstrates validation/transport only.
        text=opening+progression+shared
        result.append({'candidateId':f'candidate-{i}','title':f'Offline contract case {i}',
                       'text':text,'schemaVersion':'story-pilot-candidates-v1','durationSeconds':15,
                       'openingVisualState':opening.strip(),'motivation':opening.strip(),
                       'progression':progression.strip(),'ending':quotes['ENDING'],
                       'proposedChanges':['Unprotected progression differs from the baseline.'],
                       'weaknesses':['Audience response is unknown.'],
                       'productionRisks':['Fine contact continuity remains unverified.'],
                       'sourceContract':{'status':'SOURCE_COMPLIANT','protectedChanges':[],
                           'bindings':[{'anchorId':a['id'],'sourceQuote':a['quote'],'candidateQuote':a['quote']} for a in policy['protectedAnchors']]}})
    return result


def review(candidates, context):
    from app.workflow.creative_reconstruction import DIMENSIONS
    ids=[c['candidateId'] for c in candidates]
    return {'reviewId':'offline-review','sourceRequestId':context['sourceRequestId'],
            'sourceFingerprint':context['sourceFingerprint'],'reviewModel':'gpt-4o-mini-2024-07-18',
            'reviewModelVersion':'offline-mock','reviewPolicyVersion':'creative-story-merit-v1',
            'reviewTimestamp':'2026-10-17T00:00:00Z','reviewStatus':'COMPLETED',
            'diversityAssessment':{},'comparativeFindings':[],
            'candidateReviews':[{'candidateId':c['candidateId'],'materialFindings':[
                {'dimension':d,'finding':'A textual proposal only; actual benefit unverified.',
                 'supportingTextEvidence':c['openingVisualState'],'severity':'ADVISORY',
                 'confidenceOrEvidenceStatus':'TEXT_SUPPORTED','suggestedMinimalImprovement':'Obtain independent visual evidence.'}
                for d in DIMENSIONS]} for c in candidates],
            'recommendedCandidateId':None,'recommendationReason':'NO_CREATIVE_WINNER','overallConcerns':['Contract fixture, not creativity evidence'],
            'usageAndCost':{},'evidenceLimitations':['No real model or render'], 'revisionComparison':{},
            'creativeQualityAssessment':{'candidateAssessments':[{'candidateId':cid,'status':'CREATIVELY_WEAK',
                'reason':'No real creative evidence','strengths':[],'risks':['Fixture only']} for cid in ids]},
            'structuralFeasibilityAssessment':{'candidateAssessments':[{'candidateId':c['candidateId'],
                'status':'STRUCTURALLY_PROMISING','remainingBlockers':[],'visualEvidenceUnknowns':['No images'],
                'ruleAssessments':[{'ruleId':rule,'storyEvidenceExcerpt':c['openingVisualState'],'status':'RISK',
                    'reason':'Offline structural fixture','necessaryImprovement':'Independent review required','changesProtectedSource':False}
                 for rule in ['ATTEMPT_001','ATTEMPT_002','CHAR_002','REPETITION_004','MINI_STORY_LOCK']]} for c in candidates]}}


def assessment_inputs():
    import json,hashlib
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]/'docs'
    path=root/'AUTHENTIC_STORY_ASSESSMENT_SOURCE_CATALOG.json';catalog=json.loads(path.read_text());items=[]
    for entry in catalog['candidates']:
        receipt=json.loads((root/entry['receiptFile']).read_text());candidate=next(c for c in json.loads(receipt['rawProviderResponse'])['alternatives'] if c['candidateId']==entry['candidateId'])
        items.append({**entry,'receipt':receipt,'originalCandidate':candidate})
    source=catalog['sourceScope'];scope={'experimentVersion':'REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1','assessmentOnlyPolicy':catalog['policy'],'catalogSha256':hashlib.sha256(path.read_bytes()).hexdigest(),'sourceScope':source,'candidates':items,'sourceStoryRecordId':source['sourceStoryRecordId'],'sourceStorySha256':source['sourceStorySha256'],'sourceStory':source['sourceStory'],'ownerPolicyApproval':True}
    from app.workflow.story_assessment import TIMEOUT_POLICY
    scope['transportPolicy']=dict(TIMEOUT_POLICY)
    return source['sourceStory'],{'assessmentOnlyPolicy':catalog['policy'],'assessmentScope':scope}


def evidence_ids(payload,role,fragment=None):
    records=[r for r in payload['evidenceCatalog']['records'] if r['documentRole']==role and r['exactOriginalText'].strip()]
    if fragment is not None:records=[r for r in records if fragment in r['exactOriginalText']]
    if not records:raise AssertionError('Offline fixture evidence fragment absent')
    return [r['evidenceId'] for r in records]


def assessment_review(payload):
    """Synthetic opinion/transport data, never an independent real judgment."""
    from app.workflow.story_assessment import SCHEMA, CHECKS
    return {'schemaVersion':SCHEMA,'candidateAssessments':{c['ref']:{
        'semanticChecks':{check:{'outcome':'UNKNOWN','basis':'INSUFFICIENT',
            'sourceEvidenceIds':[],'candidateEvidenceIds':[],
            'reason':'Mock contract only; independent meaning unverified.'} for check in CHECKS},
        'semanticOutcome':'SEMANTIC_SOURCE_UNKNOWN','sourceUnknowns':'Mocked review cannot independently resolve trigger or continuity semantics.',
        'creativeDimensions':{d:{'candidateEvidenceIds':evidence_ids(payload,'CANDIDATE_'+c['ref'])[:1],
            'strength':'Placement goal is introduced.','weakness':'Timing is unverified.','risk':'No visual evidence.'} for d in payload['dimensions']},
        'creativeConclusion':{'outcome':'UNKNOWN','baselineEvidenceIds':[],'candidateEvidenceIds':[],
            **{k:'' for k in ('change','visibleConsequence','addressedWeakness','newRisk','materialityReason')}},
        'eligibleForOwnerProposal':False} for c in payload['candidates']},
        'researchPreference':'NO_CREATIVE_WINNER','reason':'Mocked review proves contract only.',
        'evidenceLimitations':'No real reviewer, rendered or audience evidence.'}


def assessment_failed_check(value,payload):
    row=value['candidateAssessments']['A'];row['semanticOutcome']='SEMANTIC_SOURCE_FAIL'
    row['semanticChecks']['trigger_conditions']={'outcome':'FAIL','basis':'CONTRADICTION',
        'sourceEvidenceIds':evidence_ids(payload,'SOURCE','every removal or transfer attempt'),
        'candidateEvidenceIds':evidence_ids(payload,'CANDIDATE_A','Pip shakes the hand'),
        'reason':'Offline mock alleges a non-removal trigger; actual meaning remains unverified.'}
