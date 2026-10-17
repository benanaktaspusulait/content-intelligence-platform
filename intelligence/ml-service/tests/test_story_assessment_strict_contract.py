"""No network/provider calls: actual SDK serialization + exact archived response replay."""
from copy import deepcopy
import hashlib,json,os,uuid
from pathlib import Path
from unittest.mock import patch
import httpx,pytest,openai
from jsonschema import Draft202012Validator
from app.workflow import story_assessment as a
from app.workflow.story_experiment import encoded
from story_experiment_fixture import assessment_inputs,assessment_review
from story_assessment_cases import material_comparison,case_response,HISTORICAL,DOCS
from test_story_assessment import configuration,grant


def example():
    text,c=assessment_inputs();return text,c,assessment_review(a.wire(text,c)['payload'])


def test_schema_uses_only_provider_supported_subset_and_is_same_local_authority():
    Draft202012Validator.check_schema(a.RESPONSE_CONTRACT)
    allowed={'type','properties','required','additionalProperties','$ref','$defs','enum'}
    def check(node):
        assert set(node)<=allowed
        if node.get('type')=='object':assert set(node['required'])==set(node['properties']) and node['additionalProperties'] is False
        for v in node.get('properties',{}).values():check(v)
        for v in node.get('$defs',{}).values():check(v)
    check(a.RESPONSE_CONTRACT)
    assert a.response_format()['json_schema']['schema']==a.RESPONSE_CONTRACT
    assert a.response_format()['json_schema']['strict'] is True
    text,c,v=example();assert a.validate_review(v,text,c) is v
    assert 'responseContract' not in a.wire(text,c)['payload']


@pytest.mark.parametrize('ref',['A','B'])
@pytest.mark.parametrize('check',a.CHECKS)
def test_every_semantic_check_is_structurally_required(ref,check):
    text,c,v=example();v['candidateAssessments'][ref]['semanticChecks'].pop(check)
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(v,text,c)


@pytest.mark.parametrize('ref',['A','B'])
@pytest.mark.parametrize('dimension',list(a.DIMENSIONS))
def test_every_creative_dimension_is_structurally_required(ref,dimension):
    text,c,v=example();v['candidateAssessments'][ref]['creativeDimensions'].pop(dimension)
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(v,text,c)


@pytest.mark.parametrize('mode',['missing-top','nested','missing-B','extra-C','missing-field','extra-field','invalid-enum','combined-enum'])
def test_exact_topology_and_enums(mode):
    text,c,v=example()
    if mode=='missing-top':v.pop('candidateAssessments')
    if mode=='nested':v['responseContract']={'candidateAssessments':v.pop('candidateAssessments')}
    if mode=='missing-B':v['candidateAssessments'].pop('B')
    if mode=='extra-C':v['candidateAssessments']['C']=deepcopy(v['candidateAssessments']['A'])
    if mode=='missing-field':v['candidateAssessments']['A']['semanticChecks']['identity'].pop('reason')
    if mode=='extra-field':v['renderAuthorized']=True
    if mode=='invalid-enum':v['candidateAssessments']['A']['semanticOutcome']='PASS'
    if mode=='combined-enum':v['researchPreference']='A | B | NO_CREATIVE_WINNER'
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(v,text,c)


@pytest.mark.parametrize('candidateQuote,outcome,basis,reason',[
 ('Pip the rabbit','PASS','SEMANTIC_SUPPORT','Same named rabbit is explicit.'),
 ('The notes stay put.','PASS','SEMANTIC_SUPPORT','Attached notes persist into the following sneeze; wording differs.'),
 ('The notes stay put.','UNKNOWN','INSUFFICIENT','Persistence is suggested, but exact release continuity needs independent judgment.'),
 ('','UNKNOWN','INSUFFICIENT','No sufficient evidence for this question.'),
])
def test_verbatim_paraphrase_and_uncertainty_are_distinct(candidateQuote,outcome,basis,reason):
    text,c,v=example();row=v['candidateAssessments']['A'];row['semanticChecks']['continuity'].update(outcome=outcome,basis=basis,sourceQuote='Pip remains covered until a sneeze scatters the notes onto the cabinet',candidateQuote=candidateQuote,reason=reason)
    assert a.validate_review(v,text,c)['candidateAssessments']['A']['semanticChecks']['continuity']['outcome']==outcome
    assert row['eligibleForOwnerProposal'] is False


