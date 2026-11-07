#!/usr/bin/env python3
"""Execute at most one Phase B request for the already stored rolling-pin seed."""
import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / 'intelligence/ml-service'
DOCS = ROOT / 'intelligence/docs'
SOURCE_RUN = DOCS / 'semantic-two-stage-v1-run-001'
SEED_ID = 'mimi-rolling-pin-dough-wall'
SOURCE_SEED_PATH = SOURCE_RUN / 'opening-b/seed.json'
SOURCE_GATE_PATH = SOURCE_RUN / 'opening-b/gate.json'
RUN = DOCS / 'semantic-two-stage-v1-phase-b-run-001'
PREFLIGHT = DOCS / 'semantic-two-stage-v1-phase-b-preflight-v1'
PROOF = PREFLIGHT / 'pre-live-verification.json'
sys.path.insert(0, str(SERVICE))
os.environ.setdefault('POMPOM_DATA_ROOT', str(ROOT / 'intelligence/data'))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, value, *, raw=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(value if raw else json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def build_context():
    from app.workflow import semantic_two_stage_v1 as stage
    from app.workflow import semantic_low_reasoning_probe_v1 as low
    from app.workflow.semantic_transport_isolation_v1 import TIMEOUT
    from app.workflow.creative_provider_profiles import profile
    from app.workflow.short_concept_generation import resolve_cast

    seed_bytes = SOURCE_SEED_PATH.read_bytes()
    source_seed_sha256 = sha256_bytes(seed_bytes)
    seed_payload = json.loads(seed_bytes)
    seed = stage.OpeningSeed.model_validate(seed_payload)
    if seed.seedId != SEED_ID:
        raise ValueError('SOURCE_SEED_ID_MISMATCH')
    saved_gate = json.loads(SOURCE_GATE_PATH.read_text())
    if saved_gate['seedSha256'] != stage.digest(seed.model_dump()):
        raise ValueError('SOURCE_SEED_HASH_MISMATCH')
    stored_record = json.loads((SOURCE_RUN / 'opening-b-record.json').read_text())
    if stored_record.get('seed') != seed.model_dump():
        raise ValueError('SOURCE_SEED_RECORD_MISMATCH')

    prior = json.loads((DOCS / 'semantic-compact-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    accepted = json.loads((DOCS / 'semantic-low-reasoning-full-contract-probe-1-run-001/request-before-sdk.json').read_text())
    inherited = low.plan(profile('openai-escalation'), prior)
    if inherited['newRequest'] != accepted or inherited['selectedReasoningEffort'] != 'low':
        raise ValueError('ACCEPTED_LOW_PROFILE_CHANGED')
    selected_profile = inherited['profile']
    config = stage.TwoStageRequest.model_validate({
        **inherited['spec']['configuration'],
        'semanticConceptPromptVersion': 'two-stage-v1',
        'semanticStoryExpansionPromptVersion': 'v1',
    })
    cast, _ = resolve_cast(config)
    current_gate = stage.gate_seed(seed, cast, saved_gate['openingSeedId'])
    if not current_gate['acceptedForExpansion']:
        raise ValueError('STORED_SEED_NO_LONGER_ACCEPTED')
    provenance = stage.SeedProvenance(
        openingSeedId=saved_gate['openingSeedId'],
        openingSeedRunId='semantic-two-stage-v1-run-001/opening-b',
        storyExpansionRunId=f'{RUN.name}/expansion-1',
    )
    frozen = stage.freeze_seed(seed, current_gate, provenance)
    spec = stage.request_spec(config, cast, selected_profile, 'B', frozen)
    if spec['arguments']['model'] != 'gpt-6.1-sol' or spec['arguments']['reasoning_effort'] != 'low':
        raise ValueError('PHASE_B_PROFILE_MISMATCH')
    if spec['arguments']['max_completion_tokens'] != 8192 or spec['phase'] != 'B':
        raise ValueError('PHASE_B_ENVELOPE_MISMATCH')
    return dict(seed=seed, sourceSeedSha256=source_seed_sha256, sourceSeedCanonicalSha256=saved_gate['seedSha256'],
        savedGate=saved_gate, currentGate=current_gate, frozen=frozen, config=config, cast=cast,
        profile=selected_profile, spec=spec)


def prepare_preflight():
    from app.workflow.semantic_transport_isolation_v1 import TIMEOUT
    context = build_context()
    PREFLIGHT.mkdir(parents=True, exist_ok=False)
    spec = context['spec']
    artifacts = dict(
        sourceSeed=dict(path=str(SOURCE_SEED_PATH.relative_to(ROOT)), id=context['seed'].seedId,
            rawSha256=context['sourceSeedSha256'], canonicalSha256=context['sourceSeedCanonicalSha256'],
            fields=context['seed'].model_dump()),
        openingGate=dict(savedPhaseAOpeningScore=context['savedGate']['openingScore'],
            currentOpeningScore=context['currentGate']['openingScore'],
            currentAcceptedForExpansion=context['currentGate']['acceptedForExpansion'],
            currentOpeningEvidence=context['currentGate']['Naturalness']['openingEvidence']),
        frozenOpeningSeed=context['frozen'], prompt=spec['prompt'],
        request=dict(provider='openai', model=spec['arguments']['model'], reasoningEffort=spec['arguments']['reasoning_effort'],
            phase=spec['phase'], semanticStoryExpansionPromptVersion='v1', arguments=spec['arguments'],
            requestCountMaximum=1, sdkRetries=0, timeoutSeconds=context['config'].semanticProvider.timeoutSeconds,
            timeoutEnvelope=TIMEOUT, maxCompletionTokens=spec['arguments']['max_completion_tokens'], streaming='NON_STREAMING',
            schemaValidation=spec['FINAL_PROVIDER_SCHEMA_VALIDATION']),
    )
    write_new(PREFLIGHT / 'preflight.json', artifacts)
    return artifacts


def execute_once(context, runner, directory=RUN):
    """Claim the immutable output path before one injected provider boundary."""
    from app.workflow.semantic_live_experiment import write_new as safe_write_new
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    spec = context['spec']; profile = context['profile']
    safe_write_new(directory / 'plan.json', dict(
        runId=directory.name, sourceSeedId=context['seed'].seedId,
        sourceSeedSha256=context['sourceSeedSha256'], provider='openai', model='gpt-6.1-sol',
        reasoningEffort='low', phase='B', promptVersion=spec['prompt']['version'],
        maximumLiveRequests=1, maximumPhaseBRequests=1, retries=0, sdkRetries=0,
        fallbacks=0, DeepSeekCalls=0, renders=0,
    ))
    safe_write_new(directory / 'source-seed.json', context['seed'].model_dump())
    safe_write_new(directory / 'frozen-opening-seed.json', context['frozen'])
    safe_write_new(directory / 'prompt.json', spec['prompt'])
    from app.workflow.semantic_transport_isolation_v1 import TIMEOUT
    from app.workflow.concept_fingerprint import digest
    safe_write_new(directory / 'request-before-sdk.json', dict(provider='openai', baseUrl=profile['baseUrl'], model='gpt-6.1-sol',
        arguments=spec['arguments'], requestCountMaximum=1, sdkRetries=0, timeout=TIMEOUT))
    safe_write_new(directory / 'offline-schema-validation.json', spec['FINAL_PROVIDER_SCHEMA_VALIDATION'])
    safe_write_new(directory / 'request-started.json', dict(requestCount=1, maximumLiveRequests=1, provider='openai',
        model='gpt-6.1-sol', reasoningEffort='low', requestSha256=digest(spec['arguments']), retries=0,
        fallbacks=0, DeepSeekCalls=0, renders=0))
    start_utc = datetime.now(UTC); start_ns = time.monotonic_ns()
    try:
        result = runner(directory, profile, spec)
    except Exception as error:
        result = dict(status='FAILED', errorClass=type(error).__name__, usage=None,
            safeMessage='Single Phase B request failed; no retry, fallback or replacement.')
    end_utc = datetime.now(UTC); elapsed = (time.monotonic_ns() - start_ns) / 1e9
    response_path = directory / 'response.txt'
    if not response_path.exists(): safe_write_new(response_path, '', raw=True)
    raw = response_path.read_text()
    result.update(requestCount=1, maximumLiveRequests=1, elapsedSeconds=elapsed,
        wallClockStartUTC=start_utc.isoformat(), wallClockEndUTC=end_utc.isoformat(),
        responseBytes=len(response_path.read_bytes()), retries=0, fallbacks=0,
        DeepSeekCalls=0, renders=0, phase='B')
    safe_write_new(directory / 'execution-result.json', result)
    analysis = None
    if result.get('status') == 'COMPLETED' and raw:
        from app.workflow import semantic_two_stage_v1 as stage
        try:
            analysis = stage.analyze_expansion(raw, context['frozen'], context['config'], spec['prompt'])
        except Exception as error:
            analysis = dict(status='EXPANSION_REJECTED', errorClass=type(error).__name__,
                message=str(error)[:2000], pipelineRan=False, repairPerformed=False)
    safe_write_new(directory / 'analysis.json', analysis or dict(status='NO_COMPLETED_RESPONSE', pipelineRan=False))
    story_audit = build_story_audit(context, raw, analysis) if raw else None
    if story_audit is not None: safe_write_new(directory / 'story-audit.json', story_audit)
    record = dict(execution=result, analysis=analysis, storyAudit=story_audit, sourceSeedId=context['seed'].seedId,
        sourceSeedSha256=context['sourceSeedSha256'], openingScoreBefore=context['currentGate']['openingScore'],
        requestCount=1, retries=0, fallbacks=0, DeepSeekCalls=0, renders=0)
    safe_write_new(directory / 'run-result.json', record)
    return record



def build_story_audit(context, raw, analysis):
    """Expose existing deterministic per-beat and payoff evidence without new scoring."""
    from app.workflow.semantic_compact_capability_probe_v1 import parse_exact
    from app.workflow.evidence_supported_admission_v2 import coherence_findings
    payload = parse_exact(raw); idea = payload['ideas'][0]
    all_findings = coherence_findings(idea)
    pipeline = (analysis or {}).get('pipeline') or {}
    rows = [row for row in pipeline.get('allRawIdeas', []) if row.get('raw', {}).get('ideaId') == idea.get('ideaId')]
    record = rows[0].get('record') if rows else None
    observation = (record or {}).get('observation') or {}
    beat_evidence = observation.get('beatCausalEvidence') or []
    global_status = observation.get('ruleConsistency', {}).get('status')
    per_beat = []
    for index, beat in enumerate(idea.get('beats', [])):
        findings = [finding for finding in all_findings if finding.get('beatNumber') == index + 1]
        evidence = beat_evidence[index] if index < len(beat_evidence) else {}
        if findings:
            status = 'INCONSISTENT'
        elif global_status == 'SUPPORTED_BY_EXISTING_EVIDENCE' and evidence.get('progressionSupported') and evidence.get('actionEvidence', {}).get('supported'):
            status = 'CONSISTENT'
        else:
            status = 'AMBIGUOUS'
        per_beat.append(dict(beatNumber=index + 1, trigger=context['seed'].visibleTrigger,
            expectedResponse=context['seed'].impossibleRule, actualResponse=beat.get('visibleConsequence'),
            consistency=status, existingEvidence=evidence, findings=findings))
    payoff_evidence = observation.get('payoffEvidence') or {}
    payoff_findings = observation.get('payoffRuleConsistencyFindings') or []
    if payoff_findings or idea.get('finalPayoff') != (idea.get('beats') or [{}])[-1].get('visibleConsequence'):
        payoff_status = 'INCONSISTENT'
    elif payoff_evidence.get('ruleLinked') is True and payoff_evidence.get('stateChanging') is True:
        payoff_status = 'CLEAR'
    else:
        payoff_status = 'AMBIGUOUS'
    beats = idea.get('beats') or []
    return dict(seedDrift=(analysis or {}).get('drift'), ruleConsistency=per_beat,
        payoffOrientation=dict(beforeState=beats[-2].get('visibleConsequence') if len(beats) > 1 else context['seed'].frameZeroDescription,
            trigger=beats[-1].get('strategy') if beats else None, afterState=idea.get('finalPayoff'),
            classification=payoff_status, evidence=payoff_evidence, findings=payoff_findings),
        canonicalRuleFindings=all_findings, pipelineRecordPresent=record is not None)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-preflight', action='store_true')
    parser.add_argument('--execute-live', action='store_true')
    args = parser.parse_args()
    if args.prepare_preflight == args.execute_live:
        parser.error('Choose exactly one mode')
    if args.prepare_preflight:
        print(json.dumps(prepare_preflight(), ensure_ascii=False))
        return
    if RUN.exists(): parser.error('Phase B run already claimed; no retry or second request')
    from dotenv import load_dotenv
    load_dotenv(SERVICE / '.env', override=False)
    if not os.getenv('OPENAI_API_KEY'): parser.error('Credential unavailable; no request sent')
    context = build_context()
    proof = json.loads(PROOF.read_text())
    if not proof.get('noNewFailures') or not proof.get('schemaIntegrityPassed'):
        parser.error('Required focused/full offline verification is missing or failed')
    for path, expected in proof['sourceHashes'].items():
        if sha256_bytes((ROOT / path).read_bytes()) != expected:
            parser.error('Source changed after pre-live verification: ' + path)
    preflight = json.loads((PREFLIGHT / 'preflight.json').read_text())
    if preflight['sourceSeed']['rawSha256'] != context['sourceSeedSha256'] or preflight['prompt']['sha256'] != context['spec']['prompt']['sha256']:
        parser.error('Source seed or prompt changed after preflight')
    from app.workflow.semantic_compact_1_probe_v1 import bounded
    result = execute_once(context, bounded)
    print(json.dumps(dict(status=result['analysis']['status'] if result['analysis'] else result['execution']['status'],
        requestCount=result['requestCount'], responseBytes=result['execution']['responseBytes'],
        elapsedSeconds=result['execution']['elapsedSeconds'], runDirectory=str(RUN.relative_to(ROOT))), indent=2))


if __name__ == '__main__': main()
