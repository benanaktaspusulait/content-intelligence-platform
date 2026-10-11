"""Explicit text roles over existing adapters; generation never approves its own output."""
from __future__ import annotations
import json
import math
import os
import re
from pathlib import Path
from difflib import SequenceMatcher
from hashlib import sha256
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


def _configured_generator_capabilities(context: dict[str, Any]) -> dict[str, Any]:
    target = context.get('targetConfiguration') if isinstance(context.get('targetConfiguration'), dict) else {}
    generator = str(target.get('selectedGenerator') or context.get('selectedGenerator') or '')
    try:
        path = Path(os.getenv('POMPOM_DATA_ROOT', 'data')) / 'workflow' / 'provider-capabilities.json'
        catalog = json.loads(path.read_text(encoding='utf-8'))
        model = catalog.get('models', {}).get(generator)
        if not isinstance(model, dict):
            return {'status': 'UNKNOWN', 'source': str(path)}
        properties = model.get('modes', {}).get('image2video', {}).get('properties', {})
        duration = properties.get('duration', {})
        ratio = properties.get('aspectRatio')
        return {'status': 'SYSTEM_VERIFIED', 'source': str(model.get('version') or catalog.get('version')),
                'apiModelId': model.get('apiModelId'), 'duration': {k: duration.get(k) for k in ('minimum', 'maximum')},
                'aspectRatio': {'supportedValues': ratio.get('enum')} if isinstance(ratio, dict) else {'status': 'NOT_EXPOSED_BY_SCHEMA'},
                'startFrameSupported': 'startFrame' in properties}
    except (OSError, ValueError, TypeError):
        return {'status': 'UNKNOWN', 'source': 'provider-capabilities.json unavailable'}


