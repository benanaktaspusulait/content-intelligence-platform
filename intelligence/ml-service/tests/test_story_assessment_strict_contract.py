"""Reference-contract tests: immutable real inputs; SDK HTTP only is mocked."""
from copy import deepcopy
import hashlib,json,uuid
from pathlib import Path
from unittest.mock import patch
import httpx,pytest,openai
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from app.main import app
from app.workflow import story_assessment as a
from app.workflow.story_evidence import review_evidence_catalog,verify_review_evidence_catalog
from story_experiment_fixture import assessment_inputs,assessment_review,evidence_ids,assessment_failed_check
from story_assessment_cases import material_comparison,case_response,HISTORICAL,DOCS
from test_story_assessment import configuration,grant


def example():
    text,c=assessment_inputs();payload=a.wire(text,c)['payload']
    return text,c,payload,assessment_review(payload)


def test_native_subset_and_same_local_schema_without_any_quotation_fields():
    text,c,p,v=example();schema=a.response_contract(p['evidenceCatalog']);Draft202012Validator.check_schema(schema)
    allowed={'type','properties','required','additionalProperties','$ref','$defs','enum','items'}
    def inspect(n):
        assert set(n)<=allowed
        if n.get('type')=='object':
            assert set(n['required'])==set(n['properties']) and not n['additionalProperties']
            assert not any(k in n['properties'] for k in ('sourceQuote','candidateQuote','baselineQuote','quote'))
        for x in n.get('properties',{}).values():inspect(x)
        for x in n.get('$defs',{}).values():inspect(x)
        if 'items' in n:inspect(n['items'])
    inspect(schema)
    assert a.wire(text,c)['responseFormat']['json_schema']['schema']==schema
    assert a.validate_review(v,text,c) is v


@pytest.mark.parametrize('ref',['A','B'])
@pytest.mark.parametrize('check',a.CHECKS)
def test_each_semantic_check_required(ref,check):
    text,c,p,v=example();v['candidateAssessments'][ref]['semanticChecks'].pop(check)
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(v,text,c)


@pytest.mark.parametrize('ref',['A','B'])
@pytest.mark.parametrize('dimension',list(a.DIMENSIONS))
def test_each_creative_dimension_required(ref,dimension):
    text,c,p,v=example();v['candidateAssessments'][ref]['creativeDimensions'].pop(dimension)
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(v,text,c)


@pytest.mark.parametrize('mode',['nested','missing-top','missing-B','extra-C','missing-field','extra-field','combined-enum','authored-quote'])
def test_fixed_topology_and_no_old_quote_fields(mode):
    text,c,p,v=example()
    if mode=='nested':v['responseContract']={'candidateAssessments':v.pop('candidateAssessments')}
    if mode=='missing-top':v.pop('candidateAssessments')
    if mode=='missing-B':v['candidateAssessments'].pop('B')
    if mode=='extra-C':v['candidateAssessments']['C']=deepcopy(v['candidateAssessments']['A'])
    if mode=='missing-field':v['candidateAssessments']['A']['semanticChecks']['identity'].pop('reason')
    if mode=='extra-field':v['renderAuthorized']=True
    if mode=='combined-enum':v['researchPreference']='A | B | NO_CREATIVE_WINNER'
    if mode=='authored-quote':v['candidateAssessments']['A']['semanticChecks']['identity']['candidateQuote']='Pip the rabbit'
    with pytest.raises(ValueError):a.validate_review(v,text,c)


@pytest.mark.parametrize('body',["  Café 🐇 waits; then sneezes.\n Notes stay put!  ", 'α'*1700, 'First clause, '+('word '*230)+'last.', 'One.\nTwo?'])
def test_catalog_lossless_unicode_offsets_and_determinism(body):
    docs={'SOURCE':body,'CANDIDATE_A':body,'CANDIDATE_B':body};cat=review_evidence_catalog(docs)
    assert cat==review_evidence_catalog(docs);verify_review_evidence_catalog(cat,docs)
    for role,text in docs.items():
        spans=[r for r in cat['records'] if r['documentRole']==role]
        assert ''.join(r['exactOriginalText'] for r in spans)==text
        assert all(text[r['startOffset']:r['endOffset']]==r['exactOriginalText'] and len(r['exactOriginalText'])<=800 for r in spans)
        assert cat['documentBindings'][role]==hashlib.sha256(text.encode()).hexdigest()
    assert len({r['evidenceId'] for r in cat['records']})==len(cat['records'])


