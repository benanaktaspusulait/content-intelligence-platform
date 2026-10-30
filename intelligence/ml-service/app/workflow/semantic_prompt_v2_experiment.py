"""One explicitly authorized V2 transport, then the accepted offline pipeline.

Reporting maps existing outputs; it is not a validator and supplies no score,
threshold, taxonomy label, or selection override. Import has no live side effects.
"""
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from statistics import mean, median

from . import beat_grammar, creative_shape, premise_naturalness
from .canonical_evidence_propagation import evaluate
from .concept_fingerprint import digest
from .evidence_supported_admission_v2 import assess, project_naturalness, coherence_findings
from .semantic_concept_adapter import normalize_idea
from .semantic_concept_generation import review_pool
from .semantic_concept_prompt_v2 import PromptV2Request, prompt_v2, PROMPT_VERSION
from .semantic_concept_provider import parse_response
from .semantic_live_experiment import response_format, request_arguments, write_new
from .short_concept_generation import resolve_cast
from .structured_sfe_replay import structured_input, selected_run

EXPERIMENT_ID = 'semantic-live-v2-count-40-run-001'


def configuration_for(profile):
    return PromptV2Request(generatorMode='semantic',seed=42,count=20,semanticRawCount=40,
        semanticProvider=dict(provider=profile['provider'],model=profile['model'],
            maxCandidates=60,maxOutputTokens=64000,timeoutSeconds=90),
        allowExternalGeneration=True)


def plan(profile):
    return dict(experimentId=EXPERIMENT_ID,provider=profile['provider'],model=profile['model'],
        semanticConceptPromptVersion='v2',promptVersion=PROMPT_VERSION,requestedRawCount=40,
        requestedFinalCount=20,seed=42,maxRequestCount=1,automaticRetries=0,fallback=False,
        maxOutputTokens=64000,timeoutSeconds=90,externalAuthorizationRequired=True,
        renderAuthorized=False,actualCostUsd=None,costEstimate=None)


def execute(directory, profile, *, allow_external_generation=False, authorization=None,
            test_evidence=None, provider_factory=None):
    """Atomic run claim and one request, even on failure. No analysis/repair retry."""
    if not allow_external_generation or not authorization:
        raise ValueError('EXTERNAL_GENERATION_DISABLED: explicit authorization evidence required')
    if not test_evidence or not test_evidence.get('noNewFailures'):
        raise ValueError('TESTS_NOT_VERIFIED: offline tests must finish before live execution')
    if profile['maxOutputTokens'] < 64000:
        raise ValueError('Configured output capacity insufficient; no request attempted')
    if not os.getenv(profile['provider'].upper()+'_API_KEY'):
        raise ValueError('Configured provider credential unavailable; no request attempted')
    config=configuration_for(profile);cast,_=resolve_cast(config);prompt=prompt_v2(config,cast)
    arguments=request_arguments(profile,config,prompt)
    if len(json.dumps(arguments).encode())+64000 > profile['contextTokens']:
        raise ValueError('Configured context capacity insufficient; no request attempted')
    # This exclusive directory survives failures; the fixed experiment cannot be rerun.
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    attempt=directory/'live-attempt';attempt.mkdir()
    write_new(attempt/'preflight.json',{**plan(profile),'externalAuthorization':authorization,
        'credentialPresent':True,'testsPassedBeforeLive':test_evidence,
        'scope':'Single raw ideation request; no renders or production prompts'})
    write_new(attempt/'configuration.json',dict(profile=profile,generation=config.model_dump(),cast=cast))
    write_new(attempt/'prompt.json',prompt)
    write_new(attempt/'request.json',dict(baseUrl=profile['baseUrl'],method='chat.completions.create',
        arguments=arguments,maxRetries=0,timeoutSeconds=90))
    if provider_factory is None:
        from .creative_provider_profiles import CreativeCapabilityProvider
        provider_factory=CreativeCapabilityProvider
    provider=None;raw=''
    metadata=dict(startedAt=datetime.now(UTC).isoformat(),provider=profile['provider'],model=profile['model'],
        promptVersion=PROMPT_VERSION,requestCount=0,status='PREPARING',usage=None,
        actualCostUsd=None,automaticRetries=0,renders=0)
    try:
        provider=provider_factory(profile,64000,90);provider.response_format=response_format()
        metadata.update(requestCount=1,status='REQUEST_STARTED')
        write_new(attempt/'request-started.json',metadata)
        raw=provider.complete(prompt['prompt'],system=prompt['system'],temperature=config.semanticProvider.temperature)
        metadata['status']='COMPLETED'
    except Exception as error:
        metadata.update(status='FAILED',errorType=type(error).__name__,
            httpStatus=getattr(error,'status_code',None),error='Provider failed; no retry or fallback.')
        raw=getattr(provider,'last_raw_response','') if provider else ''
    finally:
        metadata.update(finishedAt=datetime.now(UTC).isoformat(),usage=getattr(provider,'last_usage',None),
            providerResponseMetadata=getattr(provider,'last_response_metadata',None))
        # Actual cost is populated only if explicitly returned by the provider in USD.
        usage=metadata['usage'] or {}
        if isinstance(usage,dict) and isinstance(usage.get('actual_cost_usd'),(float,int)):
            metadata['actualCostUsd']=usage['actual_cost_usd']
        write_new(attempt/'response.txt',raw,raw=True)
        write_new(attempt/'provider-metadata.json',metadata)
        write_new(attempt/'transport-manifest.json',{
            p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(attempt.iterdir()) if p.is_file()})
    return metadata


