"""Strict research contract inside the existing STORY/STORY_REVIEW workflow.

No scheduler, persistence or provider fallback. The Java owner-scoped ledger
owns authorization/reservations/receipts; this module compiles and checks the
exact request at its final transport boundary.
"""
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import math
import os
import re
from pathlib import Path

VERSION = 'REAL_CREATIVE_STORY_EVOLUTION_PILOT_V1'
SCHEMA = 'story-pilot-candidates-v1'
EVIDENCE_CONTRACT = 'exact-protected-facts-and-narrative-excerpts-v2'
ANCHORS = {'CHARACTER_IDENTITY', 'CORE_PREMISE', 'PHYSICAL_RULE', 'CONTINUITY', 'ENDING'}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sha(value):
    return hashlib.sha256((value if isinstance(value, str) else encoded(value)).encode()).hexdigest()


def contract(text, context):
    value = context.get('storyExperiment') or {}
    if value.get('version') != VERSION or value.get('requestedAlternativeCount') != 2:
        raise ValueError('SCOPE_OR_INSTRUCTION_MISMATCH: exact experiment/count required')
    anchors = value.get('protectedAnchors')
    if not isinstance(anchors, list) or {a.get('kind') for a in anchors if isinstance(a, dict)} != ANCHORS:
        raise ValueError('Complete protected source anchor contract required')
    if len({a.get('id') for a in anchors}) != len(anchors):
        raise ValueError('Distinct protected source anchor IDs required')
    for anchor in anchors:
        start, end = anchor.get('start'), anchor.get('end')
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text) or text[start:end] != anchor.get('quote'):
            raise ValueError('Protected anchor must bind an exact approved source span')
    if value.get('sourceStorySha256') != sha(text) or not value.get('sourceScopeSha256'):
        raise ValueError('SCOPE_OR_INSTRUCTION_MISMATCH: source binding differs')
    return value


def normalize(text):
    return re.sub(r'\s+', ' ', text.casefold()).strip(' .;,:!?')


def model_policy(role, model):
    """Direct identities only. Historical compatibility names are never aliases.

    The documented Flash profile is opt-in for a newly bound owner grant; it
    cannot reinterpret an existing deepseek-chat authorization or receipt.
    """
    profile = os.getenv('WORKFLOW_STORY_PILOT_MODEL_POLICY', 'LEGACY_EXACT_CHAT_V1')
    if role == 'STORY':
        expected = {'LEGACY_EXACT_CHAT_V1': 'deepseek-chat',
                    'DIRECT_FLASH_TEXT_V1': 'deepseek-flash'}.get(profile)
    else:
        expected = 'gpt-4o-mini-2024-07-18'
    if not expected or model != expected:
        raise ValueError('SCOPE_OR_INSTRUCTION_MISMATCH: model/profile is not explicitly configured')
    return {'version': 'exact-provider-model-v2', 'profile': profile if role == 'STORY' else 'EXACT_OPENAI_REVIEW_V1',
            'requestedModel': model, 'requiredReturnedModel': model, 'pricingIdentity': model,
            'aliasPolicy': 'NONE', 'inputModality': 'TEXT_ONLY',
            'requestParameters': {'thinking': {'type': 'disabled'}} if model == 'deepseek-flash' else {}}


def model_identity(requested, metadata):
    actual = metadata.get('model')
    return {'policyVersion': 'exact-provider-model-v2', 'requestedModel': requested,
            'actualReturnedModel': actual, 'verified': bool(actual) and actual == requested,
            'aliasApplied': False, 'pricingIdentity': actual if actual == requested else None}


