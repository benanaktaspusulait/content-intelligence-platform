"""V2 production reconstruction inside the existing plan-first role.

The provider selects and critiques source-bound spatial/choreographic operations.
Server-owned compilation preserves narrative bytes, never delegates story approval,
and does not infer visual or audience success. Legacy plans remain readable.
"""
import json
import re
from copy import deepcopy
from hashlib import sha256
from typing import Literal
from pydantic import Field
from .optimization_plans import Strict, protected_contract
from .optimization_distinctness import _beats, _narrative, _outside
from .optimization_profile_contract import normalize_candidate_profiles
from .model_authored_execution import AUTHORING_VERSION, AuthoredProduction, reference_catalog, assemble_authored, validate_authored, provenance_spans

VERSION = 'creative-reconstruction-v2'
QUALITY_MODEL = 'creative-quality-evidence-v2'
DIMENSIONS = ['SCROLL_STOP_VISUAL_PROMISE', 'CAUSAL_PROGRESSION', 'VISUAL_STORYTELLING',
              'PRODUCTION_EXECUTABILITY', 'ENDING_REPLAY', 'DISTINCTIVE_CREATIVE_VALUE']

class Intervention(Strict):
    opportunityId: str
    operation: Literal['CONTACT_PLANE', 'SEPARATE_ACTION_RESULT', 'COUNTABLE_STATE_PATH', 'CAMERA_LABEL', 'TIMING_SPLIT']
    layout: Literal['LATERAL', 'DEPTH', 'UNCHANGED']
    camera: Literal['LOCKED', 'PAN', 'TRACK']
    rationale: str = Field(min_length=20, max_length=700)

class Reconstruction(Strict):
    candidateId: Literal['candidate-a', 'candidate-b']
    title: str = Field(min_length=3, max_length=100)
    objective: str = Field(min_length=20, max_length=700)
    interventions: list[Intervention] = Field(min_length=1, max_length=4)
    storyChangeRequested: bool

class Proposal(Strict):
    initial: Reconstruction
    revision: Reconstruction | None

class ReconstructionResponse(Strict):
    proposals: list[Proposal] = Field(max_length=2)
    noImprovementReason: str | None


class AuthoredIntervention(Intervention):
    authorship: Literal['MODEL_AUTHORED', 'BOUNDED_TEMPLATE_FALLBACK']
    production: AuthoredProduction | None
    fallbackReason: str | None

class AuthoredReconstruction(Reconstruction):
    interventions: list[AuthoredIntervention] = Field(min_length=1, max_length=4)

class AuthoredProposal(Strict):
    initial: AuthoredReconstruction
    revision: AuthoredReconstruction | None

class AuthoredResponse(Strict):
    proposals: list[AuthoredProposal] = Field(max_length=2)
    noImprovementReason: str | None

def authored_context(context):
    return context.get('optimizationGenerationInstructionsVersion') == AUTHORING_VERSION

def generation_system(context):
    return SYSTEM + AUTHORED_SYSTEM if authored_context(context) else SYSTEM