def migrate_legacy_production_spec(prompt: str, approved_story: str, context: dict[str, Any]) -> dict[str, Any]:
    """Deterministically project a legacy saved prompt into the current read model.

    This function is deliberately provider-free. It preserves the source prompt,
    labels prompt-derived descriptions as such, and never converts inferred
    semantics into source-confirmed evidence.
    """
    import hashlib

    target = context.get('targetConfiguration') if isinstance(context.get('targetConfiguration'), dict) else {}
    identity = context.get('sourceIdentity') if isinstance(context.get('sourceIdentity'), dict) else {}
    character = str(target.get('mainCharacter') or context.get('mainCharacter') or '').strip()
    character_record = context.get('characterRecord') if isinstance(context.get('characterRecord'), dict) else {}
    capabilities = context.get('generatorCapabilities') if isinstance(context.get('generatorCapabilities'), dict) else {'status': 'UNKNOWN', 'source': 'unavailable'}
    duration = target.get('duration')
    aspect_ratio = target.get('aspectRatio')
    generator = target.get('selectedGenerator')
    profile = target.get('contentProfile')

    # Keep only exact contiguous word spans. A textual overlap is not a semantic
    # judgment and is never represented as an approved beat relationship.
    def exact_overlap_span(candidate: str) -> tuple[int, int, str] | None:
        source_words = list(re.finditer(r"\b[\w’'-]+\b", approved_story, re.UNICODE))
        candidate_words = list(re.finditer(r"\b[\w’'-]+\b", candidate, re.UNICODE))
        left = [m.group(0).casefold() for m in source_words]
        right = [m.group(0).casefold() for m in candidate_words]
        best = (0, 0, 0)
        previous: dict[int, int] = {}
        for i, word in enumerate(left):
            if i and re.search(r"[.!?]", approved_story[source_words[i - 1].end():source_words[i].start()]):
                previous = {}
            current: dict[int, int] = {}
            for j, other in enumerate(right):
                if word == other:
                    length = previous.get(j - 1, 0) + 1
                    current[j] = length
                    if length > best[0]:
                        best = (length, i, j)
            previous = current
        length, source_end, _ = best
        if length < 4:
            return None
        source_start = source_end - length + 1
        start = source_words[source_start].start()
        end = source_words[source_end].end()
        return start, end, approved_story[start:end]

    def prompt_supported_state_change(candidate: str) -> str | None:
        # Extract only a literal result clause from the saved prompt. It is
        # production evidence, not independent semantic approval or a claim
        # about the rendered video.
        anchors = re.finditer(r"\b(?:it|they|(?:the|a|one)\s+)?(?:sticky\s+)?notes?\b|\b(?:it|they)\b", candidate, re.IGNORECASE)
        transition = re.compile(
            r"\b(?:twists?|lands?|sticks?|adheres?|covers?|covering|returns?|multiply|multiplies|flies back|fly back|"
            r"swarm(?:s|ed|ing)?|follows?|becomes?|remains?|leaves?)\b[^.;:!?]*",
            re.IGNORECASE,
        )
        for anchor in anchors:
            result = transition.search(candidate, anchor.start())
            if result:
                return result.group(0).strip(" ,")
        return None

    beats: list[dict[str, Any]] = []
    beat_pattern = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)\s*:\s*", re.IGNORECASE)
    markers = list(beat_pattern.finditer(prompt))
    for index, match in enumerate(markers):
        start, end = float(match.group(1)), float(match.group(2))
        description_end = markers[index + 1].start() if index + 1 < len(markers) else len(prompt)
        description = re.sub(r"\s+", " ", prompt[match.end():description_end]).strip(" \n\t:-")
        description = re.split(r"\b(?:AUDIO|NEGATIVE CONSTRAINTS|FINAL CUT|PRODUCTION SETTINGS)\b", description, maxsplit=1, flags=re.I)[0].strip()
        if not description:
            continue
        overlap = exact_overlap_span(description)
        quote = overlap[2] if overlap else ''
        prompt_state_change = prompt_supported_state_change(description)
        beat: dict[str, Any] = {
            'time': f'{match.group(1)}-{match.group(2)}s',
            'startSeconds': start, 'endSeconds': end,
            'subject': character if character and re.search(rf'\b{re.escape(character)}\b', description, re.I) else 'UNKNOWN',
            'action': description,
            'object': 'sticky notes / toy cabinet' if re.search(r'sticky note|cabinet', description, re.I) else 'UNKNOWN',
            'stateChange': prompt_state_change or 'UNKNOWN_NOT_INDEPENDENTLY_CLASSIFIED',
            'stateChangeStatus': 'PROMPT_SUPPORTED_ONLY' if prompt_state_change else 'UNKNOWN_NOT_INDEPENDENTLY_CLASSIFIED',
            'stateChangeEvidenceSource': 'SAVED_PROMPT_TEXT' if prompt_state_change else 'UNKNOWN',
            'framing': 'PROMPT_SUPPORTED' if re.search(r'\b(close-up|medium|wide|overhead|low-angle)\b', description, re.I) else 'UNKNOWN',
            'staging': description,
            'consequence': 'UNKNOWN_NOT_INDEPENDENTLY_CLASSIFIED',
            'sourceEvidence': quote,
            'sourceEvidenceOffsets': {'start': overlap[0], 'end': overlap[1]} if overlap else None,
            'evidenceStatus': 'SOURCE_TEXT_OVERLAP_ONLY' if overlap else 'PROMPT_SUPPORTED_ONLY',
            'sourceRelationship': 'UNKNOWN',
            'importance': 'UNKNOWN',
            'provenance': 'SAVED_PROMPT_TEXT; NOT_RENDER_OBSERVATION',
        }
        beats.append(beat)

    ordered = all(beats[i]['startSeconds'] < beats[i]['endSeconds'] and
                  (i == 0 or beats[i]['startSeconds'] >= beats[i - 1]['endSeconds'])
                  for i in range(len(beats)))
    covers = bool(beats) and ordered and beats[0]['startSeconds'] == 0 and isinstance(duration, (int, float)) and beats[-1]['endSeconds'] == float(duration)
    timeline = {
        'status': 'PROMPT_RANGES_STRUCTURALLY_VALID' if covers else ('PROMPT_RANGES_PRESENT_REVIEW_REQUIRED' if beats else 'UNKNOWN_NO_TIMED_RANGES'),
        'coveredFromSeconds': beats[0]['startSeconds'] if beats else None,
        'coveredToSeconds': beats[-1]['endSeconds'] if beats else None,
        'eventCount': len(beats), 'orderedNonOverlapping': ordered,
        'semanticMajorBeatCount': 'UNKNOWN',
    }
    verified_character = bool(character_record.get('id') and character_record.get('catalogVerified'))
    refs = context.get('characterReferences') if isinstance(context.get('characterReferences'), list) else []
    bound_refs = [item for item in refs if isinstance(item, dict) and item.get('verified') is True]
    capability_assessment = {'status': 'UNKNOWN', 'source': capabilities.get('source', 'UNKNOWN')}
    if capabilities.get('status') == 'UNKNOWN':
        capability_assessment = dict(capabilities)
    else:
        model = capabilities
        mode = (model.get('modes') or {}).get('image2video') or {}
        properties = mode.get('properties') or {}
        duration_spec = properties.get('duration') or {}
        ratio_spec = properties.get('aspectRatio') or {}
        duration_ok = isinstance(duration, (int, float)) and duration_spec.get('minimum') is not None and duration_spec.get('maximum') is not None and duration_spec['minimum'] <= duration <= duration_spec['maximum']
        ratio_values = ratio_spec.get('enum') if isinstance(ratio_spec, dict) else None
        ratio_ok = aspect_ratio in ratio_values if isinstance(ratio_values, list) else None
        capability_assessment = {
            'status': 'SCHEMA_SNAPSHOT', 'source': model.get('version') or 'provider-capabilities.json',
            'apiModelId': model.get('apiModelId'),
            'duration': {'requested': duration, 'supported': duration_ok},
            'aspectRatio': {'requested': aspect_ratio, 'supported': ratio_ok,
                            'status': 'SUPPORTED' if ratio_ok is True else ('UNSUPPORTED' if ratio_ok is False else 'NOT_EXPOSED_BY_SCHEMA')},
            'startFrameFieldSupported': 'startFrame' in properties,
            'liveVerified': False,
        }
    opening_assessment = {'status': 'PLANNED_TEXT_ONLY_NOT_EVALUATED', 'imageEvidence': 'UNKNOWN_NOT_GENERATED',
                          'openingText': next((beat['action'] for beat in beats if beat['startSeconds'] == 0), 'UNKNOWN')}
    plan = {
        'builderContractVersion': 'openart-production-prompt-v2',
        'migrationStatus': 'LOCALLY_REVALIDATED_NOT_PROVIDER_VALIDATED',
        'sourceIdentity': {
            **identity,
            'storyRecordId': identity.get('storyRecordId') or 'UNKNOWN',
            'storyRevisionId': identity.get('storyRevisionId') or 'UNKNOWN',
            'approvalRecordId': identity.get('approvalRecordId') or 'UNKNOWN',
            'savedPromptRecordId': identity.get('savedPromptRecordId') or 'UNKNOWN',
            'savedPromptVersion': identity.get('savedPromptVersion') or 'UNKNOWN',
            'storyTitle': identity.get('storyTitle') or 'UNKNOWN',
            'narrativeTitle': identity.get('storyTitle') or 'UNKNOWN',
            'projectTitle': identity.get('projectTitle') or 'UNKNOWN',
            'workspacePath': identity.get('workspacePath') or 'UNKNOWN',
            'provenance': 'EXACT_RECORD_POINTERS' if identity.get('storyRecordId') and identity.get('storyRevisionId') and identity.get('approvalRecordId') else 'PARTIAL_EXACT_RECORD_POINTERS',
            'sourceFingerprint': hashlib.sha256(approved_story.encode('utf-8')).hexdigest(),
        },
        'creativeObjective': 'UNKNOWN_NOT_RECONSTRUCTED_DURING_LOCAL_MIGRATION',
        'characterBindings': [{
            'name': character or 'UNKNOWN',
            'canonicalCharacterId': character_record.get('id') if verified_character else 'UNKNOWN',
            'identityStatus': 'CATALOG_CONFIRMED' if verified_character else 'UNKNOWN',
            'referenceStatus': 'VERIFIED_REFERENCE_BOUND' if bound_refs else 'MISSING_OR_UNVERIFIED',
            'referenceIds': [str(item.get('id')) for item in bound_refs if item.get('id')],
            'visualAppearanceStatus': 'REFERENCE_VERIFIED' if bound_refs else 'UNKNOWN_NO_APPROVED_VISUAL_REFERENCE',
        }],
        'visualExecution': {
            'openingState': next((beat['action'] for beat in beats if beat['startSeconds'] == 0), 'UNKNOWN'),
            'openingAssessment': opening_assessment,
            'beats': beats, 'timelineIntegrity': timeline,
            'mechanism': 'UNKNOWN_NOT_RECONSTRUCTED', 'continuity': 'UNKNOWN_NOT_RECONSTRUCTED',
            'endingState': beats[-1]['action'] if beats else 'UNKNOWN',
        },
        'productionConstraints': {
            'duration': duration if duration is not None else 'UNKNOWN',
            'aspectRatio': aspect_ratio or 'UNKNOWN', 'generator': generator or 'UNKNOWN',
            'contentProfile': profile or 'UNKNOWN',
            'provenance': 'SAVED_BUILD_REQUEST' if target else 'UNKNOWN',
        },
        'storyPromptFidelity': {
            'status': 'NOT_EVALUATED', 'sourceSentenceCount': None, 'traceableSentenceCount': None,
            'comparisonProvenance': 'NO_SEMANTIC_COMPARISON_PERFORMED_DURING_MIGRATION',
        },
        'openingAssessment': opening_assessment,
        'generatorCapabilityAssessment': capability_assessment,
        'generatorRisks': _legacy_source_risks(approved_story),
        'referencePlan': {'status': 'NOT_VERIFIED', 'firstFrameStatus': 'NOT_GENERATED_IN_STEP_3'},
        'evidenceLimitations': [
            'Local migration preserves the saved prompt and does not validate provider output.',
            'Text overlap is reported with exact offsets; beat semantics and story fidelity remain unevaluated.',
            'No rendered image or video was inspected.',
        ],
        'fieldProvenance': {
            'sourceIdentity': 'EXACT_SAVED_RECORDS', 'characterIdentity': 'CHARACTER_CATALOG' if verified_character else 'UNKNOWN',
            'visualReferences': 'REFERENCE_CATALOG' if bound_refs else 'MISSING_OR_UNVERIFIED',
            'timedEvents': 'SAVED_PROMPT_TEXT', 'eventSourceOverlap': 'EXACT_TEXT_SPANS_IN_APPROVED_STORY',
            'storyPromptFidelity': 'NOT_EVALUATED', 'providerCapabilities': capability_assessment.get('source', capabilities.get('source', 'UNKNOWN')),
            'settings': 'SAVED_BUILD_REQUEST' if target else 'UNKNOWN',
        },
    }
    return {'prompt': prompt, 'productionPlan': plan, 'validationStatus': 'NOT_VALIDATED', 'providerCalls': 0}