@pytest.mark.parametrize('change',['sha','offset','text','role','id','version','dropped-span','revised-document'])
def test_catalog_cannot_rebind_or_normalize(change):
    docs={'SOURCE':'One note. Two notes.','CANDIDATE_A':'Stay still. Sneeze now.','CANDIDATE_B':'Stay still. Sneeze now.'};cat=review_evidence_catalog(docs)
    key={'sha':'documentSha256','offset':'startOffset','text':'exactOriginalText','role':'documentRole','id':'evidenceId'}.get(change)
    if key:cat['records'][0][key]=999 if change=='offset' else 'tampered'
    if change=='version':cat['version']='other'
    if change=='dropped-span':cat['records'].pop()
    if change=='revised-document':docs['CANDIDATE_A']+=' Different revision.'
    with pytest.raises(ValueError):verify_review_evidence_catalog(cat,docs)


@pytest.mark.parametrize('bad',[None,'','   ','Bad\x00text','\ud800','x'*12001])
def test_malformed_document_fails_before_provider(bad):
    with pytest.raises(ValueError):review_evidence_catalog({'SOURCE':bad,'CANDIDATE_A':'Valid.','CANDIDATE_B':'Valid.'})


@pytest.mark.parametrize('target',['A','B'])
@pytest.mark.parametrize('area',['semantic','creative','comparison'])
def test_candidate_scoped_native_enums_and_local_isolation(target,area):
    text,c,p,v=example();other='B' if target=='A' else 'A';row=v['candidateAssessments'][target]
    wrong=evidence_ids(p,'CANDIDATE_'+other)[:1]
    if area=='semantic':row['semanticChecks']['identity']['candidateEvidenceIds']=wrong
    if area=='creative':row['creativeDimensions']['PRODUCTION_EXECUTABILITY']['candidateEvidenceIds']=wrong
    if area=='comparison':row['creativeConclusion']['candidateEvidenceIds']=wrong
    assert list(Draft202012Validator(a.response_contract(p['evidenceCatalog'])).iter_errors(v))
    with pytest.raises(ValueError):a.validate_review(v,text,c)


@pytest.mark.parametrize('bad',['invented','A01-different-revision'])
def test_unknown_or_stale_id_rejected(bad):
    text,c,p,v=example();v['candidateAssessments']['A']['creativeDimensions']['ENDING_REPLAY']['candidateEvidenceIds']=[bad]
    with pytest.raises(ValueError):a.validate_review(v,text,c)


@pytest.mark.parametrize('ref,fragment,check',[('A','The notes stay put.','continuity'),('B','letting the notes rest.','continuity'),('A','Pip the rabbit','identity')])
def test_verbatim_or_paraphrased_preservation_selects_real_adjacent_context(ref,fragment,check):
    text,c,p,v=example();row=v['candidateAssessments'][ref]
    ids=evidence_ids(p,'CANDIDATE_'+ref,fragment)
    if check=='continuity':
        records=[r for r in p['evidenceCatalog']['records'] if r['documentRole']=='CANDIDATE_'+ref]
        start=min(i for i,r in enumerate(records) if r['evidenceId'] in ids)
        ids=[r['evidenceId'] for r in records[start:]]
    row['semanticChecks'][check].update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=evidence_ids(p,'SOURCE','Pip remains covered' if check=='continuity' else 'Pip the rabbit')[:1],candidateEvidenceIds=list(dict.fromkeys(ids)),reason='Selected sequence supports preserved meaning without a copied source sentence; synthetic opinion only.')
    assert a.validate_review(v,text,c) is v
    derived=a.resolve_review_evidence(v,text,c)
    assert derived['semanticInterpretation']=='MODEL_OPINION_NOT_DETERMINISTIC_PROOF'
    assert derived['evidenceType']=='APPLICATION_DERIVED_EVIDENCE'


