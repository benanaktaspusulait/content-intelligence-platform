"""Two-stage contracts and orchestration gates. No new creative score or taxonomy.

Seed projection has ZERO story beats and NO payoff. Missing story evidence is
reported as unavailable; it is never fabricated to gain canonical rule support.
"""
from copy import deepcopy
import json
import re
from pathlib import Path
from typing import Literal

from jsonschema import Draft202012Validator
from pydantic import Field

from .semantic_concept_provider import BoundedData, SemanticIdea, MAX_RESPONSE_BYTES
from .semantic_concept_prompt_v2_compact_2 import Compact2PromptRequest
from .semantic_compact_capability_probe_v1 import parse_exact
from .semantic_native_schema_integrity_v1 import native_response_format, final_provider_schema_validation
from .semantic_evidence_adapter import project
from .canonical_creative_evidence import from_structured
from . import premise_naturalness as natural
from .evidence_supported_admission_v2 import assess as admission, OPENING_FLOOR, coherence_findings, PLACEHOLDER
from .beat_consequence_evidence import action_evidence
from .concept_fingerprint import digest
from .semantic_prompt_v2_experiment import analyze

ARCHITECTURE = 'TWO_STAGE_V1'
OPENING_PROMPT_VERSION = 'semantic-opening-seed-prompt-v1'
EXPANSION_PROMPT_VERSION = 'semantic-story-expansion-prompt-v1'
FROZEN_FIELDS = ('protagonistSuggestion','everydayGoal','primaryObject','normalExpectation','impossibleRule',
                 'visibleTrigger','whyThisObject','goalRuleRelationship','frameZeroDescription','environment','dialogueNeed')


class OpeningSeed(BoundedData):
    seedId: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$')
    protagonistSuggestion: str = Field(min_length=1,max_length=100)
    everydayGoal: str = Field(min_length=3,max_length=300)
    primaryObject: str = Field(min_length=2,max_length=100)
    normalExpectation: str = Field(min_length=8,max_length=600)
    impossibleRule: str = Field(min_length=12,max_length=1200)
    visibleTrigger: str = Field(min_length=3,max_length=300)
    whyThisObject: str = Field(min_length=8,max_length=600)
    goalRuleRelationship: str = Field(min_length=8,max_length=600)
    frameZeroDescription: str = Field(min_length=15,max_length=1800)
    openingPhysicalState: str = Field(min_length=3,max_length=1800)
    openingGoalEvidence: str = Field(min_length=3,max_length=1800)
    openingProblemEvidence: str = Field(min_length=3,max_length=1800)
    environment: str = Field(min_length=3,max_length=300)
    dialogueNeed: Literal['NONE','OPTIONAL','REQUIRED']


class SeedEnvelope(BoundedData):
    seeds: list[OpeningSeed] = Field(min_length=1,max_length=1)


class TwoStageRequest(Compact2PromptRequest):
    semanticConceptPromptVersion: Literal['two-stage-v1'] = 'two-stage-v1'
    semanticOpeningSeedPromptVersion: Literal['v1'] = 'v1'
    semanticStoryExpansionPromptVersion: Literal['v1'] = 'v1'


class SeedProvenance(BoundedData):
    generationArchitecture: Literal['TWO_STAGE_V1'] = ARCHITECTURE
    openingSeedId: str
    openingSeedPromptVersion: Literal['v1'] = 'v1'
    storyExpansionPromptVersion: Literal['v1'] = 'v1'
    provider: Literal['openai'] = 'openai'
    model: Literal['gpt-6.1-sol'] = 'gpt-6.1-sol'
    reasoningProfile: Literal['low'] = 'low'
    openingSeedRunId: str
    storyExpansionRunId: str


def seed_response_format():
    schema = deepcopy(SeedEnvelope.model_json_schema())
    final_provider_schema_validation(schema)
    return dict(type='json_schema',json_schema=dict(name='semantic_opening_seed_v1',strict=False,schema=schema))


def parse_seed(raw):
    if len(raw.encode())>MAX_RESPONSE_BYTES: raise ValueError('Seed response exceeds accepted byte cap')
    data=parse_exact(raw)
    Draft202012Validator(seed_response_format()['json_schema']['schema']).validate(data)
    return SeedEnvelope.model_validate(data).seeds[0]


def seed_projection(seed, cast, identity):
    seed=OpeningSeed.model_validate(seed)
    actors=[c for c in cast if seed.protagonistSuggestion.casefold() in (c['name'].casefold(),c['id'].casefold())]
    if len(actors)!=1: raise ValueError('NON_CANONICAL_PROTAGONIST')
    actor=actors[0]
    if any(c['id']!=actor['id'] and re.search(r'\b'+re.escape(c['name'])+r'\b',seed.frameZeroDescription,re.I) for c in cast):
        raise ValueError('MULTIPLE_OR_CONFLICTING_CANONICAL_CHARACTERS')
    candidate=dict(candidateId=identity,title=seed.seedId,protagonist=actor['name'],everydayGoal=seed.everydayGoal,
                   primaryObject=seed.primaryObject,impossibleRule=seed.impossibleRule,frameZeroDescription=seed.frameZeroDescription,
                   normalExpectation=seed.normalExpectation,whyThisObject=seed.whyThisObject)
    fields, projection=project(seed.model_dump(),candidate)
    structured=dict(projection=projection.model_dump(),semanticFields=fields,protagonist=actor['name'],timing=[])
    canonical=from_structured('',structured)
    return candidate,structured,canonical