@pytest.mark.parametrize('failure',['source-quote','candidate-quote','empty-fail','absence-fail','basis','aggregation','unknown-question','fail-eligibility'])
def test_unsupported_or_inconsistent_semantic_claims_rejected(failure):
    text,c,v=example();row=v['candidateAssessments']['A'];f=row['semanticChecks']['continuity']
    if failure=='source-quote':f['sourceQuote']='Invented source'
    if failure=='candidate-quote':f['candidateQuote']='Notes detach before the sneeze'
    if failure in ('empty-fail','absence-fail','fail-eligibility'):
        row['semanticOutcome']='SEMANTIC_SOURCE_FAIL';f.update(outcome='FAIL',basis='CONTRADICTION',sourceQuote='Pip remains covered until a sneeze scatters the notes onto the cabinet',candidateQuote='The notes stay put.',reason='A conflicting release is alleged by this offline test.')
    if failure=='empty-fail':f['candidateQuote']=''
    if failure=='absence-fail':f['reason']='The exact source sentence is missing.'
    if failure=='fail-eligibility':row['eligibleForOwnerProposal']=True
    if failure=='basis':f['basis']='CONTRADICTION'
    if failure=='aggregation':row['semanticOutcome']='SEMANTIC_SOURCE_PASS'
    if failure=='unknown-question':row['sourceUnknowns']='NONE'
    with pytest.raises(ValueError):a.validate_review(v,text,c)


@pytest.mark.parametrize('conflict,check,sourceQuote',[
 ('The notes fall off before Pip sneezes.','continuity','Pip remains covered until a sneeze scatters the notes onto the cabinet'),
 ('Standing still doubles the notes.','trigger_conditions','every removal or transfer attempt multiplies the notes'),
])
def test_explicit_negative_opinions_need_real_conflicting_evidence(conflict,check,sourceQuote):
    # Isolated synthetic conflict; no authentic candidate is modified or re-hashed.
    text,c,v=example();synthetic=deepcopy(a.sources(text,c));synthetic[0]['narrative']+=' '+conflict
    row=v['candidateAssessments']['A'];row['semanticChecks'][check].update(outcome='FAIL',basis='CONTRADICTION',sourceQuote=sourceQuote,candidateQuote=conflict,reason='The candidate explicitly describes a conflicting state or trigger.')
    row['semanticOutcome']='SEMANTIC_SOURCE_FAIL'
    with patch.object(a,'sources',return_value=synthetic):assert a.validate_review(v,text,c)['candidateAssessments']['A']['eligibleForOwnerProposal'] is False


@pytest.mark.parametrize('failure',['empty-comparison','generic','synonym','cosmetic','fake-baseline','fake-candidate','audience','A-plus'])
def test_material_claims_need_specific_comparative_evidence(failure):
    text,c,v=example();row=v['candidateAssessments']['A'];comp=material_comparison();row['creativeConclusion']=comp
    if failure=='empty-comparison':comp['visibleConsequence']=''
    if failure=='generic':
        for k in ('change','visibleConsequence','addressedWeakness','materialityReason'):comp[k]='Narrative shows creativity but lacks engagement and variety.'
    if failure=='synonym':comp['baselineQuote']=comp['candidateQuote']='Pip the rabbit'
    if failure=='cosmetic':comp['change']='Shorter wording describes how Pip sits with arms folded.'
    if failure=='fake-baseline':comp['baselineQuote']='Made-up original'
    if failure=='fake-candidate':comp['candidateQuote']='Made-up new narrative'
    if failure=='audience':row['creativeDimensions']['ENDING_REPLAY']['strength']='Measured retention improved by 30 percent.'
    if failure=='A-plus':row['creativeDimensions']['ENDING_REPLAY']['strength']='Official A+ achieved.'
    with pytest.raises(ValueError):a.validate_review(v,text,c)