def observe(raw, candidate, validation, decision):
    """Display existing evidence only. None of these observations enter ranking."""
    sfe=validation['shortFormEngine'];dimensions=sfe['canonicalEvidence']['dimensions']
    findings=coherence_findings(raw)
    coherence=decision.factors.get('causalCoherence',{}).get('supported',
        decision.corePremiseSupported if decision.provenance=='KNOWN_COMPATIBILITY' else False)
    beats=candidate['beatGrammar'].get('canonicalBeatEvidence',[])
    final_findings=[f for f in findings if f.get('beatNumber')==len(raw['beats'])]
    return dict(ruleConsistency=dict(
            status='CONTRADICTION_DETECTED' if findings else 'SUPPORTED_BY_EXISTING_EVIDENCE' if coherence else 'UNRESOLVED',
            sourceFindings=findings,absenceOfFindingIsNotProof=True),
        frameZeroSupported=decision.openingPassed,openingScore=candidate['premiseNaturalness']['instantCausalLegibility'],
        frameZeroCompleteness=dimensions['opening'],goalVisible=dimensions['goal']['openingVisible'],
        causalBeatCount=sfe['majorCausalBeatCount'],describedBeatCount=len(raw['beats']),
        supportedCausalBeatRatio=sfe['majorCausalBeatCount']/len(raw['beats']),
        beatCausalEvidence=beats,sameRuleEscalation=bool(coherence and not findings),
        payoffRuleLinked=bool(dimensions['payoff']['ruleLinked'] and not final_findings),
        payoffEvidence=dimensions['payoff'],payoffRuleConsistencyFindings=final_findings,
        arbitraryMagicRisk=decision.status=='NOT_ADMITTED_ARBITRARY',
        objectSpecificity=decision.factors.get('objectSpecificity'),
        productionFeasibility=dict(ranking=validation['productionRisk'],
            beatGrammar=candidate['beatGrammar']['productionFeasibility'],
            sfeScore=sfe['productionFeasibilityScore'],sfeRisks=sfe['productionRisks'],stagingRisks=sfe['stagingRisks']),
        authority='OBSERVATION_OF_EXISTING_JUDGES_ONLY_NO_SCORING_OR_GATE',
        limitation='Source-text support is not observed visual proof or full semantic verification.')


