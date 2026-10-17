#!/usr/bin/env python3
"""Prepare the existing one-round Story Evolution workflow; never dispatch.

Uses saved research evidence and resolved Compose role configuration. No
credentials, database connections, provider construction or application POSTs.
"""
import hashlib
import json
import os
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault('POMPOM_DATA_ROOT', str(ROOT / 'intelligence/data'))
sys.path.insert(0, str(ROOT / 'intelligence/ml-service'))
from app.workflow.creative_roles import preview_story_request
from app.workflow.adaptive_optimization import feasibility


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def main():
    if '--assessment-only-review' in sys.argv:
        return assessment_only_review()
    if '--identity-fidelity-followup' in sys.argv:
        return identity_fidelity_followup()
    if '--repaired-contract' in sys.argv:
        return repaired_contract()
    evidence = ROOT / 'intelligence/backend/target/disposable-owner-http/run-oT9HS7/real-execution-runtime'
    saved = json.loads((evidence / 'run-a-final.json').read_text())
    scope = saved['scope']
    story = scope['approvedStory']['text']
    assert sha(story) == 'ba352d486c4252c5c6fefe585ad976c0b6f73c299f7554863848bdd842a99b3d'
    assert sha(scope['baselinePrompt']) == '1a9a8cfc7e4c6e0a037ba3642a10c11c81d41ce8b574aa3c79cbaee7ce1215f5'
    canonical = (saved['progress'].get('baselineEvaluation') or saved['progress']['bestEvaluation'])['canonical']
    policy = feasibility(canonical, scope['baselinePrompt'])
    objective = ('Propose a materially stronger, natural 15-second ABSURD_PHYSICS story for SEEDANCE_2_0_MINI, '
                 'image2video, 480p, 9:16. Preserve Pip the rabbit, the sticky-note/cabinet premise, the existing '
                 'multiplication rule and the final sneeze leaving Pip relieved beside a messy cabinet. '
                 'Other source events/order are revision proposals, not automatically approved facts. '
                 'Improve the first visible promise, distinct viewer-visible consequences and natural pacing; '
                 'reduce artificial strategy density and overloaded final seconds. Avoid thin-object precision '
                 'where possible; report concept unsuitability rather than disguising generator risk. '
                 'Compare real creative merit, not numerical rule coverage. No audience or render claims.')
    findings = []
    losses = {row['ruleId']: row for row in policy['losses']}
    for bucket in ('failedRules', 'unknownRules'):
        for row in canonical[bucket]:
            loss = losses.get(row['ruleId'], {})
            kind = loss.get('classification')
            classification = ('STORY_LEVEL_CHANGE_REQUIRES_OWNER_APPROVAL' if kind == 'PROTECTED_STORY_CONFLICT' else
                              'EVIDENCE_ONLY' if kind == 'EVIDENCE_REQUIRED' or (not loss and bucket == 'unknownRules') else
                              'PROMPT_OR_EXECUTION_LEVEL')
            findings.append({**{key: row[key] for key in ('ruleId','outcome','severity','family','message','details') if key in row},
                             'repairClassification': classification,
                             **({key: loss[key] for key in ('reason','overallLoss')} if loss else {})})
    feasibility_context = {
        'version': 'canonical-story-feasibility-context-v1', 'creativeReviewVersion': 'creative-story-merit-v1',
        'sourceStoryId': scope['approvedStory']['storyId'],
        'sourceApprovalRecordId': scope['approvedStory']['approvalRecordId'],
        'sourceRevisionId': scope['approvedStory']['revision'], 'sourceStorySha256': sha(story),
        'baselineAnalysisId': scope['analysisId'], 'rulesetVersion': '1.11',
        'target': {'name':'CANONICAL_A','minimumScore':92,'rulesetVersion':'1.11','scoreIsPrediction':False},
        'baseline': {key: canonical[key] for key in ('score','grade','status')},
        'targetAwarePreflight': {key: policy[key] for key in ('version','state','generationAllowed','researchGenerationEligibility','currentScore','fixedEvidenceOptimisticCeiling','canonicalATargetStatus','reasons','losses','missingEvidence','genuineSourceAttemptCount','renderAuthorized')},
        'canonicalFindings': findings,
        'mandatoryEvidenceContracts': ['SOURCE_BOUND_BEATS','EXACT_STORY_QUOTES_WHEN_CLAIMED','UNKNOWN_WHEN_UNSUPPORTED','INDEPENDENT_VISUAL_EVIDENCE_FOR_VISUAL_GATES'],
        'creativeRequirements': ['IMMEDIATE_VISUALLY_UNDERSTANDABLE_OPENING','CLEAR_PHYSICAL_CAUSALITY','MEANINGFUL_VISUAL_PROGRESSION','ACTIVE_MAIN_CHARACTER','GENUINELY_DISTINCT_PROBLEM_SOLVING_WHEN_NARRATIVELY_JUSTIFIED','ESCALATING_CONSEQUENCES','MEANINGFUL_REALIZATION_OR_REVERSAL_OR_PAYOFF','GENERATOR_FEASIBLE_MOVEMENT','ORIGINALITY_WITHOUT_COPYING_PRIOR_SILHOUETTES'],
        'prohibitedShortcuts': ['INVENT_PASS_EVIDENCE','TREAT_UNKNOWN_AS_PASS','ADD_MEANINGLESS_SCORE_ACTIONS','RENAME_REPEATED_ACTIONS_AS_STRATEGIES','COUNT_CAMERA_CHANGES_AS_STORY_STRATEGIES','CLAIM_UNSEEN_EFFECTS_VISIBLE','ADD_UNRELATED_PROTAGONISTS_OR_ANIMALS','COPY_PRIOR_WINNING_SILHOUETTES','CHANGE_PROTECTED_SOURCE_WITHOUT_OWNER_APPROVAL'],
        'assessmentScope': 'TEXTUAL_STORY_FEASIBILITY_PREDICTION_ONLY; CANONICAL OUTCOMES REQUIRE BUILD_PROMPT_AND_RULESET_1_11',
    }
    feasibility_context['contextSha256'] = sha(json.dumps(feasibility_context, ensure_ascii=False, separators=(',',':')))
    context = {'inputMode':'DETAILED_STORY','storyGenerationMode':'IMPROVE_EXISTING_STORY',
               'approvedStoryText':story,'sourceStoryRecordId':scope['approvedStory']['storyId'],
               'sourceFingerprint':sha(story),
               'lockedRequirements':['PRESERVE_CORE_PREMISE','PRESERVE_CHARACTER_IDENTITY','PRESERVE_PHYSICAL_RULE','PRESERVE_ENDING'],
               'objective':objective,'roundNumber':1,'previousRevision':'','bestCandidate':{},
               'rejectedCandidates':[],'acceptedChanges':[],'previousAssessment':{},'requestedAlternativeCount':2,
               'canonicalStoryFeasibilityContext':feasibility_context}
    outbound = preview_story_request('STORY', story, context)
    # Resolve configuration in memory. Never emit credentials or the complete
    # compose configuration, which contains secrets.
    config = json.loads(subprocess.check_output(['docker','compose','config','--format','json'], cwd=ROOT/'intelligence'))
    env = config['services']['ml-service']['environment']
    profiles = {}
    for role, provider, tokens in [('STORY','deepseek',4000),('STORY_REVIEW','openai',4000)]:
        model = env.get('WORKFLOW_'+role+'_MODEL')
        input_rate = Decimal(str(env.get('WORKFLOW_'+role+'_INPUT_USD_PER_MILLION')))
        output_rate = Decimal(str(env.get('WORKFLOW_'+role+'_OUTPUT_USD_PER_MILLION')))
        if not model or input_rate <= 0 or output_rate <= 0:
            raise SystemExit('Missing exact current role model/pricing; no experiment ready')
        preview = outbound if role == 'STORY' else preview_story_request(role, story, {
            'canonicalStoryFeasibilityContext':feasibility_context})
        payload_bound = outbound['payloadBytes'] if role == 'STORY' else 24000
        if payload_bound > 24000:
            raise SystemExit('Prepared request exceeds current role input limit')
        bound = (Decimal(payload_bound + preview['systemBytes'] + 1000) * input_rate + tokens * output_rate) / Decimal(1000000)
        profiles[role] = {'provider':provider,'model':model,
            'configured':bool(env.get(provider.upper()+'_API_KEY')),
            'liveAvailability':'NOT_PROBED_NO_INFERENCE', 'inputUsdPerMillion':str(input_rate),'outputUsdPerMillion':str(output_rate),
            'maxOutputTokens':tokens,'payloadByteUpperBound':payload_bound,'systemBytes':preview['systemBytes'],
            'framingSafetyMargin':1000,'maximumCalculatedUsd':str(bound),
            'boundBasis':'EXACT_PREPARED_PAYLOAD' if role == 'STORY' else 'CURRENT_24000_BYTE_REVIEW_INPUT_ENVELOPE; GENERATED_STORIES_NOT_YET_AVAILABLE'}
    # Existing ledger splits total authorization equally across two requests.
    per_request = max(Decimal(p['maximumCalculatedUsd']) for p in profiles.values()).quantize(Decimal('.000001'),rounding=ROUND_CEILING)
    total = per_request * 2
    grant = {'sourceStoryRecordId':scope['approvedStory']['storyId'],
             'approvalRecordId':scope['approvedStory']['approvalRecordId'],'baselineAnalysisId':scope['analysisId'],
             'objective':objective,'maxRounds':1,'maxRequests':2,'maxTotalUsd':float(total),'maxRunSeconds':600,
             'idempotencyKey':'story-creative-v1-'+sha(story+objective)[:32],
             'authorizePaidInference':False,'confirmSourceAuthority':False,'automaticRetries':False}
    manifest = {'version':'prepared-story-creative-experiment-v1','preparedOnly':True,
                'originalStory':story,'proposedStories':None,'exactProtectedChanges':'PENDING_PROVIDER_OUTPUT_AND_INDEPENDENT_REVIEW',
                'ownerApprovalDecision':'PENDING','sourceSnapshot':scope['approvedStory'],
                'sourcePromptSha256':sha(scope['baselinePrompt']),'profiles':profiles,
                'storyRequestPreview':outbound,'requestContextPreview':context,
                'contextBindingNote':'Backend revalidates persisted subject and recompiles context on start. This preview is not authority to restore or recreate saved IDs.',
                'endpoint':'/api/v1/intelligence/workflow/cpq/story-evolution-runs','authorizationTemplate':grant,
                'maximumRequests':2,'maximumTotalReservationUsd':str(total),'perRequestReservationUsd':str(per_request),
                'sumCalculatedRequestUpperBoundsUsd':str(sum(Decimal(p['maximumCalculatedUsd']) for p in profiles.values())),
                'reviewPayloadLimitation':'Exact review bytes depend on the generated stories. The enforced current 24000-byte maximum is priced instead of inventing a candidate.',
                'realDispatchEnabled':env.get('CPQ_PILOT_REAL_ENABLED','false'),
                'requiredPreDispatchChecks':['FRESH_EXPLICIT_OWNER_AUTHORIZATION','EXACT_EXISTING_STORY_APPROVAL_ANALYSIS_BINDINGS','CURRENT_MODEL_PRICE_AND_PAYLOAD_MATCH','GENUINE_CROSS_PROVIDER_REVIEW','DURABLE_RESERVATION_BEFORE_EACH_REQUEST','STOP_ON_AMBIGUOUS_DISPATCH_OR_USAGE','NO_RETRY_FALLBACK_OR_EXTRA_ROUND'],
                'providerCalls':0,'providerSpendUsd':0,'productionDatabaseWrites':0}
    output = ROOT/'intelligence/docs/CREATIVE_STORY_NEXT_EXPERIMENT_MANIFEST.json'
    output.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'manifest':str(output),'maximumTotalReservationUsd':str(total),'profiles':profiles,'providerCalls':0}))