def test_real_v5_response_is_byte_identical_and_rejected_for_original_boundary_failure():
    text,c=assessment_inputs();path=DOCS/'story-review-derived-verdict-evidence/real-v5-execution/raw-provider-response.json'
    raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()=='797732d070321ad5f50b35503bfab0d6ff073eae2aeb864d7722fb469649ea81'
    payload=a.wire(text,c)['payload'];assert payload['evidenceCatalog']['catalogSha256']=='5b15086899fc5c80f5de99a749fa3b70d47d32175a6a0ee0bcfdd8ab6f2273d7'
    value=json.loads(raw)
    with pytest.raises(ValueError,match=r'Creative boundary evidence missing: A\.ENDING_REPLAY'):
        a.validate_review(value,text,c)
    assert hashlib.sha256(path.read_bytes()).hexdigest()=='797732d070321ad5f50b35503bfab0d6ff073eae2aeb864d7722fb469649ea81'


def test_semantic_ending_pass_requires_final_span_but_unknown_remains_valid():
    text,c,p,v=example();row=v['candidateAssessments']['A'];f=row['semanticChecks']['ending']
    f.update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=evidence_ids(p,'SOURCE','Pip is relieved'),
        candidateEvidenceIds=evidence_ids(p,'CANDIDATE_A','The notes stay put.'),reason='Synthetic ending opinion based only on an intermediate state.')
    with pytest.raises(ValueError,match='Ending PASS evidence must include'):
        a.validate_review(v,text,c)
    f['candidateEvidenceIds']=evidence_ids(p,'CANDIDATE_A')[-1:]
    assert a.validate_review(v,text,c) is v
    f.update(outcome='UNKNOWN',basis='INSUFFICIENT',sourceEvidenceIds=[],candidateEvidenceIds=[],reason='Synthetic uncertainty remains unresolved.')
    assert a.derive_assessment(v,text,c)['candidateAssessments']['A']['semanticOutcome']=='SEMANTIC_SOURCE_UNKNOWN'


def test_continuity_pass_requires_full_candidate_suffix_and_allows_adjacent_context():
    text,c,p,v=example();f=v['candidateAssessments']['A']['semanticChecks']['continuity']
    f.update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=evidence_ids(p,'SOURCE','Pip remains covered'))
    f['candidateEvidenceIds']=evidence_ids(p,'CANDIDATE_A','goes still')
    with pytest.raises(ValueError,match='Continuity PASS evidence must reach'):
        a.validate_review(v,text,c)
    records=[r for r in p['evidenceCatalog']['records'] if r['documentRole']=='CANDIDATE_A']
    start=next(i for i,r in enumerate(records) if 'goes still' in r['exactOriginalText'])
    f['candidateEvidenceIds']=[r['evidenceId'] for r in records[start:]]
    assert a.validate_review(v,text,c) is v


def test_synthetic_final_boundary_counterfactual_preserves_intermediate_context():
    text,c,p,v=example();row=v['candidateAssessments']['A']
    final=evidence_ids(p,'CANDIDATE_A')[-1]
    row['creativeDimensions']['ENDING_REPLAY']['candidateEvidenceIds']=evidence_ids(p,'CANDIDATE_A','The notes stay put.')+[final]
    row['semanticChecks']['ending'].update(outcome='PASS',basis='SEMANTIC_SUPPORT',
        sourceEvidenceIds=evidence_ids(p,'SOURCE','Pip is relieved'),candidateEvidenceIds=[final],
        reason='Synthetic opinion cites the final outcome; application does not prove its meaning.')
    continuity=row['semanticChecks']['continuity'];records=[r for r in p['evidenceCatalog']['records'] if r['documentRole']=='CANDIDATE_A']
    start=next(i for i,r in enumerate(records) if 'goes still' in r['exactOriginalText'])
    continuity.update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=evidence_ids(p,'SOURCE','Pip remains covered'),
        candidateEvidenceIds=[r['evidenceId'] for r in records[start:]],reason='Synthetic transition claim with full catalog suffix; meaning remains a model opinion.')
    assert a.validate_review(v,text,c) is v