def diagnose(source, context):
    from app.config import settings
    policy = json.loads((settings.data_root/'workflow/creative-quality-v2.json').read_text())
    if policy.get('version') != QUALITY_MODEL or policy.get('dimensions') != DIMENSIONS or policy.get('generationContract') != VERSION:
        raise ValueError('Creative quality governance contract is unavailable or inconsistent')
    contract = protected_contract(source, context)
    beats = _beats(source)
    strategy = context.get('openingStrategy', 'AUTO')
    causal = contract['openingCausalParticipants']
    opportunities = []
    def add(beat, dimension, operation, status, weakness, proposal, expected, risk, bindings):
        opportunities.append({'opportunityId': f'{operation}:{beat["id"]}', 'beatId': beat['id'],
            'timeWindow': [beat['startTime'], beat['endTime']], 'dimension': dimension,
            'currentExecution': beat['sourceQuote'], 'sourceEvidence': {
                'quote': beat['sourceQuote'], 'span': beat['sourceSpan'], 'status': 'EXACT_SOURCE_TEXT'},
            'weaknessOrUncertainty': weakness, 'proposedImprovement': proposal,
            'expectedVisualChange': expected, 'viewingRationale': 'A viewer may be able to distinguish the cited physical states; this is a hypothesis, not audience evidence.',
            'productionRisk': risk, 'confidence': 'TEXT_SUPPORTED_HYPOTHESIS', 'classification': status,
            'operation': operation, 'bindings': bindings,
            'benefitEvidence': 'UNVERIFIED_UNTIL_VISUAL_REVIEW'})
    participants = [(causal.get(k) or {}).get('value') for k in ('expectedSurface', 'actualSurface')]
    if strategy != 'CURIOSITY_DISCOVERY' and all(p and p != 'UNKNOWN' for p in participants):
        b = beats[0]
        add(b, 'VISUAL_STORYTELLING', 'CONTACT_PLANE', 'CREATIVE_IMPROVEMENT_HYPOTHESIS',
            'The source names intended and actual attachment surfaces but does not specify their spatial alignment, contact plane or occlusion control.',
            'Stage the intended surface behind or beside the actual attachment point; follow the existing reach continuously, retaining the failed destination and wrong attachment in view.',
            'The reach destination and wrong-surface attachment have distinct visible positions through contact.',
            'Keeping both surfaces visible may increase composition density; actual contact geometry needs image review.', participants)
    for b in beats:
        quote = b['sourceQuote']
        match = re.search(r'\bmultiply from (.+?) as ', quote, re.I)
        if match and len(match[1].split(' to ')) >= 3:
            add(b, 'CAUSAL_PROGRESSION', 'COUNTABLE_STATE_PATH', 'EVIDENCE_SUPPORTED_EXECUTION_RISK',
                'The source lists a count progression but gives no continuity, spatial grouping or unobstructed count-transition choreography.',
                'Expose the complete existing count path in stable spatial groups; couple each count transition to the existing pull without an edit hiding contact.',
                'Each existing count state has a distinguishable arrangement before progressive body coverage.',
                'Count fidelity and fine contact remain difficult; arrangement is a proposed mitigation, not verified generator capability.', match[1].split(' to '))
        elif '->' in quote and b not in (beats[0], beats[-1]) and re.search(r'\b(?:split|splits|separate|separates|peel|peels)\b', re.sub(r'\[[^\]]*\]', '', quote), re.I):
            before, after = quote.split('->', 1)
            add(b, 'PRODUCTION_EXECUTABILITY', 'SEPARATE_ACTION_RESULT', 'CREATIVE_IMPROVEMENT_HYPOTHESIS',
                'The source states an action and result without separating their screen positions or protecting their visibility during the transition.',
                'Separate the two source-bound action/result regions and retain their transition in one locked shot.',
                'The action and resulting state occupy distinguishable regions with continuous visible contact.',
                'A wider contact tableau may reduce facial detail; visual continuity remains unverified.',
                [re.sub(r'\[[^\]]*\]', '', before).strip(), after.strip()])
    # Do not assume a formulaic ending/loop or invent a text defect where only images could resolve it.
    ending = beats[-1]
    return {'contractVersion': VERSION, 'qualityModelVersion': QUALITY_MODEL, 'openingStrategy': strategy,
        'protectedStoryContract': contract,
        'protectedLayer': ['identity', 'premise', 'approved events and order', 'physical rule', 'outcomes', 'ending', 'safety'],
        'editableLayer': ['staging', 'spatial visibility', 'choreography', 'composition', 'continuity', 'relative timing', 'visual emphasis'],
        'opportunities': opportunities,
        'dimensions': [{'dimension': dim, 'status': 'TEXTUAL_HYPOTHESES_AVAILABLE' if any(o['dimension'] == dim for o in opportunities) else 'VISUAL_EVIDENCE_REQUIRED',
                        'numericScore': None} for dim in DIMENSIONS],
        'endingReview': {'sourceQuote': ending['sourceQuote'], 'sourceSpan': ending['sourceSpan'],
                        'classification': 'VISUAL_EVIDENCE_REQUIRED', 'loopRequired': False},
        'semanticStoryFidelity': 'UNKNOWN', 'renderAuthorization': 'NOT_GRANTED'}


def response_format(context=None):
    schema = (AuthoredResponse if authored_context(context or {}) else ReconstructionResponse).model_json_schema()
    def wire(x):
        if isinstance(x, dict):
            result = {k: wire(v) for k, v in x.items() if k != 'default' and not (k == 'title' and isinstance(v, str))}
            if 'const' in result: result['enum'] = [result.pop('const')]
            return result
        return [wire(v) for v in x] if isinstance(x, list) else x
    return {'type': 'json_schema', 'json_schema': {'name': 'creative_reconstruction_v2', 'strict': True, 'schema': wire(schema)}}