def repaired_contract():
    """Recompute the tested owner's exact strict preflight; never dispatch."""
    from app.workflow.story_experiment import preview, sha as fingerprint, VERSION
    evidence_path = ROOT/'intelligence/backend/target/story-experiment-contract-dry-run.json'
    tested = json.loads(evidence_path.read_text())
    if tested.get('realProviderCalls') != 0 or tested.get('productionDbWrites') != 0:
        raise SystemExit('Non-billable integrated contract evidence required')
    scope = tested['trace']['scope']
    source_scope = scope['sourceScopeSha256']
    assert fingerprint({k:v for k,v in scope.items() if k != 'sourceScopeSha256'}) == source_scope
    historical = json.loads((ROOT/'intelligence/docs/CREATIVE_STORY_NEXT_EXPERIMENT_MANIFEST.json').read_text())
    assert scope['sourceStory'] == historical['originalStory']
    config = json.loads(subprocess.check_output(['docker','compose','config','--format','json'],cwd=ROOT/'intelligence'))
    env = config['services']['ml-service']['environment']
    for role in ('STORY','STORY_REVIEW'):
        for suffix in ('MODEL','INPUT_USD_PER_MILLION','OUTPUT_USD_PER_MILLION'):
            key='WORKFLOW_'+role+'_'+suffix
            if not env.get(key):raise SystemExit('Missing current configured role value: '+key)
            os.environ[key]=str(env[key])
    common = {'canonicalStoryFeasibilityContext':scope['canonicalStoryFeasibilityContext'],
              'approvedStoryText':scope['sourceStory'],'sourceFingerprint':scope['sourceStorySha256'],
              'objective':scope['objective'],'roundNumber':1,
              'storyExperiment':{'version':VERSION,'requestedAlternativeCount':2,
                  'sourceStorySha256':scope['sourceStorySha256'],'sourceScopeSha256':source_scope,
                  'protectedAnchors':scope['protectedAnchors']}}
    generation={**common,'inputMode':'DETAILED_STORY','storyGenerationMode':'IMPROVE_EXISTING_STORY',
                'requestedAlternativeCount':2,'lockedRequirements':['PRESERVE_CORE_PREMISE','PRESERVE_CHARACTER_IDENTITY','PRESERVE_PHYSICAL_RULE','PRESERVE_ENDING']}
    review_context={**common,'reviewPolicyVersion':'creative-story-merit-v1'}
    operations=[preview('STORY',scope['sourceStory'],generation),preview('STORY_REVIEW',scope['sourceStory'],review_context)]
    per_request=max(Decimal(str(x['maximumCalculatedUsd'])) for x in operations).quantize(Decimal('.000001'),rounding=ROUND_CEILING)
    for operation in operations:operation['maxCostUsd']=float(per_request)
    total=per_request*2
    # These must be the same bindings exercised through PostgreSQL + signed ML
    # request boundaries. A stale test artifact cannot confer fresh readiness.
    expected=tested['trace']['authorization']['operations']
    for observed,wanted in zip(operations,expected):
        if observed != wanted:raise SystemExit('Current preflight differs from integrated evidence; rerun the focused contract test')
    grant={'experimentVersion':VERSION,'sourceStoryRecordId':scope['sourceStoryRecordId'],
           'approvalRecordId':scope['sourceApprovalRecordId'],'baselineAnalysisId':scope['baselineAnalysisId'],
           'protectedAnchors':scope['protectedAnchors'],'objective':scope['objective'],'sourceScopeSha256':source_scope,
           'operations':operations,'maxRounds':1,'maxRequests':2,'maxRunSeconds':600,'maxTotalUsd':float(total),
           'automaticRetries':False,'fallback':False,'authorizePaidInference':False,'confirmSourceAuthority':False,
           'idempotencyKey':'real-story-pilot-v1-'+fingerprint({'scope':source_scope,'operations':operations})[:32]}
    output={'experimentVersion':VERSION,'sourceStorySha256':scope['sourceStorySha256'],
            'sourceScopeSha256':source_scope,'sourceScope':scope,'operations':operations,
            'historicalPreparedCapUsd':'0.017966','recomputedMaximumReservationUsd':str(total),
            'budgetChangeRequiresExplicitOwnerApproval':total != Decimal('.017966'),
            'authorizationTemplate':grant,'ownerAuthorization':'NOT_GRANTED','providerCalls':0,'providerSpendUsd':0,
            'liveAvailability':'NOT_PROBED_NO_INFERENCE','storyRequestPreview':preview_story_request('STORY',scope['sourceStory'],generation),
            'reviewTemplatePreview':preview_story_request('STORY_REVIEW',scope['sourceStory'],review_context),
            'reviewPayloadSha256':'NOT_CREATED_UNTIL_DURABLE_STORY_RECEIPT',
            'integrationEvidenceSha256':hashlib.sha256(evidence_path.read_bytes()).hexdigest()}
    target=ROOT/'intelligence/docs/REAL_STORY_EXPERIMENT_REPAIRED_MANIFEST.json'
    target.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'manifest':str(target),'recomputedMaximumReservationUsd':str(total),'providerCalls':0,
                      'sourceScopeSha256':source_scope}))


