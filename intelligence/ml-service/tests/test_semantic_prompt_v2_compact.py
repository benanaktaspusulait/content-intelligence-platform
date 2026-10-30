"""Offline policy coverage, native structure, adversarial intent and frozen judges."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import protected_integrity as integrity
from jsonschema import Draft202012Validator
from app.workflow.semantic_concept_prompt_v2_compact import CompactPromptRequest,compact_prompt,construct_native_request,size_metrics
from app.workflow.semantic_concept_prompt_v2 import PromptV2Request,prompt_v2
from app.workflow.semantic_concept_generation import GenerationRequest
from app.workflow.semantic_concept_provider import SemanticIdea,parse_response
from app.workflow.semantic_native_schema_integrity_v1 import native_response_format
from app.workflow.short_concept_generation import resolve_cast

ROOT=Path(__file__).resolve().parents[3]
FIX=Path(__file__).parent/'fixtures'
SPEC=importlib.util.spec_from_file_location('compact_audit',ROOT/'intelligence/scripts/audit-semantic-prompt-v2-compact.py')
AUDIT=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(AUDIT)
POLICIES=json.loads((FIX/'semantic_prompt_v2_compact_policy_v1.json').read_text())['requirements']
MOCKS=json.loads((FIX/'semantic_prompt_v2_compact_mocks_v1.json').read_text())['cases']

@pytest.fixture(scope='module')
def prompts():
    cfg=AUDIT.config();cast,_=resolve_cast(cfg)
    return cfg,cast,compact_prompt(cfg,cast,1),prompt_v2(AUDIT.config('v2'),cast,1)

@pytest.fixture(scope='module')
def mocks():return AUDIT.mock_results()


def test_additive_opt_in_and_legacy_versions_immutable(prompts):
    cfg,cast,p,old=prompts
    assert cfg.semanticConceptPromptVersion=='v2-compact'
    assert GenerationRequest().semanticConceptPromptVersion=='v1'
    with pytest.raises(ValueError):GenerationRequest(semanticConceptPromptVersion='v2-compact')
    with pytest.raises(ValueError):compact_prompt(AUDIT.config('v2'),cast,1)
    assert p['version']=='semantic-concept-prompt-v2-compact'
    assert prompt_v2(AUDIT.config('v2'),cast,1)==old


def test_native_request_reuses_exact_corrected_schema_and_no_transport(prompts,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('No provider construction or network allowed')
    import socket
    from app.workflow import creative_provider_profiles
    monkeypatch.setattr(socket,'create_connection',forbidden)
    monkeypatch.setattr(creative_provider_profiles,'CreativeCapabilityProvider',forbidden)
    cfg,cast,p,_=prompts;r=construct_native_request(cfg,cast,1,AUDIT.PROFILE)
    assert r['arguments']['response_format']==native_response_format(1)
    assert r['FINAL_PROVIDER_SCHEMA_VALIDATION']['schemaSha256']=='91b6a9023b8d7a952ad380b494a4fa91d6f94f58c03a9fe0a979f894f7470ce3'
    assert r['FINAL_PROVIDER_SCHEMA_VALIDATION']['unresolvedReferences']==0
    assert r['semanticEquivalence']['candidateLogicalSchemaIdentical']
    assert r['providerCalls']==0 and 'NO_TRANSPORT' in r['execution']
    assert r['arguments']['max_completion_tokens']==cfg.semanticProvider.maxOutputTokens
    assert r['arguments']['reasoning_effort']=='high' and 'temperature' not in r['arguments']
    assert r['arguments']['messages']==[dict(role='system',content=p['system']),dict(role='user',content=p['prompt'])]
    assert json.loads(json.dumps(r))==r
    with pytest.raises(ValueError):construct_native_request(cfg,cast,1,{**AUDIT.PROFILE,'responseMode':'json_object'})


def test_output_contract_deduplicated_but_cast_history_and_fields_preserved(prompts):
    cfg,cast,p,old=prompts;a=json.loads(p['prompt']);b=json.loads(old['prompt'])
    assert a['canonicalCast']==b['canonicalCast'] and a['historicalCautionZones']==b['historicalCautionZones']
    for key in ('candidateSchema','outputEnvelope','batchInstructions'):assert key not in a
    assert 'candidateSchema' in b
    assert not p['candidateSchemaDuplicatedInPrompt']
    native=native_response_format(1)['json_schema']['schema']['properties']['ideas']['items']
    assert native['properties']==SemanticIdea.model_json_schema()['properties']
    assert native['required']==SemanticIdea.model_json_schema()['required']
    assert a['requestedRawCount']==1


@pytest.mark.parametrize('row',POLICIES,ids=lambda r:r['id'])
def test_every_v2_policy_has_exact_compact_evidence(row,prompts):
    _,_,new,old=prompts
    assert row['preserved']=='YES'
    assert row['v2Evidence'] in old['system'] and row['compactEvidence'] in new['system']
    assert row['v2Evidence'] in old['system'].splitlines()[row['v2Line']-1]
    assert row['compactEvidence'] in new['system'].splitlines()[row['compactLine']-1]


def test_compaction_measured_and_one_private_self_check(prompts):
    _,_,p,old=prompts;a=size_metrics(p['system']);b=size_metrics(old['system'])
    assert b['characters']==9879 and len(b['sections'])==10
    reduction=1-a['characters']/b['characters']
    assert .4<=reduction<=.6
    assert a['exactTokenizerTokens'] is None and 'proxy' in a['estimateMethod']
    assert sum(line.startswith('CORE RULE INVARIANT:') for line in p['system'].splitlines())==1
    assert p['system'].count('FINAL SELF-CHECK (PRIVATE)')==1


@pytest.mark.parametrize('count,expected',[(3,False),(4,True),(5,True),(6,False)])
def test_structural_beat_bounds_count_not_creative_judgment(count,expected):
    row=next(r for r in AUDIT.structural_results()['beats'] if r['beatCount']==count)
    assert row['nativeSchemaValid']==row['domainValid']==expected


@pytest.mark.parametrize('value,expected',[(9,False),(10,True),(15,True),(20,True),(24,False),(None,True)])
def test_declared_duration_bounds_and_optional_default(value,expected):
    row=next(r for r in AUDIT.structural_results()['durations'] if r['suppliedDuration']==value)
    assert row['nativeSchemaValid']==row['domainValid']==expected
    if value is None:assert row['effectiveDomainDuration']==15


@pytest.mark.parametrize('case',MOCKS,ids=lambda c:c['case']+'-'+c['purpose'])
def test_adversarial_mock_intent_and_unchanged_system_scores(case,mocks):
    r=next(r for r in mocks['cases'] if r['case']==case['case']);e=case['expect'];o=r['observation'];a=r['admission']
    assert r['V2CompactScoresEqual']
    if 'schemaValid' in e:assert (r['schemaResult']=='VALID')==e['schemaValid']==r['nativeCandidateSchemaValid']
    if e.get('contradiction'):assert o['ruleConsistency']['status']=='CONTRADICTION_DETECTED'
    if 'finding' in e:assert e['finding'] in [f['code'] for f in o['ruleConsistency']['sourceFindings']]
    if 'frameZeroSupported' in e:assert o['frameZeroSupported']==e['frameZeroSupported']
    if 'payoffRuleLinked' in e:assert o['payoffRuleLinked']==e['payoffRuleLinked']
    if 'admitted' in e:assert a['admitted']==e['admitted']
    if e.get('weakGrammar'):assert r['beatGrammar']['beatGrammarQuality'] in ('MECHANICAL','BROKEN')
    if e.get('sameRuleEscalation'):assert o['sameRuleEscalation']
    if e.get('unclassified'):assert a['responseClassification'] is None and a['responseClassificationStatus']=='PRESENT_UNCLASSIFIED'


def test_free_text_self_scoring_cannot_add_score_and_semantics_are_not_schema(mocks):
    assert mocks['selfClaimInRationale']['scoresEqual']
    assert mocks['selfClaimInRationale']['structurallyAllowed']
    assert mocks['allScoresIdenticalAcrossVersions'] and mocks['providerCalls']==mocks['renders']==0
    a=mocks['cases'][0]
    assert a['nativeCandidateSchemaValid'] and not a['admission']['admitted']
    assert mocks['cases'][10]['admission']['admitted'] and not mocks['cases'][10]['observation']['frameZeroSupported']


def test_probe_classification_from_exact_last_mile_evidence():
    a=AUDIT.old_probe_audit()
    assert a['classification']['CORRECTED_FULL_NATIVE_SCHEMA']=='PASS_AT_EXECUTION_LEVEL'
    assert a['classification']['LOCAL_STRUCTURAL_CONFORMANCE']=='FAIL'
    assert a['strict'] is False and a['beats']['required']
    assert a['beats']['minItems']==4 and a['beats']['maxItems']==5 and a['beats']['returnedCount']==3
    assert a['beats']['nestedRequired']==['strategy','visibleConsequence','newInformation']
    assert a['duration']['returnedValue']==24 and a['duration']['schema']['maximum']==20
    assert not a['domainAccepted']
    assert {(tuple(e['path']),e['validator']) for e in a['actualLocalErrors']}=={(('ideas',0,'beats'),'minItems'),(('ideas',0,'durationSeconds'),'maximum')}


def test_matrix_distinguishes_shape_from_semantic_and_media_guarantees():
    rows=AUDIT.placement_matrix();assert len(rows)>=28
    assert all(r['placement'] in {'SCHEMA_ENFORCED','PROMPT_ENFORCED','VALIDATOR_ENFORCED','MULTI_LAYER','NOT_ENFORCED'} for r in rows)
    assert next(r for r in rows if r['requirement']=='Actual rendered duration ≤20')['placement']=='NOT_ENFORCED'
    assert all((ROOT/r['evidence']['path']).is_file() for r in rows)


def test_all_preexisting_prompts_validators_and_evidence_byte_identical():
    before=json.loads((ROOT/'intelligence/docs/semantic-prompt-v2-compact-v1/protected-before.json').read_text())
    assert len(before)==2295
    integrity.assert_manifest_integrity(ROOT,{p:h for p,h in before.items() if p!='intelligence/ml-service/tests/protected_integrity.py'})