def test_semantically_valid_no_winner_completes_machine_assessment_without_authority():
    text,c,p,v=example()
    scope=a.check_scope(text,c,p['evidenceCatalog'])
    for ref,row in v['candidateAssessments'].items():
        role='CANDIDATE_'+ref
        records=[r for r in p['evidenceCatalog']['records'] if r['documentRole']==role and r['exactOriginalText'].strip()]
        for check,f in row['semanticChecks'].items():
            source=[]
            for ids in scope[check]['anchorEvidence'].values():source.extend(ids)
            f.update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=list(dict.fromkeys(source)),
                reason='Synthetic contract-only finding; not an independent semantic result.')
            if check=='continuity':
                start=next(i for i,r in enumerate(records) if 'stops struggling' in r['exactOriginalText'] or 'goes still' in r['exactOriginalText'] or 'deliberately stops' in r['exactOriginalText'])
                f['candidateEvidenceIds']=[r['evidenceId'] for r in records[start:]]
            elif check=='ending':f['candidateEvidenceIds']=[records[-1]['evidenceId']]
            elif check in ('protected_events','trigger_conditions'):f['candidateEvidenceIds']=[r['evidenceId'] for r in records]
            elif check in ('rule','single_mechanic','causal_clarity'):f['candidateEvidenceIds']=[r['evidenceId'] for r in records if 'split into' in r['exactOriginalText'] or 'multiplies' in r['exactOriginalText']][:2]
            else:f['candidateEvidenceIds']=[records[0]['evidenceId']]
    v['researchPreference']='NO_CREATIVE_WINNER'
    assert a.validate_review(v,text,c) is v
    derived=a.derive_assessment(v,text,c)
    for result in derived['candidateAssessments'].values():
        assert result['semanticOutcome']=='SEMANTIC_SOURCE_PASS'
        assert result['eligibleForOwnerProposal'] is False
        assert 'NO_SUPPORTED_MATERIAL_IMPROVEMENT' in result['eligibilityRestrictions']
    assert derived['researchPreferenceAuthority']=='MACHINE_OPINION_ONLY'
    assert derived['ownerDecision']=='PENDING' and derived['sourceApproved'] is False
    assert derived['buildPromptAuthorized'] is False and derived['renderAuthorized'] is False
    assert derived['officialAPlus']=='INACTIVE'


@pytest.mark.parametrize('check',['protected_events','trigger_conditions'])
def test_all_event_pass_cannot_use_only_a_valid_but_partial_candidate_reference(check):
    text,c,p,v=example();f=v['candidateAssessments']['A']['semanticChecks'][check]
    scope=a.check_scope(text,c,p['evidenceCatalog']);source=[]
    for ids in scope[check]['anchorEvidence'].values():source.extend(ids)
    f.update(outcome='PASS',basis='SEMANTIC_SUPPORT',sourceEvidenceIds=list(dict.fromkeys(source)),
        candidateEvidenceIds=evidence_ids(p,'CANDIDATE_A')[:1],reason='Synthetic all-events claim for coverage test only.')
    with pytest.raises(ValueError,match='full candidate narrative'):
        a.validate_review(v,text,c)
    f['candidateEvidenceIds']=evidence_ids(p,'CANDIDATE_A')
    assert a.validate_review(v,text,c) is v


@pytest.mark.parametrize('failure',['unsupported-pass','unsupported-fail','literal-absence','wrong-basis','aggregation','unknown-question','fail-eligibility','duplicate-id'])
def test_semantic_evidence_and_aggregation_guards(failure):
    text,c,p,v=example();row=v['candidateAssessments']['A'];f=row['semanticChecks']['continuity']
    if failure in ('unsupported-pass','unsupported-fail'):
        f.update(outcome='PASS' if failure=='unsupported-pass' else 'FAIL',basis='SEMANTIC_SUPPORT' if failure=='unsupported-pass' else 'CONTRADICTION')
    if failure in ('literal-absence','fail-eligibility'):
        assessment_failed_check(v,p);f=row['semanticChecks']['trigger_conditions']
        if failure=='literal-absence':f['reason']='The exact source sentence is missing.'
        else:row['eligibleForOwnerProposal']=True
    if failure=='wrong-basis':f['basis']='CONTRADICTION'
    if failure=='aggregation':row['semanticOutcome']='SEMANTIC_SOURCE_PASS'
    if failure=='unknown-question':row['sourceUnknowns']='NONE'
    if failure=='duplicate-id':f['candidateEvidenceIds']=evidence_ids(p,'CANDIDATE_A')[:1]*2
    with pytest.raises(ValueError):a.validate_review(v,text,c)