@pytest.mark.parametrize('outcome',['NO_MATERIAL_IMPROVEMENT','MINOR_VARIATION','UNKNOWN','MATERIAL_IMPROVEMENT'])
def test_creative_comparison_never_approves_or_overrides_unknown_source(outcome):
    text,c,v=example();row=v['candidateAssessments']['A'];row['creativeConclusion']=material_comparison();row['creativeConclusion']['outcome']=outcome
    assert a.validate_review(v,text,c)['researchPreference']=='NO_CREATIVE_WINNER'
    assert row['eligibleForOwnerProposal'] is False
    v['researchPreference']='A'
    with pytest.raises(ValueError,match='ineligible'):a.validate_review(v,text,c)


def test_historical_exact_bytes_fail_both_contracts_without_normalization():
    text,c=assessment_inputs();raw=HISTORICAL.read_bytes();value=json.loads(raw)
    receipt=json.loads((HISTORICAL.parent/'durable-provider-receipt.json').read_text())
    assert hashlib.sha256(raw).hexdigest()==receipt['responseSha256']
    ns={'sources':a.sources,'DIMENSIONS':a.DIMENSIONS,'SCHEMA':'assessment-only-story-review-v1','EXTRA_CHECKS':a.EXTRA_CHECKS}
    exec((DOCS/'story-review-contract-fix-evidence/legacy-validator.py.txt').read_text(),ns)
    with pytest.raises(ValueError,match='Both independent candidate assessments required'):ns['validate_review'](value,text,c)
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(value,text,c)
    assert raw==HISTORICAL.read_bytes()


@pytest.mark.parametrize('mode',['positive','historical','missing-check','fake-quote','invalid-enum','aggregation','refusal','incomplete','malformed','timeout'])
def test_real_installed_sdk_serializes_strict_schema_and_preserves_every_receipt(monkeypatch,mode):
    text,c=grant();calls=[]
    def transport(request):
        body=json.loads(request.content);calls.append(body)
        assert body==a.request_body(text,c)
        assert body['model']=='gpt-4o-mini-2024-07-18'
        if mode=='timeout':raise httpx.ReadTimeout('Offline transport timeout',request=request)
        message={'role':'assistant','content':case_response(json.loads(body['messages'][1]['content']),mode),'refusal':None}
        if mode=='refusal':message.update(content=None,refusal='Offline refusal')
        return httpx.Response(200,json={'id':'mock-sdk-only','object':'chat.completion','created':0,'model':body['model'],'choices':[{'index':0,'message':message,'finish_reason':'length' if mode=='incomplete' else 'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':200,'total_tokens':300}})
    def client(**kwargs):
        assert kwargs['max_retries']==0 and kwargs['timeout']==20
        return openai.OpenAI(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
    monkeypatch.setenv('OPENAI_API_KEY','offline-not-a-credential')
    with patch('app.llm.openai_provider.OpenAI',side_effect=client):result=a.execute(text,c,.1)
    assert len(calls)==1
    assert (result['processingStatus']=='INDEPENDENT_REVIEW_COMPLETED')==(mode=='positive')
    if mode=='timeout':assert result['billingStatus']=='USAGE_UNKNOWN' and result['actualCostUsd'] is None
    else:
        checkpoint=json.loads(Path(result['rawReceiptFile']).read_text());assert checkpoint['capturedBeforeParsing']
        assert checkpoint['providerApiResponse']==result['providerApiResponse']
        assert result['actualCostUsd']==pytest.approx(.000135)
    with patch('app.llm.openai_provider.OpenAI',side_effect=AssertionError('No repeat')):
        with pytest.raises(FileExistsError):a.execute(text,c,.1)


def test_old_paid_grant_cannot_authorize_revised_request():
    text,c=assessment_inputs();old=json.loads((DOCS/'authentic-story-independent-review-result-evidence/actual-owner-spending-grant.json').read_text())
    c.update(assessmentSpendingAuthorized=True,assessmentDispatch=old['operations'][0],storyRequestId=str(uuid.uuid4()))
    with patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('No dispatch')):
        with pytest.raises(ValueError,match='exact assessment spending grant'):a.execute(text,c,.1)