SYSTEM = '''Diagnose and reconstruct production execution, not story. Read the server's creativeDiagnosis and protected story layer before proposing zero, one or two candidates. Prefer one defensible improvement to two superficial variants. For each plan identify the diagnosed opportunity and choose a matching production operation. CONTACT_PLANE changes spatial staging through existing contact; SEPARATE_ACTION_RESULT changes action/result screen choreography; COUNTABLE_STATE_PATH changes spatial arrangement and continuous presentation of existing state transitions. Specify LATERAL or DEPTH layout and a feasible camera discipline. Rationale and objective must identify an observable difference; camera labels or unchanged actions under new timestamps are insufficient. These operations are execution treatments of existing events, never additional attempts or new story events. Do not copy the baseline wording as the creative objective. Preserve identity, premise, physical rule, all approved events/order and ending. If a protected event must change, set storyChangeRequested true; it will be classified STORY_CHANGE_REQUIRES_APPROVAL, not used as a standard candidate.
Use creativeDiagnosis.openingStrategy. CURIOSITY_DISCOVERY need not reveal complete causality at frame zero. No universal joke, resolved ending or loop requirement. Every benefit is an unverified hypothesis until images/video/audience evidence exists. Do not claim proven superiority, retention uplift or guaranteed generation. Consider contact, occlusion, count continuity, character continuity, mirror and scatter execution risks. Critique the initial plan before answering: does it change staging, preserve story, address the opportunity and avoid new complexity? You may supply one revised plan in the same response if your initial proposal needs correction. No additional paid call or retry is authorized. Return proposals [] with a concrete noImprovementReason if no justified improvement exists. Never approve or create a prompt version. The server will critique each plan, compile valid interventions into complete production prompts and run existing source/canonical validation. Framing/camera-only and timestamp-only plans are rejected.'''


AUTHORED_SYSTEM = """
For model-authored-production-v1 you author the actual production instructions, not merely operation labels. Use sourceReferenceCatalog for exact beat-bound action, consequence, entity and count-state references. Put MODEL_AUTHORED in authorship and supply production; fallbackReason must be null. Write original spatial relationships, physical choreography, visible consequence presentation, state progression, relative temporal presentation, camera/composition and generator constraints. The compiler only substitutes {referenceId} with its exact source quote and joins your fields; it will not invent choreography for you. Do not submit a full rewritten prompt. Source narrative and beat windows are protected and assembled separately. Describe how existing actions are performed and shown, never add actions, attempts, props, count states or events. Use only references from the relevant beat. Spatial instructions must name both bound participants and express the typed relation. For count progression include every bound state in source order, with concrete differentiated spatial arrangements and continuous transitions; do not invent sub-beat timestamps. Camera/composition prose must agree with LOCKED camera discipline. State contact and occlusion constraints explicitly. Materiality requires a new observable spatial or state presentation; long paraphrases, camera labels and timing splits are insufficient. You may address several relevant diagnosed beats; do not force changes to every beat. All benefits remain hypotheses and semantic fidelity remains unknown. If a bounded server template is deliberately sufficient, explicitly choose BOUNDED_TEMPLATE_FALLBACK, production null and a concrete fallbackReason; this is attributed to the server, not model-authored choreography. Invalid authored instructions are rejected, never silently replaced by a template.
"""


def request_payload(source, context):
    diagnosis = diagnose(source, context)
    payload = {'phase': 'CREATIVE_DIAGNOSIS_RECONSTRUCTION_CRITIQUE', 'contractVersion': VERSION,
            'creativeDiagnosis': diagnosis, 'maxCandidates': 2, 'maxRevisionsPerCandidate': 1,
            'revisionBudget': 'WITHIN_THIS_SINGLE_RESPONSE_ONLY', 'visualEvidence': 'NOT_SUPPLIED',
            'audienceEvidence': 'NOT_SUPPLIED'}
    if authored_context(context):
        payload.update(instructionsVersion=AUTHORING_VERSION, sourceReferenceCatalog=reference_catalog(source, context, diagnosis))
    return payload