def identity_fidelity_followup():
    """Prepare a fresh direct-identity grant; leave historical manifests intact."""
    from app.workflow.story_experiment import preview, sha as fingerprint, VERSION
    original = json.loads((ROOT/'intelligence/docs/REAL_STORY_EXPERIMENT_REPAIRED_MANIFEST.json').read_text())
    proof_path = ROOT/'intelligence/backend/target/story-model-fidelity-fix-dry-run.json'
    proof = json.loads(proof_path.read_text())
    if proof.get('realProviderCalls') != 0 or proof.get('productionDbWrites') != 0:
        raise SystemExit('Non-billable complete workflow proof required')
    trace = proof['trace']; scope = trace['scope']
    if scope != original['sourceScope']:
        raise SystemExit('Protected source changed; separate owner decision required')
    evidence = ROOT/'intelligence/docs/story-model-fidelity-fix-evidence'
    catalog = json.loads((evidence/'live-model-catalog.json').read_text())
    review_catalog = json.loads((evidence/'openai-review-model.json').read_text())
    if (catalog['statusCode'] != 200 or 'deepseek-flash' not in {m['id'] for m in catalog['body']['data']}
            or review_catalog['statusCode'] != 200 or review_catalog['body']['id'] != 'gpt-4o-mini-2024-07-18'):
        raise SystemExit('Exact non-inference model discovery is required')
    environment = {'WORKFLOW_STORY_PILOT_MODEL_POLICY':'DIRECT_FLASH_TEXT_V1',
        'WORKFLOW_STORY_MODEL':'deepseek-flash','WORKFLOW_STORY_INPUT_USD_PER_MILLION':'.3',
        'WORKFLOW_STORY_OUTPUT_USD_PER_MILLION':'1.2',
        'WORKFLOW_STORY_REVIEW_MODEL':'gpt-4o-mini-2024-07-18',
        'WORKFLOW_STORY_REVIEW_INPUT_USD_PER_MILLION':'.15','WORKFLOW_STORY_REVIEW_OUTPUT_USD_PER_MILLION':'.6'}
    os.environ.update(environment)
    common={'canonicalStoryFeasibilityContext':scope['canonicalStoryFeasibilityContext'],
        'approvedStoryText':scope['sourceStory'],'sourceFingerprint':scope['sourceStorySha256'],
        'objective':scope['objective'],'roundNumber':1,
        'storyExperiment':{'version':VERSION,'requestedAlternativeCount':2,
            'sourceStorySha256':scope['sourceStorySha256'],'sourceScopeSha256':scope['sourceScopeSha256'],
            'protectedAnchors':scope['protectedAnchors']}}
    generation={**common,'inputMode':'DETAILED_STORY','storyGenerationMode':'IMPROVE_EXISTING_STORY',
        'requestedAlternativeCount':2,'lockedRequirements':['PRESERVE_CORE_PREMISE','PRESERVE_CHARACTER_IDENTITY','PRESERVE_PHYSICAL_RULE','PRESERVE_ENDING']}
    review={**common,'reviewPolicyVersion':'creative-story-merit-v1'}
    operations=[preview('STORY',scope['sourceStory'],generation),preview('STORY_REVIEW',scope['sourceStory'],review)]
    per_request=max(Decimal(str(x['maximumCalculatedUsd'])) for x in operations).quantize(Decimal('.000001'),rounding=ROUND_CEILING)
    for op in operations:op['maxCostUsd']=float(per_request)
    if operations != trace['authorization']['operations']:
        raise SystemExit('Current bindings differ from complete mocked workflow proof')
    grant={**original['authorizationTemplate'],'operations':operations,'maxTotalUsd':float(per_request*2),
        'authorizePaidInference':False,'confirmSourceAuthority':False,
        'idempotencyKey':'story-identity-fidelity-v2-'+fingerprint({'scope':scope['sourceScopeSha256'],'operations':operations})[:32]}
    manifest={'experimentVersion':VERSION,'followupContractVersion':'direct-identity-exact-evidence-v2',
        'sourceScope':scope,'sourceScopeSha256':scope['sourceScopeSha256'],'sourceStorySha256':scope['sourceStorySha256'],
        'operations':operations,'authorizationTemplate':grant,'ownerAuthorization':'NOT_GRANTED',
        'maximumRequests':2,'maximumTotalReservationUsd':str(per_request*2),
        'perRequestReservationUsd':str(per_request),'maxRunSeconds':600,'automaticRetries':False,'fallback':False,
        'requiredDisposableEnvironmentOverrides':environment,'productionConfigurationChanged':False,
        'pricingBasis':'2026-10-17 official DeepSeek peak uncached rates, OpenAI standard rates; no cache/discount assumed',
        'pricingSources':['https://api-docs.deepseek.com/quick_start/pricing/','https://developers.openai.com/api/docs/models/gpt-4o-mini'],
        'reviewPayloadSha256':'NOT_CREATED_UNTIL_DURABLE_ACCEPTED_CANDIDATES',
        'storyRequestPreview':preview_story_request('STORY',scope['sourceStory'],generation),
        'reviewTemplatePreview':preview_story_request('STORY_REVIEW',scope['sourceStory'],review),
        'disposableProofSha256':hashlib.sha256(proof_path.read_bytes()).hexdigest(),
        'realProviderCalls':0,'providerSpendUsd':0,'preparedOnly':True,
        'limitations':['Model catalog discovery is not an inference success guarantee',
            'OpenAI snapshot is documented deprecated but account metadata lookup returned 200',
            'No alias accepted; exact requested/returned identity required',
            'Source textual mapping does not establish independent semantic fidelity']}
    target=ROOT/'intelligence/docs/REAL_STORY_IDENTITY_FIDELITY_FOLLOWUP_MANIFEST.json'
    target.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'manifest':str(target),'maximumTotalReservationUsd':str(per_request*2),'providerCalls':0,'ownerAuthorization':'NOT_GRANTED'}))