def analyze(raw, config, prompt):
    """Parse every raw item, normalize with V1 adapter, explicitly select accepted opt-ins."""
    payload=json.loads(raw);ideas,rejected=parse_response(raw,config.semanticProvider.maxCandidates)
    cast,_=resolve_cast(config);normalized=[];raw_by_id={i.ideaId:i.model_dump() for i in ideas}
    for idea in ideas:
        try:normalized.append(normalize_idea(idea,config,cast,prompt))
        except ValueError as error:
            rejected.append(dict(ideaId=idea.ideaId,stage='NORMALIZATION',errors=[dict(message=str(error))]))
    # Same accepted source adapter/batch review first, followed by explicit canonical propagation.
    normalized=review_pool(normalized)
    candidates=[];rows={};contexts={};records={}
    for original in normalized:
        idea=raw_by_id[original['providerData']['ideaId']];s=structured_input(idea,original)
        c,v,ctx=evaluate(original,s)
        c['premiseNaturalness']=premise_naturalness.assess(c,canonical_creative_evidence=ctx,generalized_premise_evidence=True)
        decision=assess(c,ctx)
        n=deepcopy(c['premiseNaturalness']);c['premiseNaturalness']=project_naturalness(n,decision)
        assert all(c['premiseNaturalness'][k]==value for k,value in n.items() if k!='admitted')
        c['beatGrammar']=beat_grammar.assess(c['structuredBeatPlan'],canonical_creative_evidence=ctx,unclassified_consequence_support=True)
        c['historicalCreativeTerritory']=creative_shape.territory(c)
        cid=c['candidateId'];rows[cid]=v;candidates.append(c)
        contexts[cid]=dict(canonicalCreativeEvidenceMode='v1',shortFormEvidenceSourceVersion='structured-canonical-v1',structuredCanonicalInput=s)
        records[idea['ideaId']]=dict(candidateId=cid,candidate=c,validation=v,admission=decision.model_dump(),
            openingMandatoryAdmission=assess(c,ctx,opening_mandatory=True).model_dump(),
            observation=observe(idea,c,v,decision),canonicalContext=ctx.receipt(),structuredCanonicalInput=s,
            sourceAdapterGenerationLabel=c['generationSource'],actualSemanticConceptPromptVersion=prompt['version'])
    selection=selected_run(candidates,rows,config,contexts)
    suppressed={s['candidateId']:s['reasons'] for s in selection['suppressed']}
    slate={s['candidateId']:s for s in selection['productionSelection']['productionSlate']}
    ranking=selection['canonicalRanking'];finalranks={}
    if ranking:
        finalranks={r['candidateId']:r for r in ranking['rankedEligibleCandidates']+ranking['revisionCandidates']}
    allraw=[]
    for index,item in enumerate(payload['ideas']):
        id=item.get('ideaId') if isinstance(item,dict) else None
        errors=[e for e in rejected if e.get('index')==index or e.get('stage')=='NORMALIZATION' and e.get('ideaId')==id]
        record=records.get(id) if not errors else None
        row=dict(rawIndex=index,ideaId=id,raw=item,schemaResult='INVALID' if any(e['stage']=='SCHEMA' for e in errors) else 'VALID',
            normalization='NORMALIZED' if record else 'REJECTED',rejections=errors,record=record)
        if record:
            cid=record['candidateId'];v=record['validation'];d=record['admission'];o=record['observation']
            blockers=suppressed.get(cid,[])
            review=[]
            if not blockers:review.append('PRODUCTION_ADMISSIBLE')
            if v['eligibility']=='ELIGIBLE':review.append('RANKING_ELIGIBLE')
            if v['shortFormEngine']['status']=='PASS':review.append('SFE_PASS')
            if d['admitted'] and len(blockers)==1:review.append('ADMITTED_ONE_REMAINING_GATE')
            if d['responseClassificationStatus']=='PRESENT_UNCLASSIFIED' and d['corePremiseSupported']:
                review.append('UNCLASSIFIED_STRONG_SOURCE_EVIDENCE_NOVELTY_UNVERIFIED')
            record.update(productionBlockers=blockers,productionAdmissible=not blockers,
                productionSlateRank=slate.get(cid,{}).get('productionSlateRank'),
                rawRank=finalranks.get(cid,{}).get('rank'),humanReviewReasons=review,
                productionDisposition='PRODUCTION_SLATE' if cid in slate else 'PRODUCTION_ADMISSIBLE' if not blockers else 'BLOCKED')
        allraw.append(row)
    result=dict(promptVersion=prompt['version'],semanticConceptPromptVersion=config.semanticConceptPromptVersion,
        rawCount=len(payload['ideas']),requestedRawCount=config.semanticRawCount,allRawIdeas=allraw,
        schemaRejections=[e for e in rejected if e['stage']=='SCHEMA'],normalizationRejections=[e for e in rejected if e['stage']=='NORMALIZATION'],
        preselection=selection,HUMAN_REVIEW_SET=[r['record']['candidateId'] for r in allraw if r['record'] and r['record']['humanReviewReasons']],
        providerCallsDuringAnalysis=0,renders=0,sourceAdapter='Accepted semantic-plan-adapter-v1; its SEMANTIC_V1 source label is inherited adapter metadata, not the actual prompt version.')
    result['metrics']=metrics(result)
    return result