def _instructions(op, intervention):
    bindings = op['bindings']
    axis = 'left and right screen regions' if intervention.layout == 'LATERAL' else 'separate foreground and background planes'
    if op['operation'] == 'CONTACT_PLANE':
        expected, actual = bindings
        return (f'Stage {expected} and {actual} on {axis}. Align the existing reach toward {expected}; '
                f'keep the intended contact area unobstructed behind the reaching motion. Show the existing attachment to {actual} '
                'through the same continuous view; maintain a visible gap to the intended destination after wrong-surface contact. '
                'Keep the note contact edge outside the silhouette of the other hand; do not hide the attachment with a cut.')
    if op['operation'] == 'SEPARATE_ACTION_RESULT':
        return (f'Use {axis} for the existing action and its result. Separate the participating hands/objects in screen space '
                'during the existing separation; keep the contact edge visible until the stated result settles. '
                f'Preserve the continuous transition into this source result: {bindings[1]}. '
                'Do not add a repeated attempt, cut away during contact, or substitute a new outcome.')
    states = ' → '.join(bindings)
    return (f'Arrange the existing multiplying objects across {axis} as countable separated groups. '
            f'Expose the complete existing count sequence {states}; after each existing pull, show its resulting group '
            'without overlap obscuring the count before the next pull. Keep the pull/contact path continuous and the group positions stable '
            'between transformations; let the established progressive body coverage follow the growing groups. '
            'Use the original beat window, with no invented sub-beat timestamps, additional pull, freeze or new outcome.')


def critique(plan, diagnosis, source=None, refs=None):
    opportunities = {o['opportunityId']: o for o in diagnosis['opportunities']}
    reasons = []
    if plan.storyChangeRequested: reasons.append('STORY_CHANGE_REQUIRES_APPROVAL')
    from types import SimpleNamespace
    from .optimization_plans import _validate_outcome_claims
    try:
        _validate_outcome_claims(SimpleNamespace(candidateId=plan.candidateId,title=plan.title,
            baselineOpportunity=plan.objective,proposedVisualConsequence='',materialDifference='',
            risksIntroduced=[],risksReducedHypotheses=[i.rationale for i in plan.interventions],unknowns=[]))
    except ValueError:
        reasons.append('UNSUPPORTED_AUDIENCE_OR_RENDER_CLAIM')
    seen = set()
    for i in plan.interventions:
        op = opportunities.get(i.opportunityId)
        if not op or i.operation != op['operation']:
            reasons.append('NO_DIAGNOSED_MATERIAL_OPERATION')
            continue
        if i.opportunityId in seen: reasons.append('REPEATED_INTERVENTION')
        seen.add(i.opportunityId)
        if i.layout == 'UNCHANGED': reasons.append('NO_SPATIAL_OR_CHOREOGRAPHIC_CHANGE')
        if i.camera != 'LOCKED': reasons.append('EXECUTION_RISK_REGRESSION_MOVING_CONTACT_VIEW')
        if isinstance(i, AuthoredIntervention):
            if i.authorship == 'MODEL_AUTHORED':
                if i.production is None or i.fallbackReason is not None:
                    reasons.append('INVALID_AUTHORSHIP_CONTRACT')
                else:
                    try: validate_authored(i, op, refs or {}, source or '')
                    except ValueError as error: reasons.append(str(error))
            elif i.production is not None or not i.fallbackReason or len(i.fallbackReason.strip()) < 20:
                reasons.append('INVALID_EXPLICIT_FALLBACK')
        elif _instructions(op, i) in op['currentExecution']: reasons.append('BASELINE_EQUIVALENT')
    return {'status': 'ACCEPTED_TEXTUAL_PLAN' if not reasons else 'REVISION_REQUIRED',
            'reasons': sorted(set(reasons)), 'checks': {
                'observableChange': not reasons, 'addressesDiagnosis': not reasons,
                'sourceBoundOperations': all(i.opportunityId in opportunities for i in plan.interventions),
                'semanticStoryFidelity': 'UNKNOWN', 'generatorSuccess': 'UNKNOWN', 'audienceBenefit': 'UNMEASURED'},
            'revisionFeedback': ['Use a cited diagnosis, a distinct spatial/contact/state treatment, and locked continuity; preserve every protected event.'] if reasons else []}