def test_substantive_omission_requires_adjacent_context_not_single_matching_passage():
    text,c,p,v=example();row=v['candidateAssessments']['A'];f=row['semanticChecks']['continuity'];ids=evidence_ids(p,'CANDIDATE_A')
    f.update(outcome='FAIL',basis='SUBSTANTIVE_OMISSION',sourceEvidenceIds=evidence_ids(p,'SOURCE','Pip remains covered'),candidateEvidenceIds=ids[4:5],reason='Hypothetical omission claim; neighbouring narrative context must be supplied.')
    with pytest.raises(ValueError,match='adjacent'):a.validate_review(v,text,c)
    f['candidateEvidenceIds']=[ids[0],ids[-1]]
    with pytest.raises(ValueError,match='adjacent'):a.validate_review(v,text,c)
    f['candidateEvidenceIds']=ids[4:6]
    assert a.validate_review(v,text,c) is v  # provenance/context only, not proof that this alleged omission is true


@pytest.mark.parametrize('conflict',['The notes fall off before the sneeze.','Standing still doubles the notes.'])
def test_conflicting_text_can_be_referenced_without_hardcoded_outcome(conflict):
    text,c,p,v=example();synthetic=deepcopy(a.sources(text,c));synthetic[0]['narrative']+=' '+conflict
    with patch.object(a,'sources',return_value=synthetic):
        payload=a.wire(text,c)['payload'];value=assessment_review(payload);row=value['candidateAssessments']['A']
        check='continuity' if 'fall off' in conflict else 'trigger_conditions'
        row['semanticChecks'][check].update(outcome='FAIL',basis='CONTRADICTION',sourceEvidenceIds=evidence_ids(payload,'SOURCE','Pip remains covered' if check=='continuity' else 'every removal or transfer attempt'),candidateEvidenceIds=evidence_ids(payload,'CANDIDATE_A',conflict),reason='The selected synthetic passage explicitly conflicts with the protected release timing or multiplication trigger.')
        assert a.derive_assessment(value,text,c)['candidateAssessments']['A']['eligibleForOwnerProposal'] is False


@pytest.mark.parametrize('failure',['empty','generic','cosmetic','audience','A-plus'])
def test_materiality_and_invented_production_claims_rejected(failure):
    text,c,p,v=example();row=v['candidateAssessments']['A'];comp=material_comparison(p);row['creativeConclusion']=comp
    if failure=='empty':comp['candidateEvidenceIds']=[]
    if failure=='generic':
        for k in ('change','visibleConsequence','addressedWeakness','materialityReason'):comp[k]='More engaging and creative.'
    if failure=='cosmetic':comp['change']='Shorter wording describes how the character sits with arms folded.'
    if failure=='audience':row['creativeDimensions']['ENDING_REPLAY']['strength']='Measured retention improved by 30 percent.'
    if failure=='A-plus':row['creativeDimensions']['ENDING_REPLAY']['strength']='Official A+ achieved.'
    with pytest.raises(ValueError):a.validate_review(v,text,c)


@pytest.mark.parametrize('outcome',['MATERIAL_IMPROVEMENT','MINOR_VARIATION','NO_MATERIAL_IMPROVEMENT','UNKNOWN'])
def test_comparative_opinion_never_overrides_source_unknown(outcome):
    text,c,p,v=example();row=v['candidateAssessments']['A'];row['creativeConclusion']=material_comparison(p);row['creativeConclusion']['outcome']=outcome
    assert a.validate_review(v,text,c)['researchPreference']=='NO_CREATIVE_WINNER'
    assert a.derive_assessment(v,text,c)['candidateAssessments']['A']['eligibleForOwnerProposal'] is False
    v['researchPreference']='A'
    assert a.validate_review(v,text,c)['researchPreference']=='A'
    assert a.derive_assessment(v,text,c)['candidateAssessments']['A']['eligibleForOwnerProposal'] is False


