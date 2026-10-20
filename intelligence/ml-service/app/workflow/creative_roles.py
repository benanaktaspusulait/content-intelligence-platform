"""Explicit text roles over existing adapters; generation never approves its own output."""
from __future__ import annotations
import json
from copy import deepcopy
import logging
import math
import os
import re
from uuid import uuid4
from openai import Timeout
from pathlib import Path
from difflib import SequenceMatcher
from hashlib import sha256
from typing import Any

from app.llm.provider import LLMProvider
from app.llm.openai_provider import OpenAIProvider
from .deepseek import DeepSeekTextProvider
from .story_quality import analyse_story_candidates

ROLES = {
    'IDEA': 'openai',
    'STORY': 'deepseek',
    'STORY_REVIEW': 'openai',
    'BUILD_PROMPT': 'openai',
    'MINIMAL_REPAIR': 'openai',
    'PROMPT_OPTIMIZATION': 'openai',
}
logger = logging.getLogger(__name__)

_NAMED_CHARACTER_SPECIES = re.compile(
    r"(?u)\b([A-Z][A-Za-zÀ-ÖØ-öø-ÿ’'-]{1,40})\s*,?\s+(?:the\s+)?(rabbit|bunny|bear|cat|dog|fox|hedgehog|crocodile)\b"
)
_CHARACTER_DETERMINERS = frozenset({'the', 'a', 'an'})

_LONG_FORM_STORY_CONTRACT = '''
LONG-FORM STORY CONTRACT (one complete story, not a premise or a list of odd events):
EXACT JSON ENVELOPE: Return exactly one root JSON object shaped as {"alternatives":[{"candidateId":"candidate-1","title":"short title","protagonistCharacterId":"registered-id-from-context","text":"complete story"}]}. Return one complete root object only. Do not include a `storyPlan`, duplicate fields, other root keys, Markdown, commentary, or any characters after the root object closes. The application derives evidence from the story text; do not repeat the same evidence in a second schema.
CONCEPT SELECTION GATE: Before expanding the story, compare the proposed object's visual engine and causal progression with context.establishedWinnerMechanisms and context.rejectedCandidates. Do not reuse or cosmetically rename a winner or rejected concept. Reject chair/cushion escape, door shrinking/inversion, missing-shoe reveals, simple chase/return loops, oversized-object spectacle, sticky attachment/multiplication, and observation-dependent object state unless the causal engine is materially different. Prefer a fresh mechanism whose consequences create new story information. Any provider-authored comparison is only a generation rationale, not verified originality evidence. If no strong distinct concept emerges, do not falsely claim novelty.
The opening begins with the established character pursuing one believable ordinary task and already visibly blocked at frame zero. The first timed beat must show the goal, visible problem, and immediate reaction together. State the goal and why it matters in the story text itself. Follow the selected creative profile: ABSURD_PHYSICS requires one coherent impossible physical rule; CURIOSITY_ADVENTURE does not require impossible physics and may use a grounded visual mystery. Do not add magic merely to satisfy a generic story template.
For CURIOSITY_ADVENTURE, make the unresolved problem and viewer-facing question concrete and understandable from the opening image. Place a visible clue or contradiction where viewers can notice it before the character does. The character's motivated discovery must change the strategy or interpretation, and that discovery must cause a genuinely new consequence or development before a rewarding resolution of the original goal. Do not substitute repeated inspection, movement, or the same failed attempt for new information. For other profiles, preserve their selected creative objective and use only the mechanism that profile requires.
Build one coherent causal mechanism. Every later action must try to achieve the same goal. Give each major attempt a different strategy and a different visible consequence that changes the situation. Include a discovery or reversal that changes the character's strategy, then a meaningful payoff to the original goal. A replay ending is optional; use one only if the established mechanism naturally brings the opening problem back.
Do not count repeated force, a camera change, another direction of the same movement, waiting, or a longer reaction as progression. Do not add props, characters, magic rules, or dense hand-object choreography to fill time. Prefer large, simple, continuous actions suitable for Seedance image-to-video.
The requested duration is context.targetDuration (normally 20 seconds). A 20-second story is valid. Recommend a shorter runtime when the progression does not earn the requested duration. For 20–22 seconds, usually use about 5–6 distinct developments; for 25–30 seconds, about 6–8. These are creative guidance, not a beat-count score.
Current Ruleset 1.12 evaluates active character attempts separately from distinct story developments. The seven-attempt long-form requirement is historical and no longer applies. Preserve sufficient motivated attempts to show the character pursuing the goal, but do not add an arbitrary attempt quota or relabel consequences, discoveries, reversals, payoff, or loop as attempts. Never pad or repeat actions to satisfy a count. The application evaluates runtime and production feasibility from source evidence; absent independent evidence stays NOT_EVALUATED. Do not award itself a pass.
`text` must contain the actual concept, an explicit everyday Goal, one explicit Rule, a duration declaration and chronological, non-overlapping timed story beats formatted `0.0-3.0 SEC: ...` that cover the whole story. Its first beat must show the character's trouble already happening. Keep every fact needed for creative evaluation in this text. The application parses only evidence present in the text into its canonical IR; missing content remains missing and fails or stays unknown. Do not claim that text analysis proves visual legibility, duration value or Seedance success. Do not return self-awarded creative PASS, render readiness, or an approval.
'''


def _story_plan_errors(candidate: dict[str, Any], target_duration: Any) -> list[str]:
    """Check the existing STORY role's structured evidence against its own text."""
    text = str(candidate.get('text') or '')
    plan = candidate.get('storyPlan')
    if not isinstance(plan, dict):
        return ['STORY_PLAN_MISSING']
    errors: list[str] = []

    def exact_quote(container: Any, key: str, label: str, required: bool = True) -> str:
        value = container.get(key) if isinstance(container, dict) else None
        quote = value.strip() if isinstance(value, str) else ''
        if required and (not quote or quote not in text):
            errors.append(f'{label}_QUOTE_NOT_IN_STORY')
        return quote

    for field in ('character', 'causalRelationship'):
        if not isinstance(plan.get(field), str) or not plan[field].strip():
            errors.append(f'{field.upper()}_MISSING')
    # Selection rationale and duration-value judgment are metadata about a
    # story, not source evidence for the story itself. Missing/unsupported
    # metadata is recorded separately and must never prevent canonical
    # evaluation of otherwise source-bound story content.
    goal = plan.get('everydayGoal')
    if not isinstance(goal, dict) or not all(isinstance(goal.get(key), str) and goal[key].strip() for key in ('task', 'why')):
        errors.append('EVERYDAY_GOAL_INCOMPLETE')
    goal_quote = exact_quote(goal, 'sourceQuote', 'EVERYDAY_GOAL')
    trouble = plan.get('frameZeroTrouble')
    if not isinstance(trouble, dict) or not isinstance(trouble.get('description'), str) or not trouble.get('description', '').strip():
        errors.append('FRAME_ZERO_TROUBLE_INCOMPLETE')
    trouble_quote = exact_quote(trouble, 'sourceQuote', 'FRAME_ZERO_TROUBLE')
    rule = plan.get('impossiblePhysicalRule')
    if not isinstance(rule, dict) or not isinstance(rule.get('rule'), str) or not rule.get('rule', '').strip():
        errors.append('PHYSICAL_RULE_INCOMPLETE')
    exact_quote(rule, 'sourceQuote', 'PHYSICAL_RULE')

    attempts = plan.get('attempts')
    if not isinstance(attempts, list):
        errors.append('ATTEMPTS_MISSING')
    else:
        for index, attempt in enumerate(attempts, start=1):
            if not isinstance(attempt, dict) or not all(isinstance(attempt.get(key), str) and attempt[key].strip() for key in ('strategy', 'action', 'consequence', 'stateChange')):
                errors.append(f'ATTEMPT_{index}_INCOMPLETE')
                continue
            exact_quote(attempt, 'sourceQuote', f'ATTEMPT_{index}')

    for field, required_keys in (
        ('discovery', ('description', 'strategyChange')),
        ('payoff', ('description', 'goalOutcome')),
    ):
        item = plan.get(field)
        if not isinstance(item, dict) or any(not isinstance(item.get(key), str) or not item[key].strip() for key in required_keys):
            errors.append(f'{field.upper()}_INCOMPLETE')
        else:
            exact_quote(item, 'sourceQuote', field.upper())
    loop = plan.get('loopMechanism')
    if not isinstance(loop, dict) or not isinstance(loop.get('description'), str):
        errors.append('LOOP_MECHANISM_MISSING')
    elif loop.get('description', '').strip():
        exact_quote(loop, 'sourceQuote', 'LOOP_MECHANISM')

    beats = plan.get('timecodedBeats')
    intervals: list[tuple[float, float]] = []
    if not isinstance(beats, list) or not beats:
        errors.append('TIMECODED_BEATS_MISSING')
    else:
        for index, beat in enumerate(beats, start=1):
            if not isinstance(beat, dict) or any(not isinstance(beat.get(key), str) or not beat[key].strip() for key in ('development', 'action', 'consequence', 'stateChange')):
                errors.append(f'TIMECODED_BEAT_{index}_INCOMPLETE')
                continue
            exact_quote(beat, 'sourceQuote', f'TIMECODED_BEAT_{index}')
            try:
                start, end = float(beat.get('startSeconds')), float(beat.get('endSeconds'))
                if start < 0 or end <= start:
                    raise ValueError
                intervals.append((start, end))
            except (TypeError, ValueError):
                errors.append(f'TIMECODED_BEAT_{index}_TIME_INVALID')
        if intervals:
            if intervals[0][0] != 0 or any(intervals[i][0] != intervals[i - 1][1] for i in range(1, len(intervals))):
                errors.append('TIMECODED_PLAN_HAS_GAP_OR_OVERLAP')
            runtime = plan.get('recommendedRuntimeSeconds')
            if not isinstance(runtime, (int, float)) or isinstance(runtime, bool) or intervals[-1][1] != float(runtime):
                errors.append('TIMECODED_PLAN_RUNTIME_MISMATCH')
            if target_duration is not None and runtime != target_duration:
                errors.append('RUNTIME_DIFFERS_FROM_REQUESTED_TARGET')
            if runtime is not None and not 20 <= float(runtime) <= 30:
                errors.append('RUNTIME_OUTSIDE_LONG_FORM_TARGET')
            try:
                from app.parser.prompt_parser import parse_prompt
                parsed = parse_prompt(text)
                if parsed.video_plan_ir.get('metadata', {}).get('duration') != float(runtime):
                    errors.append('STORY_TEXT_DURATION_NOT_PARSEABLE')
                if len(parsed.video_plan_ir.get('beats', [])) != len(intervals):
                    errors.append('STORY_TEXT_TIMECODES_NOT_PARSEABLE')
            except Exception:
                errors.append('STORY_TEXT_PARSE_FAILED')
        if beats and isinstance(beats[0], dict) and trouble_quote and beats[0].get('sourceQuote') and trouble_quote not in beats[0]['sourceQuote']:
            errors.append('FRAME_ZERO_TROUBLE_NOT_IN_FIRST_BEAT')
        if beats and goal_quote and goal_quote not in text:
            errors.append('EVERYDAY_GOAL_NOT_IN_STORY')

    justification = plan.get('durationJustification')
    if not isinstance(justification, dict) or not isinstance(justification.get('eightSecondRemovalTest'), str) or not justification['eightSecondRemovalTest'].strip() or not isinstance(justification.get('sourceQuotes'), list):
        errors.append('DURATION_JUSTIFICATION_INCOMPLETE')
    elif not isinstance(justification.get('meaningfulLossIfShortened'), bool):
        errors.append('DURATION_VERDICT_NOT_BOOLEAN')
    elif isinstance(justification.get('meaningfulLossIfShortened'), bool) and not justification['meaningfulLossIfShortened']:
        errors.append('LONG_FORM_DURATION_NOT_JUSTIFIED')
    elif not justification['sourceQuotes'] or any(not isinstance(q, str) or not q or q not in text for q in justification['sourceQuotes']):
        errors.append('DURATION_JUSTIFICATION_QUOTES_NOT_IN_STORY')
    complexity = plan.get('productionComplexity')
    if not isinstance(complexity, dict) or complexity.get('level') not in {'LOW', 'MODERATE', 'HIGH'} or complexity.get('segmentStrategy') not in {'SINGLE_GENERATION', 'CONTROLLED_SEGMENTS', 'UNKNOWN'} or not isinstance(complexity.get('seedanceRisks'), list):
        errors.append('PRODUCTION_COMPLEXITY_INCOMPLETE')
    return errors