def compile_reconstruction(source, context, raw_plan):
    plan = (AuthoredReconstruction if authored_context(context) else Reconstruction).model_validate(raw_plan)
    diagnosis = diagnose(source, context)
    refs = reference_catalog(source, context, diagnosis) if authored_context(context) else {}
    criticism = critique(plan, diagnosis, source, refs)
    if criticism['reasons']: raise ValueError('Creative reconstruction rejected: ' + ', '.join(criticism['reasons']))
    opportunities = {o['opportunityId']: o for o in diagnosis['opportunities']}
    by_beat = {}
    for intervention in plan.interventions:
        op = opportunities[intervention.opportunityId]
        by_beat.setdefault(op['beatId'], []).append((op, intervention))
    prompt = source
    changes = []
    provenance = []
    for b in reversed(_beats(source)):
        if b['id'] not in by_beat: continue
        compiled = []
        for op, i in by_beat[b['id']]:
            if isinstance(i, AuthoredIntervention) and i.authorship == 'MODEL_AUTHORED':
                text, validation, fields = assemble_authored(i, op, refs, source)
                compiled.append((text, fields, 'MODEL_AUTHORED'))
            else:
                compiled.append(('locked-off medium shot; ' + _instructions(op, i), [], 'SERVER_TEMPLATE'))
        instructions = [item[0] for item in compiled]
        # Preserve source narrative exactly; validated authored production is assembled verbatim.
        narrative = re.sub(r'\[[^\]]*\]', '', b['sourceQuote']).rstrip()
        replacement = narrative + ' [' + ' '.join(instructions) + ']'
        provenance.append({'beatId':b['id'], 'instructions':[{'text':text,'author':author,'fields':fields} for text,fields,author in compiled]})
        a, z = b['sourceSpan']; prompt = prompt[:a] + replacement + prompt[z:]
        for (op, i), (text, fields, author) in zip(by_beat[b['id']], compiled):
            changes.append({'opportunityId': op['opportunityId'], 'beatId': b['id'],
                'originalExecution': b['sourceQuote'], 'newExecution': replacement,
                'observableDifference': text, 'authorship': author, 'creativeRationale': i.rationale,
                'sourceFidelity': {'quote': b['sourceQuote'], 'span': b['sourceSpan'], 'protectedEventUnchanged': True, 'semanticFidelity': 'UNKNOWN'},
                'productionRisk': {'change': 'UNKNOWN', 'evidence': op['productionRisk'], 'newMitigation': 'Locked contact view with explicit spatial separation.'},
                'evidenceLimitation': 'Text specifies a different execution. Render adherence, visual clarity and audience benefit are unverified.'})
    candidate = {'candidateId': plan.candidateId, 'title': plan.title, 'hypothesis': plan.objective,
        'prompt': prompt, 'reconstructionPlan': plan.model_dump(), 'creativeContractVersion': VERSION,
        'creativeDiagnosis': {k: v for k, v in diagnosis.items() if k != 'protectedStoryContract'},
        'creativeAssessment': {'contractVersion': QUALITY_MODEL, 'classification': 'PLAUSIBLE_IMPROVEMENT_UNVERIFIED',
            'dimensions': [
                {'dimension':'SCROLL_STOP_VISUAL_PROMISE','assessment':'Spatial contact intervention proposed' if any(i.operation=='CONTACT_PLANE' for i in plan.interventions) else 'Opening source retained', 'evidence':'PLANNED_TEXT_ONLY'},
                {'dimension':'CAUSAL_PROGRESSION','assessment':'Explicit count-state arrangement proposed' if any(i.operation=='COUNTABLE_STATE_PATH' for i in plan.interventions) else 'Approved causal events retained', 'evidence':'PLANNED_TEXT_ONLY'},
                {'dimension':'VISUAL_STORYTELLING','assessment':'Source-bound spatial separation and contact visibility changed', 'evidence':'OBSERVED_TEXTUAL_CHANGE'},
                {'dimension':'PRODUCTION_EXECUTABILITY','assessment':'Locked continuity and occlusion mitigation proposed; actual risk change UNKNOWN', 'evidence':'UNVERIFIED_GENERATOR_HYPOTHESIS'},
                {'dimension':'ENDING_REPLAY','assessment':'Approved ending retained; no loop or audience benefit assumed', 'evidence':'EXACT_SOURCE_TEXT'},
                {'dimension':'DISTINCTIVE_CREATIVE_VALUE','assessment':'Concrete choreography differs from source; novelty and viewer value unverified', 'evidence':'OBSERVED_TEXTUAL_CHANGE'}],
            'materiality': 'SOURCE_BOUND_SPATIAL_CHOREOGRAPHIC_CHANGE', 'changeContract': list(reversed(changes)),
            'critique': criticism, 'semanticStoryFidelity': 'UNKNOWN', 'audiencePerformance': 'UNMEASURED',
            'canonicalCompliance': 'SEPARATELY_EVALUATED', 'provenBetter': False},
        'planValidation': {'contractVersion': VERSION, 'status': 'SOURCE_BOUND_MATERIAL_PLAN',
            'storyFidelity': 'UNKNOWN', 'sourcePromptSha256': sha256(source.encode()).hexdigest(),
            'preservedStorySha256': diagnosis['protectedStoryContract']['approvedStorySha256'], 'renderAuthorization': 'NOT_GRANTED'}}
    normalize_candidate_profiles(source, [candidate], context)
    validate_compiled_source(source, candidate, context)
    if authored_context(context):
        candidate['instructionsVersion'] = AUTHORING_VERSION
        for beat in provenance:
            row = next(b for b in _beats(candidate['prompt']) if b['id'] == beat['beatId'])
            cursor = row['sourceSpan'][0]
            for instruction in beat['instructions']:
                start = candidate['prompt'].index(instruction['text'], cursor)
                instruction['candidateSpan'] = [start, start + len(instruction['text'])]
                for field in instruction['fields']:
                    field['candidateSpan'] = [start + x for x in field['localSpan']]
                cursor = instruction['candidateSpan'][1]
        candidate['productionProvenance'] = {
            'version': AUTHORING_VERSION, 'spanUnit':'UNICODE_CODE_POINTS', 'beats': list(reversed(provenance)),
            'sourceEventMapping':candidate['sourceEventCoverage']['mappings'],
            'segments':provenance_spans(source,candidate['prompt'],provenance),
            'compilerContribution':['Source narrative preservation', 'Reference substitution using exact source spans',
                'Annotation delimiters and field separators', 'Authoritative production-profile normalization'],
            'semanticFidelity':'UNKNOWN', 'creativeEffectiveness':'UNVERIFIED'}
    return candidate