def test_same_text_in_other_document_never_authorizes_other_role_id():
    cat=review_evidence_catalog({'SOURCE':'Same text.','CANDIDATE_A':'Same text.','CANDIDATE_B':'Same text.'})
    A=next(r for r in cat['records'] if r['documentRole']=='CANDIDATE_A');B=next(r for r in cat['records'] if r['documentRole']=='CANDIDATE_B')
    assert A['documentSha256']==B['documentSha256'] and A['evidenceId']!=B['evidenceId']
    assert A['evidenceId'] not in a.response_contract(cat)['$defs']['ids_B']['items']['enum']


def test_both_historical_paid_responses_are_unchanged_and_rejected():
    text,c=assessment_inputs();folder=DOCS/'story-review-evidence-reference-fix-evidence'
    for label,path,validator_path,schema in [
        ('v1',DOCS/'authentic-story-independent-review-result-evidence/raw-openai-review.txt',DOCS/'story-review-contract-fix-evidence/legacy-validator.py.txt',None),
        ('v2',DOCS/'real-strict-story-review-execution-evidence/raw-openai-review.txt',folder/'legacy-v2-validator.py.txt',json.loads((folder/'legacy-v2-schema.json').read_text()))]:
        data=path.read_bytes();value=json.loads(data);receipt=json.loads((path.parent/'durable-provider-receipt.json').read_text());assert hashlib.sha256(data).hexdigest()==receipt['responseSha256']
        ns={'__name__':'app.workflow.story_assessment','__package__':'app.workflow','sources':a.sources,'DIMENSIONS':a.DIMENSIONS,'EXTRA_CHECKS':a.EXTRA_CHECKS,'SCHEMA':'assessment-only-story-review-'+label,'RESPONSE_CONTRACT':schema}
        exec(validator_path.read_text(),ns)
        with pytest.raises(ValueError):ns['validate_review'](value,text,c)
        with pytest.raises(ValueError):a.validate_review(value,text,c)
        assert path.read_bytes()==data
        assert json.loads((path.parent/'actual-final-run.json').read_text())['state']=='STOPPED'