def metrics(result):
    records=[r['record'] for r in result['allRawIdeas'] if r['record']]
    n=len(records);sfe=[r['validation']['shortFormScore'] for r in records];openings=[r['observation']['openingScore'] for r in records]
    distributions=dict(
        openingScores=dict(sorted(Counter(openings).items())),
        BeatGrammar=dict(Counter(r['candidate']['beatGrammar']['beatGrammarQuality'] for r in records)),
        SFE=dict(Counter(r['validation']['shortFormEngine']['status'] for r in records)),
        SFE_scores=dict(sorted(Counter(sfe).items())),
        admissionStatuses=dict(Counter(r['admission']['status'] for r in records)))
    failure_names=['RULE_INCONSISTENCY','OPENING_EVIDENCE_INSUFFICIENT','PREMISE_NOT_ADMITTED','ARBITRARY_MAGIC',
        'WEAK_OBJECT_SPECIFICITY','WEAK_CAUSAL_PROGRESSION','MECHANICAL_BEATS','PAYOFF_NOT_RULE_LINKED',
        'HISTORICAL_COLLISION','CREATIVE_SHAPE_RISK','PRODUCTION_FEASIBILITY']
    failures={key:[] for key in failure_names};gaps=[]
    for r in records:
        d=r['admission'];o=r['observation'];c=r['candidate'];v=r['validation'];id=r['candidateId']
        tests=dict(RULE_INCONSISTENCY=o['ruleConsistency']['status']=='CONTRADICTION_DETECTED',
            OPENING_EVIDENCE_INSUFFICIENT='OPENING_EVIDENCE_INSUFFICIENT' in r['productionBlockers'],
            PREMISE_NOT_ADMITTED='PREMISE_NOT_ADMITTED' in r['productionBlockers'],
            ARBITRARY_MAGIC=o['arbitraryMagicRisk'],
            WEAK_OBJECT_SPECIFICITY=d['factors'].get('objectSpecificity',{}).get('supported') is False,
            WEAK_CAUSAL_PROGRESSION=bool(c['beatGrammar']['flags']) and c['beatGrammar']['beatGrammarQuality'] in ('MECHANICAL','BROKEN'),
            MECHANICAL_BEATS=c['beatGrammar']['beatGrammarQuality']=='MECHANICAL',
            PAYOFF_NOT_RULE_LINKED=not o['payoffRuleLinked'],
            HISTORICAL_COLLISION=c['historicalCreativeTerritory']['historicalCreativeTerritoryRisk']=='HIGH',
            CREATIVE_SHAPE_RISK=c['templateShapeRisk']['risk']=='HIGH',
            PRODUCTION_FEASIBILITY=bool(v['productionRisk']['flags'] or o['productionFeasibility']['sfeRisks'] or c['beatGrammar']['productionFeasibility']['flags']))
        for name,yes in tests.items():
            if yes:failures[name].append(id)
        if d['responseClassificationStatus']!='PRESENT_CLASSIFIED' or d['provenance']=='EVIDENCE_SUPPORTED_UNCLASSIFIED':
            gaps.append(dict(candidateId=id,responseClassificationStatus=d['responseClassificationStatus'],responseClassification=d['responseClassification'],admissionStatus=d['status']))
    return dict(rawCount=result['rawCount'],schemaValidCount=sum(r['schemaResult']=='VALID' for r in result['allRawIdeas']),normalizedCount=n,
        ruleConsistentSupportedCount=sum(r['observation']['ruleConsistency']['status']=='SUPPORTED_BY_EXISTING_EVIDENCE' for r in records),
        ruleConsistencyUnresolvedCount=sum(r['observation']['ruleConsistency']['status']=='UNRESOLVED' for r in records),
        frameZeroSupportedCount=sum(r['observation']['frameZeroSupported'] for r in records),
        goalVisibleCount=sum(r['observation']['goalVisible'] for r in records),
        supportedCausalBeats=sum(r['observation']['causalBeatCount'] for r in records),
        describedBeats=sum(r['observation']['describedBeatCount'] for r in records),
        supportedCausalBeatRatio=sum(r['observation']['causalBeatCount'] for r in records)/sum(r['observation']['describedBeatCount'] for r in records) if n else None,
        payoffRuleLinkedCount=sum(r['observation']['payoffRuleLinked'] for r in records),
        sameRuleEscalationCount=sum(r['observation']['sameRuleEscalation'] for r in records),
        SFE_mean=mean(sfe) if n else None,SFE_median=median(sfe) if n else None,
        openingMean=mean(openings) if n else None,premiseAdmittedCount=sum(r['admission']['admitted'] for r in records),
        rankingEligibleCount=sum(r['validation']['eligibility']=='ELIGIBLE' for r in records),
        productionAdmissibleCount=sum(r['productionAdmissible'] for r in records),productionSlateSize=len(result['preselection']['productionSelection']['productionSlate']),
        humanReviewCount=len(result['HUMAN_REVIEW_SET']),distributions=distributions,
        failureReasonDistribution={k:dict(count=len(v),candidateIds=v) for k,v in failures.items()},
        taxonomyCoverageGaps=gaps,
        metricScope='ALL_NORMALIZED; category counts may overlap; unsupported/unresolved is not proof of invalidity. Existing text-risk screens are not render verification. No new gate or score.')