def validate(text, context, result):
    """Exact protected-fact mapping, not a claim of semantic/visual fidelity.

    Only cited, unchanged protected clauses establish the bounded textual
    contract. Paraphrased/unmapped protected facts remain UNKNOWN and stop this
    pilot. Unprotected prose/events may vary. Independent semantic review is
    still required; no keyword-derived semantic PASS is emitted.
    """
    policy = contract(text, context)
    alternatives = result.get('alternatives') if isinstance(result, dict) else None
    rows = []; errors = []
    if not isinstance(alternatives, list) or len(alternatives) != 2:
        return {'eligible': False, 'status': 'INSUFFICIENT_TWO_CANDIDATE_RESULT', 'candidates': [], 'errors': ['Exactly two alternatives required']}
    ids = [a.get('candidateId') if isinstance(a, dict) else None for a in alternatives]
    if any(not isinstance(cid, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', cid) for cid in ids) or len(set(ids)) != 2:
        errors.append('Distinct stable candidate identifiers required')
    texts = []
    for candidate in alternatives:
        if not isinstance(candidate, dict):
            rows.append({'status': 'SOURCE_VIOLATION', 'errors': ['Candidate object required']}); continue
        failures = []; status = 'SOURCE_COMPLIANT'
        body = candidate.get('text')
        declarations = candidate.get('sourceContract') or {}
        if not isinstance(declarations, dict): declarations = {}
        if declarations.get('status') == 'PROTECTED_CHANGE_PROPOSAL':
            proposals = declarations.get('protectedChanges')
            valid_proposal = isinstance(proposals, list) and bool(proposals) and all(
                isinstance(p, dict) and p.get('anchorId') in {a['id'] for a in policy['protectedAnchors']}
                and all(isinstance(p.get(k), str) and p[k].strip() for k in ('proposedChange', 'justification')) for p in proposals)
            status = 'PROTECTED_CHANGE_PROPOSAL' if valid_proposal else 'SOURCE_VIOLATION'
            failures.append('OWNER_APPROVAL_REQUIRED_FOR_PROTECTED_STORY_CHANGE')
        elif declarations.get('status') != 'SOURCE_COMPLIANT':
            status = 'UNKNOWN'; failures.append('Protected source compliance is unsupported')
        if not isinstance(body, str) or not 160 <= len(body.strip()) <= 12000:
            status = 'SOURCE_VIOLATION'; failures.append('Complete bounded story required'); body = ''
        texts.append(normalize(body))
        for key in ('title', 'openingVisualState', 'motivation', 'progression', 'ending'):
            value = candidate.get(key)
            if not isinstance(value, str) or not value.strip() or (key != 'title' and value not in body):
                failures.append('Missing/extraneous narrative evidence: '+key)
        for key in ('proposedChanges', 'weaknesses', 'productionRisks'):
            value = candidate.get(key)
            if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
                failures.append('Required creative metadata: '+key)
        if candidate.get('durationSeconds') != 15 or candidate.get('schemaVersion') != SCHEMA:
            failures.append('Exact duration/schema required')
        if status == 'SOURCE_COMPLIANT':
            bindings = declarations.get('bindings')
            if not isinstance(bindings, list): bindings = []
            bound = {b.get('anchorId'): b for b in bindings if isinstance(b, dict)}
            if len(bound) != len(bindings) or set(bound) != {a['id'] for a in policy['protectedAnchors']}:
                failures.append('Every protected anchor needs one exact source/candidate binding')
            for anchor in policy['protectedAnchors']:
                binding = bound.get(anchor['id'], {})
                quote = binding.get('candidateQuote', '')
                # Optional offsets must support, never override, the cited text.
                # Offsets use Python/Unicode code points, not UTF-8 bytes.
                for prefix, narrative, excerpt in (('candidate', body, quote), ('source', text, anchor['quote'])):
                    if prefix+'Start' in binding or prefix+'End' in binding:
                        start, end = binding.get(prefix+'Start'), binding.get(prefix+'End')
                        if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(narrative)
                                or narrative[start:end] != excerpt):
                            status = 'SOURCE_VIOLATION'; failures.append('Incorrect '+prefix+' excerpt offsets: '+anchor['id'])
                if isinstance(quote, str) and quote and quote not in body:
                    status = 'SOURCE_VIOLATION'; failures.append('Claimed protected fact absent from story: '+anchor['id']); continue
                if binding.get('sourceQuote') != anchor['quote'] or not isinstance(quote, str) or not quote or normalize(quote) != normalize(anchor['quote']):
                    if status != 'SOURCE_VIOLATION': status = 'UNKNOWN'
                    failures.append('Unestablished protected fact: '+anchor['id']); continue
                # Do not accept a quoted protected clause with an explicit
                # nearby negation. This is a contradiction guard, not NLP proof.
                prefix = body[max(0, body.find(quote)-35):body.find(quote)]
                if re.search(r'\b(?:not|never|no longer|instead of)\b[^.!?]*$', prefix, re.I):
                    status = 'SOURCE_VIOLATION'; failures.append('Negated protected fact: '+anchor['id'])
            if declarations.get('protectedChanges'):
                status = 'SOURCE_VIOLATION'; failures.append('Undeclared protected change')
        # Existing general story evidence provides structural support only.
        from .story_evidence import extract_story_evidence
        evidence = extract_story_evidence(body, {})
        if len(evidence.get('events', [])) < 2 or not evidence.get('progressionSignal'):
            failures.append('Narrative progression structure unsupported')
        rows.append({'candidateId': candidate.get('candidateId'), 'status': status,
                     'eligible': status == 'SOURCE_COMPLIANT' and not failures, 'errors': failures,
                     'semanticFidelity': 'UNKNOWN_REQUIRES_INDEPENDENT_REVIEW',
                     'evidenceScope': 'EXACT_PROTECTED_TEXT_FACTS_ONLY', 'candidateSha256': sha(body)})
    if len(texts) == 2 and (texts[0] == texts[1] or SequenceMatcher(None, texts[0], texts[1], autojunk=False).ratio() >= .90):
        errors.append('Identical or near-identical stories are not distinct alternatives')
    return {'eligible': not errors and len(rows) == 2 and all(r.get('eligible') for r in rows),
            'status': 'SOURCE_COMPLIANT' if not errors and all(r.get('eligible') for r in rows) else 'INSUFFICIENT_TWO_CANDIDATE_RESULT',
            'candidates': rows, 'errors': errors, 'semanticFidelity': 'UNKNOWN_REQUIRES_INDEPENDENT_REVIEW'}


def preview(role, text, context):
    from .creative_roles import preview_story_request
    contract(text, context)
    if role not in {'STORY', 'STORY_REVIEW'}: raise ValueError('Unauthorized role')
    wire = preview_story_request(role, text, context)
    template_context = {k: deepcopy(v) for k, v in context.items() if k not in {'candidates', 'sourceRequestId', 'storyExperimentDispatch'}}
    template = preview_story_request(role, text, template_context)
    model = os.getenv('WORKFLOW_'+role+'_MODEL', '')
    identity_policy = model_policy(role, model)
    rates = [float(os.getenv('WORKFLOW_'+role+'_'+suffix+'_USD_PER_MILLION', 'nan')) for suffix in ('INPUT', 'OUTPUT')]
    if not all(math.isfinite(r) and r > 0 for r in rates): raise ValueError('Verified role pricing required')
    size = wire['payloadBytes'] if role == 'STORY' else 24000
    if wire['payloadBytes'] > 24000: raise ValueError('Review/request input envelope exceeded')
    cap = ((size + wire['systemBytes'] + 1000) * rates[0] + 4000 * rates[1]) / 1e6
    result = {'experimentVersion': VERSION, 'role': role,
              'provider': 'deepseek' if role == 'STORY' else 'openai', 'model': model,
              'systemSha256': sha(wire['system']), 'templateSha256': sha(template),
              'sourceScopeSha256': context['storyExperiment']['sourceScopeSha256'],
              'sourceStorySha256': sha(text), 'schemaVersion': SCHEMA if role == 'STORY' else 'creative-story-merit-v1',
              'evidenceContractVersion': EVIDENCE_CONTRACT, 'modelIdentityPolicy': identity_policy,
              'maxOutputTokens': 4000, 'maximumInputBytes': 24000,
              'inputUsdPerMillion': rates[0], 'outputUsdPerMillion': rates[1],
              'maximumCalculatedUsd': cap, 'automaticRetries': False, 'fallback': False,
              'transport': 'REAL_PROVIDER_ADAPTER', 'payloadBytes': wire['payloadBytes']}
    app_root = Path(__file__).resolve().parents[1]
    result['implementationSha256'] = sha({name: hashlib.sha256((app_root / name).read_bytes()).hexdigest()
        for name in ('workflow/story_experiment.py', 'workflow/creative_roles.py', 'workflow/deepseek.py',
                     'workflow/api.py', 'llm/openai_provider.py')})
    if role == 'STORY' or 'candidates' in context:
        result['effectiveRequestSha256'] = sha(encoded(wire['payload']))
    return result


def verify(role, text, context, authorized, cap):
    current = preview(role, text, context)
    # The final review payload is bound to its persisted request just before
    # dispatch. Its preauthorized template deliberately has no candidate hash.
    for key, value in current.items():
        if key in {'payloadBytes', 'effectiveRequestSha256'} and role == 'STORY_REVIEW': continue
        if authorized.get(key) != value:
            raise ValueError('SCOPE_OR_INSTRUCTION_MISMATCH: '+key)
    if cap < current['maximumCalculatedUsd'] or cap > authorized.get('maxCostUsd', 0):
        raise ValueError('Authorized reservation/budget mismatch')
    if role == 'STORY_REVIEW':
        gate = validate(text, context, {'alternatives': context.get('candidates')})
        if not gate['eligible']: raise ValueError('Two source-compliant persisted candidates required')
        if context.get('reviewPayloadSha256') != current['effectiveRequestSha256']:
            raise ValueError('SCOPE_OR_INSTRUCTION_MISMATCH: final review payload')
    return current


def execute(role, text, context, cap):
    """Always return a recoverable receipt after possible transport dispatch."""
    from .creative_roles import perform_role, _optimization_cost
    from .deepseek import DeepSeekTextProvider
    from app.llm.openai_provider import OpenAIProvider
    authorized = context.get('storyExperimentDispatch') or {}
    checked = verify(role, text, context, authorized, cap)
    if os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'false').lower() != 'true':
        raise ValueError('Story dispatch disabled')
    if os.getenv('POMPOM_ISOLATED_ACCEPTANCE') == 'true' or os.getenv('POMPOM_ISOLATED_FIXTURE_DIR') or os.getenv('POMPOM_ISOLATED_FIXTURE_TOKEN'):
        raise ValueError('Fixture fallback forbidden for real story experiment')
    receipt = {'requestId': context.get('storyRequestId'), 'role': role, 'provider': checked['provider'],
               'model': checked['model'], 'binding': checked, 'requestStartedAt': datetime.now(timezone.utc).isoformat(),
               'providerDispatched': False, 'rawProviderResponse': None, 'usage': None,
               'actualCostUsd': None, 'billingStatus': 'NOT_DISPATCHED', 'processingStatus': 'NOT_STARTED',
               'retrySafe': False, 'evidenceType': 'MACHINE_REVIEW' if role == 'STORY_REVIEW' else 'MODEL_GENERATION'}
    provider = None
    try:
        provider = DeepSeekTextProvider(checked['model']) if role == 'STORY' else OpenAIProvider(model=checked['model'])
        provider.max_output_tokens = 4000; provider.json_output = True
        if checked['modelIdentityPolicy']['requestParameters']:
            provider.request_parameters = checked['modelIdentityPolicy']['requestParameters']
        receipt['providerDispatched'] = True
        result = perform_role(role, text, context, provider, checked['model'])
        receipt.update(result=result['result'], processingStatus='PARSED')
    except Exception as error:
        receipt.update(processingStatus='LOCALLY_REJECTED', error={'category': type(error).__name__, 'detail': str(error)[:2000]})
    if provider is not None:
        receipt.update(rawProviderResponse=getattr(provider, 'last_raw_response', None),
                       providerApiResponse=getattr(provider, 'last_provider_response', None),
                       usage=getattr(provider, 'last_usage', None), providerResponseMetadata=getattr(provider, 'last_response_metadata', None))
    raw = receipt['rawProviderResponse']; metadata = receipt.get('providerResponseMetadata') or {}
    receipt['modelIdentity'] = model_identity(checked['model'], metadata)
    received = raw is not None or receipt.get('providerApiResponse') is not None
    if isinstance(raw, str):
        try: receipt['parsedProviderResponse'] = json.loads(raw)
        except (ValueError, TypeError): pass
    receipt.update(responseReceived=received, responseSha256=sha(raw) if isinstance(raw, str) else sha(receipt['providerApiResponse']) if receipt.get('providerApiResponse') is not None else None,
                   responseReceivedAt=datetime.now(timezone.utc).isoformat())
    try:
        cost = _optimization_cost(receipt['usage'], checked['inputUsdPerMillion'], checked['outputUsdPerMillion'])
        receipt['configuredRateCostUsd'] = cost
        if not receipt['modelIdentity']['verified']:
            receipt['billingStatus'] = 'MODEL_IDENTITY_UNVERIFIED'
            raise ValueError('Actual provider model identity missing or differs; configured-rate cost is not verified billing')
        receipt.update(actualCostUsd=cost, billingStatus='KNOWN_INCURRED')
        if cost > cap or receipt['usage'].get('completion_tokens', receipt['usage'].get('output_tokens', 0)) > 4000:
            raise ValueError('Provider usage exceeded authorization')
        if metadata.get('finishReason') != 'stop':
            raise ValueError('Incomplete provider response')
        if receipt['processingStatus'] == 'PARSED':
            if role == 'STORY':
                receipt['sourceValidation'] = validate(text, context, receipt['result'])
                receipt['processingStatus'] = 'CANDIDATES_ACCEPTED' if receipt['sourceValidation']['eligible'] else 'LOCALLY_REJECTED'
            else: receipt['processingStatus'] = 'INDEPENDENT_REVIEW_COMPLETED'
    except Exception as error:
        receipt['processingStatus'] = 'LOCALLY_REJECTED' if received else 'DISPATCH_UNCERTAIN' if receipt['providerDispatched'] else 'NOT_DISPATCHED'
        receipt['error'] = {'category': type(error).__name__, 'detail': str(error)[:2000]}
        if receipt['actualCostUsd'] is None and receipt['billingStatus'] != 'MODEL_IDENTITY_UNVERIFIED':
            receipt['billingStatus'] = 'USAGE_UNKNOWN' if receipt['providerDispatched'] else 'NOT_DISPATCHED'
    return receipt