def gate_seed(seed,cast,identity):
    seed=OpeningSeed.model_validate(seed)
    candidate,structured,canonical=seed_projection(seed,cast,identity)
    report=natural.assess(candidate,canonical_creative_evidence=canonical,generalized_premise_evidence=True)
    decision=admission(candidate,canonical,opening_mandatory=True).model_dump()
    opening=report['openingEvidence'];quality=report['qualityEvidence'];response=report['responseEvidence']
    action=action_evidence(seed.visibleTrigger,candidate['protagonist'])
    findings=coherence_findings(canonical.fields)
    blockers=[]
    if report['instantCausalLegibility']<OPENING_FLOOR: blockers.append('OPENING_TOO_WEAK')
    if findings: blockers.append('RULE_INCONSISTENT')
    if response['state'] in ('RESPONSE_MISSING','RESPONSE_AMBIGUOUS') or PLACEHOLDER.fullmatch(seed.impossibleRule) or not action['supported']:
        blockers.append('RULE_UNCLEAR')
    if quality['arbitraryMagicRisk']['qualitySupport']=='HIGH' or response['compatibility']=='INCOMPATIBLE':
        blockers.append('PREMISE_TOO_WEAK')
    if quality['exactObjectRelevance']['qualitySupport']=='CONTRADICTED': blockers.append('OBJECT_SPECIFICITY_WEAK')
    # Full known-compatibility admission is applicable without inventing story facts.
    # Unclassified fallback needs >=2 supported consequences, absent in a seed.
    known=decision['provenance']=='KNOWN_COMPATIBILITY'
    if known and not decision['admitted']: blockers.append('PREMISE_TOO_WEAK')
    if report['goalInterferenceType'] in ('NONE','CONTRIVED'): blockers.append('PREMISE_TOO_WEAK')
    if seed.dialogueNeed=='REQUIRED' or opening['requiresTextOrDialogue']: blockers.append('OTHER_EXISTING_BLOCKER')
    blockers=list(dict.fromkeys(blockers))
    return dict(seedId=seed.seedId,seedSha256=digest(seed.model_dump()),openingSeedId=identity,openingScore=report['instantCausalLegibility'],acceptedFloor=OPENING_FLOOR,
                acceptedForExpansion=not blockers,disposition=blockers[0] if blockers else 'OPENING_SEED_ACCEPTED',blockers=blockers,
                Naturalness=report,admissionEvidence=decision,
                admissionApplicability='KNOWN_COMPATIBILITY_FULL_DECISION' if known else 'PARTIAL_SEED_ONLY_STORY_FACTORS_UNAVAILABLE',
                storyDependentCriteriaUnavailable=['two supporting beat consequences','across-beat causal coherence','payoff'],
                ruleClarity=dict(responseEvidence=response,triggerActionEvidence=action,findings=findings),
                structuredCanonicalInput=structured,canonicalReceipt=canonical.receipt(),providerCalls=0,
                scope='No score bonus from seed annotation fields. Unknown taxonomy is not itself a rejection; unsupported story-dependent admission is not fabricated or treated as an automatic seed failure.')


def select_seed(records):
    accepted=[r for r in records if (r.get('gate') or {}).get('acceptedForExpansion')]
    if not accepted:return None
    # Existing opening score first, then existing configured Naturalness evidence.
    # Stable request order resolves exact residual ties without a new quality score.
    return sorted(accepted,key=lambda r:(-r['gate']['openingScore'],
        -r['gate']['Naturalness']['objectSpecificityScore'],-r['gate']['Naturalness']['triggerNaturalness'],r['requestId']))[0]


def freeze_seed(seed,gate,provenance):
    seed=OpeningSeed.model_validate(seed);provenance=SeedProvenance.model_validate(provenance)
    if not gate['acceptedForExpansion'] or gate['openingScore']<OPENING_FLOOR:raise ValueError('DO_NOT_EXPAND')
    if gate['seedSha256']!=digest(seed.model_dump()) or gate['openingSeedId']!=provenance.openingSeedId:
        raise ValueError('Seed/gate/provenance binding mismatch')
    body=dict(seed=seed.model_dump(),gate=deepcopy(gate),provenance=provenance.model_dump())
    return {**body,'sha256':digest(body)}


def assert_frozen(frozen):
    body={k:v for k,v in frozen.items() if k!='sha256'}
    if digest(body)!=frozen['sha256']:raise ValueError('FROZEN_SEED_TAMPERED')
    if not body['gate']['acceptedForExpansion'] or body['gate']['openingScore']<OPENING_FLOOR:raise ValueError('DO_NOT_EXPAND')
    seed=OpeningSeed.model_validate(body['seed'])
    if body['gate']['seedSha256']!=digest(seed.model_dump()) or body['gate']['openingSeedId']!=body['provenance']['openingSeedId']:
        raise ValueError('Seed/gate/provenance binding mismatch')
    return seed