def all_ideas_text(result):
    lines=['ALL RAW IDEAS — exact stored source plus unchanged system outputs','']
    for row in result['allRawIdeas']:
        raw=row['raw'];record=row['record']
        lines += [f"{row['rawIndex']+1}. {row['ideaId']} / {raw.get('title') if isinstance(raw,dict) else 'INVALID'}",'']
        if isinstance(raw,dict):
            for key,value in raw.items():
                if key=='beats' and isinstance(value,list):
                    for i,beat in enumerate(value,1):
                        lines.append(f'Beat {i}:')
                        lines.extend(f'  {k}: {v}' for k,v in beat.items()) if isinstance(beat,dict) else lines.append(str(beat))
                else:lines.append(f'{key}: {value}')
        else:lines.append(json.dumps(raw))
        lines+=['SYSTEM RESULTS:',json.dumps({k:v for k,v in row.items() if k not in ('raw','record')},ensure_ascii=False,indent=2)]
        if record:
            v=record['validation'];o=record['observation'];c=record['candidate']
            lines.append(json.dumps(dict(candidateId=record['candidateId'],ruleConsistency=o['ruleConsistency'],opening=o,
                Naturalness=c['premiseNaturalness'],admission=record['admission'],BeatGrammar=c['beatGrammar'],SFE=v['shortFormEngine'],
                ranking=v,productionDisposition=record['productionDisposition'],blockers=record['productionBlockers'],
                rawRank=record['rawRank'],productionSlateRank=record['productionSlateRank']),ensure_ascii=False,indent=2))
        lines+=['','']
    return '\n'.join(lines)


def review_cards(result):
    cards=[]
    for row in result['allRawIdeas']:
        r=row['record'];raw=row['raw']
        if not r or not r['humanReviewReasons']:continue
        cards.append(dict(candidateId=r['candidateId'],ideaId=row['ideaId'],title=raw['title'],
            oneSentencePremise=f"{raw['protagonistSuggestion']} tries to {raw['everydayGoal']}: {raw['impossibleRule']}",
            frameZeroHook=raw['frameZeroDescription'],coreRule=raw['impossibleRule'],progression=raw['beats'],payoff=raw['finalPayoff'],
            systemConcerns=dict(blockers=r['productionBlockers'],admissionReasons=r['admission']['reasons'],
                sfeFindings=r['validation']['shortFormEngine']['findings'],rankingWarnings=r['validation']['weaknesses'],
                penalties=r['validation']['penalties'],shapeRisk=r['candidate']['templateShapeRisk'],
                historical=r['candidate']['historicalCreativeTerritory'],productionRisk=r['validation']['productionRisk']),
            currentStatus=r['productionDisposition'],reviewReasons=r['humanReviewReasons'],
            noveltyVerified=False,canonicalPromotion=False,humanDecision=None))
    return cards