@pytest.mark.parametrize('mode',['positive','cross-candidate','fabricated-id','stale-id','missing-evidence','aggregation','unsupported-materiality','refusal','incomplete','malformed','timeout'])
def test_installed_sdk_serializes_dynamic_enums_preserves_raw_no_retry(monkeypatch,mode):
    text,c=grant();calls=[]
    def transport(request):
        body=json.loads(request.content);calls.append(body);assert body==a.request_body(text,c)
        assert body['response_format']['json_schema']['strict'] and body['model']=='gpt-4o-mini-2024-07-18'
        if mode=='timeout':raise httpx.ReadTimeout('Offline only',request=request)
        message={'role':'assistant','content':case_response(json.loads(body['messages'][1]['content']),mode),'refusal':None}
        if mode=='refusal':message.update(content=None,refusal='Offline refusal')
        return httpx.Response(200,json={'id':'MOCK_ONLY','object':'chat.completion','created':0,'model':body['model'],'choices':[{'index':0,'message':message,'finish_reason':'length' if mode=='incomplete' else 'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':200,'total_tokens':300}})
    def client(**kw):
        assert kw['max_retries']==0 and kw['timeout'].as_dict()=={'connect':5,'pool':5,'write':10,'read':240}
        return openai.OpenAI(**kw,http_client=httpx.Client(transport=httpx.MockTransport(transport)))
    monkeypatch.setenv('OPENAI_API_KEY','offline-not-a-credential')
    with patch('app.llm.openai_provider.OpenAI',side_effect=client):r=a.execute(text,c,.1)
    assert len(calls)==1 and (r['processingStatus']=='INDEPENDENT_REVIEW_COMPLETED')==(mode=='positive')
    if mode=='timeout':assert r['actualCostUsd'] is None and r['billingStatus']=='USAGE_UNKNOWN'
    else:assert json.loads(Path(r['rawReceiptFile']).read_text())['providerApiResponse']==r['providerApiResponse']
    if mode=='positive':
        assert r['result']==json.loads(r['rawProviderResponse'])
        assert r['resolvedEvidence']['evidenceType']=='APPLICATION_DERIVED_EVIDENCE'
        assert r['assessmentValidation']['modelSemanticFindings']=='MACHINE_REVIEW_OPINION_NOT_DETERMINISTIC_PROOF'
    with patch('app.llm.openai_provider.OpenAI',side_effect=AssertionError('No repeat')):
        with pytest.raises(FileExistsError):a.execute(text,c,.1)


@pytest.mark.parametrize('archive',['authentic-story-independent-review-result-evidence','real-strict-story-review-execution-evidence'])
def test_consumed_old_grants_cannot_authorize_reference_contract(archive):
    text,c=assessment_inputs();old=json.loads((DOCS/archive/'actual-owner-spending-grant.json').read_text());c.update(assessmentSpendingAuthorized=True,assessmentDispatch=old['operations'][0],storyRequestId=str(uuid.uuid4()))
    with patch('app.llm.openai_provider.OpenAIProvider',side_effect=AssertionError('No provider')):
        with pytest.raises(ValueError):a.execute(text,c,.1)


def test_id_from_a_real_different_revision_is_not_admitted():
    text,c,p,v=example();docs={'SOURCE':text,**{'CANDIDATE_'+r['ref']:r['narrative'] for r in p['candidates']}}
    docs['CANDIDATE_A']+=' Another revision.'
    revised=review_evidence_catalog(docs)
    stale=next(r['evidenceId'] for r in revised['records'] if r['documentRole']=='CANDIDATE_A')
    v['candidateAssessments']['A']['creativeDimensions']['PRODUCTION_EXECUTABILITY']['candidateEvidenceIds']=[stale]
    with pytest.raises(ValueError,match='Strict review schema'):a.validate_review(v,text,c)


@pytest.mark.parametrize('ref',['A','B'])
def test_same_authorized_source_reference_is_valid_for_both_baselines(ref):
    text,c,p,v=example();v['candidateAssessments'][ref]['creativeConclusion']['baselineEvidenceIds']=evidence_ids(p,'SOURCE')[:1]
    assert a.validate_review(v,text,c)['candidateAssessments'][ref]['creativeConclusion']['outcome']=='UNKNOWN'
    derived=a.resolve_review_evidence(v,text,c)
    assert derived['resolvedReferences'][ref+'.creativeConclusion.baselineEvidenceIds'][0]['documentRole']=='SOURCE'


def test_signed_story_review_http_route_uses_only_mocked_provider_and_keeps_no_winner_non_authoritative(monkeypatch):
    text,c=grant();token='offline-story-review-test-token-0123456789abcdef'
    monkeypatch.setenv('WORKFLOW_ADAPTIVE_DISPATCH_TOKEN',token)
    body={'role':'STORY_REVIEW','text':text,'context':c,'maxCostUsd':.1}
    raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
    import hmac
    signature=hmac.new(token.encode(),raw,hashlib.sha256).hexdigest();calls=[]
    class MockProvider:
        def __init__(self,**kwargs):self.last_usage=None;self.last_response_metadata=None;self.last_provider_response=None
        def complete(self,prompt,**kwargs):
            calls.append(prompt);value=assessment_review(json.loads(prompt));result=json.dumps(value,ensure_ascii=False,separators=(',',':'))
            self.last_raw_response=result;self.last_usage={'prompt_tokens':100,'completion_tokens':200}
            self.last_response_metadata={'model':'gpt-4o-mini-2024-07-18','finishReason':'stop','requestId':'MOCK_ONLY'}
            self.last_provider_response={'model':'gpt-4o-mini-2024-07-18','choices':[{'message':{'content':result},'finish_reason':'stop'}],'usage':self.last_usage}
            return result
    with patch('app.llm.openai_provider.OpenAIProvider',MockProvider):
        response=TestClient(app).post('/api/v1/workflow/creative-role',content=raw,headers={'Content-Type':'application/json','X-Adaptive-Dispatch':signature})
    assert response.status_code==200 and len(calls)==1
    result=response.json();assert result['providerDispatched'] is True and result['evidenceType']=='MACHINE_REVIEW'
    assert result['processingStatus']=='INDEPENDENT_REVIEW_COMPLETED'
    assert result['derivedAssessment']['researchPreference']=='NO_CREATIVE_WINNER'
    assert result['derivedAssessment']['ownerDecision']=='PENDING'
    assert result['derivedAssessment']['buildPromptAuthorized'] is False and result['derivedAssessment']['renderAuthorized'] is False
