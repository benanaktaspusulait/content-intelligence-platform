"""Server-owned profile mapping. Raw provider evidence is never overwritten."""
import re
from copy import deepcopy
from .review import PROFILES

CONTRACT_VERSION = 'optimization-profile-ownership-v1'
_LABEL = re.compile(r'(Content profile:\s*)([A-Za-z_ -]+)(?=[.\n]|$)', re.I)


def canonical_profile(value):
    normalized = re.sub(r'[ -]+', '_', str(value).strip().upper())
    if normalized not in (*PROFILES, 'AUTO'):
        raise ValueError('Source-plan profile is outside the canonical content profile enum')
    return normalized


def historical_profile(text):
    match = _LABEL.search(text)
    return canonical_profile(match[2]) if match else 'UNKNOWN'


class ProfileContractError(ValueError):
    def __init__(self, result):
        self.profile_validation = result
        super().__init__(f"{result['candidateId']}: source-plan MATERIAL_CREATIVE_PROFILE_CONFLICT: {result['detail']}")


def generation_contract(text, context):
    target = context.get('targetConfiguration') or {}
    profile = target.get('contentProfile')
    if not profile or profile == 'UNKNOWN':
        return None
    return {
        'contractVersion': CONTRACT_VERSION,
        'baselinePromptText': text,
        'baselinePromptHistoricalProfile': historical_profile(text),
        'targetContentProfile': canonical_profile(profile),
        'targetOwner': 'SERVER_VERSION_BOUND_PRODUCTION_SETTINGS',
        'productionSettingsRecordId': context.get('productionSettingsRecordId', 'UNAVAILABLE'),
        'approvedStory': context.get('approvedStoryText', ''),
        'protectedIntent': context.get('protectedIntent', context.get('essentialEvents', [])),
        'generatorSettings': {k: v for k, v in target.items() if k != 'contentProfile'},
        'optimizationObjectives': {'candidate-a': 'FIRST_FRAME_ANOMALY_CLARITY_CURIOSITY',
                                   'candidate-b': 'BEAT_PROGRESSION_TIMING_ESCALATION_SEEDANCE_FEASIBILITY'},
    }


def normalize_candidate_profiles(source, candidates, context):
    contract = generation_contract(source, context)
    if contract is None:
        return
    target = contract['targetContentProfile']
    for candidate in candidates:
        raw = candidate['prompt']
        result = {'contractVersion': CONTRACT_VERSION, 'candidateId': candidate['candidateId'],
                  'historicalBaselineProfile': contract['baselinePromptHistoricalProfile'],
                  'effectiveContentProfile': target, 'targetOwner': contract['targetOwner'],
                  'productionSettingsRecordId': contract['productionSettingsRecordId'],
                  'rawProviderPrompt': raw, 'providerProfileEcho': candidate.get('targetContentProfile'),
                  'metadataMappings': [], 'semanticFidelity': 'UNKNOWN'}
        # A dedicated production-settings section is metadata. Profile directives
        # anywhere else describe creative execution and cannot be relabelled.
        section = re.search(r'(?im)^PRODUCTION SETTINGS\s*\n', raw)
        creative = raw[:section.start()] if section else raw
        material = re.findall(r'(?i)(?:content\s+profile|target(?:\s+content)?\s+profile|optimi[sz]e\s+for(?:\s+profile)?)\s*[:=]?\s*([A-Z_]+)', creative)
        source_plan = candidate.get('sourcePlan') or {}
        for key in ('creativeInstructions', 'creativeObjective'):
            material.extend(re.findall(r'(?i)(?:content\s+profile|target(?:\s+content)?\s+profile|optimi[sz]e\s+for(?:\s+profile)?)\s*[:=]?\s*([A-Z_]+)', str(source_plan.get(key, ''))))
        for key in ('targetContentProfile', 'creativeProfile'):
            if key in source_plan:
                material.append(source_plan[key])
        for value in material:
            try:
                actual = canonical_profile(value)
            except ValueError:
                continue  # not an explicit enum directive; never infer approval
            if actual != target:
                result.update(status='MATERIAL_CREATIVE_PROFILE_CONFLICT',
                              detail=f'creative instructions explicitly target {actual}; server target is {target}')
                raise ProfileContractError(result)
        metadata = raw[section.end():] if section else ''
        echoes = _LABEL.findall(metadata)
        for _, echo in echoes:
            actual = canonical_profile(echo)
            if actual != target:
                result['metadataMappings'].append({'field': 'productionSettings.contentProfile',
                                                  'rawValue': echo, 'canonicalRawValue': actual,
                                                  'effectiveValue': target, 'owner': 'SERVER'})
        for field, value in [('targetContentProfile', candidate.get('targetContentProfile')),
                             ('sourcePlan.contentProfile', source_plan.get('contentProfile'))]:
            if value is not None and canonical_profile(value) != target:
                result['metadataMappings'].append({'field': field, 'rawValue': value,
                                                  'effectiveValue': target, 'owner': 'SERVER'})
        if section:
            metadata = _LABEL.sub(lambda m: m[1] + target, metadata)
            if not echoes:
                metadata = metadata.rstrip() + '\nContent profile: ' + target + '.\n'
            candidate['prompt'] = raw[:section.end()] + metadata
        else:
            candidate['prompt'] = raw.rstrip() + '\n\nPRODUCTION SETTINGS\nContent profile: ' + target + '.\n'
        candidate['targetContentProfile'] = target
        candidate['sourcePlan'] = {**deepcopy(source_plan), 'contentProfile': target,
                                   'profileOwner': 'SERVER_VERSION_BOUND_PRODUCTION_SETTINGS'}
        result['status'] = 'PROFILE_METADATA_MISMATCH' if result['metadataMappings'] else 'PROFILE_ALIGNED'
        result['detail'] = 'Effective metadata mapped from server settings; raw provider evidence retained.'
        candidate['profileValidation'] = result