def expansion_drift(frozen,raw):
    seed=assert_frozen(frozen)
    differences=[dict(field=k,seed=getattr(seed,k),expansion=raw.get(k)) for k in FROZEN_FIELDS if raw.get(k)!=getattr(seed,k)]
    beats=raw.get('beats',[])
    first=' '.join(str(beats[0].get(k,'')) for k in ('strategy','visibleConsequence')) if beats and isinstance(beats[0],dict) else ''
    if re.search(r'\b(?:resets?|restores?|returns?)\b.{0,80}\b(?:normal|original|straight|unactivated)\b',first,re.I):
        differences.append(dict(field='beats[0].openingContinuity',seed=seed.frameZeroDescription,expansion=first,reason='Explicit reset contradicts frozen opening continuation'))
    return dict(check='STORY_MUST_PRESERVE_OPENING_SEED',status='EXPANSION_SEED_DRIFT' if differences else 'PRESERVED',
                differences=differences,exactComparison=True,repairPerformed=False,
                limitation='Exact field equality is deliberately conservative. Unstated semantic resets inside generated beats are additionally screened by the unchanged downstream source/coherence judges, not fully proved by string identity.')


def analyze_expansion(raw,frozen,config,prompt):
    assert_frozen(frozen);data=parse_exact(raw)
    Draft202012Validator(native_response_format(1)['json_schema']['schema']).validate(data)
    if len(data['ideas'])!=1:raise ValueError('Exactly one expansion required')
    drift=expansion_drift(frozen,data['ideas'][0])
    if drift['status']!='PRESERVED':return dict(status='EXPANSION_SEED_DRIFT',drift=drift,pipelineRan=False)
    idea=SemanticIdea.model_validate(data['ideas'][0])
    # The accepted source-constraint comparison catches explicit new magic BEFORE scoring.
    findings=coherence_findings(idea.model_dump())
    if findings:return dict(status='EXPANSION_RULE_INCONSISTENT',drift=drift,findings=findings,pipelineRan=False)
    result=analyze(raw,config,prompt)
    for row in result['allRawIdeas']:
        if row['record']:
            row['record']['candidate']['provenance'].update(frozen['provenance'])
            row['record']['twoStageProvenance']=deepcopy(frozen['provenance'])
    return dict(status='EXPANDED_AND_VALIDATED',drift=drift,pipelineRan=True,pipeline=result,provenance=frozen['provenance'])


def request_spec(config,cast,profile,phase,frozen=None):
    if phase not in ('A','B'):raise ValueError('Unknown phase')
    if (profile['provider'],profile['model'],profile.get('reasoningEffort'))!=('openai','gpt-6.1-sol','low'):
        raise ValueError('Exact accepted LOW profile required')
    if profile.get('responseMode')!='json_schema' or profile.get('tokenParameter')!='max_completion_tokens' or profile.get('temperatureSupported') is not False:
        raise ValueError('Accepted native structured-output transport required')
    if (config.semanticProvider.provider,config.semanticProvider.model,config.semanticProvider.maxOutputTokens,config.semanticProvider.timeoutSeconds,config.semanticRawCount)!=('openai','gpt-6.1-sol',8192,90,1):
        raise ValueError('Accepted single-candidate execution envelope required')
    if phase=='B':
        seed=assert_frozen(frozen)
        current=gate_seed(seed,cast,frozen['provenance']['openingSeedId'])
        if not current['acceptedForExpansion']:raise ValueError('DO_NOT_EXPAND')
    version=OPENING_PROMPT_VERSION if phase=='A' else EXPANSION_PROMPT_VERSION
    name='semantic_opening_seed_prompt_v1.txt' if phase=='A' else 'semantic_story_expansion_prompt_v1.txt'
    system=Path(__file__).with_name(name).read_text().strip()
    payload=dict(promptVersion=version,canonicalCast=cast,requestedCount=1)
    if phase=='B':payload.update(frozenOpeningSeed=frozen['seed'],openingSeedId=frozen['provenance']['openingSeedId'],frozenFields=list(FROZEN_FIELDS))
    fmt=seed_response_format() if phase=='A' else native_response_format(1)
    prompt=dict(system=system,prompt=json.dumps(payload,sort_keys=True,ensure_ascii=False),version=version,sha256=digest([system,payload]))
    args=dict(model='gpt-6.1-sol',messages=[dict(role='system',content=system),dict(role='user',content=prompt['prompt'])],response_format=fmt,max_completion_tokens=8192,reasoning_effort='low')
    return dict(prompt=prompt,arguments=args,configuration=config.model_dump(),cast=cast,phase=phase,
                FINAL_PROVIDER_SCHEMA_VALIDATION=final_provider_schema_validation(fmt['json_schema']['schema']))