def validate_compiled_source(source, candidate, context):
    before, after = _beats(source), _beats(candidate['prompt'])
    if len(before) != len(after) or any(_narrative(a) != _narrative(b) or (a['startTime'], a['endTime']) != (b['startTime'], b['endTime']) for a,b in zip(before,after)):
        raise ValueError('Story fidelity/source-plan event, ending or timing changed')
    if _outside(source,before) != _outside(candidate['prompt'],after):
        raise ValueError('Story fidelity/protected identity, physical rule, ending or production settings changed')
    target = context['targetConfiguration']
    if after[0]['startTime'] != 0 or after[-1]['endTime'] != float(target['duration']):
        raise ValueError('Source-plan target duration changed')
    if any(a['endTime'] != b['startTime'] for a,b in zip(after,after[1:])):
        raise ValueError('Source-plan timeline is discontinuous')
    for key,label in [('generator','Target generator'),('contentProfile','Content profile')]:
        if not re.search(re.escape(label)+r':\s*'+re.escape(str(target[key]))+r'\b',candidate['prompt'],re.I):
            raise ValueError('Source-plan target setting changed: '+key)
    ratio = target.get('settings',{}).get('aspectRatio')
    if ratio and set(re.findall(r'\b(?:9:16|16:9|1:1)\b',candidate['prompt'])) != {ratio}:
        raise ValueError('Source-plan target aspect ratio changed')
    candidate['sourceEventCoverage'] = {'status': 'SOURCE_TEXT_COVERED', 'semanticFidelity': 'UNKNOWN',
        'sourceEventCount':len(before),'candidateShotCount':len(after),'mappings':[
            {'baselineBeatId':a['id'],'baselineQuote':a['sourceQuote'],'baselineSourceSpan':a['sourceSpan'],
             'candidateQuote':b['sourceQuote'],'candidateSourceSpan':b['sourceSpan'],'method':'EXACT_NARRATIVE_AND_SERVER_COMPILED_EXECUTION'} for a,b in zip(before,after)]}