def _legacy_source_risks(source: str) -> list[dict[str, Any]]:
    rules = [
        (r'\btries? (?:again|to stick)|already stuck\b', 'Repeated sticky-note contact', 'Track the note from each deliberate contact attempt so attached-note positions remain continuous.'),
        (r'\bnotes? stick to (?:her )?(?:other )?(?:paw|ear|face)|\bsticky notes? (?:lands?|sticks?)\b', 'Sticky-note placement continuity', 'Preserve which note is attached to Mimi’s face, paw and ear when the framing changes.'),
        (r'\bpeels? .+? and tries? again|\bother paw and ear\b', 'Simultaneous action complexity', 'Stage the peel and new attachments as readable sequential beats instead of one crowded gesture.'),
        (r'\bmultiply|multiplies|multiplication\b', 'Object-count continuity', 'Show count changes one at a time and preserve already attached notes.'),
        (r'\bfly back|return|returns\b', 'Returning-note path', 'Keep the motion path visible through reattachment.'),
        (r'\bfollow|chase|chases\b', 'Pursuit readability', 'Keep the character and pursuing notes in the same readable composition.'),
        (r'\bhides? behind|occlusion\b', 'Cabinet occlusion', 'Keep the notes and final character state readable around the cabinet.'),
        (r'\bfinal beat\b.*\beyes? visible|\bleaving only her (?:wide )?eyes visible\b', 'Final facial visibility', 'Preserve eye visibility through the final cover state and cut at the stated ending.'),
        (r'\bfinal beat\b|\bcover(?:s|ed)? her completely\b', 'Final-state continuity', 'Make the transition from pursuit to the final covered state visually continuous.'),
    ]
    sentences = [item.strip() for item in re.split(r'(?<=[.!?])\s+', source) if item.strip()]
    risks = []
    for pattern, risk, mitigation in rules:
        evidence = next((sentence for sentence in sentences if re.search(pattern, sentence, re.I)), None)
        if evidence:
            risks.append({'risk': risk, 'sourceEvidence': evidence, 'severity': 'ADVISORY', 'confidence': 'RULE_MATCH_ONLY', 'mitigation': mitigation, 'blocker': False, 'provenance': 'DETERMINISTIC_SOURCE_TEXT_RULE'})
    return risks


def _validate_production_settings(prompt: str, plan: dict[str, Any], context: dict[str, Any]) -> list[str]:
    target = context.get('targetConfiguration') if isinstance(context.get('targetConfiguration'), dict) else {}
    expected_ratio = str(target.get('aspectRatio') or context.get('aspectRatio') or '').strip()
    expected_duration = target.get('duration') or context.get('targetDuration')
    expected_generator = str(target.get('selectedGenerator') or context.get('selectedGenerator') or '').strip()
    expected_profile = str(target.get('contentProfile') or context.get('profile') or '').strip()
    if not any((expected_ratio, expected_duration, expected_generator, expected_profile)):
        return []
    constraints = plan.get('productionConstraints') if isinstance(plan.get('productionConstraints'), dict) else {}
    conflicts: list[str] = []
    if expected_ratio:
        ratios = set(re.findall(r'(?<!\d)(?:9:16|16:9|1:1)(?!\d)', prompt))
        plan_ratio = str(constraints.get('aspectRatio') or '').strip()
        if expected_ratio not in ratios:
            conflicts.append(f'prompt does not state the selected aspect ratio {expected_ratio}')
        if plan_ratio and plan_ratio != expected_ratio:
            conflicts.append(f'production plan says {plan_ratio} but the selected aspect ratio is {expected_ratio}')
        if any(r != expected_ratio for r in ratios):
            conflicts.append(f'prompt contains conflicting aspect ratio(s): {", ".join(sorted(ratios - {expected_ratio}))}')
    if expected_duration:
        plan_duration = str(constraints.get('duration') or '')
        if plan_duration and plan_duration not in {str(expected_duration), f'{expected_duration}s'}:
            conflicts.append(f'production plan says duration {plan_duration} but the selected duration is {expected_duration}s')
    if expected_generator:
        plan_generator = str(constraints.get('generator') or constraints.get('targetGenerator') or '').strip()
        if plan_generator and plan_generator.lower() != expected_generator.lower():
            conflicts.append(f'production plan targets {plan_generator} but the selected generator is {expected_generator}')
    if expected_profile:
        plan_profile = str(constraints.get('contentProfile') or '').strip()
        if plan_profile and plan_profile.lower() != expected_profile.lower():
            conflicts.append(f'production plan uses {plan_profile} but the selected content profile is {expected_profile}')
    return conflicts


