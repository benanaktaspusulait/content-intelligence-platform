"""Mock intent, source provenance, unchanged judges and bounded live transport."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from app.workflow import semantic_prompt_v2_experiment as experiment
from app.workflow.semantic_concept_prompt_v2 import PromptV2Request, prompt_v2
from app.workflow.semantic_concept_provider import SemanticIdea, build_prompt, parse_response
from app.workflow.semantic_live_experiment import live_prompt
from app.workflow.semantic_concept_generation import GenerationRequest
from app.workflow.short_concept_generation import resolve_cast
from app.workflow.evidence_supported_admission_v2 import assess
from app.workflow.canonical_evidence_propagation import evaluate
from app.workflow.structured_sfe_replay import structured_input

FIXTURE=Path(__file__).parent/'fixtures/semantic_prompt_v2_mock_pairs.json'
PAIRS=json.loads(FIXTURE.read_text())['cases']
PROFILE=dict(provider='deepseek',model='mock-configured-model',baseUrl='https://example.invalid',
    maxOutputTokens=64000,contextTokens=1000000,responseMode='json_object',tokenParameter='max_tokens',
    temperatureSupported=False,reasoningEffort='high')


@pytest.fixture(scope='module')
def config():return experiment.configuration_for(PROFILE)


@pytest.fixture(scope='module')
def pair_results(config):
    cast,_=resolve_cast(config)
    p2=prompt_v2(config,cast)
    # Explicit paired mocks are hand-authored; they do not measure a model's response to a prompt.
    v1=GenerationRequest.model_validate({**config.model_dump(),'semanticConceptPromptVersion':'v1'})
    return dict(v1=experiment.analyze(json.dumps({'ideas':[p['mockV1'] for p in PAIRS]}),v1,live_prompt(v1,cast)),
        v2=experiment.analyze(json.dumps({'ideas':[p['mockV2'] for p in PAIRS]}),config,p2))


def test_v2_additive_version_and_v1_unchanged(config):
    cast,_=resolve_cast(config);original=build_prompt(config,cast,40);live=live_prompt(config,cast)
    p=prompt_v2(config,cast)
    assert p['version']=='semantic-concept-prompt-v2' and config.semanticConceptPromptVersion=='v2'
    assert p['basePromptSha256']==original['sha256']
    assert build_prompt(config,cast,40)==original and live_prompt(config,cast)==live
    assert json.loads(p['prompt'])['candidateSchema']==SemanticIdea.model_json_schema()
    assert not p['responseSchemaChanged']
    with pytest.raises(ValueError):GenerationRequest(semanticConceptPromptVersion='v2')


def test_prompt_covers_immutable_rule_static_frame_and_private_checks(config):
    cast,_=resolve_cast(config);p=prompt_v2(config,cast);s=p['system']
    for clause in ['Once the impossible rule is established, every beat must obey exactly that same physical rule.',
        'one simultaneous, stageable STILL','no first 2–3 seconds','different trigger',
        'Beat 5 if present','Could this payoff happen if the original rule were removed?',
        'Sharing a noun is not enough','outside the known engine taxonomy','property transfer',
        'No extra event after it','Do not rank, score','Do not expose chain-of-thought']:
        assert clause in s
    assert json.loads(p['prompt'])['requestedRawCount']==40
    assert 'ruleConsistencyStatement' not in json.loads(p['prompt'])['candidateSchema']['properties']


@pytest.mark.parametrize('pair',PAIRS,ids=lambda p:p['case'])
def test_all_mock_intent_controls(pair,pair_results):
    v1=next(r['record'] for r in pair_results['v1']['allRawIdeas'] if r['ideaId']==pair['mockV1']['ideaId'])
    v2=next(r['record'] for r in pair_results['v2']['allRawIdeas'] if r['ideaId']==pair['mockV2']['ideaId'])
    assert v1 and v2
    e=pair['expect'];a=v1['observation'];b=v2['observation']
    if 'v2RuleContradiction' in e:assert (b['ruleConsistency']['status']=='CONTRADICTION_DETECTED')==e['v2RuleContradiction']
    if e.get('v1RuleContradiction'):assert a['ruleConsistency']['status']=='CONTRADICTION_DETECTED'
    if e.get('v2OpeningAboveV1'):assert b['openingScore']>a['openingScore']
    if e.get('v2WeakOpening'):assert not b['frameZeroSupported'] and 'OPENING_EVIDENCE_INSUFFICIENT' in v2['productionBlockers']
    if e.get('v2Unclassified'):assert v2['admission']['responseClassificationStatus']=='PRESENT_UNCLASSIFIED'
    if e.get('v2NotAdmitted'):assert not v2['admission']['admitted']
    if e.get('v2NotStrongGrammar'):assert v2['candidate']['beatGrammar']['beatGrammarQuality'] in ('MECHANICAL','BROKEN')
    if pair['case'] in ('A','E','J'):assert b['payoffRuleLinked'] and b['sameRuleEscalation']
    if pair['case']=='F':assert not b['payoffRuleLinked']
    if pair['case']=='G':assert v2['admission']['admitted'] and v2['admission']['responseClassification'] is None


def test_all_raw_ideas_cards_and_counts_complete(pair_results):
    r=pair_results['v2'];text=experiment.all_ideas_text(r);cards=experiment.review_cards(r)
    assert r['rawCount']==10 and r['metrics']['normalizedCount']==10
    assert len(cards)==len(r['HUMAN_REVIEW_SET'])
    for row in r['allRawIdeas']:
        raw=row['raw'];assert raw['impossibleRule'] in text and raw['finalPayoff'] in text
        assert all(b['visibleConsequence'] in text for b in raw['beats'])
        assert raw['frameZeroDescription'] in text
    assert all(c['humanDecision'] is None and not c['canonicalPromotion'] and not c['noveltyVerified'] for c in cards)


def test_existing_sfe_bg_ranking_and_source_are_authoritative(pair_results):
    for row in pair_results['v2']['allRawIdeas']:
        c=row['record']['candidate'];_,v,ctx=evaluate(c,row['record']['structuredCanonicalInput'])
        assert v==row['record']['validation']
        assert assess(c,ctx).model_dump()==row['record']['admission']
        assert row['record']['candidate']['provenance']['rationaleScored'] is False
    assert pair_results['v2']['providerCallsDuringAnalysis']==0
    assert pair_results['v2']['renders']==0


def test_prompt_version_and_rationale_give_no_score_bonus(config):
    cast,_=resolve_cast(config);p=prompt_v2(config,cast);raw=deepcopy(PAIRS[0]['mockV2'])
    first=experiment.analyze(json.dumps({'ideas':[raw]}),config,p)
    raw['providerRationale']='This is a different non-authoritative explanation.'
    second=experiment.analyze(json.dumps({'ideas':[raw]}),config,{**p,'version':'semantic-concept-prompt-v1.1'})
    a=first['allRawIdeas'][0]['record'];b=second['allRawIdeas'][0]['record']
    def without_source_receipt(value):
        value=deepcopy(value)
        for receipt in [value['canonicalCreativeEvidence'],value['normalizedConcept']['canonicalCreativeEvidence']]:
            receipt['provenance'].pop('structuredSourceSha256')
        return value
    # Raw-source hashes truthfully differ when unscored rationale/prompt provenance changes.
    assert without_source_receipt(a['validation'])==without_source_receipt(b['validation'])
    assert a['admission']==b['admission'] and a['productionBlockers']==b['productionBlockers']


def test_schema_failures_retained_no_repair_or_quality_gate(config):
    raw=deepcopy(PAIRS[0]['mockV2']);raw['score']=100
    ideas,rejections=parse_response(json.dumps({'ideas':[raw]}),60)
    assert not ideas and len(rejections)==1
    cast,_=resolve_cast(config);r=experiment.analyze(json.dumps({'ideas':[raw]}),config,prompt_v2(config,cast))
    assert len(r['allRawIdeas'])==1 and r['metrics']['normalizedCount']==0
    assert r['allRawIdeas'][0]['raw']==raw
    # Behavioral contradictions are reported by the existing admission assessor, not a new schema validator.
    assert SemanticIdea.model_validate(PAIRS[5]['mockV2'])


class MockTransport:
    calls=[]
    def __init__(self,*args):pass
    def complete(self,prompt,system='',temperature=.7):
        self.calls.append((prompt,system));self.last_usage={'prompt_tokens':100,'completion_tokens':200}
        self.last_response_metadata={'finishReason':'stop','model':PROFILE['model']}
        return json.dumps({'ideas':[PAIRS[0]['mockV2']]})


def test_single_explicit_request_immutable_record_and_no_cost_estimate(tmp_path,monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','test-secret');MockTransport.calls=[]
    out=tmp_path/'run'
    kw=dict(allow_external_generation=True,authorization={'file':'test-authorization'},
        test_evidence={'noNewFailures':True},provider_factory=MockTransport)
    meta=experiment.execute(out,PROFILE,**kw)
    assert meta['requestCount']==1 and meta['status']=='COMPLETED' and len(MockTransport.calls)==1
    assert meta['usage']=={'prompt_tokens':100,'completion_tokens':200} and meta['actualCostUsd'] is None
    stored=json.loads((out/'live-attempt/request.json').read_text())
    assert stored['arguments']['messages'][1]['content']==MockTransport.calls[0][0]
    assert json.loads((out/'live-attempt/prompt.json').read_text())['system']==MockTransport.calls[0][1]
    assert stored['maxRetries']==0
    assert 'test-secret' not in ''.join(p.read_text() for p in (out/'live-attempt').iterdir())
    with pytest.raises(FileExistsError):experiment.execute(out,PROFILE,**kw)
    assert len(MockTransport.calls)==1


@pytest.mark.parametrize('failure',['network','truncated','malformed'])
def test_failed_request_never_retried(tmp_path,monkeypatch,failure):
    monkeypatch.setenv('DEEPSEEK_API_KEY','test-secret');calls=[]
    class Failure(MockTransport):
        def complete(self,*args,**kwargs):
            calls.append(1);self.last_raw_response='{"ideas": ['
            if failure!='malformed':raise RuntimeError('test-secret must not enter evidence')
            return self.last_raw_response
    kw=dict(allow_external_generation=True,authorization={'file':'test'},test_evidence={'noNewFailures':True},provider_factory=Failure)
    out=tmp_path/'run';experiment.execute(out,PROFILE,**kw)
    assert len(calls)==1 and (out/'live-attempt/response.txt').read_text()=='{"ideas": ['
    assert 'test-secret' not in (out/'live-attempt/provider-metadata.json').read_text()
    with pytest.raises(FileExistsError):experiment.execute(out,PROFILE,**kw)
    assert len(calls)==1


def test_no_live_without_authorization_tests_credentials_or_capacity(tmp_path,monkeypatch):
    out=tmp_path/'run';monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    with pytest.raises(ValueError,match='DISABLED'):experiment.execute(out,PROFILE)
    with pytest.raises(ValueError,match='TESTS_NOT_VERIFIED'):
        experiment.execute(out,PROFILE,allow_external_generation=True,authorization={'file':'test'})
    with pytest.raises(ValueError,match='credential'):
        experiment.execute(out,PROFILE,allow_external_generation=True,authorization={'file':'test'},test_evidence={'noNewFailures':True})
    assert not out.exists()


def test_metrics_are_observations_not_an_additional_gate(pair_results):
    r=pair_results['v2'];before=deepcopy(r['preselection'])
    assert experiment.metrics(r)==r['metrics'] and r['preselection']==before
    assert set(r['metrics']['failureReasonDistribution'])==set('RULE_INCONSISTENCY OPENING_EVIDENCE_INSUFFICIENT PREMISE_NOT_ADMITTED ARBITRARY_MAGIC WEAK_OBJECT_SPECIFICITY WEAK_CAUSAL_PROGRESSION MECHANICAL_BEATS PAYOFF_NOT_RULE_LINKED HISTORICAL_COLLISION CREATIVE_SHAPE_RISK PRODUCTION_FEASIBILITY'.split())