def assess_candidate(source, candidate, context, baseline_score):
    try:
        compiled = compile_reconstruction(source, context, candidate['reconstructionPlan'])
        if compiled['prompt'] != candidate['prompt']: raise ValueError('Candidate differs from its source-bound compiled production plan')
        evidence = deepcopy(compiled['creativeAssessment'])
        if 'productionProvenance' in compiled: evidence['productionProvenance'] = compiled['productionProvenance']
        canonical = candidate.get('review',{}).get('canonicalRuleEvaluation',{})
        score = canonical.get('score')
        regression = isinstance(score,(float,int)) and isinstance(baseline_score,(float,int)) and score < baseline_score
        baseline_rows = {r['ruleId']:r for r in context.get('baselineCanonicalFailures',[])}
        new_failures = [r['ruleId'] for r in canonical.get('failedRules',[]) if r['ruleId'] not in baseline_rows] if 'baselineCanonicalFailures' in context else []
        baseline_canonical = context.get('baselineCanonicalEvaluation', {})
        rows = lambda value: {r['ruleId']:r for key in ('passedRules','failedRules','unknownRules','notApplicableRules') for r in value.get(key,[])}
        old_rows, new_rows = rows(baseline_canonical), rows(canonical)
        changes = [{'ruleId':key,'before':old_rows[key],'after':row} for key,row in new_rows.items() if key in old_rows and (old_rows[key].get('outcome'),old_rows[key].get('severity')) != (row.get('outcome'),row.get('severity'))]
        rank = {'PASS':0,'WARNING':1,'CRITICAL':2,'BLOCKER':3}
        risk_regression = any(x['ruleId'].startswith('PRODUCIBILITY_') and rank.get(x['after'].get('severity'),0)>rank.get(x['before'].get('severity'),0) for x in changes)
        evidence['canonicalChanges'] = changes
        evidence['productionRiskIndicatorRegression'] = risk_regression
        if regression or new_failures or risk_regression: evidence['classification'] = 'REGRESSION'
        critic = candidate.get('review',{}).get('executionReview',{})
        critic_review_required = authored_context(context) and critic.get('status') in {'REWRITE','BLOCKED','FAIL'}
        if authored_context(context):
            evidence['executionCritic'] = deepcopy(critic)
            evidence['executionRiskReviewRequired'] = critic_review_required
        eligible = canonical.get('status') == 'EVALUATED' and not regression and not new_failures and not risk_regression and not critic_review_required
        evidence.update(canonicalScore=score, canonicalRegression=regression, newCanonicalFailures=new_failures)
        return {'candidateId':candidate['candidateId'],'contractVersion':VERSION,
            'classification': evidence['classification'], 'approvalEligible': eligible,
            'approvalBlockReason': None if eligible else 'Execution critic requires risk review; canonical score does not establish safe execution.' if critic_review_required else 'Canonical evaluation missing or regressed; explicit review is unavailable.',
            'actualChanges':[c['observableDifference'] for c in evidence['changeContract']], 'creativeAssessment': evidence,
            'conclusion':('Source-bound execution changes introduced a canonical or production-risk regression; do not approve.' if regression or new_failures or risk_regression else 'Source-bound staging/choreography changes address a diagnosed opportunity; visual and audience benefits remain unverified.'),
            'validationStatus':'SOURCE_TEXT_CONTRACT_PASSED', 'storyCoverage':'SOURCE_EVENTS_COVERED; SEMANTIC_FIDELITY_UNKNOWN',
            'endingPreservation':'PROTECTED_ENDING_TEXT_PRESERVED', 'productionRiskChange':'UNKNOWN; proposed mitigations require visual review.',
            'qualityScore':score,'scoreDelta':score-baseline_score if isinstance(score,(int,float)) and isinstance(baseline_score,(int,float)) else None}
    except (ValueError,KeyError,TypeError) as error:
        return {'candidateId':candidate.get('candidateId'),'contractVersion':VERSION,'classification':'STORY_FIDELITY_FAILED',
                'approvalEligible':False,'approvalBlockReason':str(error),'conclusion':str(error),'actualChanges':[]}


def metrics(candidates, rejected, calls, cost=None):
    total = len(candidates) + len(rejected)
    count = lambda value: sum(r.get('classification') == value for r in rejected)
    return {'contractVersion':'creative-improvement-metrics-v1','candidateAttempts':total,
        'materialCandidates':len(candidates), 'materialCandidateSuccessRate':len(candidates)/total if total else None,
        'baselineEquivalentRejections':count('VALID_BUT_EQUIVALENT'),
        'baselineEquivalentRejectionRate':count('VALID_BUT_EQUIVALENT')/total if total else None,
        'storyFidelityFailures':count('STORY_FIDELITY_FAILED')+count('STORY_CHANGE_REQUIRES_APPROVAL'),
        'storyFidelityFailureRate':(count('STORY_FIDELITY_FAILED')+count('STORY_CHANGE_REQUIRES_APPROVAL'))/total if total else None,
        'productionRiskRegressions':count('REGRESSION'), 'canonicalRegressions':None,
        'operatorPreferredCandidates':None,'defensibleOperatorPreferenceRate':None,
        'providerCalls':calls, 'callsWithoutAcceptableCandidate':calls if not candidates else 0,
        'providerCostUsd':cost,'costPerOperatorAcceptedMaterialImprovement':None,
        'visualClarity':None,'generatorAdherence':None,'physicalMechanicReadability':None,
        'characterContinuity':None,'observedRenderDefects':None,
        'earlyRetention':None,'averageWatchTime':None,'completion':None,'rewatch':None,'savesShares':None,
        'evidenceStatus':'TEXT_ONLY; NULL_MEANS_NOT_OBSERVED'}