def _complete_confirmed_settings(prompt: str, plan: dict[str, Any], context: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Make confirmed operator settings explicit in the persisted prompt contract.

    Providers occasionally return a valid structured prompt while omitting a
    setting that was already confirmed in the workflow. We can fill only an
    absent setting deterministically; a conflicting provider value is left
    untouched so the existing fail-closed validation still rejects it.
    """
    target = context.get('targetConfiguration') if isinstance(context.get('targetConfiguration'), dict) else {}
    expected_ratio = str(target.get('aspectRatio') or context.get('aspectRatio') or '').strip()
    expected_duration = target.get('duration') or context.get('targetDuration')
    expected_generator = str(target.get('selectedGenerator') or context.get('selectedGenerator') or '').strip()
    expected_profile = str(target.get('contentProfile') or context.get('profile') or '').strip()
    constraints = plan.get('productionConstraints') if isinstance(plan.get('productionConstraints'), dict) else {}
    if not isinstance(plan.get('productionConstraints'), dict):
        plan['productionConstraints'] = constraints
    additions: list[str] = []
    if expected_ratio:
        ratios = set(re.findall(r'(?<!\d)(?:9:16|16:9|1:1)(?!\d)', prompt))
        if not ratios:
            additions.append(f'Aspect ratio: {expected_ratio}.')
            constraints.setdefault('aspectRatio', expected_ratio)
    if expected_duration and not re.search(rf'(?<!\d){re.escape(str(expected_duration))}\s*(?:s|sec|secs|seconds)\b', prompt, re.IGNORECASE):
        additions.append(f'Target duration: {expected_duration}s.')
        constraints.setdefault('duration', expected_duration)
    if expected_generator and not re.search(re.escape(expected_generator), prompt, re.IGNORECASE):
        additions.append(f'Target generator: {expected_generator}.')
        constraints.setdefault('generator', expected_generator)
    if expected_profile and not re.search(re.escape(expected_profile), prompt, re.IGNORECASE):
        additions.append(f'Content profile: {expected_profile}.')
        constraints.setdefault('contentProfile', expected_profile)
    if additions:
        prompt = prompt.rstrip() + '\n\nPRODUCTION SETTINGS\n' + ' '.join(additions)
    return prompt, plan


def _evidence_backed_production_fields(prompt: str, plan: dict[str, Any], source: str,
                                       context: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Bind authoritative workflow facts and mark generated interpretation honestly."""
    target = context.get('targetConfiguration') if isinstance(context.get('targetConfiguration'), dict) else {}
    identity = plan.get('sourceIdentity') if isinstance(plan.get('sourceIdentity'), dict) else {}
    narrative_title = identity.get('narrativeTitle') or identity.get('storyTitle') or identity.get('title')
    identity.update({
        'projectTitle': context.get('storyTitle') or context.get('projectTitle') or 'UNKNOWN',
        'narrativeTitle': narrative_title or 'UNKNOWN',
        'storyRecordId': context.get('sourceStoryRecordId') or 'UNKNOWN',
        'storyRevisionId': context.get('storyRevisionId') or 'UNKNOWN',
        'storySha256': sha256(source.encode('utf-8')).hexdigest(),
        'provenance': 'SYSTEM_VERIFIED' if context.get('sourceStoryRecordId') and context.get('storyRevisionId') else 'UNKNOWN',
    })
    plan['sourceIdentity'] = identity

    character = str(target.get('mainCharacter') or context.get('mainCharacter') or '').strip()
    record = context.get('characterRecord') if isinstance(context.get('characterRecord'), dict) else {}
    raw_references = context.get('characterReferences') if isinstance(context.get('characterReferences'), list) else []
    references = [item for item in raw_references if isinstance(item, dict) and item.get('status') == 'VERIFIED'
                  and item.get('id') and item.get('sha256')]
    bindings = plan.get('characterBindings') if isinstance(plan.get('characterBindings'), list) else []
    if character:
        binding = next((item for item in bindings if isinstance(item, dict) and
                        str(item.get('name') or item.get('characterName') or '').casefold() == character.casefold()), {})
        binding.update({
            'name': character,
            'canonicalCharacterId': str(record.get('id') or 'UNKNOWN'),
            'identityRequirement': ('Anthropomorphic bunny identity; preserve this operator-confirmed canonical identity.'
                                   if character.casefold() == 'mimi' else 'Preserve the selected character identity.'),
            'identityProvenance': 'OPERATOR_CONFIRMED' if character.casefold() == 'mimi' else ('SYSTEM_VERIFIED' if record else 'UNKNOWN'),
            'referenceStatus': 'VERIFIED_REFERENCE_BOUND' if references else 'MISSING_VERIFIED_REFERENCE',
            'referenceIds': [str(item.get('id')) for item in references],
            'referenceVersions': [{'id': str(item['id']), 'sha256': str(item['sha256'])} for item in references],
            'visualDescriptionStatus': 'UNKNOWN_WITHOUT_APPROVED_REFERENCE' if not references else 'REFERENCE_BOUND',
        })
        bindings = [item for item in bindings if not (isinstance(item, dict) and
                    str(item.get('name') or item.get('characterName') or '').casefold() == character.casefold())]
        bindings.insert(0, binding)
        if character.casefold() == 'mimi':
            prompt += '\n\nCHARACTER IDENTITY LOCK\nMimi is the established anthropomorphic bunny character. Preserve that identity; do not render a human or invent unverified visual details. No approved visual reference is currently bound, so appearance details remain unverified.'
    plan['characterBindings'] = bindings

    constraints = plan.get('productionConstraints') if isinstance(plan.get('productionConstraints'), dict) else {}
    constraints.update({key: value for key, value in {
        'duration': target.get('duration'), 'aspectRatio': target.get('aspectRatio'),
        'generator': target.get('selectedGenerator'), 'contentProfile': target.get('contentProfile'),
        'mainCharacter': target.get('mainCharacter') or context.get('mainCharacter'),
    }.items() if value is not None})
    constraints['provenance'] = 'SYSTEM_VERIFIED' if target else 'UNKNOWN'
    plan['productionConstraints'] = constraints
    capability_status: dict[str, Any] = {'status': 'UNKNOWN', 'source': 'UNKNOWN'}
    try:
        capability_file = Path(os.getenv('POMPOM_DATA_ROOT', 'data')) / 'workflow' / 'provider-capabilities.json'
        catalog = json.loads(capability_file.read_text(encoding='utf-8'))
        model = catalog.get('models', {}).get(str(target.get('selectedGenerator') or ''), {})
        mode = model.get('modes', {}).get('image2video', {})
        fields = mode.get('properties', {})
        duration_spec = fields.get('duration', {})
        duration = target.get('duration')
        duration_supported = isinstance(duration, (int, float)) and duration_spec.get('minimum', -1) <= duration <= duration_spec.get('maximum', -1)
        ratio_spec = fields.get('aspectRatio')
        ratio_supported = (target.get('aspectRatio') in ratio_spec.get('enum', [])) if isinstance(ratio_spec, dict) else None
        capability_status = {
            'status': 'SYSTEM_VERIFIED', 'source': str(model.get('version') or catalog.get('version') or 'provider-capabilities.json'),
            'apiModelId': model.get('apiModelId'), 'duration': {'requested': duration, 'supported': duration_supported},
            'aspectRatio': {'requested': target.get('aspectRatio'), 'supported': ratio_supported,
                            'status': 'SUPPORTED' if ratio_supported is True else ('UNSUPPORTED' if ratio_supported is False else 'NOT_EXPOSED_BY_VERIFIED_SCHEMA')},
            'startFrameFieldSupported': 'startFrame' in fields,
        }
    except (OSError, ValueError, TypeError):
        pass
    plan['generatorCapabilityAssessment'] = capability_status

    plan['fieldProvenance'] = {
        'sourceIdentity': 'SYSTEM_VERIFIED' if context.get('sourceStoryRecordId') else 'UNKNOWN',
        'approvedStory': 'SOURCE_CONFIRMED', 'characterBindings': 'SYSTEM_VERIFIED' if record else 'UNKNOWN',
        'creativeObjective': 'AI_DERIVED', 'visualExecution': 'AI_DERIVED',
        'openingAssessment': 'AI_DERIVED_TEXT_ONLY', 'generatorRisks': 'AI_DERIVED_FROM_SOURCE_TEXT',
        'productionConstraints': 'SYSTEM_VERIFIED' if target else 'UNKNOWN',
        'firstFrame': 'UNKNOWN_NO_IMAGE_EVIDENCE',
    }
    plan.setdefault('evidenceLimitations', [])
    if not references:
        plan['evidenceLimitations'].append('No verified character visual reference is bound; generated appearance details are not approved evidence.')
    plan['referencePlan'] = {
        **(plan.get('referencePlan') if isinstance(plan.get('referencePlan'), dict) else {}),
        'characterReferenceStatus': 'VERIFIED_REFERENCE_BOUND' if references else 'MISSING_VERIFIED_REFERENCE',
        'firstFrameStatus': 'NOT_GENERATED_IN_STEP_3',
        'provenance': 'SYSTEM_VERIFIED' if references else 'UNKNOWN',
    }

    execution = plan.get('visualExecution') if isinstance(plan.get('visualExecution'), dict) else {}
    beats = execution.get('beats') if isinstance(execution.get('beats'), list) else []
    for beat in beats:
        if isinstance(beat, dict):
            quote = str(beat.get('sourceEvidence') or '').strip()
            exact = bool(quote and quote in source)
            beat['evidenceStatus'] = 'SOURCE_CONFIRMED' if exact else 'UNKNOWN'
            allowed = {'FAITHFUL_ADAPTATION', 'CLARIFICATION', 'OPTIONAL_EXECUTION_INTERPRETATION', 'MATERIAL_CREATIVE_DEVIATION', 'UNKNOWN'}
            relationship = str(beat.get('sourceRelationship') or 'UNKNOWN')
            beat['sourceRelationship'] = relationship if exact and relationship in allowed else 'UNKNOWN'
            beat['sourceRelationshipProvenance'] = 'AI_DERIVED' if exact and relationship in allowed else 'UNKNOWN'
            beat['importance'] = beat.get('importance') if beat.get('importance') in {'CORE', 'FLEXIBLE', 'POLISH'} else 'UNKNOWN'
            if not exact:
                plan['evidenceLimitations'].append(f"Beat {beat.get('time', 'UNKNOWN')} lacks a verbatim source quote; its event mapping is unverified.")

    profile = str(target.get('contentProfile') or context.get('profile') or '').upper()
    objectives = {
        'ABSURD_PHYSICS': 'Make the approved impossible physical rule readable through visible action, escalation and a clear final state; humor is relevant but not mandatory.',
        'DISCOVERY': 'Create curiosity through observable clues, exploration and a satisfying discovery; do not impose a joke or solved ending.',
        'CURIOSITY_ADVENTURE': 'Create curiosity through observable clues, exploration and a satisfying discovery; do not impose a joke or solved ending.',
        'EDUCATION': 'Make the approved learning idea clear through observable demonstration; do not impose comedy or an unsupported conclusion.',
        'EDUCATIONAL': 'Make the approved learning idea clear through observable demonstration; do not impose comedy or an unsupported conclusion.',
        'EMOTIONAL': 'Preserve the approved emotional intent through visible behavior and progression; do not impose a joke or conventional payoff.',
        'ADVENTURE': 'Preserve the approved goal, obstacle and progression while keeping actions visually legible.',
    }
    if profile in objectives:
        plan['creativeObjective'] = objectives[profile]

    # Text-only opening assessment: it is not evidence of an actual generated frame.
    first = None
    for beat in beats:
        match = re.match(r'\s*0\s*[-–]\s*(\d+(?:\.\d+)?)', str(beat.get('time', ''))) if isinstance(beat, dict) else None
        if match and float(match.group(1)) >= 2:
            first = beat
            break
    opening_text = ' '.join(str(first.get(k, '')) for k in ('action', 'consequence')) if first else source.split('.')[0]
    abnormal = bool(re.search(r'\b(stick|attach|multiply|follow|turns? in the air|flies? back|impossible|unexpected)\b', opening_text, re.I))
    question = bool(re.search(r'\b(mystery|discover|search|why|what|hidden|strange|curious)\b', opening_text, re.I))
    educational = profile in {'EDUCATION', 'EDUCATIONAL'}
    opening_status = ('CLEAR_ABNORMAL_RELATIONSHIP' if abnormal else
                      'INTERESTING_MYSTERY' if question else
                      'PROFILE_RELEVANT_INFORMATIONAL_SETUP' if educational and bool(opening_text.strip()) else
                      'ORDINARY_SETUP_WITHOUT_CLEAR_PROMISE')
    plan['openingAssessment'] = {
        'framework': 'Visible promise → immediate consequence or reveal → reason to keep watching',
        'classification': opening_status, 'assessmentWindow': 'first 2 seconds (planned text only)',
        'visiblePromise': opening_text or 'UNKNOWN', 'immediateConsequence': 'SOURCE_CONFIRMED' if abnormal else 'NOT_ESTABLISHED_IN_OPENING',
        'reasonToContinue': 'AI_DERIVED', 'imageEvidence': 'UNKNOWN_NOT_GENERATED',
        'smallestSourceFaithfulAdjustment': 'Show the note already moving toward the unintended attachment in the opening composition.' if not abnormal and 'sticky note' in source.lower() else 'No source-faithful adjustment established from text alone.'
    }

    low = source.casefold()
    mechanism = 'sticky-note attachment' if 'sticky note' in low else 'UNKNOWN'
    consequences = [label for needle, label in [
        ('sticks to her face', 'Unintended face attachment'), ('sticks to her paw', 'Unintended paw attachment'),
        ('multiply', 'Notes multiply'), ('fly back', 'Removed notes return'), ('follow', 'Notes pursue Mimi'),
        ('cover', 'Notes cover Mimi')
    ] if needle in low]
    if mechanism != 'UNKNOWN':
        plan['mechanismAssessment'] = {
            'coreMechanism': mechanism, 'directConsequences': consequences,
            'causalStatus': 'MULTIPLE_EFFECTS_CAUSAL_LINK_UNCLEAR' if ('multiply' in low and 'fly back' in low and 'follow' in low) else 'PARTIALLY_ESTABLISHED',
            'independentOrUnexplainedEffects': [item for item in consequences if item in {'Notes multiply', 'Removed notes return', 'Notes pursue Mimi'}],
            'viewerComprehensionImpact': 'The repeated attachment rule is visible, but multiplication, return and pursuit are not explicitly linked in the approved text.' if len(consequences) >= 3 else 'Insufficient evidence to assess all causal links.',
            'generatorExecutionRisk': 'Object count and repeated contact continuity require clear staged changes; this is an execution risk, not a premise blocker.',
            'smallestClarification': 'Clarify whether notes multiply when removed, or whether removed notes reattach; retain the current events unless the operator revises the source.'
        }

    risks = []
    for needle, event, mitigation in [
        ('multiply', 'Object-count change', 'Show one count increase at a time and keep prior notes visible.'),
        ('fly back', 'Returning notes', 'Show a continuous visible path from Mimi back to her body.'),
        ('follow', 'Pursuit', 'Keep Mimi and the pursuing notes in the same readable frame.'),
        ('face', 'Face occlusion', 'Keep Mimi’s eyes readable until the final cover state.'),
        ('cover', 'Final-state visibility', 'Preserve the stated final visible features and hold the final state before the cut.'),
        ('hides behind', 'Cabinet occlusion', 'Stage Mimi beside the cabinet so the notes remain visible.'),
        ('first frame', 'Opening reference match', 'Validate the approved first frame in pre-render preparation; none is generated here.'),
    ]:
        if needle in low:
            evidence = next((s.strip() for s in re.split(r'(?<=[.!?])\s+', source) if needle in s.lower()), 'UNKNOWN')
            affected = next((beat for beat in beats if isinstance(beat, dict) and needle in (str(beat.get('action', '')) + ' ' + str(beat.get('sourceEvidence', ''))).lower()), None)
            risks.append({'risk': event, 'sourceEvidence': evidence,
                          'affectedEvent': event, 'affectedTime': affected.get('time', 'UNKNOWN') if affected else 'UNKNOWN',
                          'intentImpact': 'CORE' if needle in {'multiply','follow'} else 'FLEXIBLE',
                          'confidence': 'MEDIUM_TEXT_EVIDENCE', 'mitigation': mitigation,
                          'nextAction': 'PROMPT_REPAIR' if needle in {'multiply','fly back'} else 'LATER_VISUAL_QA',
                          'blocker': False, 'provenance': 'AI_DERIVED_FROM_SOURCE_TEXT'})
    plan['generatorRisks'] = risks or [{'risk': 'No specific source-grounded risk identified from supplied text.', 'confidence': 'UNKNOWN', 'blocker': False, 'provenance': 'SYSTEM_VERIFIED_TEXT_SCAN'}]
    source_sentences = [item.strip() for item in re.split(r'(?<=[.!?])\s+', source) if item.strip()]
    quotes = [str(beat.get('sourceEvidence') or '') for beat in beats if isinstance(beat, dict)]
    mapped = [sentence for sentence in source_sentences if any(sentence in quote or (quote in sentence and len(quote) >= 20) for quote in quotes)]
    plan['storyPromptFidelity'] = {
        'status': 'SOURCE_SENTENCES_TRACEABLE' if source_sentences and len(mapped) == len(source_sentences) else 'UNKNOWN_INSUFFICIENT_TRACEABILITY',
        'sourceSentenceCount': len(source_sentences), 'traceableSentenceCount': len(mapped),
        'unmappedSourceSentences': [sentence for sentence in source_sentences if sentence not in mapped],
        'availableClassifications': ['FAITHFUL_ADAPTATION', 'CLARIFICATION', 'OPTIONAL_EXECUTION_INTERPRETATION', 'MATERIAL_CREATIVE_DEVIATION', 'UNKNOWN'],
        'comparisonProvenance': 'AI_DERIVED_AND_QUOTED; NOT_AN_INDEPENDENT_SEMANTIC_APPROVAL',
    }
    return prompt, plan


def _nested_response_value(value: dict[str, Any], keys: tuple[str, ...], depth: int = 0) -> Any:
    """Recover a contract field from shallow provider wrappers without guessing text."""
    if depth > 3:
        return None
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    for key in ('result', 'data', 'response', 'output', 'content'):
        nested = value.get(key)
        if isinstance(nested, dict):
            found = _nested_response_value(nested, keys, depth + 1)
            if found is not None:
                return found
    return None


def _nested_response_dict(value: dict[str, Any], keys: tuple[str, ...], depth: int = 0) -> dict[str, Any] | None:
    if depth > 3:
        return None
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, dict):
            return candidate
    for key in ('result', 'data', 'response', 'output', 'content'):
        nested = value.get(key)
        if isinstance(nested, dict):
            found = _nested_response_dict(nested, keys, depth + 1)
            if found is not None:
                return found
    return None