def _bind_story_source_evidence(candidate: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Bind plan citations to exact text/parser spans; never create story content."""
    from app.parser.prompt_parser import ParserConfig, parse_prompt

    text = str(candidate.get('text') or '')
    plan = candidate.get('storyPlan')
    result = {'goal': 'NOT_EVALUATED', 'frameZero': 'NOT_EVALUATED', 'duration': 'NOT_EVALUATED'}
    if not isinstance(plan, dict) or not text.strip():
        return result
    parsed = parse_prompt(text, ParserConfig(attempt_evidence_policy='ACTOR_SOURCE_BOUND_V3'))
    ir = parsed.video_plan_ir
    goal = plan.get('everydayGoal')
    parsed_goal = (ir.get('goalEvidence') or {}).get('primaryGoal') or {}
    span = parsed_goal.get('sourceSpan')
    quote = parsed_goal.get('sourceQuote')
    if (isinstance(goal, dict) and parsed_goal.get('state') == 'OBSERVED'
            and isinstance(span, list) and len(span) == 2
            and text[span[0]:span[1]] == quote and quote):
        goal['sourceQuote'] = quote
        result['goal'] = 'SOURCE_BOUND'
    else:
        result['goal'] = 'MISSING'

    beats = ir.get('beats') or []
    planned_beats = plan.get('timecodedBeats')
    if isinstance(planned_beats, list):
        for planned in planned_beats:
            if not isinstance(planned, dict):
                continue
            matches = [b for b in beats if b.get('startTime') == planned.get('startSeconds')
                       and b.get('endTime') == planned.get('endSeconds')]
            if len(matches) == 1:
                b = matches[0]
                source_span = b.get('sourceSpan')
                source_quote = b.get('sourceQuote')
                if (isinstance(source_span, list) and len(source_span) == 2
                        and text[source_span[0]:source_span[1]] == source_quote):
                    planned['sourceQuote'] = source_quote
    if isinstance(planned_beats, list):
        valid_quotes = [b.get('sourceQuote') for b in planned_beats if isinstance(b, dict)
                        and isinstance(b.get('sourceQuote'), str) and b['sourceQuote'] in text]
        rule_match = re.search(r'(?im)^\s*(?:impossible\s+)?rule\s*:\s*[^\n]+', text)
        rule = plan.get('impossiblePhysicalRule')
        if isinstance(rule, dict) and rule_match:
            rule['sourceQuote'] = rule_match.group(0).strip()
        for field, labels in (('discovery', ('discover', 'reversal', 'realiz', 'understand')),
                              ('payoff', ('payoff', 'ending', 'success', 'resolution'))):
            item = plan.get(field)
            if not isinstance(item, dict):
                continue
            selected = next((b for b in planned_beats if isinstance(b, dict)
                             and any(label in str(b.get('development', '')).lower() for label in labels)
                             and isinstance(b.get('sourceQuote'), str) and b['sourceQuote'] in text), None)
            if selected is None and field == 'payoff' and planned_beats:
                selected = planned_beats[-1]
            if selected and isinstance(selected.get('sourceQuote'), str) and selected['sourceQuote'] in text:
                item['sourceQuote'] = selected['sourceQuote']
        loop = plan.get('loopMechanism')
        if isinstance(loop, dict) and loop.get('description') and planned_beats:
            last = planned_beats[-1]
            if isinstance(last, dict) and isinstance(last.get('sourceQuote'), str) and last['sourceQuote'] in text:
                loop['sourceQuote'] = last['sourceQuote']
        justification = plan.get('durationJustification')
        if isinstance(justification, dict) and valid_quotes:
            # Citations identify the actual timed source material. The separate
            # duration assessment below still decides whether it supports the claim.
            justification['sourceQuotes'] = valid_quotes
    first = beats[0] if beats else {}
    hook = ir.get('hook') or {}
    first_span, first_quote = first.get('sourceSpan'), first.get('sourceQuote')
    trouble = plan.get('frameZeroTrouble')
    if (isinstance(trouble, dict) and hook.get('textualFirstFrameIntent', {}).get('status') == 'PASS'
            and isinstance(first_span, list) and len(first_span) == 2
            and text[first_span[0]:first_span[1]] == first_quote):
        trouble['sourceQuote'] = first_quote
        result['frameZero'] = 'SOURCE_BOUND'
    else:
        result['frameZero'] = 'MISSING'

    # Structured attempt quotes are mapped only to their referenced timed beat.
    attempts = plan.get('attempts')
    if isinstance(attempts, list) and isinstance(planned_beats, list):
        by_index = {i + 1: beat for i, beat in enumerate(planned_beats) if isinstance(beat, dict)}
        for attempt in attempts:
            if not isinstance(attempt, dict):
                continue
            match = re.search(r'(\d+)$', str(attempt.get('beatId') or ''))
            beat = by_index.get(int(match.group(1))) if match else None
            if beat and isinstance(beat.get('sourceQuote'), str) and beat['sourceQuote'] in text:
                attempt['sourceQuote'] = beat['sourceQuote']

    # Keep the provider's natural-language removal test, but its boolean is a
    # claim. No existing evaluator independently establishes this duration
    # verdict, so it remains NOT_EVALUATED unless a real boolean is supplied;
    # even then the claim is not treated as an evaluated duration PASS.
    justification = plan.get('durationJustification')
    if isinstance(justification, dict):
        result['duration'] = 'PROVIDER_BOOLEAN_CLAIM' if isinstance(justification.get('meaningfulLossIfShortened'), bool) else 'NOT_EVALUATED'
    candidate['storySourceEvidenceStatus'] = result
    candidate['durationAssessment'] = {
        'status': 'NOT_EVALUATED',
        'reason': 'No existing independent duration-value evaluator produced a source-bound verdict.',
        'providerClaim': justification.get('meaningfulLossIfShortened') if isinstance(justification, dict) else None,
    }
    selection = plan.get('conceptSelection')
    if not isinstance(selection, dict) or any(not isinstance(selection.get(k), str) or not selection[k].strip()
                                               for k in ('mechanism', 'nearestComparison', 'distinction')):
        persisted = (context or {}).get('conceptSelection') if isinstance(context, dict) else None
        if isinstance(persisted, dict) and all(isinstance(persisted.get(k), str) and persisted[k].strip()
                                               for k in ('mechanism', 'nearestComparison', 'distinction')):
            plan['conceptSelection'] = deepcopy(persisted)
            candidate['conceptSelectionStatus'] = 'MAPPED_FROM_PERSISTED_WORKFLOW'
        else:
            plan.pop('conceptSelection', None)
            candidate['conceptSelectionStatus'] = 'NOT_EVALUATED_MISSING_SELECTION_RATIONALE'
    else:
        candidate['conceptSelectionStatus'] = 'PROVIDER_RATIONALE_UNVERIFIED'
    return result


def _goal_evidence_from_story_plan(candidate: dict[str, Any]) -> dict[str, Any] | None:
    plan = candidate.get('storyPlan')
    goal = plan.get('everydayGoal') if isinstance(plan, dict) else None
    trouble = plan.get('frameZeroTrouble') if isinstance(plan, dict) else None
    rule = plan.get('impossiblePhysicalRule') if isinstance(plan, dict) else None
    if not all(isinstance(value, dict) for value in (goal, trouble, rule)):
        return None
    quote = goal.get('sourceQuote')
    description = goal.get('task')
    if not isinstance(quote, str) or quote not in str(candidate.get('text') or '') or not isinstance(description, str) or not description.strip():
        return None
    return {
        'goalExplicitness': 'EXPLICIT',
        'description': description.strip(),
        'goalType': 'EVERYDAY_TASK',
        'targetObject': plan.get('impossiblePhysicalRule', {}).get('targetObject'),
        'obstruction': trouble.get('description'),
        'physicalRule': rule.get('rule'),
        'sourceQuote': quote,
    }


def _bind_story_quality_goal_result(story_quality: dict[str, Any], alternatives: list[Any]) -> None:
    """Reflect the existing GOAL_001 outcome in the preliminary story assessment."""
    assessments = story_quality.get('candidates') if isinstance(story_quality, dict) else None
    if not isinstance(assessments, list):
        return
    candidates = {str(item.get('candidateId')): item for item in alternatives if isinstance(item, dict)}
    for assessment in assessments:
        structural = assessment.get('assessment')
        candidate = candidates.get(str(structural.get('candidateId'))) if isinstance(structural, dict) else None
        if not candidate:
            continue
        outcome = candidate.get('mandatoryStoryGate', {}).get('rules', {}).get('GOAL_001')
        if outcome not in {'PASS', 'FAIL', 'UNKNOWN', 'NOT_EVALUATED', 'SERVICE_ERROR'}:
            continue
        mapped = 'PASS' if outcome == 'PASS' else 'FAIL' if outcome == 'FAIL' else 'NOT_EVALUATED'
        goal_gate = structural.get('goalMotivationGate')
        if isinstance(goal_gate, dict):
            goal_gate['status'] = mapped
            goal_gate['renderReady'] = False
            goal_gate['creativePassEligible'] = False
            goal_gate['unverifiedCriteria'] = [] if mapped == 'PASS' else goal_gate.get('unverifiedCriteria', [])
            goal_gate['evidence'] = candidate.get('storyPlan', {}).get('everydayGoal', {}).get('sourceQuote')
        unknown_rows = structural.get('unknown')
        if isinstance(unknown_rows, list):
            for row in unknown_rows:
                if row.get('dimension') == 'goalMotivation':
                    row['outcome'] = mapped
                    row['message'] = (
                        'Existing GOAL_001 semantic evaluation supports the explicit everyday goal and its obstruction.'
                        if mapped == 'PASS' else
                        'Existing GOAL_001 evaluation rejected the goal-obstruction relationship.'
                        if mapped == 'FAIL' else
                        'GOAL_001 did not produce a usable semantic verdict; the goal remains unevaluated.'
                    )


def _validate_canonical_story_identity(alternatives: list[Any], context: dict[str, Any]) -> list[dict[str, str]]:
    """Keep character-registry validation separate from source-fidelity review."""
    character = context.get('characterRecord')
    if not isinstance(character, dict) or not character.get('id') or not character.get('name'):
        raise ValueError('Canonical character registry binding is required for new story generation')
    expected_id = str(character['id'])
    expected_name = str(character['name']).strip()
    registry = context.get('canonicalCharacterRegistry')
    if not isinstance(registry, list) or not registry:
        raise ValueError('Canonical character registry evidence is required for story generation')
    registered = {
        str(item.get('name', '')).casefold(): str(item.get('id', ''))
        for item in registry if isinstance(item, dict)
    }
    if registered.get(expected_name.casefold()) != expected_id:
        raise ValueError('Selected protagonist is absent from the canonical character registry')
    expected_pattern = re.compile(r'(?<![\w])' + re.escape(expected_name) + r'(?![\w])', re.IGNORECASE)
    validations: list[dict[str, str]] = []
    for index, candidate in enumerate(alternatives):
        if not isinstance(candidate, dict):
            raise ValueError('Canonical character validation requires structured story candidates')
        if str(candidate.get('protagonistCharacterId', '')) != expected_id:
            raise ValueError(f'Story candidate {index + 1} does not bind the selected canonical protagonist ID')
        story = candidate.get('text')
        if not isinstance(story, str) or not expected_pattern.search(story):
            raise ValueError(f'Story candidate {index + 1} does not use the selected canonical protagonist name')
        for match in _NAMED_CHARACTER_SPECIES.finditer(story):
            declared_name = match.group(1)
            # The matcher recognizes a name shape followed by a species.
            # A sentence-initial determiner in "The bear" is a common noun,
            # not a character declaration.
            if declared_name.casefold() in _CHARACTER_DETERMINERS:
                continue
            if declared_name.casefold() not in registered:
                raise ValueError(f'Story candidate {index + 1} names an unregistered character: {declared_name}')
        validations.append({'candidateId': str(candidate.get('candidateId', index + 1)), 'status': 'REGISTRY_PASS', 'characterId': expected_id, 'characterName': expected_name})
    return validations


def _evaluate_long_form_story_text(candidate: dict[str, Any], context: dict[str, Any], target_duration: float, index: int) -> dict[str, Any]:
    """Send the source narrative through canonical parsing without provider-authored plan metadata."""
    from app.parser.prompt_parser import ParserConfig, parse_prompt
    from .review import review_prompt

    story = str(candidate.get('text') or '')
    parsed = parse_prompt(story, ParserConfig(attempt_evidence_policy='ACTOR_SOURCE_BOUND_V3'))
    ir = parsed.video_plan_ir
    beats = ir.get('beats') or []
    goal = ir.get('goalEvidence') or {}
    primary_goal = goal.get('primaryGoal') or {}
    hook = ir.get('hook') or {}
    mechanic = ir.get('coreMechanic') or {}
    rule_evidence = mechanic.get('physicalRuleEvidence') or {}
    content_profile = str(context.get('profile') or 'ABSURD_PHYSICS').upper()
    duration = (ir.get('metadata') or {}).get('duration')
    if duration is None and beats:
        duration = max(float(beat.get('endTime') or 0) for beat in beats)

    source_errors = []
    if primary_goal.get('state') != 'OBSERVED' or not primary_goal.get('sourceQuote'):
        source_errors.append('EVERYDAY_GOAL_NOT_SOURCE_ESTABLISHED')
    if not beats:
        source_errors.append('TIMECODED_STORY_NOT_SOURCE_ESTABLISHED')
    if hook.get('textualFirstFrameIntent', {}).get('status') != 'PASS':
        source_errors.append('FRAME_ZERO_TROUBLE_NOT_SOURCE_ESTABLISHED')
    if content_profile in {'ABSURD_PHYSICS', 'MIXED', 'UNKNOWN'} and (
        rule_evidence.get('state') != 'OBSERVED' or not rule_evidence.get('sourceQuote')
    ):
        source_errors.append('PHYSICAL_RULE_NOT_SOURCE_ESTABLISHED')
    if duration is None or not 20 <= float(duration) <= 30:
        source_errors.append('LONG_FORM_RUNTIME_NOT_SOURCE_ESTABLISHED')

    # A provider's detailed storyPlan remains available in the saved result for
    # diagnostics, but it is neither required nor accepted as source evidence.
    if isinstance(candidate.get('storyPlan'), dict):
        provider_errors = _story_plan_errors(candidate, target_duration)
        candidate['providerStoryPlanDiagnostics'] = {
            'status': 'PASS' if not provider_errors else 'FAIL',
            'errors': provider_errors,
            'usedForCanonicalEvidence': False,
        }
    candidate['storyPlanValidation'] = {
        'status': 'SOURCE_TEXT_MAPPED' if not source_errors else 'SOURCE_CONTENT_INCOMPLETE',
        'errors': source_errors,
        'version': 'canonical-video-plan-ir-1.12',
        'canonicalEvaluationEligible': bool(story.strip()),
        'sourceBoundGoal': primary_goal if primary_goal.get('state') == 'OBSERVED' else None,
        'sourceBoundPhysicalRule': rule_evidence if rule_evidence.get('state') == 'OBSERVED' else None,
        'parsedBeatCount': len(beats),
        'sourceBoundFrameZero': hook.get('textualFirstFrameIntent', {}).get('status') == 'PASS',
    }

    evaluation_input = {
        'prompt': story,
        'sourceId': str(context.get('sourceRequestId') or 'creative-role-story'),
        'sourceVersion': str(candidate.get('candidateId') or index),
        'profile': 'post-family-v1',
        'canonicalRulesetVersion': '1.12',
        'contentProfile': str(context.get('profile') or 'ABSURD_PHYSICS'),
        'desiredDuration': duration,
        'plannedEditedDuration': duration,
        'generator': str(
            (context.get('targetConfiguration') or {}).get('selectedGenerator')
            if isinstance(context.get('targetConfiguration'), dict)
            else context.get('selectedGenerator') or 'SEEDANCE_2_5'
        ),
        'settings': {'aspectRatio': str(
            (context.get('targetConfiguration') or {}).get('aspectRatio')
            if isinstance(context.get('targetConfiguration'), dict)
            else context.get('aspectRatio') or '9:16'
        )},
        'references': [],
    }
    candidate['storyEvaluationInput'] = evaluation_input
    review = review_prompt(evaluation_input)
    candidate['postFamilyReview'] = review
    evaluation = review.get('canonicalRuleEvaluation') or {}
    candidate['canonicalStoryEvaluation'] = evaluation
    mandatory_rules = [
        'GOAL_VISIBLE_EARLY', 'MINI_STORY_LOCK', 'PROGRESSION_006',
        'PAYOFF_001', 'HOOK_004', 'CONTINUOUS_ACTION_MOMENTUM',
    ]
    if content_profile in {'ABSURD_PHYSICS', 'MIXED', 'UNKNOWN'}:
        mandatory_rules.extend([
            'GOAL_001', 'ATTEMPT_001', 'ATTEMPT_002', 'ESCALATION_005',
            'CONCEPT_007', 'CONCEPT_008', 'HOOK_002', 'INSTANT_VISUAL_ABSURDITY_GATE',
        ])
    rows = {
        row.get('ruleId'): row
        for group in ('passedRules', 'failedRules', 'unknownRules', 'notApplicableRules')
        for row in evaluation.get(group, [])
    }
    statuses = {rule_id: rows.get(rule_id, {}).get('outcome', 'NOT_EVALUATED') for rule_id in mandatory_rules}
    gate_status = (
        'FAIL' if any(status == 'FAIL' for status in statuses.values()) else
        'PASS' if all(status == 'PASS' for status in statuses.values()) else
        'UNKNOWN' if any(status in {'UNKNOWN', 'SERVICE_ERROR'} for status in statuses.values()) else
        'NOT_EVALUATED'
    )
    candidate['mandatoryStoryGate'] = {'status': gate_status, 'rules': statuses}
    candidate['storyStageStatus'] = (
        'STORY_GATES_FAIL' if gate_status == 'FAIL' else
        'STORY_GATES_NOT_EVALUATED' if gate_status != 'PASS' else
        'STORY_GATES_PASS_CREATIVE_REVIEW_PENDING'
    )
    candidate['durationAssessment'] = {
        'status': 'NOT_EVALUATED',
        'reason': 'No independent source-bound duration-value evaluator ran.',
        'parsedRuntimeSeconds': duration,
        'requestedRuntimeSeconds': target_duration,
    }
    candidate['durationReview'] = {
        'status': 'NOT_EVALUATED',
        'recommendedRuntimeSeconds': duration,
        'requestedRuntimeSeconds': target_duration,
        'assessment': candidate['durationAssessment'],
        'storyDensityEvidence': evaluation.get('storyDensityEvidence'),
        'productionFeasibility': (evaluation.get('videoPlanIR') or {}).get('producibility'),
        'generalProducibility': review.get('generalProducibility'),
        'creativeQuality': (review.get('family8') or {}).get('creativeQuality'),
        'automaticCreativePass': False,
    }
    return {'evaluation': evaluation, 'gateStatus': gate_status, 'rules': statuses}


class CreativeRoleFailure(ValueError):
    def __init__(self, detail: str, diagnostics: dict[str, Any]):
        super().__init__(detail)
        self.diagnostics = diagnostics


def _parse_role_json_response(raw_response: Any, role: str, provider: LLMProvider) -> dict[str, Any]:
    """Parse one provider JSON object while retaining its response for recovery."""
    # Preserve the exact completion before any normalization or parsing can fail.
    provider.last_raw_response = raw_response
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise ValueError(f'{ROLES[role].title()} returned an empty JSON response')
    metadata = getattr(provider, 'last_response_metadata', None) or {}
    finish_reason = metadata.get('finishReason')
    if finish_reason == 'length':
        raise ValueError(f'{ROLES[role].title()} response was truncated (finish_reason=length)')

    candidate = raw_response.strip().lstrip('\ufeff')
    # Accept a complete Markdown JSON fence, but do not guess at an object
    # embedded in arbitrary prose or repair a partial response.
    fenced = re.fullmatch(r'```(?:json)?[ \t]*\r?\n?(.*?)\r?\n?```[ \t]*', candidate,
                          flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f'Duplicate JSON key: {key}')
            value[key] = item
        return value

    try:
        value = json.loads(candidate, object_pairs_hook=unique_object)
    except json.JSONDecodeError as error:
        # DeepSeek has occasionally emitted one extra candidate-closing brace
        # immediately before the alternatives array closes. Recover only that
        # exact, provably redundant delimiter: the remaining suffix must be
        # precisely `]}`, and the corrected document must pass strict JSON
        # parsing (including duplicate-key rejection). Keep raw bytes intact.
        recoverable = (
            error.msg in {'Extra data', "Expecting ',' delimiter"}
            and error.pos < len(candidate)
            and candidate[error.pos] == '}'
            and candidate[error.pos + 1:].strip() == ']}'
            and candidate[:error.pos].rstrip().endswith('}')
        )
        if not recoverable:
            raise ValueError(f'{ROLES[role].title()} returned invalid JSON') from error
        corrected = candidate[:error.pos] + candidate[error.pos + 1:]
        try:
            value = json.loads(corrected, object_pairs_hook=unique_object)
        except (json.JSONDecodeError, ValueError) as recovery_error:
            raise ValueError(f'{ROLES[role].title()} returned invalid JSON') from recovery_error
        if not isinstance(value, dict) or not isinstance(value.get('alternatives'), list):
            raise ValueError(f'{ROLES[role].title()} response did not contain one complete alternatives object')
        provider.last_json_recovery = {
            'status': 'RECOVERED_ONE_REDUNDANT_CANDIDATE_CLOSER',
            'rawPreserved': True,
            'removedCharacterOffset': error.pos,
            'correctedDocumentStrictlyParsed': True,
        }
    except ValueError as error:
        # object_pairs_hook rejects duplicate keys with ValueError. Preserve the
        # source completion and fail closed instead of silently selecting one.
        if str(error).startswith(f'{ROLES[role].title()} returned'):
            raise
        raise ValueError(f'{ROLES[role].title()} returned invalid JSON: {error}') from error
    if not isinstance(value, dict):
        raise ValueError('Role result must be an object')
    return value


def role_readiness() -> dict[str, Any]:
    enabled = os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'false').lower() == 'true'
    return {'enabled': enabled, 'liveVerified': False,
        'storyProviders': [
            {'provider': 'DEEPSEEK', 'model': os.getenv('WORKFLOW_STORY_MODEL', ''),
             'configured': bool(os.getenv('DEEPSEEK_API_KEY') and os.getenv('WORKFLOW_STORY_MODEL'))},
            {'provider': 'OPENAI', 'model': 'gpt-6-sol', 'reasoningEffort': 'none',
             'configured': bool(os.getenv('OPENAI_API_KEY'))}], 'roles': [
        {'role': role, 'provider': provider, 'model': 'gpt-6-sol' if role == 'IDEA' else os.getenv(f'WORKFLOW_{role}_MODEL', ''),
         'configured': bool(os.getenv(f'{provider.upper()}_API_KEY') and (role == 'IDEA' or os.getenv(f'WORKFLOW_{role}_MODEL'))),
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
    el = plan.get('evidenceLimitations')
    if isinstance(el, str):
        plan['evidenceLimitations'] = [el] if el.strip() else []
    elif not isinstance(el, list):
        plan['evidenceLimitations'] = []
    else:
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
    prompt_val = value.get('prompt')
    if isinstance(prompt_val, dict):
        # OpenAI may return prompt as a structured dict with heading keys
        # (e.g. {"TITLE / FORMAT": "...", "VISUAL STYLE": "..."}).
        # Flatten it to the expected plain-text string format.
        parts = []
        for key, val in prompt_val.items():
            if isinstance(val, str):
                parts.append(f'{key}\n{val}')
            elif isinstance(val, list):
                # TIMED SHOT PLAN is a list of beat dicts; serialize as text
                beat_lines = []
                for beat in val:
                    if isinstance(beat, dict):
                        beat_parts = [f"{b.get('time', '?')}: {b.get('subject', '?')} {b.get('action', '?')} {b.get('object', '?')} {b.get('stateChange', '?')} [{b.get('framing', '?')}] {b.get('staging', '?')} -> {b.get('consequence', '?')}" for b in [beat]]
                        beat_lines.extend(beat_parts)
                    else:
                        beat_lines.append(str(beat))
                parts.append(f'{key}\n{" ".join(beat_lines)}')
            else:
                parts.append(f'{key}\n{val}')
        value['prompt'] = '\n\n'.join(parts)
    elif not isinstance(prompt_val, str) or not prompt_val.strip():
        prompt = _nested_response_value(value, ('productionPrompt', 'openArtPrompt', 'promptText', 'production_prompt', 'openart_prompt', 'prompt'))
        if isinstance(prompt, str):
            value['prompt'] = prompt
    if not isinstance(value.get('productionPlan'), dict):
        plan = _nested_response_dict(value, ('production_plan', 'productionPlan', 'plan', 'specification'))
        if plan is not None:
            value['productionPlan'] = plan
    return value


OPTIMIZATION_RESPONSE_FORMAT = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'prompt_optimization_candidates', 'strict': True,
        'schema': {
            'type': 'object', 'additionalProperties': False, 'required': ['candidates'],
            'properties': {'candidates': {
                'type': 'array', 'minItems': 2, 'maxItems': 2,
                'items': {
                    'type': 'object', 'additionalProperties': False,
                    'required': ['candidateId', 'title', 'hypothesis', 'prompt'],
                    'properties': {
                        'candidateId': {'type': 'string', 'enum': ['candidate-a', 'candidate-b']},
                        'title': {'type': 'string'}, 'hypothesis': {'type': 'string'},
                        'prompt': {'type': 'string'},
                    },
                },
            }},
        },
    },
}


def perform_role(role: str, text: str, context: dict[str, Any], provider: LLMProvider, model: str) -> dict[str, Any]:
    if role not in ROLES or not text.strip() or len(text.encode('utf-8')) > 16000:
        raise ValueError('Supported role and bounded text required')
    if any(context.get(key) for key in ('image', 'images', 'video')):
        raise ValueError('Creative roles are text-only; visual evidence was not supplied')
    if role == 'PROMPT_OPTIMIZATION' and context.get('optimizationGenerationContractVersion') == 'creative-reconstruction-v2':
        from .creative_reconstruction import perform_reconstruction
        return perform_reconstruction(text, context, provider, model)
    if role == 'PROMPT_OPTIMIZATION' and context.get('optimizationGenerationContractVersion') == 'plan-first-v1':
        from .optimization_plans import perform_plan_first
        return perform_plan_first(text, context, provider, model)
    system = {
        'IDEA': 'Invent ONE original Pompom Hills IDEA, not a timecoded story. Return ONLY JSON with title, concept, firstStaticFrame, viewerQuestion, discovery, payoff and productionRisk strings. One canonical main character from context.characterRecord. Use a concrete visual question, everyday motivation, a meaning-changing discovery and visible payoff. Warm lived-in 3D cartoon environment appropriate to the premise; preserve outdoor or indoor intent. No white void or generic studio. No automatic PASS or production approval.',
        'STORY_REVIEW': '''Review every supplied story candidate together. Return ONLY one JSON object matching this exact STORY_REVIEW contract; never omit a key and never return markdown. Required top-level keys: reviewId, sourceRequestId, sourceFingerprint, reviewModel, reviewModelVersion, reviewPolicyVersion, reviewTimestamp, reviewStatus, diversityAssessment, comparativeFindings, candidateReviews, recommendedCandidateId, recommendationReason, overallConcerns, usageAndCost, evidenceLimitations, revisionComparison. Set sourceRequestId and sourceFingerprint exactly to the values supplied in context (they may be null); the saved record timestamp is authoritative, so do not use a fixture date. reviewStatus must be COMPLETED, PARTIAL, SERVICE_ERROR, or INSUFFICIENT_EVIDENCE. candidateReviews must contain exactly one object for each supplied candidate, each with its exact candidateId. Assess concept coherence, opening visual promise, causal consistency, event progression, originality against siblings and context.establishedWinnerMechanisms, curiosity/rewatch, generator difficulty, source constraints, ending/payoff, and material differences. For originality, compare causal visual mechanisms, not object names alone; cite exact candidate evidence and identify the nearest known mechanism. Winner labels are text context, not verified visual-similarity evidence. For every material finding include dimension, finding, supportingTextEvidence, severity, confidenceOrEvidenceStatus and suggestedMinimalImprovement. Use concise structured findings and do not invent candidates. recommendedCandidateId must be one supplied candidateId or null; if no evidence supports a preference, return null and explain that. Use arrays/objects for the remaining evidence fields even when empty. Compare actual mechanisms and event progressions rather than wording, preserve source fidelity, mark uncertainty honestly, and never grant render authorization.''',
        'PROMPT_OPTIMIZATION': '''Return ONLY JSON with exactly {"candidates":[{"candidateId":"candidate-a","title":"...","hypothesis":"...","prompt":"complete prompt text"},{"candidateId":"candidate-b","title":"...","hypothesis":"...","prompt":"complete prompt text"}]}. Produce exactly two complete prompt revisions, both materially different from the original and from each other; never return the original prompt unchanged or duplicate one candidate. Candidate A must focus on first-frame visual clarity, immediate physical anomaly visibility and opening-second curiosity; its TIMED SHOT PLAN must change first-beat framing or camera focus to make the existing anomaly legible in the opening two seconds, without moving a story event earlier. Candidate B must focus on beat progression clarity, escalation pacing and execution feasibility for Seedance; its TIMED SHOT PLAN must rebalance the timing or camera decisions of the existing mid-section beats for readable escalation. Preserve every source event and its order. An existing explicit multiplication progression may be divided into contiguous camera shots only when each shot repeats the exact source action, staging and consequence and the concatenated progression edges equal the complete original chain. Never invent, omit or reorder progression steps; other beat rewrites are unsupported. The first timed beat framing/camera decision in Candidate A must differ materially from Candidate B; the protected narrative action stays unchanged. The hypothesis field for each candidate must name a concrete structural change that is actually implemented in the prompt body. Use explicit camera terms: extreme close-up, close-up, medium shot or wide shot; camera motion may be static/locked-off, pan, tracking or push-in. Implement camera/framing instructions in square brackets inside the relevant timed beats, or rebalance adjacent beat boundaries while preserving total duration and event order. Use context.baselineExecution to compare actual baseline decisions. Do not propose the same existing shot or merely move its bracket to the start of the beat. Synonyms, titles, hypotheses and appended commentary alone are not material changes. Preserve narrative text outside camera annotations and protected identity/mechanic/ending sections. Use source-supported subjects; camera proposals are hypotheses, not verified observations. Preserve the source character, physical rule, primary goal, every essential event and the exact ending. Every `essentialEvents` phrase supplied in context must remain verbatim and unchanged in both prompts. Do not add narrative outcomes, characters, objects, or mechanics. Keep the selected context.targetConfiguration profile, generator, duration and aspect ratio. If the baseline contains a stale production-settings label, replace only that label with the selected target value; this does not permit a story change. Keep the approved story unchanged. Do not assert image/video observation, audience retention, rewatch success, or renderability. Treat first-frame, pacing, and execution claims as hypotheses. Do not recommend, rank or auto-select either candidate; never grant render authorization.''',
        'STORY': '''Return ONLY one root JSON object with an `alternatives` array. For standard short-form candidates, each alternative contains candidateId, title, protagonistCharacterId and text. For a 20–30 second request, the LONG-FORM STORY CONTRACT below replaces the short-form candidate requirements; it does not require a nested storyPlan. Return exactly the number of alternatives requested in context.requestedAlternativeCount (between 1 and 3); do not add root keys. Each candidate must include a non-empty candidateId, title and text string. When context.characterRecord and context.canonicalCharacterRegistry are supplied, protagonistCharacterId MUST exactly equal context.characterRecord.id and the story must use context.characterRecord.name as its protagonist; do not substitute, rename, or introduce an unregistered named character. Registry validation is independent from source-fidelity review and does not prove visual identity or source fidelity. When returning multiple alternatives, each must have a meaningfully different narrative body — do not reuse the same story text with only a different title. Vary at least one of: action/progression strategy, how the central physical rule causes consequences, escalation structure, visual discovery, or permitted payoff. The user supplied input in mode context.inputMode (IDEA = short concept, DETAILED_STORY = complete narrative). Respect context.storyGenerationMode: for EXPLORE_DIFFERENT_STORIES generate meaningfully different narrative directions from the supplied idea; for IMPROVE_EXISTING_STORY refine the supplied narrative while preserving only the explicitly locked requirements listed in context.lockedRequirements. The locked requirements are: PRESERVE_CORE_PREMISE (keep the central concept), PRESERVE_KEY_EVENTS (keep the major events in order), PRESERVE_ENDING (keep the final outcome). Only the requirements present in context.lockedRequirements are binding; do not silently lock requirements that are absent. Preserve supplied characters and intent. Do not return markdown, reasoning, commentary or production authorization.''',
        'BUILD_PROMPT': '''Return ONLY JSON with exactly two top-level keys: `prompt` and `productionPlan`. Convert the approved story into a concrete, concise OpenArt video prompt: visible actions, object states, continuity, staging, selected aspect ratio/duration, and ending. Do not rewrite its premise. Preserve the exact character, central mechanism, essential progression, protected events, constraints and ending. Do not silently omit an essential event; mark uncertainty or material deviation in evidence instead. Use manageable actions, few cuts, uncluttered staging, and no invented reference claims. Use the selected content profile's objective; comedy is relevant only when the source/profile supports it. Separate source-confirmed facts from AI-derived execution suggestions. Prompt headings, each separated by a blank line: TITLE / FORMAT, VISUAL STYLE, CHARACTER / CONTINUITY, TIMED SHOT PLAN, AUDIO, NEGATIVE CONSTRAINTS, FINAL CUT. Make the timed plan cover the full selected duration with ordered, non-overlapping ranges; choose meaningful events from the source, not an arbitrary fixed beat count. Each plan beat must contain time, subject, action, object, stateChange, framing, staging, consequence; time, framing, action, staging and consequence are REQUIRED non-empty JSON strings; additionally supply sourceEvidence (an exact verbatim quote from approved source or empty string), evidenceStatus, sourceRelationship (FAITHFUL_ADAPTATION, CLARIFICATION, OPTIONAL_EXECUTION_INTERPRETATION, MATERIAL_CREATIVE_DEVIATION, UNKNOWN), and importance (CORE, FLEXIBLE, POLISH, UNKNOWN). Never fabricate quotes. `visualExecution` must include openingState, beats, mechanism, continuity, endingState. `productionPlan` keys: sourceIdentity, creativeObjective, characterBindings, visualExecution, productionConstraints, intentClassification, evidenceLimitations, generatorRisks, referencePlan. If Mimi is selected, honor the supplied anthropomorphic-bunny identity requirement; do not invent unverified appearance details and state whether approved references are actually bound. Assess the first two seconds as planned text only using visible promise → immediate consequence/reveal → reason to continue; distinguish mystery from ordinary setup. Do not claim first-frame image evidence. Identify causal ambiguity without rewriting the premise. Risks need a cited source event, affected beat, confidence, smallest mitigation and next action; they are advisory unless evidence establishes a true blocker. Do not claim unverified generator behavior. Do not add provider commentary, approval language or render authorization.''',
        'MINIMAL_REPAIR': 'Return JSON patches: at most three minimal edits with integer Unicode code point start/end, exact sourceQuote and replacement. Preserve protected intent and ESSENTIAL source quotes. Never return approval or rewrite the entire prompt.',
    }[role]
    requested_duration = context.get('targetDuration')
    if requested_duration is None and isinstance(context.get('targetConfiguration'), dict):
        requested_duration = context['targetConfiguration'].get('duration')
    if role == 'STORY' and isinstance(requested_duration, (int, float)) and 20 <= requested_duration <= 30:
        system += _LONG_FORM_STORY_CONTRACT
        target_configuration = context.get('targetConfiguration') if isinstance(context.get('targetConfiguration'), dict) else {}
        profile = str(target_configuration.get('contentProfile') or context.get('profile') or 'UNKNOWN').upper()
        system += f' EFFECTIVE CREATIVE PROFILE: {profile}. This profile is supplied by the application and governs the story engine; do not default to ABSURD_PHYSICS.'
    safe_context = {key: context[key] for key in ('protectedIntent', 'intentRequirements', 'findings', 'retrievedLessons', 'constraints', 'inputMode', 'storyGenerationMode', 'lockedRequirements', 'permittedVariation', 'roundNumber', 'objective', 'bestCandidate', 'previousAssessment', 'acceptedChanges', 'rejectedCandidates', 'establishedWinnerMechanisms', 'sourceStoryRecordId', 'mainCharacter', 'mainCharacterId', 'character', 'characterRecord', 'canonicalCharacterRegistry', 'characterReferences', 'referenceBindings', 'preferences', 'profile', 'candidates', 'candidateIds', 'requestedAlternativeCount', 'sourceRequestId', 'sourceFingerprint', 'previousReview', 'currentRevision', 'previousRevision', 'targetDuration', 'aspectRatio', 'reviewPolicyVersion', 'selectedGenerator', 'generatorCapabilities', 'targetConfiguration', 'storyTitle', 'promptBuilderContractVersion', 'essentialEvents', 'approvedStoryText', 'optimizationGenerationContractVersion', 'baselineExecution', 'analysisRunId', 'promptVersionId', 'contentId', 'canonicalStoryFeasibilityContext', 'visualDirection') if key in context}
    if context.get('storyExperiment'):
        from .story_experiment import contract, SCHEMA
        experiment = contract(text, context)
        safe_context['storyExperiment'] = experiment
        if role == 'STORY':
            system += (' Strict experiment: return exactly two distinct complete alternative objects. Each requires candidateId, title, text, '
                       'schemaVersion="'+SCHEMA+'", durationSeconds=15, openingVisualState, motivation, progression, ending '
                       '(these four must be exact excerpts of text), proposedChanges, weaknesses, productionRisks (nonempty string arrays), '
                       'sourceContract={status:"SOURCE_COMPLIANT" or "PROTECTED_CHANGE_PROPOSAL" or "UNKNOWN", '
                       'bindings:[{anchorId,sourceQuote,candidateQuote}],protectedChanges:[]}. '
                       'Every protectedAnchors quote must remain an affirmative unchanged fact in the narrative and have its exact source '
                       'and candidate excerpt mapped once. These limited locked facts do not freeze unprotected wording or progression. '
                       'Do not just append source quotations to an unrelated story. If a protected fact must change, explicitly list '
                       '{anchorId,proposedChange,justification} in protectedChanges and use PROTECTED_CHANGE_PROPOSAL; it will not be '
                       'sent for this pilot review. Missing protected evidence is UNKNOWN. Do not claim semantic verification. '
                       'Prefer two genuinely different causal/visual approaches with natural timing, not two camera variants.')
            system += (' Evidence contract v2: write each complete narrative first, then copy exact contiguous substrings '
                       'from that same narrative into openingVisualState, motivation, progression and ending. '
                       'Do not summarize or combine separated sentences in these four evidence fields. '
                       'If motivation needs a stated goal, include that goal in the narrative itself before citing it. '
                       'For EVERY protected anchor use its supplied id unchanged, copy sourceQuote exactly from the anchor, '
                       'and copy candidateQuote exactly from your candidate text. This pilot requires the short protected '
                       'clauses themselves verbatim within natural affirmative sentences; pronoun substitutions or semantic '
                       'paraphrases are not established by this deterministic gate and remain UNKNOWN. '
                       'Only these protected clauses are text-locked: all other narrative wording, actions, staging and '
                       'progression may be revised when consistent with them. Do not add new multiplication triggers or '
                       'independent mechanics; a stated rule plus contradictory events is not compliance. '
                       'If preserving a lock prevents the intended creative change, declare PROTECTED_CHANGE_PROPOSAL '
                       'with anchorId, proposedChange and justification, rather than claiming SOURCE_COMPLIANT. '
                       'Metadata never overrides the narrative. Bindings may optionally include candidateStart/candidateEnd '
                       'and sourceStart/sourceEnd as exact Unicode code-point offsets; if supplied they must match. '
                       'Self-check both distinct complete narratives and every excerpt without adding explanatory prose. '
                       'A matching excerpt proves a bounded textual mapping, never independent semantic or visual fidelity.')
        elif role == 'STORY_REVIEW':
            safe_context['candidates'] = [{key: c[key] for key in ('candidateId', 'title', 'text') if key in c}
                                          for c in context.get('candidates', [])]
            system += (' Independently compare both complete narratives to the original, not generator self-assessment metadata. '
                       'Would either be meaningfully better for a viewer, or merely more technically compliant? '
                       'If no material creative improvement is supported return recommendedCandidateId=null and '
                       'recommendationReason="NO_CREATIVE_WINNER". Never choose the least bad by default. '
                       'Check protected facts, first-two-second promise, pacing, repetition, artificial checklist density and production risks. '
                       'Unknown semantic or visual support must remain UNKNOWN; no creative grade or owner approval is granted.')
    story_feasibility = context.get('canonicalStoryFeasibilityContext')
    if isinstance(story_feasibility, dict):
        # The saved context retains the complete canonical evidence. Transport
        # each finding once instead of duplicating nested IR/row details in
        # both the ceiling audit and canonical findings (24k role envelope).
        wire_feasibility = deepcopy(story_feasibility)
        if isinstance(wire_feasibility.get('targetAwarePreflight'), dict):
            wire_feasibility['targetAwarePreflight'] = {
                key: value for key, value in wire_feasibility['targetAwarePreflight'].items()
                if key not in {'losses', 'missingEvidence'}
            }
        wire_feasibility['canonicalFindings'] = [
            {key: value for key, value in row.items() if key != 'details'}
            for row in wire_feasibility.get('canonicalFindings', [])
        ]
        wire_feasibility['evidenceProjection'] = 'COMPACT_FINDINGS; contextSha256 binds the complete saved source context'
        safe_context['canonicalStoryFeasibilityContext'] = wire_feasibility
        if story_feasibility.get('version') != 'canonical-story-feasibility-context-v1' or story_feasibility.get('rulesetVersion') not in {'1.11', '1.12'}:
            raise ValueError('Unsupported canonical story feasibility context')
        if role == 'STORY':
            system += (' Design observable narrative events that can later be expressed as source-bound production beats under Ruleset 1.12. '
                       'The objective is a genuinely coherent story, not a manufactured numeric score. For short ABSURD_PHYSICS work, '
                       'use distinct character problem-solving strategies only when they naturally advance the same central mechanic; '
                       'pulling harder, repeating a pull, relabeling an action, or changing the camera are not distinct story strategies. '
                       'Make active involvement, causal consequences, progression, and a realization/reversal/payoff explicit in the story text. '
                       'Opening clarity, curiosity, suspense, discovery, and non-comedic payoffs are all valid. Never claim visual or audience evidence. '
                       'Protected source changes remain proposals requiring owner approval; preserve the supplied character, core premise, physical rule, and ending.')
            system += (' Improve the actual viewer-visible story, not hand positions or a rule checklist. Consider Instant Impossible, '
                       'Immediate Problem and Curiosity/Discovery openings without requiring impossible physics in every concept. '
                       'Seek distinct visible consequences, natural pacing, active character decisions and a causally earned payoff. '
                       'Allow enough time for major events; do not pack realization, mirror reaction, scatter and resolution into the final seconds. '
                       'Prefer clear silhouettes and direct interactions; identify thin-object/count/face continuity uncertainty rather than promising render success. '
                       'Character identity and the existing physical rule are locked when PRESERVE_CHARACTER_IDENTITY or PRESERVE_PHYSICAL_RULE is supplied. '
                       'Unlocked events may be proposed for revision, but no revision is applied until explicit owner approval.')
        elif role == 'STORY_REVIEW':
            system += (' Also return two separate required top-level objects: creativeQualityAssessment and structuralFeasibilityAssessment. '
                       'Each contains candidateAssessments with exactly one entry per candidate. Creative entries require candidateId, status '
                       '(CREATIVELY_STRONG, CREATIVELY_WEAK, or UNKNOWN), reason, strengths, and risks. Structural entries require candidateId, '
                       'status (STRUCTURALLY_PROMISING, STRUCTURALLY_BLOCKED, or UNKNOWN), ruleAssessments, remainingBlockers, and visualEvidenceUnknowns. '
                       'ruleAssessments must cover ATTEMPT_001, ATTEMPT_002, CHAR_002, REPETITION_004, and MINI_STORY_LOCK; every row requires ruleId, '
                       'storyEvidenceExcerpt, status (SUPPORTED, RISK, NOT_SUPPORTED, or UNKNOWN), reason, necessaryImprovement, and changesProtectedSource. '
                       'Any non-empty storyEvidenceExcerpt must be an exact quote from that candidate. This is a text-only prediction, never canonical '
                       'PASS, a score, or proof of rendering. Recommend only a CREATIVELY_STRONG and STRUCTURALLY_PROMISING candidate whose required '
                       'rows contain no NOT_SUPPORTED or UNKNOWN status; otherwise recommendedCandidateId must be null.')
            system += (' Independently assess all six dimensions: SCROLL_STOP_VISUAL_PROMISE, CAUSAL_PROGRESSION, VISUAL_STORYTELLING, '
                       'PRODUCTION_EXECUTABILITY, ENDING_REPLAY and DISTINCTIVE_CREATIVE_VALUE. Include one materialFindings entry per '
                       'dimension in each candidateReviews item, using the existing dimension/finding/supportingTextEvidence/severity/'
                       'confidenceOrEvidenceStatus/suggestedMinimalImprovement fields. Quote the exact candidate text or explicitly mark missing '
                       'evidence UNKNOWN. Compare against the complete original story: natural pacing, visual originality, consequence variety, '
                       'causal clarity, active character role, generator feasibility and artificial rule-optimization risk. Identify weaknesses '
                       'even when recommending a candidate. CREATIVELY_STRONG alone is insufficient. No audience-performance prediction or '
                       'creative A/A+ grade is verified by this text-only MACHINE_REVIEW. Proposed story changes still await owner approval.')
    if role == 'PROMPT_OPTIMIZATION':
        from .optimization_distinctness import baseline_execution
        from .optimization_profile_contract import generation_contract
        safe_context['baselineExecution'] = baseline_execution(text)
        # JSON mode guarantees syntax only. Enforce two flat candidate objects
        # at generation; keep all semantic and source checks below unchanged.
        provider.response_format = deepcopy(OPTIMIZATION_RESPONSE_FORMAT)
        ownership = generation_contract(text, context)
        if ownership:
            items = provider.response_format['json_schema']['schema']['properties']['candidates']['items']
            items['properties']['targetContentProfile'] = {'type': 'string', 'enum': [ownership['targetContentProfile']]}
            items['required'].append('targetContentProfile')
        system += (' Framing adjectives or renamed time boundaries alone are minor variations, not material approval evidence. '
                   'Propose a concrete camera motion/static discipline or a coherent combination of framing and timing changes, '
                   'with source-supported action and consequences unchanged. Explain the causal-readability or temporal-complexity '
                   'hypothesis without claiming tested improvement. ')
        system += (' The server owns the effective targetContentProfile in the profileOwnership contract. '
                   'baselinePromptHistoricalProfile and labels inside baselinePromptText are historical only. '
                   'Preserve the approved narrative, not obsolete production metadata. Return targetContentProfile '
                   'as the supplied server value and use it in the PRODUCTION SETTINGS section of both complete prompts. '
                   'Do not copy historical AUTO labels into effective candidate plans. Keep every narrative/staging/consequence '
                   'sentence unchanged outside camera brackets; change execution, not source coverage.')
    if role == 'BUILD_PROMPT':
        safe_context['generatorCapabilities'] = _configured_generator_capabilities(context)
    provider.last_request_started = True
    payload = {'text': text, 'context': safe_context}
    if role == 'PROMPT_OPTIMIZATION':
        payload = {'baselinePromptText': text, 'context': safe_context}
        if ownership:
            payload['profileOwnership'] = {key: value for key, value in ownership.items() if key != 'baselinePromptText'}
    wire_payload = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                    if context.get('storyExperiment') else json.dumps(payload, ensure_ascii=False))
    raw_response = provider.complete(wire_payload, system=system, temperature=0)
    value = _parse_role_json_response(raw_response, role, provider)
    if role == 'PROMPT_OPTIMIZATION':
        provider.last_role_result = deepcopy(value)
    if role == 'IDEA':
        if any(not isinstance(value.get(k), str) or not value[k].strip() for k in ('title','concept','firstStaticFrame','viewerQuestion','discovery','payoff','productionRisk')):
            raise ValueError('IDEA response requires a complete concept and static opening')
    elif role == 'STORY_REVIEW':
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
        if isinstance(story_feasibility, dict):
            required_rules = {'ATTEMPT_001', 'ATTEMPT_002', 'CHAR_002', 'REPETITION_004', 'MINI_STORY_LOCK'}
            creative = value.get('creativeQualityAssessment')
            structural = value.get('structuralFeasibilityAssessment')
            if not isinstance(creative, dict) or not isinstance(structural, dict):
                raise ValueError('Canonical-aware STORY_REVIEW requires separate creative and structural assessments')
            creative_rows = creative.get('candidateAssessments')
            structural_rows = structural.get('candidateAssessments')
            for label, assessment_rows in (('creative', creative_rows), ('structural', structural_rows)):
                if not isinstance(assessment_rows, list) or len(assessment_rows) != len(candidate_ids):
                    raise ValueError(f'Canonical-aware STORY_REVIEW {label} assessment must cover every candidate')
                if {str(item.get('candidateId')) for item in assessment_rows if isinstance(item, dict)} != set(candidate_ids):
                    raise ValueError(f'Canonical-aware STORY_REVIEW {label} candidate IDs do not match')
            creative_by_id = {str(item['candidateId']): item for item in creative_rows}
            structural_by_id = {str(item['candidateId']): item for item in structural_rows}
            candidate_by_id = {str(item['candidateId']): item for item in candidates}
            for cid in candidate_ids:
                if creative_by_id[cid].get('status') not in {'CREATIVELY_STRONG', 'CREATIVELY_WEAK', 'UNKNOWN'}:
                    raise ValueError('Unsupported creative story assessment status')
                row = structural_by_id[cid]
                if row.get('status') not in {'STRUCTURALLY_PROMISING', 'STRUCTURALLY_BLOCKED', 'UNKNOWN'}:
                    raise ValueError('Unsupported structural story assessment status')
                rule_rows = row.get('ruleAssessments')
                if not isinstance(rule_rows, list) or not {str(item.get('ruleId')) for item in rule_rows if isinstance(item, dict)}.issuperset(required_rules):
                    raise ValueError('Structural feasibility assessment must cover every required rule')
                candidate_text = str(candidate_by_id[cid].get('text', ''))
                if story_feasibility.get('creativeReviewVersion') == 'creative-story-merit-v1':
                    from .creative_reconstruction import DIMENSIONS
                    reviewed = next(item for item in reviews if str(item['candidateId']) == cid)
                    findings = reviewed.get('materialFindings', [])
                    if not isinstance(findings, list) or {item.get('dimension') for item in findings if isinstance(item, dict)} != set(DIMENSIONS):
                        raise ValueError('Creative story review requires evidence for all six CPQ dimensions')
                    for finding in findings:
                        excerpt = finding.get('supportingTextEvidence')
                        unknown = finding.get('confidenceOrEvidenceStatus') == 'UNKNOWN'
                        if not finding.get('finding') or not finding.get('severity') or not finding.get('confidenceOrEvidenceStatus'):
                            raise ValueError('Creative story finding is incomplete')
                        if not unknown and (not isinstance(excerpt, str) or not excerpt or excerpt not in candidate_text):
                            raise ValueError('Creative story evidence must quote the exact candidate or remain UNKNOWN')
                for rule in rule_rows:
                    if rule.get('status') not in {'SUPPORTED', 'RISK', 'NOT_SUPPORTED', 'UNKNOWN'} or not isinstance(rule.get('changesProtectedSource'), bool):
                        raise ValueError('Invalid structural rule feasibility row')
                    if any(key not in rule for key in ('storyEvidenceExcerpt', 'reason', 'necessaryImprovement')):
                        raise ValueError('Incomplete structural rule feasibility row')
                    excerpt = str(rule.get('storyEvidenceExcerpt', ''))
                    if excerpt and excerpt not in candidate_text:
                        raise ValueError('Structural feasibility evidence must quote the exact candidate story')
            recommendation = value.get('recommendedCandidateId')
            if recommendation is not None:
                selected_creative = creative_by_id[str(recommendation)]
                selected_structural = structural_by_id[str(recommendation)]
                blocked = any(item.get('status') in {'NOT_SUPPORTED', 'UNKNOWN'}
                              for item in selected_structural['ruleAssessments']
                              if item.get('ruleId') in required_rules)
                if selected_creative.get('status') != 'CREATIVELY_STRONG' or selected_structural.get('status') != 'STRUCTURALLY_PROMISING' or blocked:
                    raise ValueError('STORY_REVIEW cannot recommend a structurally ineligible candidate')
        # STORY_REVIEW used to choose among candidates using only the review
        # model's verdict and structural rows. Run the same local canonical
        # story rules before any candidate recommendation; a model judgment
        # cannot turn a failed or unevaluated mandatory gate into PASS.
        from .review import _run_canonical_evaluation
        mandatory_story_rules = (
            'GOAL_001', 'MINI_STORY_LOCK', 'GOAL_VISIBLE_EARLY', 'CONCEPT_007',
            'CONCEPT_008', 'PROGRESSION_006', 'ESCALATION_005', 'PAYOFF_001',
        )
        story_gate_rows = []
        for candidate in candidates:
            candidate_id = str(candidate.get('candidateId'))
            evaluation = _run_canonical_evaluation({
                'prompt': str(candidate.get('text') or ''),
                'canonicalRulesetVersion': '1.12',
                'contentProfile': str(context.get('contentProfile') or 'ABSURD_PHYSICS'),
            })
            rows = {
                row.get('ruleId'): row
                for group in ('passedRules', 'failedRules', 'unknownRules', 'notApplicableRules')
                for row in evaluation.get(group, [])
            }
            selected_rows = {rule: rows.get(rule) for rule in mandatory_story_rules}
            if any(row and row.get('outcome') == 'FAIL' for row in selected_rows.values()):
                gate_status = 'FAIL'
            elif all(row and row.get('outcome') == 'PASS' for row in selected_rows.values()):
                gate_status = 'PASS'
            else:
                gate_status = 'NOT_EVALUATED'
            story_gate_rows.append({
                'candidateId': candidate_id,
                'status': gate_status,
                'rules': {
                    rule: (row.get('outcome') if row else 'NOT_EVALUATED')
                    for rule, row in selected_rows.items()
                },
            })
        value['mandatoryStoryGate'] = story_gate_rows
        recommendation = value.get('recommendedCandidateId')
        if recommendation is not None:
            selected_gate = next((row for row in story_gate_rows if row['candidateId'] == str(recommendation)), None)
            if not selected_gate or selected_gate['status'] != 'PASS':
                value['recommendedCandidateId'] = None
                value['recommendationReason'] = (
                    'No candidate can advance: the existing mandatory story rules failed or were not evaluated.'
                )
                concerns = value.get('overallConcerns')
                if isinstance(concerns, list):
                    concerns.append('A story-review recommendation cannot override a failed or NOT_EVALUATED mandatory story gate.')
    elif role == 'STORY':
        alternatives = value.get('alternatives')
        if isinstance(alternatives, list) and len(alternatives) > 3:
            # The provider may overproduce despite the bounded request. Keep
            # the first three candidates, which is the product contract.
            alternatives = alternatives[:3]
            value['alternatives'] = alternatives
        if not isinstance(alternatives, list) or not 1 <= len(alternatives) <= 3:
            raise ValueError('One to three bounded story alternatives required')
        if isinstance(requested_duration, (int, float)) and 20 <= requested_duration <= 30:
            requested_count = context.get('requestedAlternativeCount')
            if requested_count is not None and len(alternatives) != requested_count:
                raise ValueError(f'Long-form STORY returned {len(alternatives)} alternatives; exactly {requested_count} were requested')
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
        if isinstance(requested_duration, (int, float)) and 20 <= requested_duration <= 30:
            for index, candidate in enumerate(alternatives, start=1):
                if not isinstance(candidate, dict):
                    raise ValueError('Long-form STORY candidates must be structured objects')
                _evaluate_long_form_story_text(candidate, context, float(requested_duration), index)
        if context.get('characterRecord') is not None:
            value['canonicalIdentityValidation'] = _validate_canonical_story_identity(alternatives, context)
        value['storyQuality'] = analyse_story_candidates(alternatives, context)
        if isinstance(requested_duration, (int, float)) and 20 <= requested_duration <= 30:
            _bind_story_quality_goal_result(value['storyQuality'], alternatives)
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
        for beat_index, beat in enumerate(beats, start=1):
            required_beat = ('time', 'framing', 'action', 'staging', 'consequence')
            if not isinstance(beat, dict) or any(not isinstance(beat.get(key), str) or not beat[key].strip() for key in required_beat):
                invalid_fields=[key for key in required_beat if not isinstance(beat,dict) or not isinstance(beat.get(key),str) or not beat[key].strip()]
                raise ValueError(f'Beat {beat_index} requires non-empty string fields: {", ".join(invalid_fields)}')
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
    elif role == 'PROMPT_OPTIMIZATION':
        candidates = value.get('candidates')
        if not isinstance(candidates, list) or len(candidates) != 2:
            count = len(candidates) if isinstance(candidates, list) else 'missing/non-array'
            nested = any(isinstance(item, dict) and 'candidate-b' in item for item in candidates) if isinstance(candidates, list) else False
            raise ValueError(f'Exactly two prompt optimization candidates are required; received {count}'
                             + ('; candidate-b was nested inside another candidate instead of a separate array item' if nested else ''))
        ids = [item.get('candidateId') for item in candidates if isinstance(item, dict)]
        if ids != ['candidate-a', 'candidate-b']:
            raise ValueError('Prompt optimization candidate IDs must be candidate-a and candidate-b')
        if any(item.get('prompt') == text for item in candidates):
            raise ValueError('Candidate prompt exactly matches the source; a revised prompt is required')
        if candidates[0].get('prompt') == candidates[1].get('prompt'):
            raise ValueError('Candidate prompt duplicates candidate-a; two distinct revisions are required')
        from .optimization_profile_contract import normalize_candidate_profiles
        # Preserve the original provider result above, then map only metadata.
        if all(isinstance(item.get('prompt'), str) and item['prompt'].strip() for item in candidates):
            normalize_candidate_profiles(text, candidates, context)
            provider.last_normalized_role_result = deepcopy(value)
        prompts: list[str] = []
        essential = context.get('essentialEvents')
        if not isinstance(essential, list) or not essential or any(
            not isinstance(item, str) or not item.strip() or item not in text for item in essential
        ):
            raise ValueError('Source-supported essential event anchors are required')
        for candidate in candidates:
            if (
                not isinstance(candidate.get('title'), str)
                or not candidate['title'].strip()
                or not isinstance(candidate.get('hypothesis'), str)
                or not candidate['hypothesis'].strip()
                or not isinstance(candidate.get('prompt'), str)
                or not candidate['prompt'].strip()
                or len(candidate['prompt']) > 16000
            ):
                raise ValueError('Each prompt optimization candidate must be complete and bounded')
            candidate['prompt'] = candidate['prompt'].strip()
            if candidate['prompt'] == text:
                raise ValueError(f"Candidate {candidate['candidateId']} prompt exactly matches the source; a revised prompt is required")
            if candidate['prompt'] in prompts:
                raise ValueError(f"Candidate {candidate['candidateId']} prompt duplicates candidate-a; two distinct revisions are required")
            if any(anchor not in candidate['prompt'] for anchor in essential):
                raise ValueError('Candidate omits an essential source event; candidate rejected')
            prompts.append(candidate['prompt'])
        if len({str(item['hypothesis']).strip().casefold() for item in candidates}) != 2:
            raise ValueError('Each candidate requires a distinct optimization hypothesis')
        from .optimization_distinctness import validate_execution_candidates
        validate_execution_candidates(text,candidates,context)
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
            **({'rawProviderResult': deepcopy(provider.last_role_result), 'rawProviderResponse': raw_response}
               if role == 'PROMPT_OPTIMIZATION' else {}),
            'usage': getattr(provider, 'last_usage', None),
            'providerResponseMetadata': response_metadata}


def _optimization_cost(usage: Any, input_rate: float, output_rate: float) -> float:
    if not isinstance(usage, dict):
        raise ValueError('Provider response omitted verifiable token usage; actual cost cannot be checked against the authorized ceiling')
    input_tokens = usage.get('prompt_tokens', usage.get('input_tokens'))
    output_tokens = usage.get('completion_tokens', usage.get('output_tokens'))
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in (input_tokens, output_tokens)):
        raise ValueError('Provider response contained invalid token usage; actual cost cannot be checked against the authorized ceiling')
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def _verified_optimization_cost(usage: Any, input_rate: float, output_rate: float, max_cost_usd: float) -> float:
    actual_cost = _optimization_cost(usage, input_rate, output_rate)
    if actual_cost > max_cost_usd:
        raise ValueError('Actual provider cost exceeded the authorized cost ceiling; candidate response rejected')
    return actual_cost


def _safe_usage_summary(usage: Any) -> dict[str, int] | None:
    if not isinstance(usage, dict):
        return None
    input_tokens = usage.get('prompt_tokens', usage.get('input_tokens'))
    output_tokens = usage.get('completion_tokens', usage.get('output_tokens'))
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
           for value in (input_tokens, output_tokens)):
        return None
    return {'inputTokens': input_tokens, 'outputTokens': output_tokens}


def _provider_failure_category(error: Exception) -> str:
    name = type(error).__name__.lower()
    if 'authentication' in name or 'permission' in name:
        return 'PROVIDER_AUTHENTICATION_ERROR'
    if 'ratelimit' in name or 'rate_limit' in name:
        return 'PROVIDER_RATE_LIMIT'
    if 'timeout' in name:
        return 'PROVIDER_TIMEOUT'
    if 'connection' in name:
        return 'PROVIDER_CONNECTION_ERROR'
    return 'PROVIDER_OUTCOME_UNKNOWN'


def _optimization_validation_category(error: Exception) -> str:
    detail = str(error).lower()
    if 'returned invalid json' in detail or 'empty json response' in detail:
        return 'PROVIDER_RESPONSE_SCHEMA_ERROR'
    if 'essential source event' in detail or 'source-supported essential event' in detail:
        return 'STORY_FIDELITY_VALIDATION_FAILED'
    if 'source-plan' in detail: return 'SOURCE_PLAN_VALIDATION_FAILED'
    if 'approved source narrative' in detail or 'story fidelity' in detail: return 'STORY_FIDELITY_VALIDATION_FAILED'
    if 'distinct' in detail or 'duplicates candidate' in detail or 'matches the source' in detail:
        return 'CANDIDATE_STRUCTURE_INVALID'
    return 'CANDIDATE_STRUCTURE_INVALID'


def _provider_failure_detail(error: Exception) -> str:
    category = _provider_failure_category(error)
    return {
        'PROVIDER_AUTHENTICATION_ERROR': 'OpenAI rejected provider authentication; verify server credentials before another authorized attempt.',
        'PROVIDER_RATE_LIMIT': 'OpenAI rate-limited the request; review the saved attempt before explicitly authorizing another call.',
        'PROVIDER_TIMEOUT': 'The OpenAI request timed out; its outcome is unresolved and must not be retried automatically.',
        'PROVIDER_CONNECTION_ERROR': 'The OpenAI connection failed; provider dispatch outcome may be uncertain and must not be retried automatically.',
        'PROVIDER_OUTCOME_UNKNOWN': 'The provider request outcome is unknown; do not retry automatically.',
    }[category]


def _isolated_fixture_role(role: str, text: str, context: dict[str, Any], max_cost_usd: float) -> dict[str, Any]:
    """Return a complete role response from an isolated, no-egress fixture.

    This boundary intentionally preserves the normal role parser below it: the
    fixture is only transport, while schema, source and evaluator validation
    remain application code. A missing/invalid fixture fails closed.
    """
    import hashlib
    if not isinstance(max_cost_usd, (int, float)) or not math.isfinite(max_cost_usd) or max_cost_usd <= 0 or max_cost_usd > 20:
        raise ValueError('Verified isolated fixture budget must be positive and <=20 USD')
    fixture_dir = os.getenv('POMPOM_ISOLATED_FIXTURE_DIR', '')
    token = os.getenv('POMPOM_ISOLATED_FIXTURE_TOKEN', '')
    if len(token) < 32 or not fixture_dir or not os.path.isdir(fixture_dir):
        raise ValueError('Isolated fixture transport requires a disposable fixture directory and token')
    path = os.path.join(fixture_dir, f'{role.lower()}.json')
    try:
        with open(path, encoding='utf-8') as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f'Missing or invalid isolated fixture for {role}') from error
    if not isinstance(value, dict):
        raise ValueError(f'Isolated fixture for {role} must be a JSON object')
    if isinstance(value.get('scenarios'), dict):
        scenario = str(context.get('objective', 'default'))
        value = value['scenarios'].get(scenario, value['scenarios'].get('default'))
        if not isinstance(value, dict):
            raise ValueError(f'Missing isolated fixture scenario for {role}')
    if isinstance(value.get('rounds'), dict):
        value = value['rounds'].get(str(context.get('roundNumber', 0)))
        if not isinstance(value, dict):
            raise ValueError(f'Missing isolated fixture round for {role}')
    if role == 'STORY_REVIEW':
        candidates = context.get('candidates') if isinstance(context.get('candidates'), list) else []
        ids = [str(item.get('candidateId')) for item in candidates if isinstance(item, dict)]
        value = {**value, 'sourceRequestId': context.get('sourceRequestId'), 'sourceFingerprint': context.get('sourceFingerprint')}
        # Preserve the authored review verdict, candidates and rationale. Never force a recommendation.
    if role == 'STORY':
        alternatives = value.get('alternatives')
        if not isinstance(alternatives, list) or not alternatives:
            raise ValueError('STORY fixture must contain alternatives')
    if role == 'BUILD_PROMPT' and not isinstance(value.get('prompt'), str):
        raise ValueError('BUILD_PROMPT fixture must contain a complete prompt')
    digest = hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    class FixtureProvider:
        saved_result_recovery = True
        last_request_started = False
        last_raw_response = ''
        last_response_metadata = {'fixture': True, 'finishReason': 'stop', 'apiStatus': 'COMPLETED'}
        last_usage = {'inputTokens': 0, 'outputTokens': 0, 'totalTokens': 0}
        def complete(self, *args, **kwargs):
            self.last_request_started = True
            with open(os.path.join(fixture_dir, 'provider-trace.jsonl'), 'a', encoding='utf-8') as trace:
                trace.write(json.dumps({'role': role, 'request': json.loads(args[0]), 'response': value, 'provider': 'ISOLATED_FIXTURE', 'providerDispatched': False, 'maxCostUsd': max_cost_usd}, ensure_ascii=False) + '\n')
            self.last_raw_response = json.dumps(value, ensure_ascii=False)
            return self.last_raw_response
    provider = FixtureProvider()
    parsed = perform_role(role, text, context, provider, 'fixture-transport-v1')
    parsed.update(provider='ISOLATED_FIXTURE', calls=0, providerDispatched=False,
                  providerResponseMetadata={**provider.last_response_metadata, 'requestId': f'fixture-{digest[:16]}'},
                  usage=provider.last_usage, actualCostUsd=0.0)
    return parsed


def preview_story_request(role: str, text: str, context: dict[str, Any]) -> dict[str, Any]:
    """Compile the existing STORY request without constructing a provider."""
    if role not in {'IDEA', 'STORY', 'STORY_REVIEW'}:
        raise ValueError('Story role required')
    class Captured(Exception):
        pass
    class Capture:
        def complete(self, prompt, system='', **kwargs):
            self.prompt, self.system = prompt, system
            raise Captured()
    capture = Capture()
    try:
        perform_role(role, text, context, capture, 'PREVIEW_ONLY_NO_PROVIDER')
    except Captured:
        return {'payload': json.loads(capture.prompt), 'system': capture.system,
                'payloadBytes': len(capture.prompt.encode('utf-8')),
                'systemBytes': len(capture.system.encode('utf-8')), 'providerDispatched': False}
    raise ValueError('Story request preview did not reach request compilation')


def run_paid_role(role: str, text: str, context: dict[str, Any], max_cost_usd: float) -> dict[str, Any]:
    if role not in ROLES:
        raise ValueError('Unknown creative role')
    if os.getenv('WORKFLOW_CREATIVE_ROLES_ENABLED', 'false').lower() != 'true':
        raise ValueError('Paid creative roles are disabled; explicit scope and budget required')
    story_provider = context.get('storyProvider', 'DEEPSEEK') if role == 'STORY' else None
    if role == 'STORY' and story_provider not in {'DEEPSEEK', 'OPENAI'}:
        raise ValueError('STORY provider must be DEEPSEEK or OPENAI')
    openai_story = (role == 'STORY' and story_provider == 'OPENAI') or role == 'IDEA'
    if context.get('assessmentOnlyPolicy'):
        if role != 'STORY_REVIEW': raise ValueError('Assessment-only scope cannot generate')
        from .story_assessment import execute
        return execute(text, context, max_cost_usd)
    if context.get('storyExperiment'):
        if openai_story:
            raise ValueError('OpenAI STORY uses the standard workflow, not the legacy DeepSeek experiment contract')
        from .story_experiment import execute
        return execute(role, text, context, max_cost_usd)
    # Test-only transport. It is deliberately opt-in, requires a disposable
    # fixture directory and a per-environment token, and never constructs an
    # SDK/provider client. Production compose does not set these variables.
    if os.getenv('POMPOM_ISOLATED_ACCEPTANCE') == 'true':
        return _isolated_fixture_role(role, text, context, max_cost_usd)
    adaptive = role == 'PROMPT_OPTIMIZATION' and context.get('adaptiveVersion') == 'adaptive-creative-optimization-v3'
    capability = None
    if adaptive:
        from .creative_provider_profiles import profile
        capability = profile(context.get('providerProfileId'))
        binding = {k:v for k,v in (context.get('providerCapabilityBinding') or {}).items() if k not in {'configured','liveAvailability'}}
        if capability != binding:
            raise ValueError('Provider capability configuration changed after authorization')
    model = capability['model'] if adaptive else os.getenv(f'WORKFLOW_{role}_MODEL', '')
    if openai_story:
        model = 'gpt-6-sol'
    if context.get('storyModel') and context['storyModel'] != model:
        raise ValueError('Selected model does not match the configured supported model')
    if not model:
        raise ValueError('Explicit server model configuration required; no fallback')
    input_rate = capability['inputUsdPerMillion'] if adaptive else float(os.getenv(f'WORKFLOW_{role}_INPUT_USD_PER_MILLION', 'nan'))
    output_rate = capability['outputUsdPerMillion'] if adaptive else float(os.getenv(f'WORKFLOW_{role}_OUTPUT_USD_PER_MILLION', 'nan'))
    if openai_story:
        # Standard short-context cache-write upper bound, not an invoice claim.
        input_rate, output_rate = 2.5, 10.0
    if not all(math.isfinite(v) and v > 0 for v in (input_rate, output_rate, max_cost_usd)):
        raise ValueError('Verified server price configuration and explicit positive budget required')
    if role == 'PROMPT_OPTIMIZATION':
        from .optimization_distinctness import baseline_execution
        context = {**context, 'baselineExecution': baseline_execution(text)}
    reconstruction = role == 'PROMPT_OPTIMIZATION' and context.get('optimizationGenerationContractVersion') == 'creative-reconstruction-v2'
    plan_first = role == 'PROMPT_OPTIMIZATION' and context.get('optimizationGenerationContractVersion') == 'plan-first-v1'
    payload_bytes = len(json.dumps({'text': text, 'context': context}, ensure_ascii=False).encode('utf-8'))
    if role == 'PROMPT_OPTIMIZATION':
        from .optimization_profile_contract import generation_contract
        ownership = generation_contract(text, context)
        if ownership:
            payload_bytes += len(json.dumps({k:v for k,v in ownership.items() if k != 'baselinePromptText'}, ensure_ascii=False).encode('utf-8'))
    if plan_first:
        from .optimization_plans import plan_request_payload, response_format, SYSTEM as plan_system
        plan_payload = plan_request_payload(text,context)
        payload_bytes = len(json.dumps(plan_payload,ensure_ascii=False).encode('utf-8'))
    if reconstruction:
        from .creative_reconstruction import request_payload, response_format, generation_system
        plan_system = generation_system(context)
        plan_payload = request_payload(text, context)
        payload_bytes = len(json.dumps(plan_payload, ensure_ascii=False).encode('utf-8'))
    output_token_limit = 4000 if role in {'IDEA', 'STORY', 'STORY_REVIEW'} or plan_first or reconstruction else 2000
    if adaptive:
        output_token_limit = context['authorizedOutputTokens']
        if type(output_token_limit) is not int or not 1 <= output_token_limit <= min(4000, capability['maxOutputTokens']):
            raise ValueError('Authorized output token limit configuration is invalid')
    schema_bytes = len(json.dumps(OPTIMIZATION_RESPONSE_FORMAT).encode('utf-8')) if role == 'PROMPT_OPTIMIZATION' else 0
    if plan_first: schema_bytes = len(json.dumps(response_format(options=plan_payload['executionOptions'])).encode('utf-8'))
    if reconstruction: schema_bytes = len(json.dumps(response_format(context,text)).encode('utf-8'))
    system_bytes = len(plan_system.encode('utf-8')) if plan_first or reconstruction else 2000
    if role in {'IDEA', 'STORY', 'STORY_REVIEW'}:
        preview = preview_story_request(role, text, context)
        payload_bytes = preview['payloadBytes']
        system_bytes = preview['systemBytes'] + 1000  # framing/accounting safety margin
    upper_bound = ((payload_bytes + schema_bytes + system_bytes) * input_rate + output_token_limit * output_rate) / 1_000_000
    if payload_bytes > (64000 if adaptive else 24000) or upper_bound > max_cost_usd:
        raise ValueError('Request exceeds approved cost ceiling')
    if adaptive:
        from .creative_provider_profiles import CreativeCapabilityProvider
        if payload_bytes + schema_bytes + system_bytes + output_token_limit > min(capability['contextTokens'], 100000):
            raise ValueError('Creative request exceeds configured context limit')
        provider = CreativeCapabilityProvider(capability,output_token_limit,min(20,context.get('authorizedTimeoutSeconds',20)))
    elif openai_story:
        provider = OpenAIProvider(model=model, request_timeout=Timeout(60, connect=10))
        provider.max_completion_tokens = output_token_limit
        provider.reasoning_effort = 'none'
        provider.omit_temperature = True
        provider.client_request_id = context.get('attemptId') or uuid4().hex
    else:
        provider = DeepSeekTextProvider(model) if role == 'STORY' else OpenAIProvider(model=model)
    provider.max_output_tokens = output_token_limit
    provider.json_output = True
    try:
        result = perform_role(role, text, context, provider, model)
        if role == 'IDEA':
            result['costBasis'] = 'CONFIGURED_CONSERVATIVE_RATES: input $2.50/M, output $10/M; not invoice'
        if role == 'STORY':
            result['provider'] = story_provider.lower()
            result['storyRevisions'] = [
                {'candidateId': item.get('candidateId'),
                 'textSha256': sha256(str(item.get('text', '')).encode('utf-8')).hexdigest(),
                 'sourceIdeaDraftId': context.get('sourceIdeaDraftId'),
                 'sourceIdeaRevision': context.get('sourceIdeaRevision'),
                 'sourceSessionId': context.get('sourceSessionId')}
                for item in result['result']['alternatives'] if isinstance(item, dict)]
        if role in {'IDEA', 'PROMPT_OPTIMIZATION', 'STORY', 'STORY_REVIEW'}:
            result['actualCostUsd'] = _verified_optimization_cost(result.get('usage'), input_rate, output_rate, max_cost_usd)
            if role in {'IDEA', 'STORY', 'STORY_REVIEW'}:
                result.update(providerDispatched=True, evidenceType='MACHINE_REVIEW' if role == 'STORY_REVIEW' else 'MODEL_GENERATION',
                              rawProviderResponse=getattr(provider, 'last_raw_response', None),
                              providerRequest=getattr(provider, 'last_request', None),
                              providerApiResponse=getattr(provider, 'last_provider_response', None),
                              requestedModel=model,
                              returnedModel=(result.get('providerResponseMetadata') or {}).get('model'))
                if role == 'STORY' and openai_story:
                    result['costBasis'] = 'CONFIGURED_CONSERVATIVE_RATES: input $2.50/M, output $10/M; not invoice'
                    if result['returnedModel'] != model:
                        raise ValueError('OpenAI STORY returned an unexpected model identity')
                    if result['providerResponseMetadata'].get('finishReason') != 'stop':
                        raise ValueError('OpenAI STORY response is incomplete; no automatic retry')
                if result['usage'].get('completion_tokens', result['usage'].get('output_tokens', 0)) > output_token_limit:
                    raise ValueError('Story role exceeded the configured output-token limit')
            if reconstruction:
                result['result']['improvementMetrics']['providerCostUsd'] = result['actualCostUsd']
    except Exception as error:
        if role in {'IDEA', 'STORY', 'STORY_REVIEW'}:
            response_metadata = getattr(provider, 'last_response_metadata', None) or {}
            raw = getattr(provider, 'last_raw_response', None)
            usage = getattr(provider, 'last_usage', None)
            response_returned = raw is not None or getattr(provider, 'last_provider_response', None) is not None
            actual_cost = None
            usage_error = None
            if response_returned:
                try:
                    actual_cost = _optimization_cost(usage, input_rate, output_rate)
                    if actual_cost > max_cost_usd:
                        usage_error = 'Actual provider cost exceeded the authorized cost ceiling'
                except ValueError as cost_error:
                    usage_error = str(cost_error)
            detail = usage_error or (str(error) if isinstance(error, ValueError) else 'Provider response processing failed.')
            diagnostics = {
                'category': 'PROVIDER_RESULT_REJECTED' if response_returned else _provider_failure_category(error),
                'provider': story_provider.lower() if role == 'STORY' else ROLES[role], 'model': model,
                'providerDispatched': bool(getattr(provider, 'last_request_started', False)),
                'providerResponseReturned': response_returned,
                'providerRequestId': response_metadata.get('requestId'),
                'finishReason': response_metadata.get('finishReason'),
                'usage': usage, 'tokenUsage': _safe_usage_summary(usage),
                'actualCostUsd': actual_cost, 'approvedCostCeilingUsd': max_cost_usd,
                'candidatesSaved': False, 'retrySafe': False,
                'retryRequiresOperatorAuthorization': False,
                'validationError': detail, 'usageError': usage_error,
                'rawProviderResponse': raw,
                'providerApiResponse': getattr(provider, 'last_provider_response', None),
                'providerRequest': getattr(provider, 'last_request', None),
                'providerError': getattr(provider, 'last_error', None),
                'attemptId': context.get('attemptId'),
            }
            logger.warning(
                'Creative story role rejected role=%s attempt_id=%s provider_dispatched=%s response_returned=%s request_id=%s',
                role, context.get('attemptId', 'unassigned'), diagnostics['providerDispatched'],
                response_returned, diagnostics['providerRequestId'] or 'unavailable',
            )
            raise CreativeRoleFailure(detail, diagnostics) from error
        if role == 'PROMPT_OPTIMIZATION':
            response_metadata = getattr(provider, 'last_response_metadata', None)
            provider_response_returned = (
                isinstance(response_metadata, dict) and response_metadata.get('apiStatus') == 'COMPLETED'
            )
            usage = getattr(provider, 'last_usage', None)
            actual_cost = None
            usage_error = None
            if provider_response_returned:
                try:
                    actual_cost = _optimization_cost(usage, input_rate, output_rate)
                    if actual_cost > max_cost_usd:
                        usage_error = 'Actual provider cost exceeded the authorized cost ceiling'
                except ValueError as cost_error:
                    usage_error = str(cost_error)
            category = (
                'COST_CEILING_EXCEEDED' if usage_error and 'exceeded' in usage_error.lower()
                else 'PROVIDER_USAGE_MISSING' if usage_error
                else _optimization_validation_category(error) if provider_response_returned
                else _provider_failure_category(error)
            )
            detail = usage_error if usage_error else (str(error) if isinstance(error,ValueError) else 'Provider response processing failed; inspect the correlated diagnostic.') if provider_response_returned else _provider_failure_detail(error)
            diagnostics = {
                'category': category,
                'provider': capability['provider'] if adaptive else 'openai',
                'model': model,
                'providerDispatched': provider_response_returned or bool(getattr(provider, 'last_request_started', False)),
                'providerResponseReturned': provider_response_returned,
                'providerRequestId': response_metadata.get('requestId') if isinstance(response_metadata, dict) else None,
                'finishReason': response_metadata.get('finishReason') if isinstance(response_metadata, dict) else None,
                'tokenUsage': _safe_usage_summary(usage),
                'actualCostUsd': actual_cost,
                'approvedCostCeilingUsd': max_cost_usd,
                'candidatesSaved': False,
                'retrySafe': False,
                'retryRequiresOperatorAuthorization': True,
                'validationError': detail,
                'usageError': usage_error,
                'attemptId': context.get('attemptId'),
                'providerResultForRecovery': getattr(provider, 'last_role_result', None),
                'rawProviderResponse': getattr(provider, 'last_raw_response', None),
                'profileValidation': getattr(error, 'profile_validation', None),
                'profileValidations': [c.get('profileValidation') for c in (getattr(provider, 'last_normalized_role_result', {}) or {}).get('candidates', [])],
            }
            logger.warning(
                "Creative role attempt rejected category=%s attempt_id=%s provider_dispatched=true response_returned=%s provider_request_id=%s",
                category, context.get('attemptId', 'unassigned'), provider_response_returned,
                diagnostics['providerRequestId'] or 'unavailable',
            )
            raise CreativeRoleFailure(detail, diagnostics) from error
        if role == 'BUILD_PROMPT':
            raw = getattr(provider,'last_raw_response',None)
            received = isinstance(raw,str) and bool(raw.strip())
            failure={'role':role,'provider':'openai','model':model,'attemptState':'PROVIDER_RESULT_REJECTED' if received else 'PROVIDER_OUTCOME_UNKNOWN',
                     'validationStatus':'REJECTED' if received else 'UNKNOWN',
                     'attemptDiagnostics':{'error':str(error) if isinstance(error,ValueError) else 'Provider response processing failed.' if received else 'Provider outcome is unknown.',
                       'exceptionType':type(error).__name__,'providerOutcome':'RECEIVED' if received else 'UNKNOWN','retryAutomatically':False},
                     'providerResponseMetadata':getattr(provider,'last_response_metadata',None)}
            if received: failure.update(rejectedProviderResponse=raw,calls=1,usage=getattr(provider,'last_usage',None))
            logger.warning("Creative build rejected exception_type=%s response_returned=%s",type(error).__name__,received)
            return failure
        raise
    if adaptive:
        result['provider']=capability['provider']
        result['providerCapabilityProfile']=capability
        result['costBasis']='CONFIGURED_CONSERVATIVE_PRICE_UPPER_BOUND; provider billing may discount cache/off-peak'
    result['costUpperBoundUsd'] = upper_bound
    result['approvedCostCeilingUsd'] = max_cost_usd
    return result