def perform_reconstruction(source, context, provider, model):
    payload = request_payload(source,context)
    provider.response_format = response_format(context); provider.last_request_started = True
    raw = provider.complete(json.dumps(payload,ensure_ascii=False),system=generation_system(context),temperature=0)
    provider.last_raw_response=raw
    value=json.loads(raw);provider.last_role_result=deepcopy(value)
    parsed=(AuthoredResponse if authored_context(context) else ReconstructionResponse).model_validate(value)
    if not parsed.proposals and not (parsed.noImprovementReason and len(parsed.noImprovementReason.strip()) >= 20):
        raise ValueError('NO_JUSTIFIED_IMPROVEMENT requires a concrete explanation')
    identities=[p.initial.candidateId for p in parsed.proposals]
    if len(set(identities)) != len(identities): raise ValueError('Duplicate candidate identities')
    candidates=[];rejected=[];cycles=[]
    for proposal in parsed.proposals:
        plan=proposal.initial;review=critique(plan,payload['creativeDiagnosis'],source,payload.get('sourceReferenceCatalog'))
        cycle={'candidateId':plan.candidateId,'initialCritique':review,'revisionsUsed':0}
        if review['reasons'] and proposal.revision is not None and 'STORY_CHANGE_REQUIRES_APPROVAL' not in review['reasons']:
            if proposal.revision.candidateId != plan.candidateId or {x.opportunityId for x in proposal.revision.interventions} != {x.opportunityId for x in plan.interventions}:
                raise ValueError('Revision must target the same candidate and diagnosed opportunities')
            plan=proposal.revision; review=critique(plan,payload['creativeDiagnosis'],source,payload.get('sourceReferenceCatalog'));cycle['revisionsUsed']=1
        cycle['finalCritique']=review;cycles.append(cycle)
        if review['reasons']:
            category='STORY_CHANGE_REQUIRES_APPROVAL' if 'STORY_CHANGE_REQUIRES_APPROVAL' in review['reasons'] else 'REGRESSION' if any('REGRESSION' in r for r in review['reasons']) else 'STORY_FIDELITY_FAILED' if any('STORY_FIDELITY_FAILED' in r for r in review['reasons']) else 'VALID_BUT_EQUIVALENT'
            rejected.append({'candidateId':plan.candidateId,'classification':category,**review});continue
        candidate=compile_reconstruction(source,context,plan.model_dump())
        if any(c['prompt']==candidate['prompt'] for c in candidates):
            rejected.append({'candidateId':plan.candidateId,'classification':'VALID_BUT_EQUIVALENT','reasons':['DUPLICATE_EXECUTION_PLAN']});continue
        candidates.append(candidate)
    return {'role':'PROMPT_OPTIMIZATION','provider':'openai','model':model,'calls':1,
        'result':{'candidates':candidates,'creativeContractVersion':VERSION,
            'instructionsVersion':context.get('optimizationGenerationInstructionsVersion', VERSION),
            'creativeDiagnosis':payload['creativeDiagnosis'],'critiqueCycles':cycles,'rejectedProposals':rejected,
            'outcome':'MATERIAL_CANDIDATES_FOR_REVIEW' if candidates else 'NO_JUSTIFIED_IMPROVEMENT',
            'noImprovementReason':parsed.noImprovementReason,'improvementMetrics':metrics(candidates,rejected,1)},
        'rawProviderResult':deepcopy(value),'rawProviderResponse':raw,'validationStatus':'NOT_VALIDATED',
        'workflowStrategy':VERSION,'promptCompilation':'DETERMINISTIC_PRODUCTION_RECONSTRUCTION_AFTER_CRITIQUE',
        'usage':getattr(provider,'last_usage',None),'providerResponseMetadata':getattr(provider,'last_response_metadata',None)}