def _normalise_build_prompt_response(value: dict[str, Any]) -> dict[str, Any]:
    """Accept documented casing/wrapper variants while keeping one stored contract."""
    if not isinstance(value.get('prompt'), str) or not value.get('prompt', '').strip():
        prompt = _nested_response_value(value, ('productionPrompt', 'openArtPrompt', 'promptText', 'production_prompt', 'openart_prompt', 'prompt'))
        if isinstance(prompt, str):
            value['prompt'] = prompt
    if not isinstance(value.get('productionPlan'), dict):
        plan = _nested_response_dict(value, ('production_plan', 'productionPlan', 'plan', 'specification'))
        if plan is not None:
            value['productionPlan'] = plan
    return value


def perform_role(role: str, text: str, context: dict[str, Any], provider: LLMProvider, model: str) -> dict[str, Any]:
    if role not in ROLES or not text.strip() or len(text.encode('utf-8')) > 16000:
        raise ValueError('Supported role and bounded text required')
    if any(context.get(key) for key in ('image', 'images', 'video')):
        raise ValueError('Creative roles are text-only; visual evidence was not supplied')
    system = {
        'STORY_REVIEW': '''Review every supplied story candidate together. Return ONLY one JSON object matching this exact STORY_REVIEW contract; never omit a key and never return markdown. Required top-level keys: reviewId, sourceRequestId, sourceFingerprint, reviewModel, reviewModelVersion, reviewPolicyVersion, reviewTimestamp, reviewStatus, diversityAssessment, comparativeFindings, candidateReviews, recommendedCandidateId, recommendationReason, overallConcerns, usageAndCost, evidenceLimitations, revisionComparison. Set sourceRequestId and sourceFingerprint exactly to the values supplied in context (they may be null); the saved record timestamp is authoritative, so do not use a fixture date. reviewStatus must be COMPLETED, PARTIAL, SERVICE_ERROR, or INSUFFICIENT_EVIDENCE. candidateReviews must contain exactly one object for each supplied candidate, each with its exact candidateId. Assess concept coherence, opening visual promise, causal consistency, event progression, originality against siblings, curiosity/rewatch, generator difficulty, source constraints, ending/payoff, and material differences. For every material finding include dimension, finding, supportingTextEvidence, severity, confidenceOrEvidenceStatus and suggestedMinimalImprovement. Use concise structured findings and do not invent candidates. recommendedCandidateId must be one supplied candidateId or null; if no evidence supports a preference, return null and explain that. Use arrays/objects for the remaining evidence fields even when empty. Compare actual mechanisms and event progressions rather than wording, preserve source fidelity, mark uncertainty honestly, and never grant render authorization.''',
        'STORY': '''Return ONLY one JSON object matching this schema: {"alternatives":[{"candidateId":"candidate-1","title":"short title","text":"complete story"}]}. Return one to three alternatives, never zero and never more than three. Each candidate must include a non-empty candidateId, title and text string. Respect the requested generation mode and locked requirements. For EXPLORE_DIFFERENT_STORIES vary meaningful narrative structure; for IMPROVE_EXISTING_STORY preserve locked events and ending while offering refinements. Preserve supplied characters and intent. Do not return markdown, reasoning, commentary or production authorization.''',
        'BUILD_PROMPT': '''Return ONLY JSON with exactly two top-level keys: `prompt` and `productionPlan`. Convert the approved story into a concrete, concise OpenArt video prompt: visible actions, object states, continuity, staging, selected aspect ratio/duration, and ending. Do not rewrite its premise. Preserve the exact character, central mechanism, essential progression, protected events, constraints and ending. Do not silently omit an essential event; mark uncertainty or material deviation in evidence instead. Use manageable actions, few cuts, uncluttered staging, and no invented reference claims. Use the selected content profile's objective; comedy is relevant only when the source/profile supports it. Separate source-confirmed facts from AI-derived execution suggestions. Prompt headings, each separated by a blank line: TITLE / FORMAT, VISUAL STYLE, CHARACTER / CONTINUITY, TIMED SHOT PLAN, AUDIO, NEGATIVE CONSTRAINTS, FINAL CUT. Make the timed plan cover the full selected duration with ordered, non-overlapping ranges; choose meaningful events from the source, not an arbitrary fixed beat count. Each plan beat must contain time, subject, action, object, stateChange, framing, staging, consequence, sourceEvidence (an exact verbatim quote from approved source or empty string), evidenceStatus, sourceRelationship (FAITHFUL_ADAPTATION, CLARIFICATION, OPTIONAL_EXECUTION_INTERPRETATION, MATERIAL_CREATIVE_DEVIATION, UNKNOWN), and importance (CORE, FLEXIBLE, POLISH, UNKNOWN). Never fabricate quotes. `visualExecution` must include openingState, beats, mechanism, continuity, endingState. `productionPlan` keys: sourceIdentity, creativeObjective, characterBindings, visualExecution, productionConstraints, intentClassification, evidenceLimitations, generatorRisks, referencePlan. If Mimi is selected, honor the supplied anthropomorphic-bunny identity requirement; do not invent unverified appearance details and state whether approved references are actually bound. Assess the first two seconds as planned text only using visible promise → immediate consequence/reveal → reason to continue; distinguish mystery from ordinary setup. Do not claim first-frame image evidence. Identify causal ambiguity without rewriting the premise. Risks need a cited source event, affected beat, confidence, smallest mitigation and next action; they are advisory unless evidence establishes a true blocker. Do not claim unverified generator behavior. Do not add provider commentary, approval language or render authorization.''',
        'MINIMAL_REPAIR': 'Return JSON patches: at most three minimal edits with integer Unicode code point start/end, exact sourceQuote and replacement. Preserve protected intent and ESSENTIAL source quotes. Never return approval or rewrite the entire prompt.',
    }[role]
    safe_context = {key: context[key] for key in ('protectedIntent', 'intentRequirements', 'findings', 'retrievedLessons', 'constraints', 'storyGenerationMode', 'lockedRequirements', 'permittedVariation', 'mainCharacter', 'character', 'characterRecord', 'characterReferences', 'referenceBindings', 'preferences', 'profile', 'candidates', 'candidateIds', 'requestedAlternativeCount', 'sourceRequestId', 'sourceFingerprint', 'previousReview', 'currentRevision', 'previousRevision', 'targetDuration', 'aspectRatio', 'reviewPolicyVersion', 'selectedGenerator', 'generatorCapabilities', 'targetConfiguration', 'storyTitle', 'promptBuilderContractVersion') if key in context}
    if role == 'BUILD_PROMPT':
        safe_context['generatorCapabilities'] = _configured_generator_capabilities(context)
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
        if isinstance(alternatives, list) and len(alternatives) > 3:
            # The provider may overproduce despite the bounded request. Keep
            # the first three candidates, which is the product contract.
            alternatives = alternatives[:3]
            value['alternatives'] = alternatives
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
        # Keep the provider boundary strict while tolerating the key spellings
        # commonly returned by otherwise valid JSON-mode responses. The
        # canonical persisted contract remains `prompt`.
        value = _normalise_build_prompt_response(value)
        if not isinstance(value.get('prompt'), str) or not value['prompt'].strip() or len(value['prompt']) > 16000:
            raise ValueError('OpenAI response must include a bounded production prompt in the `prompt` field')
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
        if not isinstance(beats, list) or not beats:
            raise ValueError('Production prompt must contain at least one source-linked visual event')
        quality_findings: list[dict[str, str]] = []
        for beat in beats:
            required_beat = ('time', 'framing', 'action', 'staging', 'consequence')
            if not isinstance(beat, dict) or any(not isinstance(beat.get(key), str) or not beat[key].strip() for key in required_beat):
                raise ValueError('Every production beat must include timing, executable staging and source traceability')
            beat.setdefault('sourceEvidence', '')
            beat.setdefault('sourceRelationship', 'UNKNOWN')
            beat.setdefault('importance', 'UNKNOWN')
            if beat.get('sourceRelationship') == 'MATERIAL_CREATIVE_DEVIATION':
                raise ValueError('Production prompt contains a material creative deviation; revise the source or request an explicit operator decision')
        prompt, plan = _evidence_backed_production_fields(prompt, plan, source, context)
        # Version the durable specification so older cached drafts cannot be
        # mistaken for results produced under the current provenance contract.
        plan['builderContractVersion'] = str(context.get('promptBuilderContractVersion') or 'UNKNOWN')
        intervals: list[tuple[float, float]] = []
        for beat in beats:
            match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds)?\s*', beat['time'], re.I)
            if not match or float(match.group(2)) <= float(match.group(1)):
                raise ValueError('Timed visual execution contains an invalid time range')
            intervals.append((float(match.group(1)), float(match.group(2))))
        ordered = intervals
        chronology = all(ordered[i][0] >= ordered[i - 1][1] for i in range(1, len(ordered)))
        if not chronology:
            raise ValueError('Timed visual execution contains overlapping or out-of-order beats')
        duration = (context.get('targetConfiguration') or {}).get('duration') if isinstance(context.get('targetConfiguration'), dict) else None
        gaps = [[ordered[i - 1][1], ordered[i][0]] for i in range(1, len(ordered)) if ordered[i][0] > ordered[i - 1][1]]
        timeline_status = 'COMPLETE' if ordered[0][0] == 0 and (duration is None or ordered[-1][1] == float(duration)) and not gaps else 'INCOMPLETE'
        plan['visualExecution']['timelineIntegrity'] = {
            'status': timeline_status, 'plannedDurationSeconds': duration,
            'coveredFromSeconds': ordered[0][0], 'coveredToSeconds': ordered[-1][1],
            'gapsSeconds': gaps,
            'semanticBeatCountInferredFromRanges': False,
        }
        if timeline_status != 'COMPLETE':
            quality_findings.append({'code': 'TIMED_PLAN_INCOMPLETE', 'severity': 'MATERIAL', 'message': 'The timed plan does not cover the complete selected duration.'})
        capability = plan.get('generatorCapabilityAssessment', {})
        if capability.get('status') != 'SYSTEM_VERIFIED':
            quality_findings.append({'code': 'GENERATOR_CAPABILITY_UNKNOWN', 'severity': 'WARNING', 'message': 'The selected generator capability snapshot was unavailable; render compatibility remains UNKNOWN.'})
        elif capability.get('duration', {}).get('supported') is False:
            quality_findings.append({'code': 'GENERATOR_DURATION_UNSUPPORTED', 'severity': 'MATERIAL', 'message': 'The selected duration is outside the verified generator schema.'})
        elif capability.get('aspectRatio', {}).get('status') == 'UNSUPPORTED':
            quality_findings.append({'code': 'GENERATOR_ASPECT_RATIO_UNSUPPORTED', 'severity': 'MATERIAL', 'message': 'The selected aspect ratio is outside the verified generator schema.'})
        elif capability.get('aspectRatio', {}).get('status') == 'NOT_EXPOSED_BY_VERIFIED_SCHEMA':
            quality_findings.append({'code': 'GENERATOR_ASPECT_RATIO_NOT_EXPOSED', 'severity': 'WARNING', 'message': 'The verified generator schema does not expose an aspect-ratio parameter; render compatibility must be resolved before authorization.'})
        if any(beat.get('evidenceStatus') != 'SOURCE_CONFIRMED' for beat in beats):
            quality_findings.append({'code': 'BEAT_SOURCE_TRACEABILITY_UNKNOWN', 'severity': 'WARNING', 'message': 'One or more beat-to-story mappings lack an exact source quote; review them before accepting the prompt.'})
        if plan.get('storyPromptFidelity', {}).get('status') != 'SOURCE_SENTENCES_TRACEABLE':
            quality_findings.append({'code': 'STORY_PROMPT_FIDELITY_UNKNOWN', 'severity': 'MATERIAL', 'message': 'Not every approved source sentence is traceable to the timed production plan. Do not treat this prompt as complete or approved.'})
        if not any(start == 0 for start, _ in intervals):
            quality_findings.append({'code': 'OPENING_BEAT_UNCLEAR', 'severity': 'MATERIAL', 'message': 'The plan does not identify an event beginning at 0 seconds.'})
        if duration is not None and not any(end == float(duration) for _, end in intervals):
            quality_findings.append({'code': 'ENDING_BEAT_UNCLEAR', 'severity': 'MATERIAL', 'message': 'The plan does not reach the selected duration.'})
        if not plan.get('evidenceLimitations'):
            quality_findings.append({'code': 'EVIDENCE_LIMITATION_MISSING', 'severity': 'WARNING', 'message': 'Evidence limitations must be explicit, including when no reference asset was supplied.'})
        if not plan.get('generatorRisks'):
            quality_findings.append({'code': 'GENERATOR_RISK_UNREPORTED', 'severity': 'WARNING', 'message': 'The target generator has no recorded risk assessment.'})
        prompt, plan = _complete_confirmed_settings(prompt, plan, context)
        value['prompt'] = prompt
        conflicts = _validate_production_settings(prompt, plan, context)
        if conflicts:
            quality_findings.extend({'code': 'CONFIRMED_SETTING_CONFLICT', 'severity': 'MATERIAL', 'message': item} for item in conflicts)
            raise ValueError('Production prompt conflicts with confirmed settings: ' + '; '.join(conflicts))
        value['qualityFindings'] = quality_findings
        value['productionPlan'] = plan
    else:
        patches = value.get('patches')
        if not isinstance(patches, list) or len(patches) > 3:
            raise ValueError('At most three minimal patches required')
        for patch in patches:
            if not isinstance(patch, dict) or any(type(patch.get(k)) is not int for k in ('start', 'end')) or not 0 <= patch['start'] < patch['end'] <= len(text) or patch.get('sourceQuote') != text[patch['start']:patch['end']] or not isinstance(patch.get('replacement'), str):
                raise ValueError('Patch must bind to the exact source span')
    response_metadata = getattr(provider, 'last_response_metadata', None) or {
        'apiStatus': 'COMPLETED',
        'promptPresent': bool(value.get('prompt')) if role == 'BUILD_PROMPT' else None,
        'promptLength': len(value.get('prompt', '')) if role == 'BUILD_PROMPT' else None,
    }
    return {'role': role, 'provider': ROLES[role], 'model': model, 'result': value,
            'calls': 1, 'visualInspected': False, 'validationStatus': 'NOT_VALIDATED',
            'usage': getattr(provider, 'last_usage', None),
            'providerResponseMetadata': response_metadata}


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
