"""Explicit text roles over existing adapters; generation never approves its own output."""
from __future__ import annotations
import json
import math
import os
import re
from difflib import SequenceMatcher
from typing import Any

from app.llm.provider import LLMProvider
from app.llm.openai_provider import OpenAIProvider
from .deepseek import DeepSeekTextProvider
from .story_quality import analyse_story_candidates

ROLES = {'STORY': 'deepseek', 'STORY_REVIEW': 'openai', 'BUILD_PROMPT': 'openai', 'MINIMAL_REPAIR': 'openai'}


def role_readiness() -> dict[str, Any]:
    enabled = os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'false').lower() == 'true'
    return {'enabled': enabled, 'liveVerified': False, 'roles': [
        {'role': role, 'provider': provider, 'model': os.getenv(f'WORKFLOW_{role}_MODEL', ''),
         'configured': bool(os.getenv(f'{provider.upper()}_API_KEY') and os.getenv(f'WORKFLOW_{role}_MODEL')),
         'modality': 'TEXT_ONLY', 'automaticFallback': False}
        for role, provider in ROLES.items()]}


def perform_role(role: str, text: str, context: dict[str, Any], provider: LLMProvider, model: str) -> dict[str, Any]:
    if role not in ROLES or not text.strip() or len(text.encode('utf-8')) > 16000:
        raise ValueError('Supported role and bounded text required')
    if any(context.get(key) for key in ('image', 'images', 'video')):
        raise ValueError('Creative roles are text-only; visual evidence was not supplied')
    system = {
        'STORY_REVIEW': '''Review every supplied story candidate together. Return ONLY one JSON object matching this exact STORY_REVIEW contract; never omit a key and never return markdown. Required top-level keys: reviewId, sourceRequestId, sourceFingerprint, reviewModel, reviewModelVersion, reviewPolicyVersion, reviewTimestamp, reviewStatus, diversityAssessment, comparativeFindings, candidateReviews, recommendedCandidateId, recommendationReason, overallConcerns, usageAndCost, evidenceLimitations, revisionComparison. Set sourceRequestId and sourceFingerprint exactly to the values supplied in context (they may be null). reviewStatus must be COMPLETED, PARTIAL, SERVICE_ERROR, or INSUFFICIENT_EVIDENCE. candidateReviews must contain exactly one object for each supplied candidate, each with its exact candidateId; use concise structured findings and do not invent candidates. recommendedCandidateId must be one supplied candidateId or null. Use arrays/objects for the remaining evidence fields even when empty. Compare structure rather than wording, preserve source fidelity, mark uncertainty honestly, and never grant render authorization.''',
        'STORY': 'Return JSON alternatives: one to three story candidates. Respect the requested generation mode and locked requirements. For EXPLORE_DIFFERENT_STORIES vary meaningful narrative structure; for IMPROVE_EXISTING_STORY preserve locked events and ending while offering refinements. Preserve the supplied characters and intent. No production authorization.',
        'BUILD_PROMPT': '''Return ONLY JSON with exactly two top-level keys: `prompt` and `productionPlan`. Transform the approved story into a production-ready OpenArt video prompt; do not paraphrase or paste the story. Preserve every required event, character, first-frame condition, timing and hard cut. Write a readable multi-paragraph prompt with a blank line between these exact headings: TITLE / FORMAT, VISUAL STYLE, CHARACTER / CONTINUITY, TIMED SHOT PLAN, AUDIO, NEGATIVE CONSTRAINTS, FINAL CUT. The TIMED SHOT PLAN must contain 0-3s, 3-6s, 6-10s, 10-13s and 13-15s beats; every beat must state camera/framing, visible action and spatial staging. Include the first-frame requirement in the opening shot, make multiplication readable, keep the main character visible when the mechanism acts, and state the final hard cut. `productionPlan` must be a structured object with these keys: sourceIdentity, creativeObjective, characterBindings, visualExecution, productionConstraints, intentClassification, evidenceLimitations, generatorRisks, referencePlan. visualExecution must contain openingState, beats (one object per timed beat), mechanism, continuity, and endingState. Each beat must contain time, framing, action, staging and consequence. Use only supplied story, references and constraints; never invent appearance or evidence. Mark missing evidence explicitly. Do not add provider commentary, approval language or production authorization.''',
        'MINIMAL_REPAIR': 'Return JSON patches: at most three minimal edits with integer Unicode code point start/end, exact sourceQuote and replacement. Preserve protected intent and ESSENTIAL source quotes. Never return approval or rewrite the entire prompt.',
    }[role]
    safe_context = {key: context[key] for key in ('protectedIntent', 'intentRequirements', 'findings', 'retrievedLessons', 'constraints', 'storyGenerationMode', 'lockedRequirements', 'permittedVariation', 'mainCharacter', 'character', 'characterRecord', 'characterReferences', 'referenceBindings', 'preferences', 'profile', 'candidates', 'candidateIds', 'sourceRequestId', 'sourceFingerprint', 'previousReview', 'currentRevision', 'previousRevision', 'targetDuration', 'aspectRatio', 'reviewPolicyVersion', 'selectedGenerator', 'generatorCapabilities', 'targetConfiguration') if key in context}
    raw_response = provider.complete(json.dumps({'text': text, 'context': safe_context}, ensure_ascii=False), system=system, temperature=0)
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise ValueError(f'{ROLES[role].title()} returned an empty JSON response')
    candidate_response = raw_response.strip()
    if candidate_response.startswith('```'):
        candidate_response = re.sub(r'^```(?:json)?\s*|\s*```$', '', candidate_response, flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        value = json.loads(candidate_response)
    except json.JSONDecodeError as error:
        # Some configured text endpoints wrap an otherwise valid object in a
        # short preamble. Recover only a complete object; never invent fields.
        start, end = candidate_response.find('{'), candidate_response.rfind('}')
        if start >= 0 and end > start:
            try:
                value = json.loads(candidate_response[start:end + 1])
            except json.JSONDecodeError:
                raise ValueError(f'{ROLES[role].title()} returned invalid JSON') from error
        else:
            raise ValueError(f'{ROLES[role].title()} returned invalid JSON') from error
    if not isinstance(value, dict):
        raise ValueError('Role result must be an object')
    if role == 'STORY_REVIEW':
        required = ('reviewId', 'sourceRequestId', 'sourceFingerprint', 'reviewModel', 'reviewModelVersion', 'reviewPolicyVersion', 'reviewTimestamp', 'reviewStatus', 'diversityAssessment', 'comparativeFindings', 'candidateReviews', 'recommendedCandidateId', 'recommendationReason', 'overallConcerns', 'usageAndCost', 'evidenceLimitations', 'revisionComparison')
        if any(key not in value for key in required):
            raise ValueError('Structured STORY_REVIEW contract is incomplete')
        if context.get('sourceRequestId') is not None and str(value.get('sourceRequestId')) != str(context.get('sourceRequestId')):
            raise ValueError('STORY_REVIEW source request identity does not match')
        if context.get('sourceFingerprint') is not None and str(value.get('sourceFingerprint')) != str(context.get('sourceFingerprint')):
            raise ValueError('STORY_REVIEW source fingerprint does not match')
        candidates = context.get('candidates') if isinstance(context.get('candidates'), list) else []
        candidate_ids = [str(item.get('candidateId')) for item in candidates if isinstance(item, dict)]
        reviews = value.get('candidateReviews')
        if not isinstance(reviews, list) or len(reviews) != len(candidate_ids):
            raise ValueError('STORY_REVIEW candidate IDs must include exactly one review per candidate')
        review_ids = [str(item.get('candidateId')) for item in reviews if isinstance(item, dict)]
        if len(review_ids) != len(set(review_ids)):
            raise ValueError('STORY_REVIEW candidate IDs do not match the request')
        if set(review_ids) != set(candidate_ids):
            # Some models preserve candidate order but shorten UUID-backed IDs to
            # candidate-1/candidate-2. Canonicalize those ordinal aliases while
            # still failing closed for missing, duplicate, or ambiguous IDs.
            ordinals = []
            for review_id in review_ids:
                match = re.search(r'(?:candidate[-_ ]?)?(\d+)$', review_id.lower())
                ordinals.append(int(match.group(1)) if match else None)
            if ordinals != list(range(1, len(candidate_ids) + 1)):
                raise ValueError('STORY_REVIEW candidate IDs do not match the request')
            for item, ordinal in zip(reviews, ordinals):
                item['candidateId'] = candidate_ids[ordinal - 1]
            review_ids = candidate_ids
        recommendation = value.get('recommendedCandidateId')
        if recommendation is not None and str(recommendation) not in candidate_ids:
            match = re.search(r'(?:candidate[-_ ]?)?(\d+)$', str(recommendation).lower())
            if match and 1 <= int(match.group(1)) <= len(candidate_ids):
                value['recommendedCandidateId'] = candidate_ids[int(match.group(1)) - 1]
            else:
                raise ValueError('STORY_REVIEW recommendation must reference a supplied candidate or null')
        if value.get('reviewStatus') not in {'COMPLETED', 'PARTIAL', 'SERVICE_ERROR', 'INSUFFICIENT_EVIDENCE'}:
            raise ValueError('Unsupported STORY_REVIEW status')
    elif role == 'STORY':
        alternatives = value.get('alternatives')
        if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 3:
            raise ValueError('One to three bounded story alternatives required')
        for candidate in alternatives:
            if isinstance(candidate, str):
                if not candidate.strip() or len(candidate) > 12000: raise ValueError('Bounded story alternative text required')
            elif isinstance(candidate, dict):
                # DeepSeek often returns a useful structured candidate using
                # `synopsis`/`logline` rather than the UI's canonical `text`.
                # Canonicalize that bounded field before quality analysis and
                # persistence; do not discard the richer structured fields.
                candidate_text = candidate.get('text') or candidate.get('description') or candidate.get('synopsis') or candidate.get('logline') or candidate.get('corePremise')
                if not isinstance(candidate_text, str) or not candidate_text.strip() or len(candidate_text) > 12000:
                    raise ValueError('Story alternatives must contain bounded text')
                candidate.setdefault('text', candidate_text.strip())
            else:
                raise ValueError('Story alternatives must contain bounded text')
        value['storyQuality'] = analyse_story_candidates(alternatives, context)
    elif role == 'BUILD_PROMPT':
        if not isinstance(value.get('prompt'), str) or not value['prompt'].strip() or len(value['prompt']) > 16000:
            raise ValueError('Bounded production prompt required')
        prompt = value['prompt'].strip()
        source = text.strip()
        markers = ('camera', 'shot', 'framing', 'seconds', 'duration', 'audio', 'sound', 'continuity', 'negative', 'hard cut')
        headings = ('title / format', 'visual style', 'character / continuity', 'timed shot plan', 'audio', 'negative constraints', 'final cut')
        if len(prompt) < 240 or sum(marker in prompt.lower() for marker in markers) < 4 or sum(heading in prompt.lower() for heading in headings) < len(headings) or prompt.count('\n\n') < 3:
            raise ValueError('Production prompt must include timed shots, camera direction, continuity, audio and final-cut details')
        if SequenceMatcher(None, prompt.lower(), source.lower()).ratio() > 0.9 and len(prompt) <= len(source) * 1.35:
            raise ValueError('Production prompt cannot be a restatement of the approved story')
        plan = value.get('productionPlan')
        required_plan = ('sourceIdentity', 'creativeObjective', 'characterBindings', 'visualExecution', 'productionConstraints', 'intentClassification', 'evidenceLimitations', 'generatorRisks', 'referencePlan')
        if not isinstance(plan, dict) or any(key not in plan for key in required_plan):
            raise ValueError('Production prompt specification is incomplete')
        execution = plan.get('visualExecution')
        if not isinstance(execution, dict) or not isinstance(execution.get('openingState'), (str, dict)) or not isinstance(execution.get('mechanism'), (str, dict)) or not isinstance(execution.get('endingState'), (str, dict)) or not isinstance(execution.get('continuity'), (str, list, dict)):
            raise ValueError('Production prompt visual execution plan is incomplete')
        beats = execution.get('beats')
        if not isinstance(beats, list) or len(beats) < 5:
            raise ValueError('Production prompt must contain five bounded visual beats')
        for beat in beats:
            if not isinstance(beat, dict) or any(not isinstance(beat.get(key), str) or not beat[key].strip() for key in ('time', 'framing', 'action', 'staging', 'consequence')):
                raise ValueError('Every production beat must include time, framing, action, staging and consequence')
        quality_findings: list[dict[str, str]] = []
        if not any('0-3' in str(beat.get('time', '')).replace('–', '-') for beat in beats):
            quality_findings.append({'code': 'OPENING_BEAT_UNCLEAR', 'severity': 'MATERIAL', 'message': 'The plan does not identify a 0-3s opening beat.'})
        if not any('13-15' in str(beat.get('time', '')).replace('–', '-') for beat in beats):
            quality_findings.append({'code': 'ENDING_BEAT_UNCLEAR', 'severity': 'MATERIAL', 'message': 'The plan does not identify a 13-15s final beat.'})
        if not plan.get('evidenceLimitations'):
            quality_findings.append({'code': 'EVIDENCE_LIMITATION_MISSING', 'severity': 'WARNING', 'message': 'Evidence limitations must be explicit, including when no reference asset was supplied.'})
        if not plan.get('generatorRisks'):
            quality_findings.append({'code': 'GENERATOR_RISK_UNREPORTED', 'severity': 'WARNING', 'message': 'The target generator has no recorded risk assessment.'})
        value['qualityFindings'] = quality_findings
        value['productionPlan'] = plan
    else:
        patches = value.get('patches')
        if not isinstance(patches, list) or len(patches) > 3:
            raise ValueError('At most three minimal patches required')
        for patch in patches:
            if not isinstance(patch, dict) or any(type(patch.get(k)) is not int for k in ('start', 'end')) or not 0 <= patch['start'] < patch['end'] <= len(text) or patch.get('sourceQuote') != text[patch['start']:patch['end']] or not isinstance(patch.get('replacement'), str):
                raise ValueError('Patch must bind to the exact source span')
    return {'role': role, 'provider': ROLES[role], 'model': model, 'result': value,
            'calls': 1, 'visualInspected': False, 'validationStatus': 'NOT_VALIDATED', 'usage': getattr(provider, 'last_usage', None)}


def run_paid_role(role: str, text: str, context: dict[str, Any], max_cost_usd: float) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError('Unknown creative role')
    if os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'false').lower() != 'true':
        raise ValueError('Paid creative roles are disabled; explicit scope and budget required')
    model = os.getenv(f'WORKFLOW_{role}_MODEL', '')
    if not model:
        raise ValueError('Explicit server model configuration required; no fallback')
    input_rate = float(os.getenv(f'WORKFLOW_{role}_INPUT_USD_PER_MILLION', 'nan'))
    output_rate = float(os.getenv(f'WORKFLOW_{role}_OUTPUT_USD_PER_MILLION', 'nan'))
    if not all(math.isfinite(v) and v > 0 for v in (input_rate, output_rate, max_cost_usd)):
        raise ValueError('Verified server price configuration and explicit positive budget required')
    payload_bytes = len(json.dumps({'text': text, 'context': context}, ensure_ascii=False).encode('utf-8'))
    output_token_limit = 4000 if role == 'STORY' else 2000
    upper_bound = ((payload_bytes + 2000) * input_rate + output_token_limit * output_rate) / 1_000_000
    if payload_bytes > 24000 or upper_bound > max_cost_usd:
        raise ValueError('Request exceeds approved cost ceiling')
    provider = DeepSeekTextProvider(model) if role == 'STORY' else OpenAIProvider(model=model)
    provider.max_output_tokens = output_token_limit
    provider.json_output = True
    result = perform_role(role, text, context, provider, model)
    result['costUpperBoundUsd'] = upper_bound
    result['approvedCostCeilingUsd'] = max_cost_usd
    return result
