"""Server-owned profile mapping. Raw provider evidence is never overwritten."""
import re
from copy import deepcopy
from .review import PROFILES

CONTRACT_VERSION = 'optimization-profile-ownership-v1'
_LABEL = re.compile(r'(Content profile:\s*)([A-Za-z_ -]+)(?=[.\n]|$)', re.I)


def _settings_section(text):
    match = re.search(r'(?im)^PRODUCTION SETTINGS\s*\n', text)
    return (match, text[match.end():]) if match else (None, '')


def _represented_profiles(metadata):
    """Return explicit profile values already represented in settings.

    Older approved prompts store the canonical enum as an unlabeled settings
    token.  That is still authoritative representation; adding a newer label
    would mutate protected prompt text.  AUTO is recognized only when labelled
    because it is otherwise ordinary prose.
    """
    represented=[]
    for match in _LABEL.finditer(metadata):
        represented.append((canonical_profile(match[2]), 'LABELED', match.span(2)))
    for profile in PROFILES:
        if profile == 'UNKNOWN':
            continue
        pattern=r'(?<![A-Za-z0-9_])'+r'[_ -]'.join(re.escape(part) for part in profile.split('_'))+r'(?![A-Za-z0-9_])'
        for match in re.finditer(pattern, metadata, re.I):
            if any(a <= match.start() < z for _,_,(a,z) in represented):
                continue
            represented.append((profile, 'CANONICAL_TOKEN', match.span()))
    return represented


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
    _, source_metadata = _settings_section(source)
    source_represented = _represented_profiles(source_metadata)
    source_profile_values = [value for value, _, _ in source_represented]
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
        section, metadata = _settings_section(raw)
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
        represented = _represented_profiles(metadata)
        represented_values = [value for value, _, _ in represented]
        # Historical prompts may contain obsolete profile metadata such as
        # `Content profile: AUTO`. Preserving that exact source representation
        # is not a new creative directive and must not make a source-faithful
        # candidate impossible. A candidate that introduces or changes a
        # conflicting representation is still rejected. The effective profile
        # always remains the version-bound server target below.
        preserves_source_representation = represented_values == source_profile_values
        conflicts = ([] if preserves_source_representation else
                     [value for value,_,_ in represented if value != target])
        if conflicts:
            result.update(status='MATERIAL_CREATIVE_PROFILE_CONFLICT',
                          detail=f'production settings explicitly contain {sorted(set(conflicts))}; server target is {target}')
            raise ProfileContractError(result)
        for field, value in [('targetContentProfile', candidate.get('targetContentProfile')),
                             ('sourcePlan.contentProfile', source_plan.get('contentProfile'))]:
            if value is not None and canonical_profile(value) != target:
                result['metadataMappings'].append({'field': field, 'rawValue': value,
                                                  'effectiveValue': target, 'owner': 'SERVER'})
        # Profile ownership is stored in structured candidate metadata.  Prompt
        # text is not a metadata sink: preserve the source representation byte
        # for byte, including legacy unlabeled canonical tokens and prompts that
        # legitimately derive their profile only from bound server settings.
        candidate['prompt'] = raw
        candidate['targetContentProfile'] = target
        candidate['sourcePlan'] = {**deepcopy(source_plan), 'contentProfile': target,
                                   'profileOwner': 'SERVER_VERSION_BOUND_PRODUCTION_SETTINGS'}
        if preserves_source_representation and represented_values and any(value != target for value in represented_values):
            result['status'] = 'HISTORICAL_PROFILE_REPRESENTATION_PRESERVED'
            result['detail'] = ('Historical source profile representation preserved byte-for-byte; '
                                'effective profile remains bound to server production settings.')
        elif represented:
            result['status'] = 'PROFILE_ALIGNED'
            result['detail'] = 'Existing production-settings representation retained without mutation.'
        else:
            result['status'] = 'PROFILE_DERIVED_WITHOUT_PROMPT_MUTATION'
            result['detail'] = 'Effective profile derived from bound server settings; protected prompt text unchanged.'
        candidate['profileValidation'] = result