def assessment_only_review():
    """One existing cross-provider reviewer; never generation or dispatch."""
    from app.workflow.story_assessment import preview, wire, POLICY
    if '--evidence-reference-review' not in sys.argv:
        raise SystemExit('Consumed quote-review manifests are immutable; use --assessment-only-review --evidence-reference-review for v3 preparation')
    proof_path=ROOT/'intelligence/docs/story-review-evidence-reference-fix-evidence/http-positive-proof.json'
    proof=json.loads(proof_path.read_text())
    if proof.get('realProviderCalls') != 0 or proof.get('productionDbWrites') != 0:
        raise SystemExit('Non-billable real-application review proof required')
    trace=proof['trace']
    if trace['state'] != 'ASSESSMENT_COMPLETE_OWNER_DECISION_PENDING':
        raise SystemExit('Complete assessment-only workflow proof required')
    scope=trace['scope'];context={'assessmentOnlyPolicy':POLICY,'assessmentScope':scope}
    config=json.loads(subprocess.check_output(['docker','compose','config','--format','json'],cwd=ROOT/'intelligence'))
    configured=config['services']['ml-service']['environment']
    for suffix in ('MODEL','INPUT_USD_PER_MILLION','OUTPUT_USD_PER_MILLION'):
        key='WORKFLOW_STORY_REVIEW_'+suffix
        if not configured.get(key):raise SystemExit('Explicit configured review profile required')
        os.environ[key]=str(configured[key])
    operation=preview(scope['sourceStory'],context)
    cap=Decimal(str(operation['maximumCalculatedUsd'])).quantize(Decimal('.000001'),rounding=ROUND_CEILING)
    operation['maxCostUsd']=float(cap)
    if [operation] != trace['authorization']['operations']:
        raise SystemExit('Current instruction/model/price/source bindings differ from complete integration proof')
    from app.workflow.story_experiment import sha as fingerprint
    grant={'assessmentOnlyPolicy':POLICY,'scopeSha256':fingerprint(scope),'operations':[operation],
        'maxRequests':1,'maxRounds':1,'maxRunSeconds':600,'maxTotalUsd':float(cap),'automaticRetries':False,'fallback':False,
        'authorizePaidInference':False,'confirmAssessmentOnly':False,
        'idempotencyKey':'authentic-assessment-v1-'+fingerprint({'scope':scope,'operation':operation})[:32]}
    prepared={'policy':POLICY,'ownerPolicyApproval':'APPROVED','ownerPaidReviewAuthorization':'NOT_GRANTED',
        'scope':scope,'operation':operation,'authorizationTemplate':grant,'fullReviewerRequest':wire(scope['sourceStory'],context),
        'maxPlannedRealProviderCalls':1,'maximumReservedUsd':str(cap),'realProviderCalls':0,'providerSpendUsd':0,
        'strictProductionAdmissionChanged':False,'productionDbWrites':0,
        'readOnlyEvidenceRootRequired':str(ROOT/'intelligence/docs'),
        'disposableProofSha256':hashlib.sha256(proof_path.read_bytes()).hexdigest(),
        'providerAvailability':'NOT_PROBED_THIS_TASK; previous non-inference model metadata retained; exact model failure must stop without fallback'}
    target=ROOT/'intelligence/docs/STORY_REVIEW_EVIDENCE_REFERENCE_REVIEW_MANIFEST.json'
    from app.workflow.story_assessment import request_body
    prepared['providerRequest']=request_body(scope['sourceStory'],context)
    prepared['authorizationTemplate']['idempotencyKey']='authentic-assessment-refs-v3-'+fingerprint({'scope':scope,'operation':operation})[:32]
    evidence=ROOT/'intelligence/docs/story-review-evidence-reference-fix-evidence'
    for name,value in [('strict-response-schema.json',prepared['providerRequest']['response_format']['json_schema']['schema']),('next-exact-sdk-request.json',prepared['providerRequest']),('evidence-catalog.json',prepared['fullReviewerRequest']['payload']['evidenceCatalog'])]:
        (evidence/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    (evidence/'next-system.txt').write_text(prepared['fullReviewerRequest']['system'])
    (evidence/'next-user.txt').write_text(json.dumps(prepared['fullReviewerRequest']['payload'],ensure_ascii=False,sort_keys=True,separators=(',',':')))
    target.write_text(json.dumps(prepared,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'manifest':str(target),'maximumReservedUsd':str(cap),'maxCalls':1,'paidAuthorization':'NOT_GRANTED','realProviderCalls':0}))


if __name__ == '__main__':
    main()
